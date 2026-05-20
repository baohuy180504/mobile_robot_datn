// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from amr_interfaces:srv/SetAiMode.idl
// generated code does not contain a copyright notice
#include "amr_interfaces/srv/detail/set_ai_mode__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

// Include directives for member types
// Member `command`
#include "rosidl_runtime_c/string_functions.h"

bool
amr_interfaces__srv__SetAiMode_Request__init(amr_interfaces__srv__SetAiMode_Request * msg)
{
  if (!msg) {
    return false;
  }
  // mode
  // command
  if (!rosidl_runtime_c__String__init(&msg->command)) {
    amr_interfaces__srv__SetAiMode_Request__fini(msg);
    return false;
  }
  return true;
}

void
amr_interfaces__srv__SetAiMode_Request__fini(amr_interfaces__srv__SetAiMode_Request * msg)
{
  if (!msg) {
    return;
  }
  // mode
  // command
  rosidl_runtime_c__String__fini(&msg->command);
}

bool
amr_interfaces__srv__SetAiMode_Request__are_equal(const amr_interfaces__srv__SetAiMode_Request * lhs, const amr_interfaces__srv__SetAiMode_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // mode
  if (lhs->mode != rhs->mode) {
    return false;
  }
  // command
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->command), &(rhs->command)))
  {
    return false;
  }
  return true;
}

bool
amr_interfaces__srv__SetAiMode_Request__copy(
  const amr_interfaces__srv__SetAiMode_Request * input,
  amr_interfaces__srv__SetAiMode_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // mode
  output->mode = input->mode;
  // command
  if (!rosidl_runtime_c__String__copy(
      &(input->command), &(output->command)))
  {
    return false;
  }
  return true;
}

amr_interfaces__srv__SetAiMode_Request *
amr_interfaces__srv__SetAiMode_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__srv__SetAiMode_Request * msg = (amr_interfaces__srv__SetAiMode_Request *)allocator.allocate(sizeof(amr_interfaces__srv__SetAiMode_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(amr_interfaces__srv__SetAiMode_Request));
  bool success = amr_interfaces__srv__SetAiMode_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
amr_interfaces__srv__SetAiMode_Request__destroy(amr_interfaces__srv__SetAiMode_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    amr_interfaces__srv__SetAiMode_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
amr_interfaces__srv__SetAiMode_Request__Sequence__init(amr_interfaces__srv__SetAiMode_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__srv__SetAiMode_Request * data = NULL;

  if (size) {
    data = (amr_interfaces__srv__SetAiMode_Request *)allocator.zero_allocate(size, sizeof(amr_interfaces__srv__SetAiMode_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = amr_interfaces__srv__SetAiMode_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        amr_interfaces__srv__SetAiMode_Request__fini(&data[i - 1]);
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
amr_interfaces__srv__SetAiMode_Request__Sequence__fini(amr_interfaces__srv__SetAiMode_Request__Sequence * array)
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
      amr_interfaces__srv__SetAiMode_Request__fini(&array->data[i]);
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

amr_interfaces__srv__SetAiMode_Request__Sequence *
amr_interfaces__srv__SetAiMode_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__srv__SetAiMode_Request__Sequence * array = (amr_interfaces__srv__SetAiMode_Request__Sequence *)allocator.allocate(sizeof(amr_interfaces__srv__SetAiMode_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = amr_interfaces__srv__SetAiMode_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
amr_interfaces__srv__SetAiMode_Request__Sequence__destroy(amr_interfaces__srv__SetAiMode_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    amr_interfaces__srv__SetAiMode_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
amr_interfaces__srv__SetAiMode_Request__Sequence__are_equal(const amr_interfaces__srv__SetAiMode_Request__Sequence * lhs, const amr_interfaces__srv__SetAiMode_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!amr_interfaces__srv__SetAiMode_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
amr_interfaces__srv__SetAiMode_Request__Sequence__copy(
  const amr_interfaces__srv__SetAiMode_Request__Sequence * input,
  amr_interfaces__srv__SetAiMode_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(amr_interfaces__srv__SetAiMode_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    amr_interfaces__srv__SetAiMode_Request * data =
      (amr_interfaces__srv__SetAiMode_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!amr_interfaces__srv__SetAiMode_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          amr_interfaces__srv__SetAiMode_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!amr_interfaces__srv__SetAiMode_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


// Include directives for member types
// Member `message`
// already included above
// #include "rosidl_runtime_c/string_functions.h"

bool
amr_interfaces__srv__SetAiMode_Response__init(amr_interfaces__srv__SetAiMode_Response * msg)
{
  if (!msg) {
    return false;
  }
  // success
  // message
  if (!rosidl_runtime_c__String__init(&msg->message)) {
    amr_interfaces__srv__SetAiMode_Response__fini(msg);
    return false;
  }
  // current_mode
  return true;
}

void
amr_interfaces__srv__SetAiMode_Response__fini(amr_interfaces__srv__SetAiMode_Response * msg)
{
  if (!msg) {
    return;
  }
  // success
  // message
  rosidl_runtime_c__String__fini(&msg->message);
  // current_mode
}

bool
amr_interfaces__srv__SetAiMode_Response__are_equal(const amr_interfaces__srv__SetAiMode_Response * lhs, const amr_interfaces__srv__SetAiMode_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // success
  if (lhs->success != rhs->success) {
    return false;
  }
  // message
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->message), &(rhs->message)))
  {
    return false;
  }
  // current_mode
  if (lhs->current_mode != rhs->current_mode) {
    return false;
  }
  return true;
}

bool
amr_interfaces__srv__SetAiMode_Response__copy(
  const amr_interfaces__srv__SetAiMode_Response * input,
  amr_interfaces__srv__SetAiMode_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // success
  output->success = input->success;
  // message
  if (!rosidl_runtime_c__String__copy(
      &(input->message), &(output->message)))
  {
    return false;
  }
  // current_mode
  output->current_mode = input->current_mode;
  return true;
}

amr_interfaces__srv__SetAiMode_Response *
amr_interfaces__srv__SetAiMode_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__srv__SetAiMode_Response * msg = (amr_interfaces__srv__SetAiMode_Response *)allocator.allocate(sizeof(amr_interfaces__srv__SetAiMode_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(amr_interfaces__srv__SetAiMode_Response));
  bool success = amr_interfaces__srv__SetAiMode_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
amr_interfaces__srv__SetAiMode_Response__destroy(amr_interfaces__srv__SetAiMode_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    amr_interfaces__srv__SetAiMode_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
amr_interfaces__srv__SetAiMode_Response__Sequence__init(amr_interfaces__srv__SetAiMode_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__srv__SetAiMode_Response * data = NULL;

  if (size) {
    data = (amr_interfaces__srv__SetAiMode_Response *)allocator.zero_allocate(size, sizeof(amr_interfaces__srv__SetAiMode_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = amr_interfaces__srv__SetAiMode_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        amr_interfaces__srv__SetAiMode_Response__fini(&data[i - 1]);
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
amr_interfaces__srv__SetAiMode_Response__Sequence__fini(amr_interfaces__srv__SetAiMode_Response__Sequence * array)
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
      amr_interfaces__srv__SetAiMode_Response__fini(&array->data[i]);
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

amr_interfaces__srv__SetAiMode_Response__Sequence *
amr_interfaces__srv__SetAiMode_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  amr_interfaces__srv__SetAiMode_Response__Sequence * array = (amr_interfaces__srv__SetAiMode_Response__Sequence *)allocator.allocate(sizeof(amr_interfaces__srv__SetAiMode_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = amr_interfaces__srv__SetAiMode_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
amr_interfaces__srv__SetAiMode_Response__Sequence__destroy(amr_interfaces__srv__SetAiMode_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    amr_interfaces__srv__SetAiMode_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
amr_interfaces__srv__SetAiMode_Response__Sequence__are_equal(const amr_interfaces__srv__SetAiMode_Response__Sequence * lhs, const amr_interfaces__srv__SetAiMode_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!amr_interfaces__srv__SetAiMode_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
amr_interfaces__srv__SetAiMode_Response__Sequence__copy(
  const amr_interfaces__srv__SetAiMode_Response__Sequence * input,
  amr_interfaces__srv__SetAiMode_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(amr_interfaces__srv__SetAiMode_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    amr_interfaces__srv__SetAiMode_Response * data =
      (amr_interfaces__srv__SetAiMode_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!amr_interfaces__srv__SetAiMode_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          amr_interfaces__srv__SetAiMode_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!amr_interfaces__srv__SetAiMode_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
