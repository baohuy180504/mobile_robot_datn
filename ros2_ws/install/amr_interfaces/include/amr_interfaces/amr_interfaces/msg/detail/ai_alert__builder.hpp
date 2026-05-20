// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from amr_interfaces:msg/AiAlert.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_ALERT__BUILDER_HPP_
#define AMR_INTERFACES__MSG__DETAIL__AI_ALERT__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "amr_interfaces/msg/detail/ai_alert__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace amr_interfaces
{

namespace msg
{

namespace builder
{

class Init_AiAlert_image_path
{
public:
  explicit Init_AiAlert_image_path(::amr_interfaces::msg::AiAlert & msg)
  : msg_(msg)
  {}
  ::amr_interfaces::msg::AiAlert image_path(::amr_interfaces::msg::AiAlert::_image_path_type arg)
  {
    msg_.image_path = std::move(arg);
    return std::move(msg_);
  }

private:
  ::amr_interfaces::msg::AiAlert msg_;
};

class Init_AiAlert_robot_pose
{
public:
  explicit Init_AiAlert_robot_pose(::amr_interfaces::msg::AiAlert & msg)
  : msg_(msg)
  {}
  Init_AiAlert_image_path robot_pose(::amr_interfaces::msg::AiAlert::_robot_pose_type arg)
  {
    msg_.robot_pose = std::move(arg);
    return Init_AiAlert_image_path(msg_);
  }

private:
  ::amr_interfaces::msg::AiAlert msg_;
};

class Init_AiAlert_active
{
public:
  explicit Init_AiAlert_active(::amr_interfaces::msg::AiAlert & msg)
  : msg_(msg)
  {}
  Init_AiAlert_robot_pose active(::amr_interfaces::msg::AiAlert::_active_type arg)
  {
    msg_.active = std::move(arg);
    return Init_AiAlert_robot_pose(msg_);
  }

private:
  ::amr_interfaces::msg::AiAlert msg_;
};

class Init_AiAlert_message
{
public:
  explicit Init_AiAlert_message(::amr_interfaces::msg::AiAlert & msg)
  : msg_(msg)
  {}
  Init_AiAlert_active message(::amr_interfaces::msg::AiAlert::_message_type arg)
  {
    msg_.message = std::move(arg);
    return Init_AiAlert_active(msg_);
  }

private:
  ::amr_interfaces::msg::AiAlert msg_;
};

class Init_AiAlert_confidence
{
public:
  explicit Init_AiAlert_confidence(::amr_interfaces::msg::AiAlert & msg)
  : msg_(msg)
  {}
  Init_AiAlert_message confidence(::amr_interfaces::msg::AiAlert::_confidence_type arg)
  {
    msg_.confidence = std::move(arg);
    return Init_AiAlert_message(msg_);
  }

private:
  ::amr_interfaces::msg::AiAlert msg_;
};

class Init_AiAlert_alert_type
{
public:
  explicit Init_AiAlert_alert_type(::amr_interfaces::msg::AiAlert & msg)
  : msg_(msg)
  {}
  Init_AiAlert_confidence alert_type(::amr_interfaces::msg::AiAlert::_alert_type_type arg)
  {
    msg_.alert_type = std::move(arg);
    return Init_AiAlert_confidence(msg_);
  }

private:
  ::amr_interfaces::msg::AiAlert msg_;
};

class Init_AiAlert_stamp
{
public:
  Init_AiAlert_stamp()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_AiAlert_alert_type stamp(::amr_interfaces::msg::AiAlert::_stamp_type arg)
  {
    msg_.stamp = std::move(arg);
    return Init_AiAlert_alert_type(msg_);
  }

private:
  ::amr_interfaces::msg::AiAlert msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::amr_interfaces::msg::AiAlert>()
{
  return amr_interfaces::msg::builder::Init_AiAlert_stamp();
}

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_ALERT__BUILDER_HPP_
