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

import logging
import enum

from pyfactorio.env import environment
from pyfactorio.render.features import Features
from pyfactorio.render import metrics
from pyfactorio.render import stopwatch
from pyfactorio.render.game import RendererHuman, ActionCmd

from pyfactorio.env import controller

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

class FactorioEnv(environment.Base):
  def __init__(self,  # pylint: disable=invalid-name
               _only_use_kwargs=None,
               map_name=None,
               discount=1.,
               discount_zero_after_timeout=False,
               step_mul=None,
               game_steps_per_episode=None,
               random_seed=None,
               disable_fog=False):
    if _only_use_kwargs:
      raise ValueError("All arguments must be passed as keyword arguments.")

    # TODO TB - load save game here
    self._map_name = map_name

    self._discount = discount
    self._step_mul = step_mul
    self._random_seed = random_seed
    self._disable_fog = disable_fog
    self._discount_zero_after_timeout = discount_zero_after_timeout

    self._episode_length = game_steps_per_episode or 0

    self._controller = controller.FactorioController()
    self._finalize()

  def _finalize(self):
    game_info = self._controller.game_info()

    # self._features = features.features_from_game_info(game_info=game_info)
    # static_data = self._controller.data()

    self._renderer_human = RendererHuman()
    self._renderer_human.init(game_info)

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
    return tuple()
    # return tuple(f.observation_spec() for f in self._features)

  def action_spec(self):
    """Look at Features for full specs."""
    return tuple()
    # return tuple(f.action_spec() for f in self._features)

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

    self._last_score = 0
    self._state = environment.StepType.FIRST
    return self._step()

  @sw.decorate("step_env")
  def step(self, actions):
    """Apply actions, step the world forward, and return observations."""
    if self._state == environment.StepType.LAST:
      return self.reset()

    self._controller.act(actions)
    self._state = environment.StepType.MID
    return self._step()

  def _step(self):
    self._raw_obs = self._controller.step()
    self._obs = Features.unpack_observation(self._raw_obs)

    # TODO TB - vectorize reward outcome here
    discount = self._discount
    # if self._score_index >= 0:  # Game score, not win/loss reward.
    #   cur_score = [o["score_cumulative"][self._score_index] for o in agent_obs]
    #   if self._episode_steps == 0:  # First reward is always 0.
    #     reward = [0] * self._num_agents
    #   else:
    #     reward = [cur - last for cur, last in zip(cur_score, self._last_score)]
    #   self._last_score = cur_score

    self._renderer_human.render(self._obs)
    cmd = self._renderer_human.get_actions(self._controller)
    if cmd == ActionCmd.STEP:
      pass
    elif cmd == ActionCmd.RESTART:
      self._state = environment.StepType.LAST
    elif cmd == ActionCmd.QUIT:
      raise KeyboardInterrupt("Quit?")

    self._total_steps += self._step_mul
    self._episode_steps += self._step_mul

    def zero_on_first_step(value):
      return 0.0 if self._state == environment.StepType.FIRST else value
    return environment.TimeStep(
        step_type=self._state,
        reward=zero_on_first_step(1),
        discount=zero_on_first_step(discount),
        observation=self._obs)

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
