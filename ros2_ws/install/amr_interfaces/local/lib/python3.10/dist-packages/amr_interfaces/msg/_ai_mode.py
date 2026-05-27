# generated from rosidl_generator_py/resource/_idl.py.em
# with input from amr_interfaces:msg/AiMode.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_AiMode(type):
    """Metaclass of message 'AiMode'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
        'IDLE': 0,
        'NAV_TO_ZONE': 1,
        'FOLLOW_DETECTING': 2,
        'FOLLOW_ACTIVE': 3,
        'FOLLOW_STOPPED': 4,
        'RETURN_TO_ZONE': 5,
        'EMERGENCY_STOP': 6,
        'LOCALIZING': 7,
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('amr_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'amr_interfaces.msg.AiMode')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__ai_mode
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__ai_mode
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__ai_mode
            cls._TYPE_SUPPORT = module.type_support_msg__msg__ai_mode
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__ai_mode

            from builtin_interfaces.msg import Time
            if Time.__class__._TYPE_SUPPORT is None:
                Time.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
            'IDLE': cls.__constants['IDLE'],
            'NAV_TO_ZONE': cls.__constants['NAV_TO_ZONE'],
            'FOLLOW_DETECTING': cls.__constants['FOLLOW_DETECTING'],
            'FOLLOW_ACTIVE': cls.__constants['FOLLOW_ACTIVE'],
            'FOLLOW_STOPPED': cls.__constants['FOLLOW_STOPPED'],
            'RETURN_TO_ZONE': cls.__constants['RETURN_TO_ZONE'],
            'EMERGENCY_STOP': cls.__constants['EMERGENCY_STOP'],
            'LOCALIZING': cls.__constants['LOCALIZING'],
        }

    @property
    def IDLE(self):
        """Message constant 'IDLE'."""
        return Metaclass_AiMode.__constants['IDLE']

    @property
    def NAV_TO_ZONE(self):
        """Message constant 'NAV_TO_ZONE'."""
        return Metaclass_AiMode.__constants['NAV_TO_ZONE']

    @property
    def FOLLOW_DETECTING(self):
        """Message constant 'FOLLOW_DETECTING'."""
        return Metaclass_AiMode.__constants['FOLLOW_DETECTING']

    @property
    def FOLLOW_ACTIVE(self):
        """Message constant 'FOLLOW_ACTIVE'."""
        return Metaclass_AiMode.__constants['FOLLOW_ACTIVE']

    @property
    def FOLLOW_STOPPED(self):
        """Message constant 'FOLLOW_STOPPED'."""
        return Metaclass_AiMode.__constants['FOLLOW_STOPPED']

    @property
    def RETURN_TO_ZONE(self):
        """Message constant 'RETURN_TO_ZONE'."""
        return Metaclass_AiMode.__constants['RETURN_TO_ZONE']

    @property
    def EMERGENCY_STOP(self):
        """Message constant 'EMERGENCY_STOP'."""
        return Metaclass_AiMode.__constants['EMERGENCY_STOP']

    @property
    def LOCALIZING(self):
        """Message constant 'LOCALIZING'."""
        return Metaclass_AiMode.__constants['LOCALIZING']


class AiMode(metaclass=Metaclass_AiMode):
    """
    Message class 'AiMode'.

    Constants:
      IDLE
      NAV_TO_ZONE
      FOLLOW_DETECTING
      FOLLOW_ACTIVE
      FOLLOW_STOPPED
      RETURN_TO_ZONE
      EMERGENCY_STOP
      LOCALIZING
    """

    __slots__ = [
        '_stamp',
        '_mode',
        '_mode_name',
        '_detail',
    ]

    _fields_and_field_types = {
        'stamp': 'builtin_interfaces/Time',
        'mode': 'uint8',
        'mode_name': 'string',
        'detail': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['builtin_interfaces', 'msg'], 'Time'),  # noqa: E501
        rosidl_parser.definition.BasicType('uint8'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from builtin_interfaces.msg import Time
        self.stamp = kwargs.get('stamp', Time())
        self.mode = kwargs.get('mode', int())
        self.mode_name = kwargs.get('mode_name', str())
        self.detail = kwargs.get('detail', str())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.stamp != other.stamp:
            return False
        if self.mode != other.mode:
            return False
        if self.mode_name != other.mode_name:
            return False
        if self.detail != other.detail:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def stamp(self):
        """Message field 'stamp'."""
        return self._stamp

    @stamp.setter
    def stamp(self, value):
        if __debug__:
            from builtin_interfaces.msg import Time
            assert \
                isinstance(value, Time), \
                "The 'stamp' field must be a sub message of type 'Time'"
        self._stamp = value

    @builtins.property
    def mode(self):
        """Message field 'mode'."""
        return self._mode

    @mode.setter
    def mode(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'mode' field must be of type 'int'"
            assert value >= 0 and value < 256, \
                "The 'mode' field must be an unsigned integer in [0, 255]"
        self._mode = value

    @builtins.property
    def mode_name(self):
        """Message field 'mode_name'."""
        return self._mode_name

    @mode_name.setter
    def mode_name(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'mode_name' field must be of type 'str'"
        self._mode_name = value

    @builtins.property
    def detail(self):
        """Message field 'detail'."""
        return self._detail

    @detail.setter
    def detail(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'detail' field must be of type 'str'"
        self._detail = value
