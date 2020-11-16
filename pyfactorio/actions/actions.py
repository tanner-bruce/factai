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
"""Define the static list of types and actions for SC2."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import numbers

import enum
import numpy
import six
from pyfactorio.render import point


class ActionSpace(enum.Enum):
  FEATURES = 1  # Act in feature layer pixel space with FUNCTIONS below.
  RGB = 2       # Act in RGB pixel space with FUNCTIONS below.
  RAW = 3       # Act with unit tags with RAW_FUNCTIONS below.


def spatial(action):
  """Choose the action space for the action proto."""
  return action.action_feature_layer


def move(action, action_space, minimap):
  """Move the camera."""
  minimap.assign_to(spatial(action, action_space).camera_move.center_minimap)


def select_entity(action, action_space, select_unit_act, select_unit_id):
  """Select a specific unit from the multi-unit selection."""
  del action_space
  select = action.action_ui.multi_panel
  select.type = select_unit_act
  select.unit_index = select_unit_id

def unload(action, action_space, unload_id):
  """Unload a unit from a transport/bunker/nydus/etc."""
  del action_space
  action.action_ui.cargo_panel.unit_index = unload_id


def build_queue(action, action_space, build_queue_id):
  """Cancel a unit in the build queue."""
  del action_space
  action.action_ui.production_panel.unit_index = build_queue_id


def raw_cmd(action, ability_id, queued, unit_tags):
  """Do a raw command to another entity."""
  action_cmd = action.action_raw.unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued
  if not isinstance(unit_tags, (tuple, list)):
    unit_tags = [unit_tags]
  action_cmd.unit_tags.extend(unit_tags)


def raw_cmd_pt(action, ability_id, queued, unit_tags, world):
  """Do a raw command to another unit towards a point."""
  action_cmd = action.action_raw.unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued
  if not isinstance(unit_tags, (tuple, list)):
    unit_tags = [unit_tags]
  action_cmd.unit_tags.extend(unit_tags)
  world.assign_to(action_cmd.target_world_space_pos)

def numpy_to_python(val):
  """Convert numpy types to their corresponding python types."""
  if isinstance(val, (int, float)):
    return val
  if isinstance(val, six.string_types):
    return val
  if (isinstance(val, numpy.number) or
      isinstance(val, numpy.ndarray) and not val.shape):  # numpy.array(1)
    return val.item()
  if isinstance(val, (list, tuple, numpy.ndarray)):
    return [numpy_to_python(v) for v in val]
  raise ValueError("Unknown value. Type: %s, repr: %s" % (type(val), repr(val)))


class ArgumentType(collections.namedtuple(
    "ArgumentType", ["id", "name", "sizes", "fn", "values", "count"])):
  """Represents a single argument type.
  Attributes:
    id: The argument id. This is unique.
    name: The name of the argument, also unique.
    sizes: The max+1 of each of the dimensions this argument takes.
    fn: The function to convert the list of integers into something more
        meaningful to be set in the protos to send to the game.
    values: An enum representing the values this argument type could hold. None
        if this isn't an enum argument type.
    count: Number of valid values. Only useful for unit_tags.
  """
  __slots__ = ()

  def __str__(self):
    return "%s/%s %s" % (self.id, self.name, list(self.sizes))

  def __reduce__(self):
    return self.__class__, tuple(self)

  @classmethod
  def enum(cls, options, values):
    """Create an ArgumentType where you choose one of a set of known values."""
    names, real = zip(*options)
    del names  # unused

    def factory(i, name):
      return cls(i, name, (len(real),), lambda a: real[a[0]], values, None)
    return factory

  @classmethod
  def scalar(cls, value):
    """Create an ArgumentType with a single scalar in range(value)."""
    return lambda i, name: cls(i, name, (value,), lambda a: a[0], None, None)

  @classmethod
  def point(cls):  # No range because it's unknown at this time.
    """Create an ArgumentType that is represented by a point.Point."""
    def factory(i, name):
      return cls(i, name, (0, 0), lambda a: point.Point(*a).floor(), None, None)
    return factory

  @classmethod
  def spec(cls, id_, name, sizes):
    """Create an ArgumentType to be used in ValidActions."""
    return cls(id_, name, sizes, None, None, None)

  @classmethod
  def unit_tags(cls, count, size):
    """Create an ArgumentType with a list of unbounded ints."""
    def clean(arg):
      arg = numpy_to_python(arg)
      if isinstance(arg, list) and len(arg) == 1 and isinstance(arg[0], list):
        arg = arg[0]  # Support [[list, of, tags]].
      return arg[:count]
    return lambda i, name: cls(i, name, (size,), clean, None, count)


class Arguments(collections.namedtuple("Arguments", [
    "screen", "minimap", "screen2", "queued", "control_group_act",
    "control_group_id", "select_point_act", "select_add", "select_unit_act",
    "select_unit_id", "select_worker", "build_queue_id", "unload_id"])):
  """The full list of argument types.
  Take a look at TYPES and FUNCTION_TYPES for more details.
  Attributes:
    screen: A point on the screen.
    minimap: A point on the minimap.
    screen2: The second point for a rectangle. This is needed so that no
        function takes the same type twice.
    queued: Whether the action should be done immediately or after all other
        actions queued for this unit.
    control_group_act: What to do with the control group.
    control_group_id: Which control group to do it with.
    select_point_act: What to do with the unit at the point.
    select_add: Whether to add the unit to the selection or replace it.
    select_unit_act: What to do when selecting a unit by id.
    select_unit_id: Which unit to select by id.
    select_worker: What to do when selecting a worker.
    build_queue_id: Which build queue index to target.
    unload_id: Which unit to target in a transport/nydus/command center.
  """
  __slots__ = ()

  @classmethod
  def types(cls, **kwargs):
    """Create an Arguments of the possible Types."""
    named = {name: factory(Arguments._fields.index(name), name)
             for name, factory in six.iteritems(kwargs)}
    return cls(**named)

  def __reduce__(self):
    return self.__class__, tuple(self)


class RawArguments(collections.namedtuple("RawArguments", [
    "world", "queued", "unit_tags", "target_unit_tag"])):
  """The full list of argument types.
  Take a look at TYPES and FUNCTION_TYPES for more details.
  Attributes:
    world: A point in world coordinates
    queued: Whether the action should be done immediately or after all other
        actions queued for this unit.
    unit_tags: Which units should execute this action.
    target_unit_tag: The target unit of this action.
  """
  __slots__ = ()

  @classmethod
  def types(cls, **kwargs):
    """Create an Arguments of the possible Types."""
    named = {name: factory(RawArguments._fields.index(name), name)
             for name, factory in six.iteritems(kwargs)}
    return cls(**named)

  def __reduce__(self):
    return self.__class__, tuple(self)


def _define_position_based_enum(name, options):
  return enum.IntEnum(
      name, {opt_name: i for i, (opt_name, _) in enumerate(options)})


SELECT_POINT_ACT_OPTIONS = [
    ("select", sc_spatial.ActionSpatialUnitSelectionPoint.Select),
]
SelectPointAct = _define_position_based_enum(  # pylint: disable=invalid-name
    "SelectPointAct", SELECT_POINT_ACT_OPTIONS)

SELECT_ADD_OPTIONS = [
    ("select", False),
    ("add", True),
]
SelectAdd = _define_position_based_enum(  # pylint: disable=invalid-name
    "SelectAdd", SELECT_ADD_OPTIONS)

SELECT_UNIT_ACT_OPTIONS = [
    ("select", sc_ui.ActionMultiPanel.SingleSelect),
    ("deselect", sc_ui.ActionMultiPanel.DeselectUnit),
]
SelectUnitAct = _define_position_based_enum(  # pylint: disable=invalid-name
    "SelectUnitAct", SELECT_UNIT_ACT_OPTIONS)

# The list of known types.
TYPES = Arguments.types(
    screen=ArgumentType.point(),
    # minimap=ArgumentType.point(),
    queued=ArgumentType.enum(QUEUED_OPTIONS, Queued),
    select_point_act=ArgumentType.enum(
        SELECT_POINT_ACT_OPTIONS, SelectPointAct),
    select_add=ArgumentType.enum(SELECT_ADD_OPTIONS, SelectAdd),
    select_unit_act=ArgumentType.enum(SELECT_UNIT_ACT_OPTIONS, SelectUnitAct),
    select_unit_id=ArgumentType.scalar(500),  # Depends on current selection.
)

RAW_TYPES = RawArguments.types(
    world=ArgumentType.point(),
    queued=ArgumentType.enum(QUEUED_OPTIONS, Queued),
    unit_tags=ArgumentType.unit_tags(512, 512),
    target_unit_tag=ArgumentType.unit_tags(1, 512),
)


# Which argument types do each function need?
FUNCTION_TYPES = {
    no_op: [],
    move_camera: [TYPES.minimap],
    select_point: [TYPES.select_point_act, TYPES.screen],
    cmd_screen: [TYPES.queued, TYPES.screen],
    cmd_minimap: [TYPES.queued, TYPES.minimap],
    raw_no_op: [],
    raw_cmd: [RAW_TYPES.queued, RAW_TYPES.unit_tags],
    raw_cmd_pt: [RAW_TYPES.queued, RAW_TYPES.unit_tags, RAW_TYPES.world],
    raw_cmd_unit: [RAW_TYPES.queued, RAW_TYPES.unit_tags,
                   RAW_TYPES.target_unit_tag],
    raw_move_camera: [RAW_TYPES.world],
    raw_autocast: [RAW_TYPES.unit_tags],
}

# Which ones need an ability?
ABILITY_FUNCTIONS = {cmd_quick, cmd_screen, cmd_minimap, autocast}
RAW_ABILITY_FUNCTIONS = {raw_cmd, raw_cmd_pt, raw_cmd_unit, raw_autocast}

# Which ones require a point?
POINT_REQUIRED_FUNCS = {
    False: {cmd_quick, autocast},
    True: {cmd_screen, cmd_minimap, autocast}}

always = lambda _: True


class Function(collections.namedtuple(
    "Function", ["id", "name", "ability_id", "general_id", "function_type",
                 "args", "avail_fn", "raw"])):
  """Represents a function action.
  Attributes:
    id: The function id, which is what the agent will use.
    name: The name of the function. Should be unique.
    ability_id: The ability id to pass to sc2.
    general_id: 0 for normal abilities, and the ability_id of another ability if
        it can be represented by a more general action.
    function_type: One of the functions in FUNCTION_TYPES for how to construct
        the sc2 action proto out of python types.
    args: A list of the types of args passed to function_type.
    avail_fn: For non-abilities, this function returns whether the function is
        valid.
    raw: Whether the function is raw or not.
  """
  __slots__ = ()

  @classmethod
  def ui_func(cls, id_, name, function_type, avail_fn=always):
    """Define a function representing a ui action."""
    return cls(id_, name, 0, 0, function_type, FUNCTION_TYPES[function_type],
               avail_fn, False)

  @classmethod
  def ability(cls, id_, name, function_type, ability_id, general_id=0):
    """Define a function represented as a game ability."""
    assert function_type in ABILITY_FUNCTIONS
    return cls(id_, name, ability_id, general_id, function_type,
               FUNCTION_TYPES[function_type], None, False)

  @classmethod
  def raw_ability(cls, id_, name, function_type, ability_id, general_id=0,
                  avail_fn=always):
    """Define a function represented as a game ability."""
    assert function_type in RAW_ABILITY_FUNCTIONS
    return cls(id_, name, ability_id, general_id, function_type,
               FUNCTION_TYPES[function_type], avail_fn, True)

  @classmethod
  def raw_ui_func(cls, id_, name, function_type, avail_fn=always):
    """Define a function representing a ui action."""
    return cls(id_, name, 0, 0, function_type, FUNCTION_TYPES[function_type],
               avail_fn, True)

  @classmethod
  def spec(cls, id_, name, args):
    """Create a Function to be used in ValidActions."""
    return cls(id_, name, None, None, None, args, None, False)

  def __hash__(self):  # So it can go in a set().
    return self.id

  def __str__(self):
    return self.str()

  def __call__(self, *args):
    """A convenient way to create a FunctionCall from this Function."""
    return FunctionCall.init_with_validation(self.id, args, raw=self.raw)

  def __reduce__(self):
    return self.__class__, tuple(self)

  def str(self, space=False):
    """String version. Set space=True to line them all up nicely."""
    return "%s/%s (%s)" % (str(int(self.id)).rjust(space and 4),
                           self.name.ljust(space and 50),
                           "; ".join(str(a) for a in self.args))


class Functions(object):
  """Represents the full set of functions.
  Can't use namedtuple since python3 has a limit of 255 function arguments, so
  build something similar.
  """

  def __init__(self, functions):
    functions = sorted(functions, key=lambda f: f.id)
    self._func_list = functions
    self._func_dict = {f.name: f for f in functions}
    if len(self._func_dict) != len(self._func_list):
      raise ValueError("Function names must be unique.")

  def __getattr__(self, name):
    return self._func_dict[name]

  def __getitem__(self, key):
    if isinstance(key, numbers.Integral):
      return self._func_list[key]
    return self._func_dict[key]

  def __getstate__(self):
    # Support pickling, which otherwise conflicts with __getattr__.
    return self._func_list

  def __setstate__(self, functions):
    # Support pickling, which otherwise conflicts with __getattr__.
    self.__init__(functions)

  def __iter__(self):
    return iter(self._func_list)

  def __len__(self):
    return len(self._func_list)

  def __eq__(self, other):
    return self._func_list == other._func_list  # pylint: disable=protected-access


# The semantic meaning of these actions can mainly be found by searching:
# http://liquipedia.net/starcraft2/ or http://starcraft.wikia.com/ .
# pylint: disable=line-too-long
_FUNCTIONS = [
    Function.ui_func(0, "no_op", no_op),
    Function.ui_func(1, "move_camera", move_camera),
    Function.ui_func(2, "select_point", select_point),
    Function.ui_func(5, "select_unit", select_unit,
                     lambda obs: obs.ui_data.HasField("multi")),
    Function.ui_func(6, "select_idle_worker", select_idle_worker,
                     lambda obs: obs.player_common.idle_worker_count > 0),
    Function.ui_func(7, "select_army", select_army,
                     lambda obs: obs.player_common.army_count > 0),
    Function.ui_func(8, "select_warp_gates", select_warp_gates,
                     lambda obs: obs.player_common.warp_gate_count > 0),
    Function.ui_func(9, "select_larva", select_larva,
                     lambda obs: obs.player_common.larva_count > 0),
    Function.ui_func(10, "unload", unload,
                     lambda obs: obs.ui_data.HasField("cargo")),
    Function.ui_func(11, "build_queue", build_queue,
                     lambda obs: obs.ui_data.HasField("production")),
    # Everything below here is generated with gen_actions.py
    Function.ability(12, "Attack_screen", cmd_screen, 3674),
    Function.ability(13, "Attack_minimap", cmd_minimap, 3674),
    Function.ability(14, "Attack_Attack_screen", cmd_screen, 23, 3674),
    Function.ability(18, "Attack_Redirect_screen", cmd_screen, 1682, 3674),
    Function.ability(20, "Scan_Move_minimap", cmd_minimap, 19, 3674),
    Function.ability(37, "Behavior_PulsarBeamOff_quick", cmd_quick, 2376),
    Function.ability(38, "Behavior_PulsarBeamOn_quick", cmd_quick, 2375),
    Function.ability(102, "Build_UltraliskCavern_screen", cmd_screen, 1159),
    Function.ability(103, "BurrowDown_quick", cmd_quick, 3661),
    Function.ability(116, "BurrowDown_Zergling_quick", cmd_quick, 1390, 3661),
    Function.ability(139, "BurrowUp_Zergling_autocast", autocast, 1392, 3662),
    Function.ability(140, "Cancel_quick", cmd_quick, 3659),
    Function.ability(175, "Cancel_QueuePassiveCancelToSelection_quick", cmd_quick, 1833, 3671),
    Function.ability(176, "Effect_Abduct_screen", cmd_screen, 2067),
    Function.ability(273, "Harvest_Return_SCV_quick", cmd_quick, 296, 3667),
    Function.ability(274, "HoldPosition_quick", cmd_quick, 3793),
    Function.ability(450, "Research_ZerglingMetabolicBoost_quick", cmd_quick, 1253),
    Function.ability(456, "Stop_Stop_quick", cmd_quick, 4, 3665),
    Function.ability(510, "TrainWarp_Zealot_screen", cmd_screen, 1413),
    Function.ability(511, "Unload_quick", cmd_quick, 3664),
]
# pylint: enable=line-too-long


# Create an IntEnum of the function names/ids so that printing the id will
# show something useful.
_Functions = enum.IntEnum(  # pylint: disable=invalid-name
    "_Functions", {f.name: f.id for f in _FUNCTIONS})
_FUNCTIONS = [f._replace(id=_Functions(f.id)) for f in _FUNCTIONS]
FUNCTIONS = Functions(_FUNCTIONS)

# Some indexes to support features.py and action conversion.
ABILITY_IDS = collections.defaultdict(set)  # {ability_id: {funcs}}
for _func in FUNCTIONS:
  if _func.ability_id >= 0:
    ABILITY_IDS[_func.ability_id].add(_func)
ABILITY_IDS = {k: frozenset(v) for k, v in six.iteritems(ABILITY_IDS)}
FUNCTIONS_AVAILABLE = {f.id: f for f in FUNCTIONS if f.avail_fn}


# pylint: disable=line-too-long
_RAW_FUNCTIONS = [



class FunctionCall(collections.namedtuple(
    "FunctionCall", ["function", "arguments"])):
  """Represents a function call action.
  Attributes:
    function: Store the function id, eg 2 for select_point.
    arguments: The list of arguments for that function, each being a list of
        ints. For select_point this could be: [[0], [23, 38]].
  """
  __slots__ = ()

  @classmethod
  def init_with_validation(cls, function, arguments, raw=False):
    """Return a `FunctionCall` given some validation for the function and args.
    Args:
      function: A function name or id, to be converted into a function id enum.
      arguments: An iterable of function arguments. Arguments that are enum
          types can be passed by name. Arguments that only take one value (ie
          not a point) don't need to be wrapped in a list.
      raw: Whether this is a raw function call.
    Returns:
      A new `FunctionCall` instance.
    Raises:
      KeyError: if the enum name doesn't exist.
      ValueError: if the enum id doesn't exist.
    """
    func = RAW_FUNCTIONS[function] if raw else FUNCTIONS[function]
    args = []
    for arg, arg_type in zip(arguments, func.args):
      arg = numpy_to_python(arg)
      if arg_type.values:  # Allow enum values by name or int.
        if isinstance(arg, six.string_types):
          try:
            args.append([arg_type.values[arg]])
          except KeyError:
            raise KeyError("Unknown argument value: %s, valid values: %s" % (
                arg, [v.name for v in arg_type.values]))
        else:
          if isinstance(arg, list):
            arg = arg[0]
          try:
            args.append([arg_type.values(arg)])
          except ValueError:
            raise ValueError("Unknown argument value: %s, valid values: %s" % (
                arg, list(arg_type.values)))
      elif isinstance(arg, int):  # Allow bare ints.
        args.append([arg])
      elif isinstance(arg, list):
        args.append(arg)
      else:
        raise ValueError(
            "Unknown argument value type: %s, expected int or list of ints, or "
            "their numpy equivalents. Value: %s" % (type(arg), arg))
    return cls(func.id, args)

  @classmethod
  def all_arguments(cls, function, arguments, raw=False):
    """Helper function for creating `FunctionCall`s with `Arguments`.
    Args:
      function: The value to store for the action function.
      arguments: The values to store for the arguments of the action. Can either
        be an `Arguments` object, a `dict`, or an iterable. If a `dict` or an
        iterable is provided, the values will be unpacked into an `Arguments`
        object.
      raw: Whether this is a raw function call.
    Returns:
      A new `FunctionCall` instance.
    """
    args_type = RawArguments if raw else Arguments

    if isinstance(arguments, dict):
      arguments = args_type(**arguments)
    elif not isinstance(arguments, args_type):
      arguments = args_type(*arguments)
    return cls(function, arguments)

  def __reduce__(self):
    return self.__class__, tuple(self)


class ValidActions(collections.namedtuple(
    "ValidActions", ["types", "functions"])):
  """The set of types and functions that are valid for an agent to use.
  Attributes:
    types: A namedtuple of the types that the functions require. Unlike TYPES
        above, this includes the sizes for screen and minimap.
    functions: A namedtuple of all the functions.
  """
  __slots__ = ()

  def __reduce__(self):
    return self.__class__, tuple(self)