// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from amr_interfaces:srv/SelectZone.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__STRUCT_H_
#define AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'zone_name'
#include "rosidl_runtime_c/string.h"

/// Struct defined in srv/SelectZone in the package amr_interfaces.
typedef struct amr_interfaces__srv__SelectZone_Request
{
  rosidl_runtime_c__String zone_name;
} amr_interfaces__srv__SelectZone_Request;

// Struct for a sequence of amr_interfaces__srv__SelectZone_Request.
typedef struct amr_interfaces__srv__SelectZone_Request__Sequence
{
  amr_interfaces__srv__SelectZone_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} amr_interfaces__srv__SelectZone_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'message'
// already included above
// #include "rosidl_runtime_c/string.h"
// Member 'goal'
#include "geometry_msgs/msg/detail/pose_stamped__struct.h"

/// Struct defined in srv/SelectZone in the package amr_interfaces.
typedef struct amr_interfaces__srv__SelectZone_Response
{
  bool accepted;
  rosidl_runtime_c__String message;
  geometry_msgs__msg__PoseStamped goal;
} amr_interfaces__srv__SelectZone_Response;

// Struct for a sequence of amr_interfaces__srv__SelectZone_Response.
typedef struct amr_interfaces__srv__SelectZone_Response__Sequence
{
  amr_interfaces__srv__SelectZone_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} amr_interfaces__srv__SelectZone_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__STRUCT_H_
