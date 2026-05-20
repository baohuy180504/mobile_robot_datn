// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from amr_interfaces:srv/SelectZone.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__BUILDER_HPP_
#define AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "amr_interfaces/srv/detail/select_zone__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace amr_interfaces
{

namespace srv
{

namespace builder
{

class Init_SelectZone_Request_zone_name
{
public:
  Init_SelectZone_Request_zone_name()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::amr_interfaces::srv::SelectZone_Request zone_name(::amr_interfaces::srv::SelectZone_Request::_zone_name_type arg)
  {
    msg_.zone_name = std::move(arg);
    return std::move(msg_);
  }

private:
  ::amr_interfaces::srv::SelectZone_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::amr_interfaces::srv::SelectZone_Request>()
{
  return amr_interfaces::srv::builder::Init_SelectZone_Request_zone_name();
}

}  // namespace amr_interfaces


namespace amr_interfaces
{

namespace srv
{

namespace builder
{

class Init_SelectZone_Response_goal
{
public:
  explicit Init_SelectZone_Response_goal(::amr_interfaces::srv::SelectZone_Response & msg)
  : msg_(msg)
  {}
  ::amr_interfaces::srv::SelectZone_Response goal(::amr_interfaces::srv::SelectZone_Response::_goal_type arg)
  {
    msg_.goal = std::move(arg);
    return std::move(msg_);
  }

private:
  ::amr_interfaces::srv::SelectZone_Response msg_;
};

class Init_SelectZone_Response_message
{
public:
  explicit Init_SelectZone_Response_message(::amr_interfaces::srv::SelectZone_Response & msg)
  : msg_(msg)
  {}
  Init_SelectZone_Response_goal message(::amr_interfaces::srv::SelectZone_Response::_message_type arg)
  {
    msg_.message = std::move(arg);
    return Init_SelectZone_Response_goal(msg_);
  }

private:
  ::amr_interfaces::srv::SelectZone_Response msg_;
};

class Init_SelectZone_Response_accepted
{
public:
  Init_SelectZone_Response_accepted()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_SelectZone_Response_message accepted(::amr_interfaces::srv::SelectZone_Response::_accepted_type arg)
  {
    msg_.accepted = std::move(arg);
    return Init_SelectZone_Response_message(msg_);
  }

private:
  ::amr_interfaces::srv::SelectZone_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::amr_interfaces::srv::SelectZone_Response>()
{
  return amr_interfaces::srv::builder::Init_SelectZone_Response_accepted();
}

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__SRV__DETAIL__SELECT_ZONE__BUILDER_HPP_
