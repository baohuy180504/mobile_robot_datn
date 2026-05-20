// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from amr_interfaces:msg/AiAlert.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_ALERT__STRUCT_HPP_
#define AMR_INTERFACES__MSG__DETAIL__AI_ALERT__STRUCT_HPP_

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
// Member 'robot_pose'
#include "geometry_msgs/msg/detail/pose_stamped__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__amr_interfaces__msg__AiAlert __attribute__((deprecated))
#else
# define DEPRECATED__amr_interfaces__msg__AiAlert __declspec(deprecated)
#endif

namespace amr_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct AiAlert_
{
  using Type = AiAlert_<ContainerAllocator>;

  explicit AiAlert_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_init),
    robot_pose(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->alert_type = "";
      this->confidence = 0.0f;
      this->message = "";
      this->active = false;
      this->image_path = "";
    }
  }

  explicit AiAlert_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_alloc, _init),
    alert_type(_alloc),
    message(_alloc),
    robot_pose(_alloc, _init),
    image_path(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->alert_type = "";
      this->confidence = 0.0f;
      this->message = "";
      this->active = false;
      this->image_path = "";
    }
  }

  // field types and members
  using _stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _stamp_type stamp;
  using _alert_type_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _alert_type_type alert_type;
  using _confidence_type =
    float;
  _confidence_type confidence;
  using _message_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _message_type message;
  using _active_type =
    bool;
  _active_type active;
  using _robot_pose_type =
    geometry_msgs::msg::PoseStamped_<ContainerAllocator>;
  _robot_pose_type robot_pose;
  using _image_path_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _image_path_type image_path;

  // setters for named parameter idiom
  Type & set__stamp(
    const builtin_interfaces::msg::Time_<ContainerAllocator> & _arg)
  {
    this->stamp = _arg;
    return *this;
  }
  Type & set__alert_type(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->alert_type = _arg;
    return *this;
  }
  Type & set__confidence(
    const float & _arg)
  {
    this->confidence = _arg;
    return *this;
  }
  Type & set__message(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->message = _arg;
    return *this;
  }
  Type & set__active(
    const bool & _arg)
  {
    this->active = _arg;
    return *this;
  }
  Type & set__robot_pose(
    const geometry_msgs::msg::PoseStamped_<ContainerAllocator> & _arg)
  {
    this->robot_pose = _arg;
    return *this;
  }
  Type & set__image_path(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->image_path = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    amr_interfaces::msg::AiAlert_<ContainerAllocator> *;
  using ConstRawPtr =
    const amr_interfaces::msg::AiAlert_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::msg::AiAlert_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::msg::AiAlert_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__amr_interfaces__msg__AiAlert
    std::shared_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__amr_interfaces__msg__AiAlert
    std::shared_ptr<amr_interfaces::msg::AiAlert_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const AiAlert_ & other) const
  {
    if (this->stamp != other.stamp) {
      return false;
    }
    if (this->alert_type != other.alert_type) {
      return false;
    }
    if (this->confidence != other.confidence) {
      return false;
    }
    if (this->message != other.message) {
      return false;
    }
    if (this->active != other.active) {
      return false;
    }
    if (this->robot_pose != other.robot_pose) {
      return false;
    }
    if (this->image_path != other.image_path) {
      return false;
    }
    return true;
  }
  bool operator!=(const AiAlert_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct AiAlert_

// alias to use template instance with default allocator
using AiAlert =
  amr_interfaces::msg::AiAlert_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_ALERT__STRUCT_HPP_
