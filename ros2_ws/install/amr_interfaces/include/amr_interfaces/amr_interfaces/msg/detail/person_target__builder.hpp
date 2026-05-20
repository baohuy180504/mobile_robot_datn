// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from amr_interfaces:msg/PersonTarget.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__BUILDER_HPP_
#define AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "amr_interfaces/msg/detail/person_target__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace amr_interfaces
{

namespace msg
{

namespace builder
{

class Init_PersonTarget_angle_rad
{
public:
  explicit Init_PersonTarget_angle_rad(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  ::amr_interfaces::msg::PersonTarget angle_rad(::amr_interfaces::msg::PersonTarget::_angle_rad_type arg)
  {
    msg_.angle_rad = std::move(arg);
    return std::move(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_distance_m
{
public:
  explicit Init_PersonTarget_distance_m(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_angle_rad distance_m(::amr_interfaces::msg::PersonTarget::_distance_m_type arg)
  {
    msg_.distance_m = std::move(arg);
    return Init_PersonTarget_angle_rad(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_position_map
{
public:
  explicit Init_PersonTarget_position_map(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_distance_m position_map(::amr_interfaces::msg::PersonTarget::_position_map_type arg)
  {
    msg_.position_map = std::move(arg);
    return Init_PersonTarget_distance_m(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_position_base
{
public:
  explicit Init_PersonTarget_position_base(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_position_map position_base(::amr_interfaces::msg::PersonTarget::_position_base_type arg)
  {
    msg_.position_base = std::move(arg);
    return Init_PersonTarget_position_map(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_position_camera
{
public:
  explicit Init_PersonTarget_position_camera(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_position_base position_camera(::amr_interfaces::msg::PersonTarget::_position_camera_type arg)
  {
    msg_.position_camera = std::move(arg);
    return Init_PersonTarget_position_base(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_bbox_h
{
public:
  explicit Init_PersonTarget_bbox_h(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_position_camera bbox_h(::amr_interfaces::msg::PersonTarget::_bbox_h_type arg)
  {
    msg_.bbox_h = std::move(arg);
    return Init_PersonTarget_position_camera(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_bbox_w
{
public:
  explicit Init_PersonTarget_bbox_w(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_bbox_h bbox_w(::amr_interfaces::msg::PersonTarget::_bbox_w_type arg)
  {
    msg_.bbox_w = std::move(arg);
    return Init_PersonTarget_bbox_h(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_bbox_y
{
public:
  explicit Init_PersonTarget_bbox_y(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_bbox_w bbox_y(::amr_interfaces::msg::PersonTarget::_bbox_y_type arg)
  {
    msg_.bbox_y = std::move(arg);
    return Init_PersonTarget_bbox_w(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_bbox_x
{
public:
  explicit Init_PersonTarget_bbox_x(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_bbox_y bbox_x(::amr_interfaces::msg::PersonTarget::_bbox_x_type arg)
  {
    msg_.bbox_x = std::move(arg);
    return Init_PersonTarget_bbox_y(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_confidence
{
public:
  explicit Init_PersonTarget_confidence(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_bbox_x confidence(::amr_interfaces::msg::PersonTarget::_confidence_type arg)
  {
    msg_.confidence = std::move(arg);
    return Init_PersonTarget_bbox_x(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_lost
{
public:
  explicit Init_PersonTarget_lost(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_confidence lost(::amr_interfaces::msg::PersonTarget::_lost_type arg)
  {
    msg_.lost = std::move(arg);
    return Init_PersonTarget_confidence(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_locked
{
public:
  explicit Init_PersonTarget_locked(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_lost locked(::amr_interfaces::msg::PersonTarget::_locked_type arg)
  {
    msg_.locked = std::move(arg);
    return Init_PersonTarget_lost(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_target_id
{
public:
  explicit Init_PersonTarget_target_id(::amr_interfaces::msg::PersonTarget & msg)
  : msg_(msg)
  {}
  Init_PersonTarget_locked target_id(::amr_interfaces::msg::PersonTarget::_target_id_type arg)
  {
    msg_.target_id = std::move(arg);
    return Init_PersonTarget_locked(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

class Init_PersonTarget_header
{
public:
  Init_PersonTarget_header()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_PersonTarget_target_id header(::amr_interfaces::msg::PersonTarget::_header_type arg)
  {
    msg_.header = std::move(arg);
    return Init_PersonTarget_target_id(msg_);
  }

private:
  ::amr_interfaces::msg::PersonTarget msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::amr_interfaces::msg::PersonTarget>()
{
  return amr_interfaces::msg::builder::Init_PersonTarget_header();
}

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__MSG__DETAIL__PERSON_TARGET__BUILDER_HPP_
