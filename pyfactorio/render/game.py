# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A viewer for starcraft observations/replays."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import ctypes
import functools
import itertools
import math
import os
import platform

from pyfactorio.render.point import Rect
from pyfactorio.env.controller import DisplayInfo, FactorioController
from pyfactorio.util import get_desktop_size
import threading
import time

from pyfactorio.render import colors, features, point, stopwatch, transform
from pyfactorio.render.surface import Surface

# from pyfactorio.render import point
# from pyfactorio.render import memoize
# from pyfactorio.render import stopwatch
# from pyfactorio.render import features

import enum
import numpy as np
import pygame
import queue

# Disable attribute-error because of the multiple stages of initialization for
# RendererHuman.
# pytype: disable=attribute-error

sw = stopwatch.sw

render_lock = threading.Lock()  # Serialize all window/render operations.


def with_lock(lock):
    """Make sure the lock is held while in this function."""

    def decorator(func):
        @functools.wraps(func)
        def _with_lock(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)

        return _with_lock

    return decorator


def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


class MouseButtons(enum.IntEnum):
    # https://www.pygame.org/docs/ref/mouse.html
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    WHEEL_UP = 4
    WHEEL_DOWN = 5


class SurfType(enum.IntEnum):
    """Used to tell what a mouse click refers to."""

    CHROME = 1  # ie help, feature layer titles, etc
    SCREEN = 2
    BIGMAP = 4
    FEATURE = 8
    RGB = 16


class ActionCmd(enum.Enum):
    STEP = 1
    RESTART = 2
    QUIT = 3


class RendererHuman(object):
    """Render factorio feature maps"""

    camera_actions = {  # camera moves by 3 world units.
        pygame.K_LEFT: point.Point(-3, 0),
        pygame.K_RIGHT: point.Point(3, 0),
        pygame.K_UP: point.Point(0, 3),
        pygame.K_DOWN: point.Point(0, -3),
    }

    cmd_group_keys = {
        pygame.K_0: 0,
        pygame.K_1: 1,
        pygame.K_2: 2,
        pygame.K_3: 3,
        pygame.K_4: 4,
        pygame.K_5: 5,
        pygame.K_6: 6,
        pygame.K_7: 7,
        pygame.K_8: 8,
        pygame.K_9: 9,
    }

    shortcuts = [
        ("F1", "Select idle worker"),
        ("F2", "Select army"),
        ("F3", "Select larva (zerg) or warp gates (protoss)"),
        ("F4", "Quit the game"),
        ("F5", "Restart the map"),
        ("F8", "Save a replay"),
        ("F9", "Toggle RGB rendering"),
        ("F10", "Toggle rendering the player_relative layer."),
        ("F11", "Toggle synchronous rendering"),
        ("F12", "Toggle raw/feature layer actions"),
        ("Ctrl++", "Zoom in"),
        ("Ctrl+-", "Zoom out"),
        ("PgUp/PgDn", "Increase/decrease the max game speed"),
        ("Ctrl+PgUp/PgDn", "Increase/decrease the step multiplier"),
        ("Pause", "Pause the game"),
        ("?", "This help screen"),
    ]

    upgrade_colors = [
        colors.black,  # unused...
        colors.white * 0.6,
        colors.white * 0.8,
        colors.white,
    ]

    def __init__(
        self,
        fps=60,
        step_mul=1,
        render_sync=False,
        render_feature_grid=True,
        video=None,
    ):
        """Create a renderer for use by humans.

        Make sure to call `init` with the game info, or just use `run`.

        Args:
          fps: How fast should the game be run.
          step_mul: How many game steps to take per observation.
          render_sync: Whether to wait for the obs to render before continuing.
          render_feature_grid: When RGB and feature layers are available, whether
              to render the grid of feature layers.
          video: A filename to write the video to. Implicitly enables render_sync.
        """
        self._fps = fps
        self._step_mul = step_mul
        self._render_sync = render_sync or bool(video)
        self._render_rgb = None
        self._render_feature_grid = render_feature_grid
        self._window = None
        self._window_scale = 0.75
        self._obs_queue = queue.Queue()
        self._render_thread = threading.Thread(
            target=self.render_thread, name="Renderer"
        )
        self._render_thread.start()
        self._game_times = collections.deque(
            maxlen=100
        )  # Avg FPS over 100 frames.  # pytype: disable=wrong-keyword-args
        self._render_times = collections.deque(
            maxlen=100
        )  # pytype: disable=wrong-keyword-args
        self._last_time = time.time()
        self._last_game_loop = 0
        self._name_lengths = {}
        self._feature_screen_px: point.Point = None
        self._obs: features.Observation = None

    def close(self):
        if self._obs_queue:
            self._obs_queue.put(None)
            self._render_thread.join(timeout=1)
            self._obs_queue = None
            self._render_thread = None

    def init(self, game_info, di):
        """Take the game info and the static data needed to set up the game.

        This must be called before render or get_actions for each game or restart.

        Args:
          game_info: A `sc_pb.ResponseGameInfo` object for this game.
          static_data: A `StaticData` object for this game.

        Raises:
          ValueError: if there is nothing to render.
        """
        self._game_info = game_info
        self._di = di
        # self._map_size = point.Point.build(game_info.map_size)
        try:
            self.init_window(di)
            self._initialized = True
        except pygame.error as e:
            self._initialized = False
            print("-" * 60)
            print("Failed to initialize pygame: %s", e)
            print("Continuing without pygame.")
            print("If you're using ssh and have an X server, try ssh -X.")
            print("-" * 60)

        self._queued_action = None
        self._queued_hotkey = ""
        self._select_start = None
        self._alerts = {}
        self._past_actions = []
        self._help = False
        self._last_zoom_time = 0

    @with_lock(render_lock)
    @sw.decorate
    def init_window(self, di: DisplayInfo):
        """Initialize the pygame window and lay out the surfaces."""
        if platform.system() == "Windows":
            # Enable DPI awareness on Windows to give the correct window size.
            ctypes.windll.user32.SetProcessDPIAware()  # pytype: disable=module-attr

        pygame.init()

        main_screen_px = di.camera_world_space_dims * 0.5
        self._feature_screen_px = di.camera_world_space_dims

        feature_cols = 0
        feature_rows = 0

        window_size_ratio = main_screen_px
        num_feature_layers = 9
        if num_feature_layers > 0:
            feature_cols = math.ceil(math.sqrt(num_feature_layers))
            feature_rows = math.ceil(num_feature_layers / feature_cols)
            features_layout = point.Point(
                feature_cols, feature_rows * 1.05
            )  # Make room for titles.

            # Scale features_layout to main_screen_px height so we know its width.
            features_aspect_ratio = (
                features_layout * main_screen_px.y / features_layout.y
            )
            window_size_ratio += point.Point(features_aspect_ratio.x, 0)

        window_size_px = window_size_ratio.scale_max_size(
            get_desktop_size() * self._window_scale
        ).ceil()

        # Create the actual window surface. This should only be blitted to from one
        # of the sub-surfaces defined below.
        self._window = pygame.display.set_mode(window_size_px, 0, 32)
        pygame.display.set_caption("FactAI Viewer")

        # The sub-surfaces that the various draw functions will draw to.
        self._surfaces = []

        def add_surface(surf_type, surf_loc, world_to_surf, di: DisplayInfo, draw_fn):
            """Add a surface. Drawn in order and intersect in reverse order."""
            sub_surf = self._window.subsurface(pygame.Rect(surf_loc.tl, surf_loc.size))
            self._surfaces.append(
                Surface(sub_surf, surf_type, surf_loc, world_to_surf, di, draw_fn)
            )

        self._scale = window_size_px.y // 32
        self._font_small = pygame.font.Font(None, int(self._scale * 0.5))
        self._font_large = pygame.font.Font(None, self._scale)

        # Renderable space for the screen.
        screen_size_px = main_screen_px.scale_max_size(window_size_px)

        # add_surface(SurfType.FEATURE | SurfType.SCREEN,
        #             point.Rect(point.origin, screen_size_px),
        #             transform.Chain(  # surf
        #                 self._world_to_feature_screen,
        #                 feature_screen_to_main_screen),
        #             self._world_to_feature_screen_px,
        #             self.draw_screen)

        if num_feature_layers > 0:
            # Add the raw and feature layers
            features_loc = point.Point(screen_size_px.x, 0)
            feature_pane = self._window.subsurface(
                pygame.Rect(features_loc, window_size_px - features_loc)
            )
            feature_pane.fill(colors.white / 2)
            feature_pane_size = point.Point(*feature_pane.get_size())
            feature_grid_size = feature_pane_size / point.Point(
                feature_cols, feature_rows
            )
            feature_layer_area = point.Point(1, 1).scale_max_size(feature_grid_size)
            feature_layer_padding = feature_layer_area // 20
            feature_layer_size = feature_layer_area - feature_layer_padding * 2

            feature_font_size = int(feature_grid_size.y * 0.09)
            feature_font = pygame.font.Font(None, feature_font_size)

            feature_counter = itertools.count()

            def add_layer(surf_type, name, world_to_surf, fn):
                """Add a layer surface."""
                i = next(feature_counter)
                grid_offset = (
                    point.Point(i % feature_cols, i // feature_cols) * feature_grid_size
                )
                text = feature_font.render(name, True, colors.white)
                rect = text.get_rect()
                rect.center = grid_offset + point.Point(
                    feature_grid_size.x / 2, feature_font_size
                )
                feature_pane.blit(text, rect)
                surf_loc = (
                    features_loc
                    + grid_offset
                    + feature_layer_padding
                    + point.Point(0, feature_font_size)
                )
                add_surface(
                    surf_type,
                    point.Rect(surf_loc, surf_loc + feature_layer_size).round(),
                    world_to_surf,
                    di,
                    fn,
                )

            def add_feature_layer(feature, surf_type, world_to_surf):
                add_layer(
                    surf_type,
                    feature.full_name,
                    world_to_surf,
                    lambda surf: self.draw_feature_layer(surf, feature),
                )

            feature_screen_to_feature_screen_surf = transform.Linear(
                feature_layer_size / self._feature_screen_px
            )

            # (78.5, 33.5) -> (0, 0)
            # normalize_to_origin = transform.Linear(offset=player_pos-di.camera_tl_player_offset_dims)

            # 0 - 114
            # ->
            # 0 - width_of_surface
            camera_to_feature = transform.Linear(
                scale=di.screen_dims / di.camera_world_space_dims
            )

            chain = transform.Chain(
                # normalize_to_origin,
                camera_to_feature,
                feature_screen_to_feature_screen_surf,
                transform.PixelToCoord(),
            )

            for feature in features.SCREEN_FEATURES:
                add_feature_layer(feature, SurfType.FEATURE | SurfType.SCREEN, chain)

    @sw.decorate
    def get_actions(self, controller: FactorioController):
        """Get actions from the UI, apply to controller, and return an ActionCmd."""
        if not self._initialized:
            return ActionCmd.STEP

        for event in pygame.event.get():
            ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
            # shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
            # alt = pygame.key.get_mods() & pygame.KMOD_ALT
            if event.type == pygame.QUIT:
                return ActionCmd.QUIT
            elif event.type == pygame.KEYDOWN:
                if self._help:
                    self._help = False
                elif event.key in (pygame.K_QUESTION, pygame.K_SLASH):
                    self._help = True
                elif event.key == pygame.K_PAUSE:
                    pause = True
                    while pause:
                        time.sleep(0.1)
                        for event2 in pygame.event.get():
                            if event2.type == pygame.KEYDOWN:
                                if event2.key in (pygame.K_PAUSE, pygame.K_ESCAPE):
                                    pause = False
                                elif event2.key == pygame.K_F4:
                                    return ActionCmd.QUIT
                                elif event2.key == pygame.K_F5:
                                    return ActionCmd.RESTART
                elif event.key == pygame.K_F4:
                    return ActionCmd.QUIT
                elif event.key == pygame.K_F5:
                    return ActionCmd.RESTART
                elif event.key == pygame.K_F11:  # Toggle synchronous rendering.
                    self._render_sync = not self._render_sync
                    print("Rendering", self._render_sync and "Sync" or "Async")
                elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                    if ctrl:
                        if event.key == pygame.K_PAGEUP:
                            self._step_mul += 1
                        elif self._step_mul > 1:
                            self._step_mul -= 1
                        print("New step mul:", self._step_mul)
                    else:
                        self._fps *= 1.25 if event.key == pygame.K_PAGEUP else 1 / 1.25
                        print("New max game speed: %.1f" % self._fps)
        return ActionCmd.STEP

    @sw.decorate
    def draw_feature_layer(self, surf: Surface, feature):
        """Draw a feature layer."""
        layer = None
        surf.surf.fill(colors.black)
        try:
            layer = self._obs.features[
                feature.name
            ]  # feature.unpack(self._obs.observation)
            if len(layer) == 0:
                return
        except:
            return
        surf.set_pos(point.Point(self._obs.player_x, self._obs.player_y))

        for (k, v) in layer:
            surf.draw_rect_pts(colors.red, k, k + 1, 3)
            # surf.draw_circle(colors.red, k, 1, 1)

        # if layer is not None:
        # surf.blit_np_array(feature.color(layer))
        # else:
        # surf.surf.fill(colors.black)

    def all_surfs(self, fn, *args, **kwargs):
        for surf in self._surfaces:
            if surf.world_to_surf:
                fn(surf, *args, **kwargs)

    def render_thread(self):
        """A render loop that pulls observations off the queue to render."""
        obs = True
        while obs:  # Send something falsy through the queue to shut down.
            obs = self._obs_queue.get()
            if obs is None:
                self._obs_queue.task_done()
                return 
            if obs:
                # for alert in obs.observation.alerts:
                # self._alerts[sc_pb.Alert.Name(alert)] = time.time()
                # for err in obs.action_errors:
                # if err.result != sc_err.Success:
                # self._alerts[sc_err.ActionResult.Name(err.result)] = time.time()

                # TODO TB prepare actions DO IT MAN

                if self._obs_queue.empty():
                    # Only render the latest observation so we keep up with the game.
                    self.render_obs(obs)
            self._obs_queue.task_done()

    @sw.decorate
    def render(self, obs):
        """Push an observation onto the queue to be rendered."""
        if not self._initialized:
            return
        now = time.time()
        self._last_time = now
        # self._last_game_loop = self._obs.observation.game_loop
        self._obs_queue.put(obs)
        if self._render_sync:
            self._obs_queue.join()

    @with_lock(render_lock)
    @sw.decorate
    def render_obs(self, obs):
        # TODO TB - render_obs where all the work happens
        """Render a frame given an observation."""
        start_time = time.time()
        self._obs = obs

        if obs is None:
            return

        for surf in self._surfaces:
            surf.draw(surf)

        # mouse_pos = self.get_mouse_pos()
        # if mouse_pos:
        #   # Draw a small mouse cursor
        #   self.all_surfs(_Surface.draw_circle, colors.green, mouse_pos.world_pos,
        #                  0.1)

        with sw("flip"):
            pygame.display.flip()

        self._render_times.append(time.time() - start_time)
