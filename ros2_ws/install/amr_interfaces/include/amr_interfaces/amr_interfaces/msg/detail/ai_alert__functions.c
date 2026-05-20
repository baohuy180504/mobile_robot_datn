// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from amr_interfaces:msg/AiAlert.idl
// generated code does not contain a copyright notice
#include "amr_interfaces/msg/detail/ai_alert__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `stamp`
#include "builtin_interfaces/msg/detail/time__functions.h"
// Member `alert_type`
// Member `message`
// Member `image_path`
#include "rosidl_runtime_c/string_functions.h"
// Member `robot_pose`
#include "geometry_msgs/msg/detail/pose_stamped__functions.h"

bool
amr_interfaces__msg__AiAlert__init(amr_interfaces__msg__AiAlert * msg)
{
  if (!msg) {
    return false;
  }
  // stamp
  if (!builtin_interfaces__msg__Time__init(&msg->stamp)) {
    amr_interfaces__msg__AiAlert__fini(msg);
    return false;
  }
  // alert_type
  if (!rosidl_runtime_c__String__init(&msg->alert_type)) {
    amr_interfaces__msg__AiAlert__fini(msg);
    return false;
  }
  // confidence
  // message
  if (!rosidl_runtime_c__String__init(&msg->message)) {
    amr_interfaces__msg__AiAlert__fini(msg);
    return false;
  }
  // active
  // robot_pose
  if (!geometry_msgs__msg__PoseStamped__init(&msg->robot_pose)) {
    amr_interfaces__msg__AiAlert__fini(msg);
    return false;
  }
  // image_path
  if (!rosidl_runtime_c__String__init(&msg->image_path)) {
    amr_interfaces__msg__AiAlert__fini(msg);
    return false;
  }
  return true;
}

void
amr_interfaces__msg__AiAlert__fini(amr_interfaces__msg__AiAlert * msg)
{
  if (!msg) {
    return;
  }
  // stamp
  builtin_interfaces__msg__Time__fini(&msg->stamp);
  // alert_type
  rosidl_runtime_c__String__fini(&msg->alert_type);
  // confidence
  // message
  rosidl_runtime_c__String__fini(&msg->message);
  // active
  // robot_pose
  geometry_msgs__msg__PoseStamped__fini(&msg->robot_pose);
  // image_path
  rosidl_runtime_c__String__fini(&msg->image_path);
}

bool
amr_interfaces__msg__AiAlert__are_equal(const amr_interfaces__msg__AiAlert * lhs, const amr_interfaces__msg__AiAlert * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // stamp
  if (!builtin_interfaces__msg__Time__are_equal(
      &(lhs->stamp), &(rhs->stamp)))
  {
    return false;
  }
  // alert_type
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->alert_type), &(rhs->alert_type)))
  {
    return false;
  }
  // confidence
  if (lhs->confidence != rhs->confidence) {
    return false;
  }
  // message
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->message), &(rhs->message)))
  {
    return false;
  }
  // active
  if (lhs->active != rhs->active) {
    return false;
  }
  // robot_pose
  if (!geometry_msgs__msg__PoseStamped__are_equal(
      &(lhs->robot_pose), &(rhs->robot_pose)))
  {
    return false;
  }
  // image_path
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->image_path), &(rhs->image_path)))
  {
    return false;
  }
  return true;
}

bool
amr_interfaces__msg__AiAlert__copy(
  const amr_interfaces__msg__AiAlert * input,
  amr_interfaces__msg__AiAlert * output)
{
  if (!input || !output) {
    return false;
  }
  // stamp
  if (!builtin_interfaces__msg__Time__copy(
      &(input->stamp), &(output->stamp)))
  {
    return false;
  }
  // alert_type
  if (!rosidl_runtime_c__String__copy(
      &(input->alert_type), &(output->alert_type)))
  {
    return false;
  }
  // confidence
  output->confidence = input->confidence;
  // message
  if (!rosidl_runtime_c__String__copy(
      &(input->message), &(output->message)))
  {
    return false;
  }
  // active
  output->active = input->active;
  // robot_pose
  if (!geometry_msgs__msg__PoseStamped__copy(
      &(input->robot_pose), &(output->robot_pose)))
  {
    return false;
  }
  // image_path
  if (!rosidl_runtime_c__String__copy(
      &(input->image_path), &(output->image_path)))
  {
    return false;
  }
  return true;
}

amr_interfaces__msg__AiAlert *
amr_interfaces__msg__AiAlert__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__AiAlert * msg = (amr_interfaces__msg__AiAlert *)allocator.allocate(sizeof(amr_interfaces__msg__AiAlert), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(amr_interfaces__msg__AiAlert));
  bool success = amr_interfaces__msg__AiAlert__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
amr_interfaces__msg__AiAlert__destroy(amr_interfaces__msg__AiAlert * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    amr_interfaces__msg__AiAlert__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
amr_interfaces__msg__AiAlert__Sequence__init(amr_interfaces__msg__AiAlert__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__AiAlert * data = NULL;

  if (size) {
    data = (amr_interfaces__msg__AiAlert *)allocator.zero_allocate(size, sizeof(amr_interfaces__msg__AiAlert), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = amr_interfaces__msg__AiAlert__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        amr_interfaces__msg__AiAlert__fini(&data[i - 1]);
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
amr_interfaces__msg__AiAlert__Sequence__fini(amr_interfaces__msg__AiAlert__Sequence * array)
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
      amr_interfaces__msg__AiAlert__fini(&array->data[i]);
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

amr_interfaces__msg__AiAlert__Sequence *
amr_interfaces__msg__AiAlert__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__AiAlert__Sequence * array = (amr_interfaces__msg__AiAlert__Sequence *)allocator.allocate(sizeof(amr_interfaces__msg__AiAlert__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = amr_interfaces__msg__AiAlert__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
amr_interfaces__msg__AiAlert__Sequence__destroy(amr_interfaces__msg__AiAlert__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    amr_interfaces__msg__AiAlert__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
amr_interfaces__msg__AiAlert__Sequence__are_equal(const amr_interfaces__msg__AiAlert__Sequence * lhs, const amr_interfaces__msg__AiAlert__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!amr_interfaces__msg__AiAlert__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
amr_interfaces__msg__AiAlert__Sequence__copy(
  const amr_interfaces__msg__AiAlert__Sequence * input,
  amr_interfaces__msg__AiAlert__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(amr_interfaces__msg__AiAlert);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    amr_interfaces__msg__AiAlert * data =
      (amr_interfaces__msg__AiAlert *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!amr_interfaces__msg__AiAlert__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          amr_interfaces__msg__AiAlert__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!amr_interfaces__msg__AiAlert__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
