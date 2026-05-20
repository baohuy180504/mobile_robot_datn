// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from amr_interfaces:srv/SetAiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__TRAITS_HPP_
#define AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "amr_interfaces/srv/detail/set_ai_mode__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace amr_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const SetAiMode_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: mode
  {
    out << "mode: ";
    rosidl_generator_traits::value_to_yaml(msg.mode, out);
    out << ", ";
  }

  // member: command
  {
    out << "command: ";
    rosidl_generator_traits::value_to_yaml(msg.command, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SetAiMode_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: mode
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "mode: ";
    rosidl_generator_traits::value_to_yaml(msg.mode, out);
    out << "\n";
  }

  // member: command
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "command: ";
    rosidl_generator_traits::value_to_yaml(msg.command, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SetAiMode_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace amr_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use amr_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const amr_interfaces::srv::SetAiMode_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  amr_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use amr_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const amr_interfaces::srv::SetAiMode_Request & msg)
{
  return amr_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<amr_interfaces::srv::SetAiMode_Request>()
{
  return "amr_interfaces::srv::SetAiMode_Request";
}

template<>
inline const char * name<amr_interfaces::srv::SetAiMode_Request>()
{
  return "amr_interfaces/srv/SetAiMode_Request";
}

template<>
struct has_fixed_size<amr_interfaces::srv::SetAiMode_Request>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<amr_interfaces::srv::SetAiMode_Request>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<amr_interfaces::srv::SetAiMode_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace amr_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const SetAiMode_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: success
  {
    out << "success: ";
    rosidl_generator_traits::value_to_yaml(msg.success, out);
    out << ", ";
  }

  // member: message
  {
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
    out << ", ";
  }

  // member: current_mode
  {
    out << "current_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.current_mode, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SetAiMode_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: success
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "success: ";
    rosidl_generator_traits::value_to_yaml(msg.success, out);
    out << "\n";
  }

  // member: message
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
    out << "\n";
  }

  // member: current_mode
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "current_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.current_mode, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SetAiMode_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace amr_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use amr_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const amr_interfaces::srv::SetAiMode_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  amr_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use amr_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const amr_interfaces::srv::SetAiMode_Response & msg)
{
  return amr_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<amr_interfaces::srv::SetAiMode_Response>()
{
  return "amr_interfaces::srv::SetAiMode_Response";
}

template<>
inline const char * name<amr_interfaces::srv::SetAiMode_Response>()
{
  return "amr_interfaces/srv/SetAiMode_Response";
}

template<>
struct has_fixed_size<amr_interfaces::srv::SetAiMode_Response>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<amr_interfaces::srv::SetAiMode_Response>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<amr_interfaces::srv::SetAiMode_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<amr_interfaces::srv::SetAiMode>()
{
  return "amr_interfaces::srv::SetAiMode";
}

template<>
inline const char * name<amr_interfaces::srv::SetAiMode>()
{
  return "amr_interfaces/srv/SetAiMode";
}

template<>
struct has_fixed_size<amr_interfaces::srv::SetAiMode>
  : std::integral_constant<
    bool,
    has_fixed_size<amr_interfaces::srv::SetAiMode_Request>::value &&
    has_fixed_size<amr_interfaces::srv::SetAiMode_Response>::value
  >
{
};

template<>
struct has_bounded_size<amr_interfaces::srv::SetAiMode>
  : std::integral_constant<
    bool,
    has_bounded_size<amr_interfaces::srv::SetAiMode_Request>::value &&
    has_bounded_size<amr_interfaces::srv::SetAiMode_Response>::value
  >
{
};

template<>
struct is_service<amr_interfaces::srv::SetAiMode>
  : std::true_type
{
};

template<>
struct is_service_request<amr_interfaces::srv::SetAiMode_Request>
  : std::true_type
{
};

template<>
struct is_service_response<amr_interfaces::srv::SetAiMode_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__TRAITS_HPP_
