// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from amr_interfaces:msg/PersonTarget.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__STRUCT_H_
#define AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.h"
// Member 'position_camera'
// Member 'position_base'
// Member 'position_map'
#include "geometry_msgs/msg/detail/point_stamped__struct.h"

/// Struct defined in msg/PersonTarget in the package amr_interfaces.
/**
  * Locked person target for following behavior
 */
typedef struct amr_interfaces__msg__PersonTarget
{
  std_msgs__msg__Header header;
  int32_t target_id;
  bool locked;
  bool lost;
  float confidence;
  /// Bounding box on RGB image
  int32_t bbox_x;
  int32_t bbox_y;
  int32_t bbox_w;
  int32_t bbox_h;
  /// Estimated target position
  geometry_msgs__msg__PointStamped position_camera;
  geometry_msgs__msg__PointStamped position_base;
  geometry_msgs__msg__PointStamped position_map;
  float distance_m;
  float angle_rad;
} amr_interfaces__msg__PersonTarget;

// Struct for a sequence of amr_interfaces__msg__PersonTarget.
typedef struct amr_interfaces__msg__PersonTarget__Sequence
{
  amr_interfaces__msg__PersonTarget * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} amr_interfaces__msg__PersonTarget__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__STRUCT_H_
