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
"""Render feature layers from SC2 Observation protos into numpy arrays."""
# pylint: disable=g-complex-comprehension

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from collections import namedtuple
import pyfactorio
from pyfactorio.api.entities import Entities, Trees
import random

import enum
import numpy as np
import six

# from pyfactorio.render import actions
from pyfactorio.render import colors
from pyfactorio.render import named_array
from pyfactorio.render import point
from pyfactorio.render import static_data
from pyfactorio.render import stopwatch
from pyfactorio.render import transform

sw = stopwatch.sw

EPSILON = 1e-5


class FeatureType(enum.Enum):
    SCALAR = 1
    CATEGORICAL = 2


class PlayerRelative(enum.IntEnum):
    """The values for the `player_relative` feature layers."""

    NONE = 0
    SELF = 1
    NEUTRAL = 2
    ENEMY = 3


class Visibility(enum.IntEnum):
    """Values for the `visibility` feature layers."""

    HIDDEN = 0
    SEEN = 1
    VISIBLE = 2


class ScoreCumulative(enum.IntEnum):
    """Indices into the `score_cumulative` observation."""

    score = 0
    science_used = 1
    rockets_launched = 2
    total_buildings = 3
    killed_units = 4
    destroyed_buildings = 5

    collected_iron = 6
    collected_copper = 7
    collected_stone = 8
    collected_coal = 9
    collected_uranium = 10
    collected_oil = 11

    collection_rate_iron = 12
    collection_rate_copper = 13
    collection_rate_stone = 14
    collection_rate_coal = 15
    collection_rate_uranium = 16
    collection_rate_oil = 17

    used_iron = 18
    used_copper = 19
    used_stone = 20
    used_coal = 21
    used_uranium = 22
    used_oil = 23

    total_power_usage_ratio = 24


class ScoreByCategory(enum.IntEnum):
    """Indices for the `score_by_category` observation's first dimension."""

    total_used_iron = 1
    total_used_copper = 2
    total_used_stone = 3
    total_used_coal = 4
    total_used_uranium = 5
    total_used_oil = 6
    total_rockets_launched = 7
    total_red_science_consumed = 8
    total_green_science_used = 8


class ScoreCategories(enum.IntEnum):
    """Indices for the `score_by_category` observation's second dimension."""

    none = 0
    army = 1
    economy = 2
    technology = 3
    upgrade = 4


class ScoreByVital(enum.IntEnum):
    """Indices for the `score_by_vital` observation's first dimension."""

    total_damage_dealt = 0
    total_damage_taken = 1
    total_enemies_killed = 2
    total_deaths = 3
    total_healed = 4
    total_buildings_built = 5
    total_iron_used = 6


class ScoreVitals(enum.IntEnum):
    """Indices for the `score_by_vital` observation's second dimension."""

    life = 0
    shields = 1
    energy = 2


class Player(enum.IntEnum):
    """Indices into the `player` observation."""

    player_id = 0
    deaths = 1
    kills = 2
    health = 3
    shield = 4
    energy = 5


class UnitLayer(enum.IntEnum):
    """Indices into the unit layers in the observations."""

    unit_type = 0
    health = 1


class UnitCounts(enum.IntEnum):
    """Indices into the `unit_counts` observations."""

    unit_type = 0
    count = 1


class FeatureUnit(enum.IntEnum):
    """Indices for the `feature_unit` observations."""

    unit_type = 0
    health = 1
    shield = 2
    energy = 3
    health_ratio = 4
    shield_ratio = 5
    energy_ratio = 6
    x = 7
    y = 8
    facing = 9
    walking = 10
    reach_radius = 11
    is_powered = 12
    is_on_screen = 13
    character_mining_progress = (14,)
    in_combat = (15,)
    character_running_speed = (16,)
    selected = (17,)


Observation = namedtuple("Observation", [
    "tick",
    "player_x",
    "player_y",
    "features",
])

class Feature(
    collections.namedtuple(
        "Feature",
        ["index", "name", "layer_set", "full_name", "scale", "type", "palette", "clip"],
    )
):
    """Define properties of a feature layer.

    Attributes:
      index: Index of this layer into the set of layers.
      name: The name of the layer within the set.
      layer_set: Which set of feature layers to look at in the observation proto.
      full_name: The full name including for visualization.
      scale: Max value (+1) of this layer, used to scale the values.
      type: A FeatureType for scalar vs categorical.
      palette: A color palette for rendering.
      clip: Whether to clip the values for coloring.
    """

    __slots__ = ()

    @sw.decorate
    def color(self, plane):
        if self.clip:
            plane = np.clip(plane, 0, self.scale - 1)
        return self.palette[plane]


class ScreenFeatures(
    collections.namedtuple(
        "ScreenFeatures",
        [
            # "water_ore",
            # "cliff_ore",
            # "rock_ore",
            # "tree_ore",
            "iron_ore",
            "copper_ore",
            "oil",
            # "uranium_ore",
            "coal",
            "stone_ore",
            # "player_id",
            # "items",
            "entity_type",
            # "powered",
            # "selected",
            "entity_health_map",
            "entity_health_ratio_map",
            # "buildable",
            # "mineable"
        ],
    )
):
    """The set of screen feature layers."""

    __slots__ = ()

    def __new__(cls, **kwargs):
        feats = {}
        for name, (scale, type_, palette, clip) in six.iteritems(kwargs):
            feats[name] = Feature(
                index=ScreenFeatures._fields.index(name),
                name=name,
                layer_set="renders",
                full_name="screen " + name,
                scale=scale,
                type=type_,
                palette=palette(scale) if callable(palette) else palette,
                clip=clip,
            )
        return super(ScreenFeatures, cls).__new__(
            cls, **feats
        )  # pytype: disable=missing-parameter


SCREEN_FEATURES = ScreenFeatures(
    # water_map=(2, FeatureType.CATEGORICAL, colors.blue, False),
    # cliff_map=(2, FeatureType.CATEGORICAL, colors.red * 0.8, False),
    # rock_map=(2, FeatureType.CATEGORICAL, colors.black, False),
    # tree_map=(2, FeatureType.CATEGORICAL, colors.green, False),
    iron_ore=(50000, FeatureType.SCALAR, colors.hot, False),
    copper_ore=(50000, FeatureType.SCALAR, colors.hot, False),
    oil=(256, FeatureType.SCALAR, colors.hot, False),
    # uranium_ore=(256, FeatureType.SCALAR, colors.hot, False),
    coal=(50000, FeatureType.SCALAR, colors.hot, False),
    stone_ore=(50000, FeatureType.SCALAR, colors.hot, False),
    # player_id=(17, FeatureType.CATEGORICAL, colors.PLAYER_ABSOLUTE_PALETTE, False),
    # items=(max(static_data.ITEMS) + 1, FeatureType.CATEGORICAL, colors.items, False),
    entity_type=(
        len(Entities) + 1,
        FeatureType.CATEGORICAL,
        colors.hot,
        False,
    ),
    # powered=(2, FeatureType.CATEGORICAL, colors.hot, False),
    # selected=(2, FeatureType.CATEGORICAL, colors.SELECTED_PALETTE, False),
    entity_health_map=(350, FeatureType.SCALAR, colors.hot, True),
    entity_health_ratio_map=(256, FeatureType.SCALAR, colors.hot, False),
    # buildable=(2, FeatureType.CATEGORICAL, colors.winter, False),
    # mineable=(2, FeatureType.CATEGORICAL, colors.winter, False)
)

# class MapFeatures(collections.namedtuple("MapFeatures", [
#     "visibility_map",
#     "camera",
#     "player_id",
#     "enemy_unit",
#     "iron_map",
#     "copper_map",
#     "oil_map",
#     "uranium_map",
#     "stone_map",
#     "power_coverage",
#     # "pathable",
#     # "buildable"
#     ])):
#   """The set of map feature layers."""
#   __slots__ = ()

#   def __new__(cls, **kwargs):
#     feats = {}
#     for name, (scale, type_, palette) in six.iteritems(kwargs):
#       feats[name] = Feature(
#           index=MapFeatures._fields.index(name),
#           name=name,
#           layer_set="map_renders",
#           full_name="map " + name,
#           scale=scale,
#           type=type_,
#           palette=palette(scale) if callable(palette) else palette,
#           clip=False)
#     return super(MapFeatures, cls).__new__(cls, **feats)  # pytype: disable=missing-parameter


# MAP_FEATURES = MinimapFeatures(
#     visibility_map=(4, FeatureType.CATEGORICAL, colors.VISIBILITY_PALETTE),
#     camera=(2, FeatureType.CATEGORICAL, colors.CAMERA_PALETTE),
#     player_id=(17, FeatureType.CATEGORICAL, colors.PLAYER_ABSOLUTE_PALETTE),
#     enemy_unit=(2, FeatureType.CATEGORICAL, colors.hot),

#     iron_map=(16, FeatureType.SCALAR, colors.hot),
#     copper_map=(16, FeatureType.SCALAR, colors.hot),
#     oil_map=(16, FeatureType.SCALAR, colors.hot),
#     uranium_map=(16, FeatureType.SCALAR, colors.hot),
#     coal_map=(16, FeatureType.SCALAR, colors.hot),
#     stone_map=(16, FeatureType.SCALAR, colors.hot),

#     # alerts=(2, FeatureType.CATEGORICAL, colors.winter),

#     # pathable=(2, FeatureType.CATEGORICAL, colors.winter),
#     # buildable=(2, FeatureType.CATEGORICAL, colors.winter),

#     # pollution=(8, FeatureType.SCALAR, colors.hot),
#     power_coverage=(2, FeatureType.SCALAR, colors.hot),
#     # turret_coverage=(2, FeatureType.SCALAR, colors.hot),
# )


def _to_point(dims):
    """Convert (width, height) or size -> point.Point."""
    assert dims

    if isinstance(dims, (tuple, list)):
        if len(dims) != 2:
            raise ValueError(
                "A two element tuple or list is expected here, got {}.".format(dims)
            )
        else:
            width = int(dims[0])
            height = int(dims[1])
            if width <= 0 or height <= 0:
                raise ValueError("Must specify +ve dims, got {}.".format(dims))
            else:
                return point.Point(width, height)
    else:
        size = int(dims)
        if size <= 0:
            raise ValueError("Must specify a +ve value for size, got {}.".format(dims))
        else:
            return point.Point(size, size)


class Dimensions(object):
    """Screen and minimap dimensions configuration.

    Both screen and minimap must be specified. Sizes must be positive.
    Screen size must be greater than or equal to minimap size in both dimensions.

    Attributes:
      screen: A (width, height) int tuple or a single int to be used for both.
      minimap: A (width, height) int tuple or a single int to be used for both.
    """

    def __init__(self, screen=None, minimap=None):
        if not screen:
            raise ValueError(
                "screen and minimap must both be set, screen={}, minimap={}".format(
                    screen, minimap
                )
            )

        self._screen = _to_point(screen)
        # self._minimap = _to_point(minimap)

    @property
    def screen(self):
        return self._screen

    # @property
    # def minimap(self):
    #     return self._minimap

    def __repr__(self):
        return "Dimensions(screen={})".format(self.screen)

    def __eq__(self, other):
        return (
            isinstance(other, Dimensions)
            and self.screen == other.screen
            # and self.minimap == other.minimap
        )

    def __ne__(self, other):
        return not self == other


class Features(object):
    def __init__(self, map_size=None):
        self._map_size = map_size

    @classmethod
    def unpack_obs(cls, obs):
        tick = obs[0][0]  # type: ignore
        xpos = obs[0][1]  # type: ignore
        ypos = obs[0][2]  # type: ignore
        walking = obs[0][3]  # type: ignore
        direction = obs[0][4]  # type: ignore
        incombat = obs[0][5]  # type: ignore
        shooting = obs[0][6]  # type: ignore

        entities = obs[1]  # type: ignore

        # # layers
        fm = {
            "iron_ore": [],
            "copper_ore": [],
            "coal": [],
            "stone_ore": [],
            "entity_type": [],
            # ("entity_hit_points",
            # ("entity_hit_points_ratio",
        }
        tm = []
        hm = []
        hmr = []
        et = []
        for (name, ents) in list(entities.items()):
            og_name = name.decode()
            new_name = og_name.replace("-", "_")
            es = None

            track_indivi = False
            is_tree = False

            try:
                es = fm[new_name]
                track_indivi = True
            except KeyError:
                pass

            if new_name.find("tree") >= 0:
                new_name = "trees"
                is_tree = True

            for e in ents:
                co = point.Point(e[0], e[1])
                if track_indivi is True:
                    if len(e) > 4:
                        es.append((co, e[4]))
                    else:
                        es.append((co, 1))

                if is_tree is True:
                    tm.append((co, 1))

                if is_tree is False:
                    try:
                        et.append((co, Entities[og_name]))
                    except:
                        pass

                if len(e) >= 4:
                    hm.append((co, e[2]))
                    hmr.append((co, e[3]))

                # e_xpos = e[0]
                # e_ypos = e[1]
                # e_health = e[2]
                # e_hr = e[3]
                # e[4] = custom val

            if track_indivi:
                fm[new_name] = es  # type: ignore

        fm["tree_map"] = tm
        fm["entity_health_map"] = hm
        fm["entity_health_ratio_map"] = hmr
        return Observation(tick=tick, player_x=xpos, player_y=ypos, features = fm)