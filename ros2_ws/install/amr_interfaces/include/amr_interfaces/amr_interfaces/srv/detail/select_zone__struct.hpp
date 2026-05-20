// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from amr_interfaces:srv/SelectZone.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__STRUCT_HPP_
#define AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__amr_interfaces__srv__SelectZone_Request __attribute__((deprecated))
#else
# define DEPRECATED__amr_interfaces__srv__SelectZone_Request __declspec(deprecated)
#endif

namespace amr_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SelectZone_Request_
{
  using Type = SelectZone_Request_<ContainerAllocator>;

  explicit SelectZone_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->zone_name = "";
    }
  }

  explicit SelectZone_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : zone_name(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->zone_name = "";
    }
  }

  // field types and members
  using _zone_name_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _zone_name_type zone_name;

  // setters for named parameter idiom
  Type & set__zone_name(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->zone_name = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    amr_interfaces::srv::SelectZone_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const amr_interfaces::srv::SelectZone_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SelectZone_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SelectZone_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__amr_interfaces__srv__SelectZone_Request
    std::shared_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__amr_interfaces__srv__SelectZone_Request
    std::shared_ptr<amr_interfaces::srv::SelectZone_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SelectZone_Request_ & other) const
  {
    if (this->zone_name != other.zone_name) {
      return false;
    }
    return true;
  }
  bool operator!=(const SelectZone_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SelectZone_Request_

// alias to use template instance with default allocator
using SelectZone_Request =
  amr_interfaces::srv::SelectZone_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace amr_interfaces


// Include directives for member types
// Member 'goal'
#include "geometry_msgs/msg/detail/pose_stamped__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__amr_interfaces__srv__SelectZone_Response __attribute__((deprecated))
#else
# define DEPRECATED__amr_interfaces__srv__SelectZone_Response __declspec(deprecated)
#endif

namespace amr_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SelectZone_Response_
{
  using Type = SelectZone_Response_<ContainerAllocator>;

  explicit SelectZone_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
      this->message = "";
    }
  }

  explicit SelectZone_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : message(_alloc),
    goal(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
      this->message = "";
    }
  }

  // field types and members
  using _accepted_type =
    bool;
  _accepted_type accepted;
  using _message_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _message_type message;
  using _goal_type =
    geometry_msgs::msg::PoseStamped_<ContainerAllocator>;
  _goal_type goal;

  // setters for named parameter idiom
  Type & set__accepted(
    const bool & _arg)
  {
    this->accepted = _arg;
    return *this;
  }
  Type & set__message(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->message = _arg;
    return *this;
  }
  Type & set__goal(
    const geometry_msgs::msg::PoseStamped_<ContainerAllocator> & _arg)
  {
    this->goal = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    amr_interfaces::srv::SelectZone_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const amr_interfaces::srv::SelectZone_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SelectZone_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::srv::SelectZone_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__amr_interfaces__srv__SelectZone_Response
    std::shared_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__amr_interfaces__srv__SelectZone_Response
    std::shared_ptr<amr_interfaces::srv::SelectZone_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SelectZone_Response_ & other) const
  {
    if (this->accepted != other.accepted) {
      return false;
    }
    if (this->message != other.message) {
      return false;
    }
    if (this->goal != other.goal) {
      return false;
    }
    return true;
  }
  bool operator!=(const SelectZone_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SelectZone_Response_

// alias to use template instance with default allocator
using SelectZone_Response =
  amr_interfaces::srv::SelectZone_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace amr_interfaces

namespace amr_interfaces
{

namespace srv
{

struct SelectZone
{
  using Request = amr_interfaces::srv::SelectZone_Request;
  using Response = amr_interfaces::srv::SelectZone_Response;
};

}  // namespace srv

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__STRUCT_HPP_
