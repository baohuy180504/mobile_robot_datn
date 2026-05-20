// generated from rosidl_typesupport_cpp/resource/idl__type_support.cpp.em
// with input from amr_interfaces:srv/SelectZone.idl
// generated code does not contain a copyright notice

#include "cstddef"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "amr_interfaces/srv/detail/select_zone__struct.hpp"
#include "rosidl_typesupport_cpp/identifier.hpp"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_c/type_support_map.h"
#include "rosidl_typesupport_cpp/message_type_support_dispatch.hpp"
#include "rosidl_typesupport_cpp/visibility_control.h"
#include "rosidl_typesupport_interface/macros.h"

namespace amr_interfaces
{

namespace srv
{

namespace rosidl_typesupport_cpp
{

typedef struct _SelectZone_Request_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _SelectZone_Request_type_support_ids_t;

static const _SelectZone_Request_type_support_ids_t _SelectZone_Request_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_cpp",  // ::rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
    "rosidl_typesupport_introspection_cpp",  // ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  }
};

typedef struct _SelectZone_Request_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _SelectZone_Request_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _SelectZone_Request_type_support_symbol_names_t _SelectZone_Request_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, amr_interfaces, srv, SelectZone_Request)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, amr_interfaces, srv, SelectZone_Request)),
  }
};

typedef struct _SelectZone_Request_type_support_data_t
{
  void * data[2];
} _SelectZone_Request_type_support_data_t;

static _SelectZone_Request_type_support_data_t _SelectZone_Request_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _SelectZone_Request_message_typesupport_map = {
  2,
  "amr_interfaces",
  &_SelectZone_Request_message_typesupport_ids.typesupport_identifier[0],
  &_SelectZone_Request_message_typesupport_symbol_names.symbol_name[0],
  &_SelectZone_Request_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t SelectZone_Request_message_type_support_handle = {
  ::rosidl_typesupport_cpp::typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_SelectZone_Request_message_typesupport_map),
  ::rosidl_typesupport_cpp::get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_cpp

}  // namespace srv

}  // namespace amr_interfaces

namespace rosidl_typesupport_cpp
{

template<>
ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<amr_interfaces::srv::SelectZone_Request>()
{
  return &::amr_interfaces::srv::rosidl_typesupport_cpp::SelectZone_Request_message_type_support_handle;
}

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_cpp, amr_interfaces, srv, SelectZone_Request)() {
  return get_message_type_support_handle<amr_interfaces::srv::SelectZone_Request>();
}

#ifdef __cplusplus
}
#endif
}  // namespace rosidl_typesupport_cpp

// already included above
// #include "cstddef"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "amr_interfaces/srv/detail/select_zone__struct.hpp"
// already included above
// #include "rosidl_typesupport_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support_dispatch.hpp"
// already included above
// #include "rosidl_typesupport_cpp/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace amr_interfaces
{

namespace srv
{

namespace rosidl_typesupport_cpp
{

typedef struct _SelectZone_Response_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _SelectZone_Response_type_support_ids_t;

static const _SelectZone_Response_type_support_ids_t _SelectZone_Response_message_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_cpp",  // ::rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
    "rosidl_typesupport_introspection_cpp",  // ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  }
};

typedef struct _SelectZone_Response_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _SelectZone_Response_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _SelectZone_Response_type_support_symbol_names_t _SelectZone_Response_message_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, amr_interfaces, srv, SelectZone_Response)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, amr_interfaces, srv, SelectZone_Response)),
  }
};

typedef struct _SelectZone_Response_type_support_data_t
{
  void * data[2];
} _SelectZone_Response_type_support_data_t;

static _SelectZone_Response_type_support_data_t _SelectZone_Response_message_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _SelectZone_Response_message_typesupport_map = {
  2,
  "amr_interfaces",
  &_SelectZone_Response_message_typesupport_ids.typesupport_identifier[0],
  &_SelectZone_Response_message_typesupport_symbol_names.symbol_name[0],
  &_SelectZone_Response_message_typesupport_data.data[0],
};

static const rosidl_message_type_support_t SelectZone_Response_message_type_support_handle = {
  ::rosidl_typesupport_cpp::typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_SelectZone_Response_message_typesupport_map),
  ::rosidl_typesupport_cpp::get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_cpp

}  // namespace srv

}  // namespace amr_interfaces

namespace rosidl_typesupport_cpp
{

template<>
ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<amr_interfaces::srv::SelectZone_Response>()
{
  return &::amr_interfaces::srv::rosidl_typesupport_cpp::SelectZone_Response_message_type_support_handle;
}

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_cpp, amr_interfaces, srv, SelectZone_Response)() {
  return get_message_type_support_handle<amr_interfaces::srv::SelectZone_Response>();
}

#ifdef __cplusplus
}
#endif
}  // namespace rosidl_typesupport_cpp

// already included above
// #include "cstddef"
#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "amr_interfaces/srv/detail/select_zone__struct.hpp"
// already included above
// #include "rosidl_typesupport_cpp/identifier.hpp"
#include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_c/type_support_map.h"
#include "rosidl_typesupport_cpp/service_type_support_dispatch.hpp"
// already included above
// #include "rosidl_typesupport_cpp/visibility_control.h"
// already included above
// #include "rosidl_typesupport_interface/macros.h"

namespace amr_interfaces
{

namespace srv
{

namespace rosidl_typesupport_cpp
{

typedef struct _SelectZone_type_support_ids_t
{
  const char * typesupport_identifier[2];
} _SelectZone_type_support_ids_t;

static const _SelectZone_type_support_ids_t _SelectZone_service_typesupport_ids = {
  {
    "rosidl_typesupport_fastrtps_cpp",  // ::rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
    "rosidl_typesupport_introspection_cpp",  // ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  }
};

typedef struct _SelectZone_type_support_symbol_names_t
{
  const char * symbol_name[2];
} _SelectZone_type_support_symbol_names_t;

#define STRINGIFY_(s) #s
#define STRINGIFY(s) STRINGIFY_(s)

static const _SelectZone_type_support_symbol_names_t _SelectZone_service_typesupport_symbol_names = {
  {
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, amr_interfaces, srv, SelectZone)),
    STRINGIFY(ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, amr_interfaces, srv, SelectZone)),
  }
};

typedef struct _SelectZone_type_support_data_t
{
  void * data[2];
} _SelectZone_type_support_data_t;

static _SelectZone_type_support_data_t _SelectZone_service_typesupport_data = {
  {
    0,  // will store the shared library later
    0,  // will store the shared library later
  }
};

static const type_support_map_t _SelectZone_service_typesupport_map = {
  2,
  "amr_interfaces",
  &_SelectZone_service_typesupport_ids.typesupport_identifier[0],
  &_SelectZone_service_typesupport_symbol_names.symbol_name[0],
  &_SelectZone_service_typesupport_data.data[0],
};

static const rosidl_service_type_support_t SelectZone_service_type_support_handle = {
  ::rosidl_typesupport_cpp::typesupport_identifier,
  reinterpret_cast<const type_support_map_t *>(&_SelectZone_service_typesupport_map),
  ::rosidl_typesupport_cpp::get_service_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_cpp

}  // namespace srv

}  // namespace amr_interfaces

namespace rosidl_typesupport_cpp
{

template<>
ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_service_type_support_t *
get_service_type_support_handle<amr_interfaces::srv::SelectZone>()
{
  return &::amr_interfaces::srv::rosidl_typesupport_cpp::SelectZone_service_type_support_handle;
}

}  // namespace rosidl_typesupport_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_CPP_PUBLIC
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_cpp, amr_interfaces, srv, SelectZone)() {
  return ::rosidl_typesupport_cpp::get_service_type_support_handle<amr_interfaces::srv::SelectZone>();
}

#ifdef __cplusplus
}
#endif
