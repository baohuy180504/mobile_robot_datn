// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from amr_interfaces:srv/SetAiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__STRUCT_H_
#define AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'command'
#include "rosidl_runtime_c/string.h"

/// Struct defined in srv/SetAiMode in the package amr_interfaces.
typedef struct amr_interfaces__srv__SetAiMode_Request
{
  uint8_t mode;
  rosidl_runtime_c__String command;
} amr_interfaces__srv__SetAiMode_Request;

// Struct for a sequence of amr_interfaces__srv__SetAiMode_Request.
typedef struct amr_interfaces__srv__SetAiMode_Request__Sequence
{
  amr_interfaces__srv__SetAiMode_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} amr_interfaces__srv__SetAiMode_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'message'
// already included above
// #include "rosidl_runtime_c/string.h"

/// Struct defined in srv/SetAiMode in the package amr_interfaces.
typedef struct amr_interfaces__srv__SetAiMode_Response
{
  bool success;
  rosidl_runtime_c__String message;
  uint8_t current_mode;
} amr_interfaces__srv__SetAiMode_Response;

// Struct for a sequence of amr_interfaces__srv__SetAiMode_Response.
typedef struct amr_interfaces__srv__SetAiMode_Response__Sequence
{
  amr_interfaces__srv__SetAiMode_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} amr_interfaces__srv__SetAiMode_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__STRUCT_H_
