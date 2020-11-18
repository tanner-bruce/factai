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
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from absl import logging

import enum

from pyfactorio import maps
from pyfactorio import run_configs
from pyfactorio.env import environment
from pyfactorio.render import features
from pyfactorio.lib import metrics
from pyfactorio.render import renderer_human
from pyfactorio.lib import run_parallel
from pyfactorio.render import stopwatch

from pyfactorio.env import controller

from threading import Thread
import os
import sched, time
import signal
import subprocess
import sys
import time

from pyfactorio.api.rcon import rcon, rconException


sw = stopwatch.sw


class Difficulty(enum.IntEnum):
  """Bot difficulties."""
  very_easy = 0
  easy = 1
  medium = 2
  medium_hard = 3
  hard = 4
  harder = 5
  very_hard = 6
  cheat_vision = 7
  cheat_money = 8
  cheat_insane = 9

# Re-export these names to make it easy to construct the environment.
Dimensions = features.Dimensions  # pylint: disable=invalid-name


class FactorioEnv(environment.Base):
  """A Factorio environment.
  The implementation details of the action and observation specs are in
  lib/features.py
  """

  def __init__(self,  # pylint: disable=invalid-name
               _only_use_kwargs=None,
               map_name=None,
               discount=1.,
               discount_zero_after_timeout=False,
               step_mul=None,
               game_steps_per_episode=None,
               score_index=None,
               score_multiplier=None,
               random_seed=None,
               disable_fog=False):
    """Create a SC2 Env.
    You must pass a resolution that you want to play at. You can send either
    feature layer resolution or rgb resolution or both. If you send both you
    must also choose which to use as your action space. Regardless of which you
    choose you must send both the screen and minimap resolutions.
    For each of the 4 resolutions, either specify size or both width and
    height. If you specify size then both width and height will take that value.
    Args:
      _only_use_kwargs: Don't pass args, only kwargs.
      map_name: Name of a SC2 map. Run bin/map_list to get the full list of
          known maps. Alternatively, pass a Map instance. Take a look at the
          docs in maps/README.md for more information on available maps.
      discount: Returned as part of the observation.
      discount_zero_after_timeout: If True, the discount will be zero
          after the `game_steps_per_episode` timeout.
      step_mul: How many game steps per agent step (action/observation). None
          means use the map default.
      save_replay_episodes: Save a replay after this many episodes. Default of 0
          means don't save replays.
      replay_dir: Directory to save replays. Required with save_replay_episodes.
      game_steps_per_episode: Game steps per episode, independent of the
          step_mul. 0 means no limit. None means use the map default.
      score_index: -1 means use the win/loss reward, >=0 is the index into the
          score_cumulative with 0 being the curriculum score. None means use
          the map default.
      score_multiplier: How much to multiply the score by. Useful for negating.
      random_seed: Random number seed to use when initializing the game. This
          lets you run repeatable games/tests.
      disable_fog: Whether to disable fog of war.
    Raises:
      ValueError: if too many players are requested for a map.
      ValueError: if the resolutions aren't specified correctly.
    """
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    # TODO TB - load save game here
    map_inst = maps.get(map_name)
    self._map_name = map_name

    self._discount = discount
    self._step_mul = step_mul or map_inst.step_mul
    self._save_replay_episodes = save_replay_episodes
    self._replay_dir = replay_dir
    self._random_seed = random_seed
    self._disable_fog = disable_fog
    self._discount_zero_after_timeout = discount_zero_after_timeout

    if score_index is None:
      self._score_index = map_inst.score_index
    else:
      self._score_index = score_index
    if score_multiplier is None:
      self._score_multiplier = map_inst.score_multiplier
    else:
      self._score_multiplier = score_multiplier

    self._episode_length = game_steps_per_episode
    if self._episode_length is None:
      self._episode_length = map_inst.game_steps_per_episode

    self._run_config = run_configs.get()
    self._parallel = run_parallel.RunParallel()  # Needed for multiplayer.

    # TODO TB launch game here
    self._launch_sp(map_inst, interfaces[0])
    self._finalize(interfaces, visualize)

  def _launch_game(self):
      def runner():
        args = [
            "E:/SteamLibrary/steamapps/common/Factorio/bin/x63/Factorio.exe",
            "--rcon-bind=127.0.0.1:9889",
            "--rcon-password=pass",
            "--start-server=sb.zip",
            "--config=E:/programming/factorio/factai/run/config.ini",
        ]
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd="run"
        )
        self._proc = process
        while True:
            output = self._proc.stdout.readline()
            if output == b"" and process.poll() is not None:
                break
            if output:
                out = output.decode()
                is_ready = "joined the game"
                if out.find(is_ready) >= -1:
                    self._ready = True

                print(out, end="")
      thread = Thread(target=self._run_headless_server, args=(1,))
      thread.start()

      while self._ready is False:
          time.sleep(0.25)
      time.sleep(0)
      print("rcon ready")
      self._controller = controller.FactorioController()

  def _finalize(self, interfaces, visualize):
    game_info = self._controller.game_info()

    # self._features = features.features_from_game_info(game_info=game_info)
    # static_data = self._controller.data()

    self._renderer_human = renderer_human.RendererHuman()
    self._renderer_human.init(game_info, static_data)

    self._metrics = metrics.Metrics("this doesnt exist")
    self._metrics.increment_instance()

    self._last_score = None
    self._total_steps = 0
    self._episode_steps = 0
    self._episode_count = 0
    self._obs = None
    self._state = environment.StepType.LAST  # Want to jump to `reset`.
    # TODO TB - use seed
    logging.info("Environment is ready on map: %s", "factorio")

  def observation_spec(self):
    """Look at Features for full specs."""
    return tuple(f.observation_spec() for f in self._features)

  def action_spec(self):
    """Look at Features for full specs."""
    return tuple(f.action_spec() for f in self._features)

  def _restart(self):
    self._controller.restart()

  @sw.decorate
  def reset(self):
    """Start a new episode."""
    self._episode_steps = 0
    if self._episode_count:
      # No need to restart for the first episode.
      self._restart()

    self._episode_count += 1
    logging.info("Starting episode: %s", self._episode_count)
    self._metrics.increment_episode()

    self._last_score = [0] * self._num_agents
    self._state = environment.StepType.FIRST
    return self._step()

  @sw.decorate("step_env")
  def step(self, actions):
    """Apply actions, step the world forward, and return observations."""
    if self._state == environment.StepType.LAST:
      return self.reset()

    obs = self._controller.act(actions)

    self._state = environment.StepType.MID
    return self._step()

  def _step(self):
    with self._metrics.measure_step_time(self._step_mul):
      self._parallel.run((c.step, self._step_mul) for c in self._controller)

    with self._metrics.measure_observation_time():
      self._obs = self._parallel.run(c.observe for c in self._controller)
      agent_obs = [f.transform_obs(o) for f, o in zip(
          self._features, self._obs)]

    # TODO TB - vectorize reward outcome here
    outcome = [0] * self._num_agents
    discount = self._discount
    # if self._score_index >= 0:  # Game score, not win/loss reward.
    #   cur_score = [o["score_cumulative"][self._score_index] for o in agent_obs]
    #   if self._episode_steps == 0:  # First reward is always 0.
    #     reward = [0] * self._num_agents
    #   else:
    #     reward = [cur - last for cur, last in zip(cur_score, self._last_score)]
    #   self._last_score = cur_score

    self._renderer_human.render(self._obs[0])
    cmd = self._renderer_human.get_actions(
        self._run_config, self._controller)
    # if cmd == renderer_human.ActionCmd.STEP:
    #   pass
    # elif cmd == renderer_human.ActionCmd.RESTART:
    #   self._state = environment.StepType.LAST
    elif cmd == renderer_human.ActionCmd.QUIT:
      raise KeyboardInterrupt("Quit?")

    self._total_steps += self._step_mul
    self._episode_steps += self._step_mul

    def zero_on_first_step(value):
      return 0.0 if self._state == environment.StepType.FIRST else value
    return tuple(environment.TimeStep(
        step_type=self._state,
        reward=zero_on_first_step(r * self._score_multiplier),
        discount=zero_on_first_step(discount),
        observation=o) for r, o in zip(reward, agent_obs))

  def close(self):
    logging.info("Environment Close")
    if hasattr(self, "_metrics") and self._metrics:
      self._metrics.close()
      self._metrics = None
    if hasattr(self, "_renderer_human") and self._renderer_human:
      self._renderer_human.close()
      self._renderer_human = None

    # Don't use parallel since it might be broken by an exception.
    if hasattr(self, "_controller") and self._controller:
    self._controller.quit()
    self._controller = None
