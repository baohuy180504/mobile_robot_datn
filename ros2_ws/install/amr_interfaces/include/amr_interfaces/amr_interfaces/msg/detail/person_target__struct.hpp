// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from amr_interfaces:msg/PersonTarget.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__STRUCT_HPP_
#define AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.hpp"
// Member 'position_camera'
// Member 'position_base'
// Member 'position_map'
#include "geometry_msgs/msg/detail/point_stamped__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__amr_interfaces__msg__PersonTarget __attribute__((deprecated))
#else
# define DEPRECATED__amr_interfaces__msg__PersonTarget __declspec(deprecated)
#endif

namespace amr_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct PersonTarget_
{
  using Type = PersonTarget_<ContainerAllocator>;

  explicit PersonTarget_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_init),
    position_camera(_init),
    position_base(_init),
    position_map(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->target_id = 0l;
      this->locked = false;
      this->lost = false;
      this->confidence = 0.0f;
      this->bbox_x = 0l;
      this->bbox_y = 0l;
      this->bbox_w = 0l;
      this->bbox_h = 0l;
      this->distance_m = 0.0f;
      this->angle_rad = 0.0f;
    }
  }

  explicit PersonTarget_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_alloc, _init),
    position_camera(_alloc, _init),
    position_base(_alloc, _init),
    position_map(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->target_id = 0l;
      this->locked = false;
      this->lost = false;
      this->confidence = 0.0f;
      this->bbox_x = 0l;
      this->bbox_y = 0l;
      this->bbox_w = 0l;
      this->bbox_h = 0l;
      this->distance_m = 0.0f;
      this->angle_rad = 0.0f;
    }
  }

  // field types and members
  using _header_type =
    std_msgs::msg::Header_<ContainerAllocator>;
  _header_type header;
  using _target_id_type =
    int32_t;
  _target_id_type target_id;
  using _locked_type =
    bool;
  _locked_type locked;
  using _lost_type =
    bool;
  _lost_type lost;
  using _confidence_type =
    float;
  _confidence_type confidence;
  using _bbox_x_type =
    int32_t;
  _bbox_x_type bbox_x;
  using _bbox_y_type =
    int32_t;
  _bbox_y_type bbox_y;
  using _bbox_w_type =
    int32_t;
  _bbox_w_type bbox_w;
  using _bbox_h_type =
    int32_t;
  _bbox_h_type bbox_h;
  using _position_camera_type =
    geometry_msgs::msg::PointStamped_<ContainerAllocator>;
  _position_camera_type position_camera;
  using _position_base_type =
    geometry_msgs::msg::PointStamped_<ContainerAllocator>;
  _position_base_type position_base;
  using _position_map_type =
    geometry_msgs::msg::PointStamped_<ContainerAllocator>;
  _position_map_type position_map;
  using _distance_m_type =
    float;
  _distance_m_type distance_m;
  using _angle_rad_type =
    float;
  _angle_rad_type angle_rad;

  // setters for named parameter idiom
  Type & set__header(
    const std_msgs::msg::Header_<ContainerAllocator> & _arg)
  {
    this->header = _arg;
    return *this;
  }
  Type & set__target_id(
    const int32_t & _arg)
  {
    this->target_id = _arg;
    return *this;
  }
  Type & set__locked(
    const bool & _arg)
  {
    this->locked = _arg;
    return *this;
  }
  Type & set__lost(
    const bool & _arg)
  {
    this->lost = _arg;
    return *this;
  }
  Type & set__confidence(
    const float & _arg)
  {
    this->confidence = _arg;
    return *this;
  }
  Type & set__bbox_x(
    const int32_t & _arg)
  {
    this->bbox_x = _arg;
    return *this;
  }
  Type & set__bbox_y(
    const int32_t & _arg)
  {
    this->bbox_y = _arg;
    return *this;
  }
  Type & set__bbox_w(
    const int32_t & _arg)
  {
    this->bbox_w = _arg;
    return *this;
  }
  Type & set__bbox_h(
    const int32_t & _arg)
  {
    this->bbox_h = _arg;
    return *this;
  }
  Type & set__position_camera(
    const geometry_msgs::msg::PointStamped_<ContainerAllocator> & _arg)
  {
    this->position_camera = _arg;
    return *this;
  }
  Type & set__position_base(
    const geometry_msgs::msg::PointStamped_<ContainerAllocator> & _arg)
  {
    this->position_base = _arg;
    return *this;
  }
  Type & set__position_map(
    const geometry_msgs::msg::PointStamped_<ContainerAllocator> & _arg)
  {
    this->position_map = _arg;
    return *this;
  }
  Type & set__distance_m(
    const float & _arg)
  {
    this->distance_m = _arg;
    return *this;
  }
  Type & set__angle_rad(
    const float & _arg)
  {
    this->angle_rad = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    amr_interfaces::msg::PersonTarget_<ContainerAllocator> *;
  using ConstRawPtr =
    const amr_interfaces::msg::PersonTarget_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::msg::PersonTarget_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      amr_interfaces::msg::PersonTarget_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__amr_interfaces__msg__PersonTarget
    std::shared_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__amr_interfaces__msg__PersonTarget
    std::shared_ptr<amr_interfaces::msg::PersonTarget_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const PersonTarget_ & other) const
  {
    if (this->header != other.header) {
      return false;
    }
    if (this->target_id != other.target_id) {
      return false;
    }
    if (this->locked != other.locked) {
      return false;
    }
    if (this->lost != other.lost) {
      return false;
    }
    if (this->confidence != other.confidence) {
      return false;
    }
    if (this->bbox_x != other.bbox_x) {
      return false;
    }
    if (this->bbox_y != other.bbox_y) {
      return false;
    }
    if (this->bbox_w != other.bbox_w) {
      return false;
    }
    if (this->bbox_h != other.bbox_h) {
      return false;
    }
    if (this->position_camera != other.position_camera) {
      return false;
    }
    if (this->position_base != other.position_base) {
      return false;
    }
    if (this->position_map != other.position_map) {
      return false;
    }
    if (this->distance_m != other.distance_m) {
      return false;
    }
    if (this->angle_rad != other.angle_rad) {
      return false;
    }
    return true;
  }
  bool operator!=(const PersonTarget_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct PersonTarget_

// alias to use template instance with default allocator
using PersonTarget =
  amr_interfaces::msg::PersonTarget_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__STRUCT_HPP_
