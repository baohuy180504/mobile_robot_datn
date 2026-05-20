// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from amr_interfaces:msg/AiMode.idl
// generated code does not contain a copyright notice
#include "amr_interfaces/msg/detail/ai_mode__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `stamp`
#include "builtin_interfaces/msg/detail/time__functions.h"
// Member `mode_name`
// Member `detail`
#include "rosidl_runtime_c/string_functions.h"

bool
amr_interfaces__msg__AiMode__init(amr_interfaces__msg__AiMode * msg)
{
  if (!msg) {
    return false;
  }
  // stamp
  if (!builtin_interfaces__msg__Time__init(&msg->stamp)) {
    amr_interfaces__msg__AiMode__fini(msg);
    return false;
  }
  // mode
  // mode_name
  if (!rosidl_runtime_c__String__init(&msg->mode_name)) {
    amr_interfaces__msg__AiMode__fini(msg);
    return false;
  }
  // detail
  if (!rosidl_runtime_c__String__init(&msg->detail)) {
    amr_interfaces__msg__AiMode__fini(msg);
    return false;
  }
  return true;
}

void
amr_interfaces__msg__AiMode__fini(amr_interfaces__msg__AiMode * msg)
{
  if (!msg) {
    return;
  }
  // stamp
  builtin_interfaces__msg__Time__fini(&msg->stamp);
  // mode
  // mode_name
  rosidl_runtime_c__String__fini(&msg->mode_name);
  // detail
  rosidl_runtime_c__String__fini(&msg->detail);
}

bool
amr_interfaces__msg__AiMode__are_equal(const amr_interfaces__msg__AiMode * lhs, const amr_interfaces__msg__AiMode * rhs)
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
  // mode
  if (lhs->mode != rhs->mode) {
    return false;
  }
  // mode_name
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->mode_name), &(rhs->mode_name)))
  {
    return false;
  }
  // detail
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->detail), &(rhs->detail)))
  {
    return false;
  }
  return true;
}

bool
amr_interfaces__msg__AiMode__copy(
  const amr_interfaces__msg__AiMode * input,
  amr_interfaces__msg__AiMode * output)
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
  // mode
  output->mode = input->mode;
  // mode_name
  if (!rosidl_runtime_c__String__copy(
      &(input->mode_name), &(output->mode_name)))
  {
    return false;
  }
  // detail
  if (!rosidl_runtime_c__String__copy(
      &(input->detail), &(output->detail)))
  {
    return false;
  }
  return true;
}

amr_interfaces__msg__AiMode *
amr_interfaces__msg__AiMode__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__AiMode * msg = (amr_interfaces__msg__AiMode *)allocator.allocate(sizeof(amr_interfaces__msg__AiMode), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(amr_interfaces__msg__AiMode));
  bool success = amr_interfaces__msg__AiMode__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
amr_interfaces__msg__AiMode__destroy(amr_interfaces__msg__AiMode * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    amr_interfaces__msg__AiMode__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
amr_interfaces__msg__AiMode__Sequence__init(amr_interfaces__msg__AiMode__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__AiMode * data = NULL;

  if (size) {
    data = (amr_interfaces__msg__AiMode *)allocator.zero_allocate(size, sizeof(amr_interfaces__msg__AiMode), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = amr_interfaces__msg__AiMode__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        amr_interfaces__msg__AiMode__fini(&data[i - 1]);
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
amr_interfaces__msg__AiMode__Sequence__fini(amr_interfaces__msg__AiMode__Sequence * array)
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
      amr_interfaces__msg__AiMode__fini(&array->data[i]);
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

amr_interfaces__msg__AiMode__Sequence *
amr_interfaces__msg__AiMode__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__msg__AiMode__Sequence * array = (amr_interfaces__msg__AiMode__Sequence *)allocator.allocate(sizeof(amr_interfaces__msg__AiMode__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = amr_interfaces__msg__AiMode__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
amr_interfaces__msg__AiMode__Sequence__destroy(amr_interfaces__msg__AiMode__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    amr_interfaces__msg__AiMode__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
amr_interfaces__msg__AiMode__Sequence__are_equal(const amr_interfaces__msg__AiMode__Sequence * lhs, const amr_interfaces__msg__AiMode__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!amr_interfaces__msg__AiMode__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
amr_interfaces__msg__AiMode__Sequence__copy(
  const amr_interfaces__msg__AiMode__Sequence * input,
  amr_interfaces__msg__AiMode__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(amr_interfaces__msg__AiMode);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    amr_interfaces__msg__AiMode * data =
      (amr_interfaces__msg__AiMode *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!amr_interfaces__msg__AiMode__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          amr_interfaces__msg__AiMode__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!amr_interfaces__msg__AiMode__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
