// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from amr_interfaces:msg/AiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_MODE__STRUCT_H_
#define AMR_INTERFACES__MSG__DETAIL__AI_MODE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Constant 'IDLE'.
enum
{
  amr_interfaces__msg__AiMode__IDLE = 0
};

/// Constant 'NAV_TO_ZONE'.
enum
{
  amr_interfaces__msg__AiMode__NAV_TO_ZONE = 1
};

/// Constant 'FOLLOW_DETECTING'.
enum
{
  amr_interfaces__msg__AiMode__FOLLOW_DETECTING = 2
};

/// Constant 'FOLLOW_ACTIVE'.
enum
{
  amr_interfaces__msg__AiMode__FOLLOW_ACTIVE = 3
};

/// Constant 'FOLLOW_STOPPED'.
enum
{
  amr_interfaces__msg__AiMode__FOLLOW_STOPPED = 4
};

/// Constant 'RETURN_TO_ZONE'.
enum
{
  amr_interfaces__msg__AiMode__RETURN_TO_ZONE = 5
};

/// Constant 'EMERGENCY_STOP'.
enum
{
  amr_interfaces__msg__AiMode__EMERGENCY_STOP = 6
};

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"
// Member 'mode_name'
// Member 'detail'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/AiMode in the package amr_interfaces.
/**
  * AMR operation mode
 */
typedef struct amr_interfaces__msg__AiMode
{
  builtin_interfaces__msg__Time stamp;
  uint8_t mode;
  rosidl_runtime_c__String mode_name;
  rosidl_runtime_c__String detail;
} amr_interfaces__msg__AiMode;

// Struct for a sequence of amr_interfaces__msg__AiMode.
typedef struct amr_interfaces__msg__AiMode__Sequence
{
  amr_interfaces__msg__AiMode * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} amr_interfaces__msg__AiMode__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_MODE__STRUCT_H_
