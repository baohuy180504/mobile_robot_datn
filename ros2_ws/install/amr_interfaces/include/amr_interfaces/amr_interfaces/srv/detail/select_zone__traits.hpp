// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from amr_interfaces:srv/SelectZone.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__TRAITS_HPP_
#define AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "amr_interfaces/srv/detail/select_zone__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace amr_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const SelectZone_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: zone_name
  {
    out << "zone_name: ";
    rosidl_generator_traits::value_to_yaml(msg.zone_name, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SelectZone_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: zone_name
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "zone_name: ";
    rosidl_generator_traits::value_to_yaml(msg.zone_name, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SelectZone_Request & msg, bool use_flow_style = false)
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
  const amr_interfaces::srv::SelectZone_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  amr_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use amr_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const amr_interfaces::srv::SelectZone_Request & msg)
{
  return amr_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<amr_interfaces::srv::SelectZone_Request>()
{
  return "amr_interfaces::srv::SelectZone_Request";
}

template<>
inline const char * name<amr_interfaces::srv::SelectZone_Request>()
{
  return "amr_interfaces/srv/SelectZone_Request";
}

template<>
struct has_fixed_size<amr_interfaces::srv::SelectZone_Request>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<amr_interfaces::srv::SelectZone_Request>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<amr_interfaces::srv::SelectZone_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'goal'
#include "geometry_msgs/msg/detail/pose_stamped__traits.hpp"

namespace amr_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const SelectZone_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: accepted
  {
    out << "accepted: ";
    rosidl_generator_traits::value_to_yaml(msg.accepted, out);
    out << ", ";
  }

  // member: message
  {
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
    out << ", ";
  }

  // member: goal
  {
    out << "goal: ";
    to_flow_style_yaml(msg.goal, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SelectZone_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: accepted
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "accepted: ";
    rosidl_generator_traits::value_to_yaml(msg.accepted, out);
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

  // member: goal
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "goal:\n";
    to_block_style_yaml(msg.goal, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SelectZone_Response & msg, bool use_flow_style = false)
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
  const amr_interfaces::srv::SelectZone_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  amr_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use amr_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const amr_interfaces::srv::SelectZone_Response & msg)
{
  return amr_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<amr_interfaces::srv::SelectZone_Response>()
{
  return "amr_interfaces::srv::SelectZone_Response";
}

template<>
inline const char * name<amr_interfaces::srv::SelectZone_Response>()
{
  return "amr_interfaces/srv/SelectZone_Response";
}

template<>
struct has_fixed_size<amr_interfaces::srv::SelectZone_Response>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<amr_interfaces::srv::SelectZone_Response>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<amr_interfaces::srv::SelectZone_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<amr_interfaces::srv::SelectZone>()
{
  return "amr_interfaces::srv::SelectZone";
}

template<>
inline const char * name<amr_interfaces::srv::SelectZone>()
{
  return "amr_interfaces/srv/SelectZone";
}

template<>
struct has_fixed_size<amr_interfaces::srv::SelectZone>
  : std::integral_constant<
    bool,
    has_fixed_size<amr_interfaces::srv::SelectZone_Request>::value &&
    has_fixed_size<amr_interfaces::srv::SelectZone_Response>::value
  >
{
};

template<>
struct has_bounded_size<amr_interfaces::srv::SelectZone>
  : std::integral_constant<
    bool,
    has_bounded_size<amr_interfaces::srv::SelectZone_Request>::value &&
    has_bounded_size<amr_interfaces::srv::SelectZone_Response>::value
  >
{
};

template<>
struct is_service<amr_interfaces::srv::SelectZone>
  : std::true_type
{
};

template<>
struct is_service_request<amr_interfaces::srv::SelectZone_Request>
  : std::true_type
{
};

template<>
struct is_service_response<amr_interfaces::srv::SelectZone_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__TRAITS_HPP_
