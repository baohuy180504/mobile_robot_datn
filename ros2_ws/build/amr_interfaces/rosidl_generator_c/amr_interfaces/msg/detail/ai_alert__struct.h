// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from amr_interfaces:msg/AiAlert.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_ALERT__STRUCT_H_
#define AMR_INTERFACES__MSG__DETAIL__AI_ALERT__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"
// Member 'alert_type'
// Member 'message'
// Member 'image_path'
#include "rosidl_runtime_c/string.h"
// Member 'robot_pose'
#include "geometry_msgs/msg/detail/pose_stamped__struct.h"

/// Struct defined in msg/AiAlert in the package amr_interfaces.
/**
  * AI alert message: fall, fire, smoke
 */
typedef struct amr_interfaces__msg__AiAlert
{
  builtin_interfaces__msg__Time stamp;
  /// FALL / FIRE / SMOKE / PERSON / UNKNOWN
  rosidl_runtime_c__String alert_type;
  float confidence;
  rosidl_runtime_c__String message;
  bool active;
  geometry_msgs__msg__PoseStamped robot_pose;
  rosidl_runtime_c__String image_path;
} amr_interfaces__msg__AiAlert;

// Struct for a sequence of amr_interfaces__msg__AiAlert.
typedef struct amr_interfaces__msg__AiAlert__Sequence
{
  amr_interfaces__msg__AiAlert * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} amr_interfaces__msg__AiAlert__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_ALERT__STRUCT_H_
