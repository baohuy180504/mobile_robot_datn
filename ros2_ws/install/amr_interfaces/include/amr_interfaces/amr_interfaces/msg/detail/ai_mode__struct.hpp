// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from amr_interfaces:msg/AiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_MODE__STRUCT_HPP_
#define AMR_INTERFACES__MSG__DETAIL__AI_MODE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__amr_interfaces__msg__AiMode __attribute__((deprecated))
#else
# define DEPRECATED__amr_interfaces__msg__AiMode __declspec(deprecated)
#endif

namespace amr_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct AiMode_
{
  using Type = AiMode_<ContainerAllocator>;

  explicit AiMode_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->mode = 0;
      this->mode_name = "";
      this->detail = "";
    }
  }

  explicit AiMode_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_alloc, _init),
    mode_name(_alloc),
    detail(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->mode = 0;
      this->mode_name = "";
      this->detail = "";
    }
  }

  // field types and members
  using _stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _stamp_type stamp;
  using _mode_type =
    uint8_t;
  _mode_type mode;
  using _mode_name_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _mode_name_type mode_name;
  using _detail_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _detail_type detail;

  // setters for named parameter idiom
  Type & set__stamp(
    const builtin_interfaces::msg::Time_<ContainerAllocator> & _arg)
  {
    this->stamp = _arg;
    return *this;
  }
  Type & set__mode(
    const uint8_t & _arg)
  {
    this->mode = _arg;
    return *this;
  }
  Type & set__mode_name(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->mode_name = _arg;
    return *this;
  }
  Type & set__detail(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->detail = _arg;
    return *this;
  }

  // constant declarations
  static constexpr uint8_t IDLE =
    0u;
  static constexpr uint8_t NAV_TO_ZONE =
    1u;
  static constexpr uint8_t FOLLOW_DETECTING =
    2u;
  static constexpr uint8_t FOLLOW_ACTIVE =
    3u;
  static constexpr uint8_t FOLLOW_STOPPED =
    4u;
  static constexpr uint8_t RETURN_TO_ZONE =
    5u;
  static constexpr uint8_t EMERGENCY_STOP =
    6u;

  // pointer types
  using RawPtr =
    amr_interfaces::msg::AiMode_<ContainerAllocator> *;
  using ConstRawPtr =
    const amr_interfaces::msg::AiMode_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::msg::AiMode_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::msg::AiMode_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__amr_interfaces__msg__AiMode
    std::shared_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__amr_interfaces__msg__AiMode
    std::shared_ptr<amr_interfaces::msg::AiMode_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const AiMode_ & other) const
  {
    if (this->stamp != other.stamp) {
      return false;
    }
    if (this->mode != other.mode) {
      return false;
    }
    if (this->mode_name != other.mode_name) {
      return false;
    }
    if (this->detail != other.detail) {
      return false;
    }
    return true;
  }
  bool operator!=(const AiMode_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct AiMode_

// alias to use template instance with default allocator
using AiMode =
  amr_interfaces::msg::AiMode_<std::allocator<void>>;

// constant definitions
#if __cplusplus < 201703L
// static constexpr member variable definitions are only needed in C++14 and below, deprecated in C++17
template<typename ContainerAllocator>
constexpr uint8_t AiMode_<ContainerAllocator>::IDLE;
#endif  // __cplusplus < 201703L
#if __cplusplus < 201703L
// static constexpr member variable definitions are only needed in C++14 and below, deprecated in C++17
template<typename ContainerAllocator>
constexpr uint8_t AiMode_<ContainerAllocator>::NAV_TO_ZONE;
#endif  // __cplusplus < 201703L
#if __cplusplus < 201703L
// static constexpr member variable definitions are only needed in C++14 and below, deprecated in C++17
template<typename ContainerAllocator>
constexpr uint8_t AiMode_<ContainerAllocator>::FOLLOW_DETECTING;
#endif  // __cplusplus < 201703L
#if __cplusplus < 201703L
// static constexpr member variable definitions are only needed in C++14 and below, deprecated in C++17
template<typename ContainerAllocator>
constexpr uint8_t AiMode_<ContainerAllocator>::FOLLOW_ACTIVE;
#endif  // __cplusplus < 201703L
#if __cplusplus < 201703L
// static constexpr member variable definitions are only needed in C++14 and below, deprecated in C++17
template<typename ContainerAllocator>
constexpr uint8_t AiMode_<ContainerAllocator>::FOLLOW_STOPPED;
#endif  // __cplusplus < 201703L
#if __cplusplus < 201703L
// static constexpr member variable definitions are only needed in C++14 and below, deprecated in C++17
template<typename ContainerAllocator>
constexpr uint8_t AiMode_<ContainerAllocator>::RETURN_TO_ZONE;
#endif  // __cplusplus < 201703L
#if __cplusplus < 201703L
// static constexpr member variable definitions are only needed in C++14 and below, deprecated in C++17
template<typename ContainerAllocator>
constexpr uint8_t AiMode_<ContainerAllocator>::EMERGENCY_STOP;
#endif  // __cplusplus < 201703L

}  // namespace msg

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_MODE__STRUCT_HPP_
