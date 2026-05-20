# generated from rosidl_generator_py/resource/_idl.py.em
# with input from amr_interfaces:msg/AiAlert.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_AiAlert(type):
    """Metaclass of message 'AiAlert'."""

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
                'amr_interfaces.msg.AiAlert')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__ai_alert
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__ai_alert
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__ai_alert
            cls._TYPE_SUPPORT = module.type_support_msg__msg__ai_alert
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__ai_alert

            from builtin_interfaces.msg import Time
            if Time.__class__._TYPE_SUPPORT is None:
                Time.__class__.__import_type_support__()

            from geometry_msgs.msg import PoseStamped
            if PoseStamped.__class__._TYPE_SUPPORT is None:
                PoseStamped.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class AiAlert(metaclass=Metaclass_AiAlert):
    """Message class 'AiAlert'."""

    __slots__ = [
        '_stamp',
        '_alert_type',
        '_confidence',
        '_message',
        '_active',
        '_robot_pose',
        '_image_path',
    ]

    _fields_and_field_types = {
        'stamp': 'builtin_interfaces/Time',
        'alert_type': 'string',
        'confidence': 'float',
        'message': 'string',
        'active': 'boolean',
        'robot_pose': 'geometry_msgs/PoseStamped',
        'image_path': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['builtin_interfaces', 'msg'], 'Time'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['geometry_msgs', 'msg'], 'PoseStamped'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from builtin_interfaces.msg import Time
        self.stamp = kwargs.get('stamp', Time())
        self.alert_type = kwargs.get('alert_type', str())
        self.confidence = kwargs.get('confidence', float())
        self.message = kwargs.get('message', str())
        self.active = kwargs.get('active', bool())
        from geometry_msgs.msg import PoseStamped
        self.robot_pose = kwargs.get('robot_pose', PoseStamped())
        self.image_path = kwargs.get('image_path', str())

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
        if self.alert_type != other.alert_type:
            return False
        if self.confidence != other.confidence:
            return False
        if self.message != other.message:
            return False
        if self.active != other.active:
            return False
        if self.robot_pose != other.robot_pose:
            return False
        if self.image_path != other.image_path:
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
    def alert_type(self):
        """Message field 'alert_type'."""
        return self._alert_type

    @alert_type.setter
    def alert_type(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'alert_type' field must be of type 'str'"
        self._alert_type = value

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
    def message(self):
        """Message field 'message'."""
        return self._message

    @message.setter
    def message(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'message' field must be of type 'str'"
        self._message = value

    @builtins.property
    def active(self):
        """Message field 'active'."""
        return self._active

    @active.setter
    def active(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'active' field must be of type 'bool'"
        self._active = value

    @builtins.property
    def robot_pose(self):
        """Message field 'robot_pose'."""
        return self._robot_pose

    @robot_pose.setter
    def robot_pose(self, value):
        if __debug__:
            from geometry_msgs.msg import PoseStamped
            assert \
                isinstance(value, PoseStamped), \
                "The 'robot_pose' field must be a sub message of type 'PoseStamped'"
        self._robot_pose = value

    @builtins.property
    def image_path(self):
        """Message field 'image_path'."""
        return self._image_path

    @image_path.setter
    def image_path(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'image_path' field must be of type 'str'"
        self._image_path = value
