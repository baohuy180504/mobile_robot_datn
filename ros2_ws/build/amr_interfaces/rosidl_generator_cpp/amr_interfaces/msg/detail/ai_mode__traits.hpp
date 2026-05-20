// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from amr_interfaces:msg/AiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_MODE__TRAITS_HPP_
#define AMR_INTERFACES__MSG__DETAIL__AI_MODE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "amr_interfaces/msg/detail/ai_mode__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__traits.hpp"

namespace amr_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const AiMode & msg,
  std::ostream & out)
{
  out << "{";
  // member: stamp
  {
    out << "stamp: ";
    to_flow_style_yaml(msg.stamp, out);
    out << ", ";
  }

  // member: mode
  {
    out << "mode: ";
    rosidl_generator_traits::value_to_yaml(msg.mode, out);
    out << ", ";
  }

  // member: mode_name
  {
    out << "mode_name: ";
    rosidl_generator_traits::value_to_yaml(msg.mode_name, out);
    out << ", ";
  }

  // member: detail
  {
    out << "detail: ";
    rosidl_generator_traits::value_to_yaml(msg.detail, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const AiMode & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: stamp
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "stamp:\n";
    to_block_style_yaml(msg.stamp, out, indentation + 2);
  }

  // member: mode
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "mode: ";
    rosidl_generator_traits::value_to_yaml(msg.mode, out);
    out << "\n";
  }

  // member: mode_name
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "mode_name: ";
    rosidl_generator_traits::value_to_yaml(msg.mode_name, out);
    out << "\n";
  }

  // member: detail
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "detail: ";
    rosidl_generator_traits::value_to_yaml(msg.detail, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const AiMode & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace amr_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use amr_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const amr_interfaces::msg::AiMode & msg,
  std::ostream & out, size_t indentation = 0)
{
  amr_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use amr_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const amr_interfaces::msg::AiMode & msg)
{
  return amr_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<amr_interfaces::msg::AiMode>()
{
  return "amr_interfaces::msg::AiMode";
}

template<>
inline const char * name<amr_interfaces::msg::AiMode>()
{
  return "amr_interfaces/msg/AiMode";
}

template<>
struct has_fixed_size<amr_interfaces::msg::AiMode>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<amr_interfaces::msg::AiMode>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<amr_interfaces::msg::AiMode>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_MODE__TRAITS_HPP_
