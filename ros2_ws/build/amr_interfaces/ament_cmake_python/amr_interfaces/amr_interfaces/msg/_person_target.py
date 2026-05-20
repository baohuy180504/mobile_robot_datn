# generated from rosidl_generator_py/resource/_idl.py.em
# with input from amr_interfaces:msg/PersonTarget.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_PersonTarget(type):
    """Metaclass of message 'PersonTarget'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
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
                'amr_interfaces.msg.PersonTarget')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__person_target
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__person_target
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__person_target
            cls._TYPE_SUPPORT = module.type_support_msg__msg__person_target
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__person_target

            from geometry_msgs.msg import PointStamped
            if PointStamped.__class__._TYPE_SUPPORT is None:
                PointStamped.__class__.__import_type_support__()

            from std_msgs.msg import Header
            if Header.__class__._TYPE_SUPPORT is None:
                Header.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class PersonTarget(metaclass=Metaclass_PersonTarget):
    """Message class 'PersonTarget'."""

    __slots__ = [
        '_header',
        '_target_id',
        '_locked',
        '_lost',
        '_confidence',
        '_bbox_x',
        '_bbox_y',
        '_bbox_w',
        '_bbox_h',
        '_position_camera',
        '_position_base',
        '_position_map',
        '_distance_m',
        '_angle_rad',
    ]

    _fields_and_field_types = {
        'header': 'std_msgs/Header',
        'target_id': 'int32',
        'locked': 'boolean',
        'lost': 'boolean',
        'confidence': 'float',
        'bbox_x': 'int32',
        'bbox_y': 'int32',
        'bbox_w': 'int32',
        'bbox_h': 'int32',
        'position_camera': 'geometry_msgs/PointStamped',
        'position_base': 'geometry_msgs/PointStamped',
        'position_map': 'geometry_msgs/PointStamped',
        'distance_m': 'float',
        'angle_rad': 'float',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Header'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['geometry_msgs', 'msg'], 'PointStamped'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['geometry_msgs', 'msg'], 'PointStamped'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['geometry_msgs', 'msg'], 'PointStamped'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Header
        self.header = kwargs.get('header', Header())
        self.target_id = kwargs.get('target_id', int())
        self.locked = kwargs.get('locked', bool())
        self.lost = kwargs.get('lost', bool())
        self.confidence = kwargs.get('confidence', float())
        self.bbox_x = kwargs.get('bbox_x', int())
        self.bbox_y = kwargs.get('bbox_y', int())
        self.bbox_w = kwargs.get('bbox_w', int())
        self.bbox_h = kwargs.get('bbox_h', int())
        from geometry_msgs.msg import PointStamped
        self.position_camera = kwargs.get('position_camera', PointStamped())
        from geometry_msgs.msg import PointStamped
        self.position_base = kwargs.get('position_base', PointStamped())
        from geometry_msgs.msg import PointStamped
        self.position_map = kwargs.get('position_map', PointStamped())
        self.distance_m = kwargs.get('distance_m', float())
        self.angle_rad = kwargs.get('angle_rad', float())

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
        if self.header != other.header:
            return False
        if self.target_id != other.target_id:
            return False
        if self.locked != other.locked:
            return False
        if self.lost != other.lost:
            return False
        if self.confidence != other.confidence:
            return False
        if self.bbox_x != other.bbox_x:
            return False
        if self.bbox_y != other.bbox_y:
            return False
        if self.bbox_w != other.bbox_w:
            return False
        if self.bbox_h != other.bbox_h:
            return False
        if self.position_camera != other.position_camera:
            return False
        if self.position_base != other.position_base:
            return False
        if self.position_map != other.position_map:
            return False
        if self.distance_m != other.distance_m:
            return False
        if self.angle_rad != other.angle_rad:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def header(self):
        """Message field 'header'."""
        return self._header

    @header.setter
    def header(self, value):
        if __debug__:
            from std_msgs.msg import Header
            assert \
                isinstance(value, Header), \
                "The 'header' field must be a sub message of type 'Header'"
        self._header = value

    @builtins.property
    def target_id(self):
        """Message field 'target_id'."""
        return self._target_id

    @target_id.setter
    def target_id(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'target_id' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'target_id' field must be an integer in [-2147483648, 2147483647]"
        self._target_id = value

    @builtins.property
    def locked(self):
        """Message field 'locked'."""
        return self._locked

    @locked.setter
    def locked(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'locked' field must be of type 'bool'"
        self._locked = value

    @builtins.property
    def lost(self):
        """Message field 'lost'."""
        return self._lost

    @lost.setter
    def lost(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'lost' field must be of type 'bool'"
        self._lost = value

    @builtins.property
    def confidence(self):
        """Message field 'confidence'."""
        return self._confidence

    @confidence.setter
    def confidence(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'confidence' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'confidence' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._confidence = value

    @builtins.property
    def bbox_x(self):
        """Message field 'bbox_x'."""
        return self._bbox_x

    @bbox_x.setter
    def bbox_x(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'bbox_x' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'bbox_x' field must be an integer in [-2147483648, 2147483647]"
        self._bbox_x = value

    @builtins.property
    def bbox_y(self):
        """Message field 'bbox_y'."""
        return self._bbox_y

    @bbox_y.setter
    def bbox_y(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'bbox_y' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'bbox_y' field must be an integer in [-2147483648, 2147483647]"
        self._bbox_y = value

    @builtins.property
    def bbox_w(self):
        """Message field 'bbox_w'."""
        return self._bbox_w

    @bbox_w.setter
    def bbox_w(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'bbox_w' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'bbox_w' field must be an integer in [-2147483648, 2147483647]"
        self._bbox_w = value

    @builtins.property
    def bbox_h(self):
        """Message field 'bbox_h'."""
        return self._bbox_h

    @bbox_h.setter
    def bbox_h(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'bbox_h' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'bbox_h' field must be an integer in [-2147483648, 2147483647]"
        self._bbox_h = value

    @builtins.property
    def position_camera(self):
        """Message field 'position_camera'."""
        return self._position_camera

    @position_camera.setter
    def position_camera(self, value):
        if __debug__:
            from geometry_msgs.msg import PointStamped
            assert \
                isinstance(value, PointStamped), \
                "The 'position_camera' field must be a sub message of type 'PointStamped'"
        self._position_camera = value

    @builtins.property
    def position_base(self):
        """Message field 'position_base'."""
        return self._position_base

    @position_base.setter
    def position_base(self, value):
        if __debug__:
            from geometry_msgs.msg import PointStamped
            assert \
                isinstance(value, PointStamped), \
                "The 'position_base' field must be a sub message of type 'PointStamped'"
        self._position_base = value

    @builtins.property
    def position_map(self):
        """Message field 'position_map'."""
        return self._position_map

    @position_map.setter
    def position_map(self, value):
        if __debug__:
            from geometry_msgs.msg import PointStamped
            assert \
                isinstance(value, PointStamped), \
                "The 'position_map' field must be a sub message of type 'PointStamped'"
        self._position_map = value

    @builtins.property
    def distance_m(self):
        """Message field 'distance_m'."""
        return self._distance_m

    @distance_m.setter
    def distance_m(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'distance_m' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'distance_m' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._distance_m = value

    @builtins.property
    def angle_rad(self):
        """Message field 'angle_rad'."""
        return self._angle_rad

    @angle_rad.setter
    def angle_rad(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'angle_rad' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'angle_rad' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._angle_rad = value
