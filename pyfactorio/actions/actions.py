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
    "screen", 
    ])):
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
    "world", 
    ])):
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


WALKING_DIRECTION_OPTIONS = [
    ("north", 0)
    ("northeast", 1)
    ("east", 2)
    ("southeast", 3)
    ("south", 4)
    ("southwest", 5)
    ("west", 6)
    ("northwest", 7)
]
WalkAct = _define_position_based_enum(  # pylint: disable=invalid-name
    "WalkingStateAct", WALKING_DIRECTION_OPTIONS)

# The list of known types.
TYPES = Arguments.types(
    walking_direction=ArgumentType.enum(WALKING_DIRECTION_OPTIONS, WalkAct),
    walking_state=ArgumentType.scalar(1)
    # entity_id=ArgumentType.enum()
    # minimap=ArgumentType.point(),
    # queued=ArgumentType.enum(QUEUED_OPTIONS, Queued),
    # select_point_act=ArgumentType.enum(
    #     SELECT_POINT_ACT_OPTIONS, SelectPointAct),
    # select_add=ArgumentType.enum(SELECT_ADD_OPTIONS, SelectAdd),
    # select_unit_act=ArgumentType.enum(SELECT_UNIT_ACT_OPTIONS, SelectUnitAct),
    # select_unit_id=ArgumentType.scalar(500),  # Depends on current selection.
)

RAW_TYPES = RawArguments.types(
    world=ArgumentType.point(),
    # queued=ArgumentType.enum(QUEUED_OPTIONS, Queued),
    # unit_tags=ArgumentType.unit_tags(512, 512),
    # target_unit_tag=ArgumentType.unit_tags(1, 512),
)

def no_op():
  pass

def cmd_move():
  pass

def cmd_build():
  pass

def cmd_rotate():
  pass

def cmd_mine():
  pass

def cmd_shoot():
  pass


# Which argument types do each function need?
FUNCTION_TYPES = {
    no_op: [],
    cmd_move: [TYPES.direction],
    # select_point: [TYPES.select_point_act, TYPES.screen],
    # cmd_screen: [TYPES.queued, TYPES.screen],
    # cmd_minimap: [TYPES.queued, TYPES.minimap],
    # raw_no_op: [],
    # raw_cmd: [RAW_TYPES.queued, RAW_TYPES.unit_tags],
    # raw_cmd_pt: [RAW_TYPES.queued, RAW_TYPES.unit_tags, RAW_TYPES.world],
    # raw_cmd_unit: [RAW_TYPES.queued, RAW_TYPES.unit_tags,
    #                RAW_TYPES.target_unit_tag],
    # raw_move_camera: [RAW_TYPES.world],
    # raw_autocast: [RAW_TYPES.unit_tags],
}

always = lambda _: True


class Function(collections.namedtuple(
    "Function", [
      "id",
      "name",
      "general_id",
      "args",
      "avail_fn",
      ])):
  """Represents a function action.
  Attributes:
    id: The function id, which is what the agent will use.
    name: The name of the function. Should be unique.
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


# pylint: disable=line-too-long
_FUNCTIONS = [
    Function.ui_func(0, "no_op", no_op),
    Function.ability(1, "move", cmd_move, 1),
]
# pylint: enable=line-too-long

# Create an IntEnum of the function names/ids so that printing the id will
# show something useful.
FUNCTIONS = Functions(_FUNCTIONS)
FUNCTIONS_AVAILABLE = {f.id: f for f in FUNCTIONS if f.avail_fn}

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
    func = FUNCTIONS[function]
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