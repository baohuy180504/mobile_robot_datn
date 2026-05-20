// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from amr_interfaces:msg/PersonTarget.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__TRAITS_HPP_
#define AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "amr_interfaces/msg/detail/person_target__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__traits.hpp"
// Member 'position_camera'
// Member 'position_base'
// Member 'position_map'
#include "geometry_msgs/msg/detail/point_stamped__traits.hpp"

namespace amr_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const PersonTarget & msg,
  std::ostream & out)
{
  out << "{";
  // member: header
  {
    out << "header: ";
    to_flow_style_yaml(msg.header, out);
    out << ", ";
  }

  // member: target_id
  {
    out << "target_id: ";
    rosidl_generator_traits::value_to_yaml(msg.target_id, out);
    out << ", ";
  }

  // member: locked
  {
    out << "locked: ";
    rosidl_generator_traits::value_to_yaml(msg.locked, out);
    out << ", ";
  }

  // member: lost
  {
    out << "lost: ";
    rosidl_generator_traits::value_to_yaml(msg.lost, out);
    out << ", ";
  }

  // member: confidence
  {
    out << "confidence: ";
    rosidl_generator_traits::value_to_yaml(msg.confidence, out);
    out << ", ";
  }

  // member: bbox_x
  {
    out << "bbox_x: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_x, out);
    out << ", ";
  }

  // member: bbox_y
  {
    out << "bbox_y: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_y, out);
    out << ", ";
  }

  // member: bbox_w
  {
    out << "bbox_w: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_w, out);
    out << ", ";
  }

  // member: bbox_h
  {
    out << "bbox_h: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_h, out);
    out << ", ";
  }

  // member: position_camera
  {
    out << "position_camera: ";
    to_flow_style_yaml(msg.position_camera, out);
    out << ", ";
  }

  // member: position_base
  {
    out << "position_base: ";
    to_flow_style_yaml(msg.position_base, out);
    out << ", ";
  }

  // member: position_map
  {
    out << "position_map: ";
    to_flow_style_yaml(msg.position_map, out);
    out << ", ";
  }

  // member: distance_m
  {
    out << "distance_m: ";
    rosidl_generator_traits::value_to_yaml(msg.distance_m, out);
    out << ", ";
  }

  // member: angle_rad
  {
    out << "angle_rad: ";
    rosidl_generator_traits::value_to_yaml(msg.angle_rad, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const PersonTarget & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: header
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "header:\n";
    to_block_style_yaml(msg.header, out, indentation + 2);
  }

  // member: target_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "target_id: ";
    rosidl_generator_traits::value_to_yaml(msg.target_id, out);
    out << "\n";
  }

  // member: locked
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "locked: ";
    rosidl_generator_traits::value_to_yaml(msg.locked, out);
    out << "\n";
  }

  // member: lost
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "lost: ";
    rosidl_generator_traits::value_to_yaml(msg.lost, out);
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

  // member: bbox_x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_x: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_x, out);
    out << "\n";
  }

  // member: bbox_y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_y: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_y, out);
    out << "\n";
  }

  // member: bbox_w
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_w: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_w, out);
    out << "\n";
  }

  // member: bbox_h
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_h: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_h, out);
    out << "\n";
  }

  // member: position_camera
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "position_camera:\n";
    to_block_style_yaml(msg.position_camera, out, indentation + 2);
  }

  // member: position_base
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "position_base:\n";
    to_block_style_yaml(msg.position_base, out, indentation + 2);
  }

  // member: position_map
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "position_map:\n";
    to_block_style_yaml(msg.position_map, out, indentation + 2);
  }

  // member: distance_m
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "distance_m: ";
    rosidl_generator_traits::value_to_yaml(msg.distance_m, out);
    out << "\n";
  }

  // member: angle_rad
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "angle_rad: ";
    rosidl_generator_traits::value_to_yaml(msg.angle_rad, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const PersonTarget & msg, bool use_flow_style = false)
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
  const amr_interfaces::msg::PersonTarget & msg,
  std::ostream & out, size_t indentation = 0)
{
  amr_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use amr_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const amr_interfaces::msg::PersonTarget & msg)
{
  return amr_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<amr_interfaces::msg::PersonTarget>()
{
  return "amr_interfaces::msg::PersonTarget";
}

template<>
inline const char * name<amr_interfaces::msg::PersonTarget>()
{
  return "amr_interfaces/msg/PersonTarget";
}

template<>
struct has_fixed_size<amr_interfaces::msg::PersonTarget>
  : std::integral_constant<bool, has_fixed_size<geometry_msgs::msg::PointStamped>::value && has_fixed_size<std_msgs::msg::Header>::value> {};

template<>
struct has_bounded_size<amr_interfaces::msg::PersonTarget>
  : std::integral_constant<bool, has_bounded_size<geometry_msgs::msg::PointStamped>::value && has_bounded_size<std_msgs::msg::Header>::value> {};

template<>
struct is_message<amr_interfaces::msg::PersonTarget>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__TRAITS_HPP_
