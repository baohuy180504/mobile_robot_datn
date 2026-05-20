// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from amr_interfaces:msg/AiAlert.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_ALERT__TRAITS_HPP_
#define AMR_INTERFACES__MSG__DETAIL__AI_ALERT__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "amr_interfaces/msg/detail/ai_alert__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__traits.hpp"
// Member 'robot_pose'
#include "geometry_msgs/msg/detail/pose_stamped__traits.hpp"

namespace amr_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const AiAlert & msg,
  std::ostream & out)
{
  out << "{";
  // member: stamp
  {
    out << "stamp: ";
    to_flow_style_yaml(msg.stamp, out);
    out << ", ";
  }

  // member: alert_type
  {
    out << "alert_type: ";
    rosidl_generator_traits::value_to_yaml(msg.alert_type, out);
    out << ", ";
  }

  // member: confidence
  {
    out << "confidence: ";
    rosidl_generator_traits::value_to_yaml(msg.confidence, out);
    out << ", ";
  }

  // member: message
  {
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
    out << ", ";
  }

  // member: active
  {
    out << "active: ";
    rosidl_generator_traits::value_to_yaml(msg.active, out);
    out << ", ";
  }

  // member: robot_pose
  {
    out << "robot_pose: ";
    to_flow_style_yaml(msg.robot_pose, out);
    out << ", ";
  }

  // member: image_path
  {
    out << "image_path: ";
    rosidl_generator_traits::value_to_yaml(msg.image_path, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const AiAlert & msg,
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

  // member: alert_type
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "alert_type: ";
    rosidl_generator_traits::value_to_yaml(msg.alert_type, out);
    out << "\n";
  }

  // member: confidence
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "confidence: ";
    rosidl_generator_traits::value_to_yaml(msg.confidence, out);
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

  // member: active
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "active: ";
    rosidl_generator_traits::value_to_yaml(msg.active, out);
    out << "\n";
  }

  // member: robot_pose
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "robot_pose:\n";
    to_block_style_yaml(msg.robot_pose, out, indentation + 2);
  }

  // member: image_path
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "image_path: ";
    rosidl_generator_traits::value_to_yaml(msg.image_path, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const AiAlert & msg, bool use_flow_style = false)
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
  const amr_interfaces::msg::AiAlert & msg,
  std::ostream & out, size_t indentation = 0)
{
  amr_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use amr_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const amr_interfaces::msg::AiAlert & msg)
{
  return amr_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<amr_interfaces::msg::AiAlert>()
{
  return "amr_interfaces::msg::AiAlert";
}

template<>
inline const char * name<amr_interfaces::msg::AiAlert>()
{
  return "amr_interfaces/msg/AiAlert";
}

template<>
struct has_fixed_size<amr_interfaces::msg::AiAlert>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<amr_interfaces::msg::AiAlert>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<amr_interfaces::msg::AiAlert>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_ALERT__TRAITS_HPP_
