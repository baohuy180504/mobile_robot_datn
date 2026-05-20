// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from amr_interfaces:srv/SetAiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__STRUCT_HPP_
#define AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__amr_interfaces__srv__SetAiMode_Request __attribute__((deprecated))
#else
# define DEPRECATED__amr_interfaces__srv__SetAiMode_Request __declspec(deprecated)
#endif

namespace amr_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SetAiMode_Request_
{
  using Type = SetAiMode_Request_<ContainerAllocator>;

  explicit SetAiMode_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->mode = 0;
      this->command = "";
    }
  }

  explicit SetAiMode_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : command(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->mode = 0;
      this->command = "";
    }
  }

  // field types and members
  using _mode_type =
    uint8_t;
  _mode_type mode;
  using _command_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _command_type command;

  // setters for named parameter idiom
  Type & set__mode(
    const uint8_t & _arg)
  {
    this->mode = _arg;
    return *this;
  }
  Type & set__command(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->command = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__amr_interfaces__srv__SetAiMode_Request
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__amr_interfaces__srv__SetAiMode_Request
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SetAiMode_Request_ & other) const
  {
    if (this->mode != other.mode) {
      return false;
    }
    if (this->command != other.command) {
      return false;
    }
    return true;
  }
  bool operator!=(const SetAiMode_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SetAiMode_Request_

// alias to use template instance with default allocator
using SetAiMode_Request =
  amr_interfaces::srv::SetAiMode_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace amr_interfaces


#ifndef _WIN32
# define DEPRECATED__amr_interfaces__srv__SetAiMode_Response __attribute__((deprecated))
#else
# define DEPRECATED__amr_interfaces__srv__SetAiMode_Response __declspec(deprecated)
#endif

namespace amr_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SetAiMode_Response_
{
  using Type = SetAiMode_Response_<ContainerAllocator>;

  explicit SetAiMode_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
      this->message = "";
      this->current_mode = 0;
    }
  }

  explicit SetAiMode_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : message(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
      this->message = "";
      this->current_mode = 0;
    }
  }

  // field types and members
  using _success_type =
    bool;
  _success_type success;
  using _message_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _message_type message;
  using _current_mode_type =
    uint8_t;
  _current_mode_type current_mode;

  // setters for named parameter idiom
  Type & set__success(
    const bool & _arg)
  {
    this->success = _arg;
    return *this;
  }
  Type & set__message(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->message = _arg;
    return *this;
  }
  Type & set__current_mode(
    const uint8_t & _arg)
  {
    this->current_mode = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__amr_interfaces__srv__SetAiMode_Response
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__amr_interfaces__srv__SetAiMode_Response
    std::shared_ptr<amr_interfaces::srv::SetAiMode_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SetAiMode_Response_ & other) const
  {
    if (this->success != other.success) {
      return false;
    }
    if (this->message != other.message) {
      return false;
    }
    if (this->current_mode != other.current_mode) {
      return false;
    }
    return true;
  }
  bool operator!=(const SetAiMode_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SetAiMode_Response_

// alias to use template instance with default allocator
using SetAiMode_Response =
  amr_interfaces::srv::SetAiMode_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace amr_interfaces

namespace amr_interfaces
{

namespace srv
{

struct SetAiMode
{
  using Request = amr_interfaces::srv::SetAiMode_Request;
  using Response = amr_interfaces::srv::SetAiMode_Response;
};

}  // namespace srv

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__STRUCT_HPP_
