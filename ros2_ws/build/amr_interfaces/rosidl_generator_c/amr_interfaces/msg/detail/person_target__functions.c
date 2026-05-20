// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from amr_interfaces:msg/PersonTarget.idl
// generated code does not contain a copyright notice
#include "amr_interfaces/msg/detail/person_target__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/detail/header__functions.h"
// Member `position_camera`
// Member `position_base`
// Member `position_map`
#include "geometry_msgs/msg/detail/point_stamped__functions.h"

bool
amr_interfaces__msg__PersonTarget__init(amr_interfaces__msg__PersonTarget * msg)
{
  if (!msg) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__init(&msg->header)) {
    amr_interfaces__msg__PersonTarget__fini(msg);
    return false;
  }
  // target_id
  // locked
  // lost
  // confidence
  // bbox_x
  // bbox_y
  // bbox_w
  // bbox_h
  // position_camera
  if (!geometry_msgs__msg__PointStamped__init(&msg->position_camera)) {
    amr_interfaces__msg__PersonTarget__fini(msg);
    return false;
  }
  // position_base
  if (!geometry_msgs__msg__PointStamped__init(&msg->position_base)) {
    amr_interfaces__msg__PersonTarget__fini(msg);
    return false;
  }
  // position_map
  if (!geometry_msgs__msg__PointStamped__init(&msg->position_map)) {
    amr_interfaces__msg__PersonTarget__fini(msg);
    return false;
  }
  // distance_m
  // angle_rad
  return true;
}

void
amr_interfaces__msg__PersonTarget__fini(amr_interfaces__msg__PersonTarget * msg)
{
  if (!msg) {
    return;
  }
  // header
  std_msgs__msg__Header__fini(&msg->header);
  // target_id
  // locked
  // lost
  // confidence
  // bbox_x
  // bbox_y
  // bbox_w
  // bbox_h
  // position_camera
  geometry_msgs__msg__PointStamped__fini(&msg->position_camera);
  // position_base
  geometry_msgs__msg__PointStamped__fini(&msg->position_base);
  // position_map
  geometry_msgs__msg__PointStamped__fini(&msg->position_map);
  // distance_m
  // angle_rad
}

bool
amr_interfaces__msg__PersonTarget__are_equal(const amr_interfaces__msg__PersonTarget * lhs, const amr_interfaces__msg__PersonTarget * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__are_equal(
      &(lhs->header), &(rhs->header)))
  {
    return false;
  }
  // target_id
  if (lhs->target_id != rhs->target_id) {
    return false;
  }
  // locked
  if (lhs->locked != rhs->locked) {
    return false;
  }
  // lost
  if (lhs->lost != rhs->lost) {
    return false;
  }
  // confidence
  if (lhs->confidence != rhs->confidence) {
    return false;
  }
  // bbox_x
  if (lhs->bbox_x != rhs->bbox_x) {
    return false;
  }
  // bbox_y
  if (lhs->bbox_y != rhs->bbox_y) {
    return false;
  }
  // bbox_w
  if (lhs->bbox_w != rhs->bbox_w) {
    return false;
  }
  // bbox_h
  if (lhs->bbox_h != rhs->bbox_h) {
    return false;
  }
  // position_camera
  if (!geometry_msgs__msg__PointStamped__are_equal(
      &(lhs->position_camera), &(rhs->position_camera)))
  {
    return false;
  }
  // position_base
  if (!geometry_msgs__msg__PointStamped__are_equal(
      &(lhs->position_base), &(rhs->position_base)))
  {
    return false;
  }
  // position_map
  if (!geometry_msgs__msg__PointStamped__are_equal(
      &(lhs->position_map), &(rhs->position_map)))
  {
    return false;
  }
  // distance_m
  if (lhs->distance_m != rhs->distance_m) {
    return false;
  }
  // angle_rad
  if (lhs->angle_rad != rhs->angle_rad) {
    return false;
  }
  return true;
}

bool
amr_interfaces__msg__PersonTarget__copy(
  const amr_interfaces__msg__PersonTarget * input,
  amr_interfaces__msg__PersonTarget * output)
{
  if (!input || !output) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__copy(
      &(input->header), &(output->header)))
  {
    return false;
  }
  // target_id
  output->target_id = input->target_id;
  // locked
  output->locked = input->locked;
  // lost
  output->lost = input->lost;
  // confidence
  output->confidence = input->confidence;
  // bbox_x
  output->bbox_x = input->bbox_x;
  // bbox_y
  output->bbox_y = input->bbox_y;
  // bbox_w
  output->bbox_w = input->bbox_w;
  // bbox_h
  output->bbox_h = input->bbox_h;
  // position_camera
  if (!geometry_msgs__msg__PointStamped__copy(
      &(input->position_camera), &(output->position_camera)))
  {
    return false;
  }
  // position_base
  if (!geometry_msgs__msg__PointStamped__copy(
      &(input->position_base), &(output->position_base)))
  {
    return false;
  }
  // position_map
  if (!geometry_msgs__msg__PointStamped__copy(
      &(input->position_map), &(output->position_map)))
  {
    return false;
  }
  // distance_m
  output->distance_m = input->distance_m;
  // angle_rad
  output->angle_rad = input->angle_rad;
  return true;
}

amr_interfaces__msg__PersonTarget *
amr_interfaces__msg__PersonTarget__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__PersonTarget * msg = (amr_interfaces__msg__PersonTarget *)allocator.allocate(sizeof(amr_interfaces__msg__PersonTarget), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(amr_interfaces__msg__PersonTarget));
  bool success = amr_interfaces__msg__PersonTarget__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
amr_interfaces__msg__PersonTarget__destroy(amr_interfaces__msg__PersonTarget * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    amr_interfaces__msg__PersonTarget__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
amr_interfaces__msg__PersonTarget__Sequence__init(amr_interfaces__msg__PersonTarget__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__PersonTarget * data = NULL;

  if (size) {
    data = (amr_interfaces__msg__PersonTarget *)allocator.zero_allocate(size, sizeof(amr_interfaces__msg__PersonTarget), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = amr_interfaces__msg__PersonTarget__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        amr_interfaces__msg__PersonTarget__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
amr_interfaces__msg__PersonTarget__Sequence__fini(amr_interfaces__msg__PersonTarget__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      amr_interfaces__msg__PersonTarget__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

amr_interfaces__msg__PersonTarget__Sequence *
amr_interfaces__msg__PersonTarget__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__PersonTarget__Sequence * array = (amr_interfaces__msg__PersonTarget__Sequence *)allocator.allocate(sizeof(amr_interfaces__msg__PersonTarget__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = amr_interfaces__msg__PersonTarget__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
amr_interfaces__msg__PersonTarget__Sequence__destroy(amr_interfaces__msg__PersonTarget__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    amr_interfaces__msg__PersonTarget__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
amr_interfaces__msg__PersonTarget__Sequence__are_equal(const amr_interfaces__msg__PersonTarget__Sequence * lhs, const amr_interfaces__msg__PersonTarget__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!amr_interfaces__msg__PersonTarget__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
amr_interfaces__msg__PersonTarget__Sequence__copy(
  const amr_interfaces__msg__PersonTarget__Sequence * input,
  amr_interfaces__msg__PersonTarget__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(amr_interfaces__msg__PersonTarget);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    amr_interfaces__msg__PersonTarget * data =
      (amr_interfaces__msg__PersonTarget *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!amr_interfaces__msg__PersonTarget__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          amr_interfaces__msg__PersonTarget__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!amr_interfaces__msg__PersonTarget__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
