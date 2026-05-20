// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from amr_interfaces:srv/SetAiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__BUILDER_HPP_
#define AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "amr_interfaces/srv/detail/set_ai_mode__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace amr_interfaces
{

namespace srv
{

namespace builder
{

class Init_SetAiMode_Request_command
{
public:
  explicit Init_SetAiMode_Request_command(::amr_interfaces::srv::SetAiMode_Request & msg)
  : msg_(msg)
  {}
  ::amr_interfaces::srv::SetAiMode_Request command(::amr_interfaces::srv::SetAiMode_Request::_command_type arg)
  {
    msg_.command = std::move(arg);
    return std::move(msg_);
  }

private:
  ::amr_interfaces::srv::SetAiMode_Request msg_;
};

class Init_SetAiMode_Request_mode
{
public:
  Init_SetAiMode_Request_mode()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_SetAiMode_Request_command mode(::amr_interfaces::srv::SetAiMode_Request::_mode_type arg)
  {
    msg_.mode = std::move(arg);
    return Init_SetAiMode_Request_command(msg_);
  }

private:
  ::amr_interfaces::srv::SetAiMode_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::amr_interfaces::srv::SetAiMode_Request>()
{
  return amr_interfaces::srv::builder::Init_SetAiMode_Request_mode();
}

}  // namespace amr_interfaces


namespace amr_interfaces
{

namespace srv
{

namespace builder
{

class Init_SetAiMode_Response_current_mode
{
public:
  explicit Init_SetAiMode_Response_current_mode(::amr_interfaces::srv::SetAiMode_Response & msg)
  : msg_(msg)
  {}
  ::amr_interfaces::srv::SetAiMode_Response current_mode(::amr_interfaces::srv::SetAiMode_Response::_current_mode_type arg)
  {
    msg_.current_mode = std::move(arg);
    return std::move(msg_);
  }

private:
  ::amr_interfaces::srv::SetAiMode_Response msg_;
};

class Init_SetAiMode_Response_message
{
public:
  explicit Init_SetAiMode_Response_message(::amr_interfaces::srv::SetAiMode_Response & msg)
  : msg_(msg)
  {}
  Init_SetAiMode_Response_current_mode message(::amr_interfaces::srv::SetAiMode_Response::_message_type arg)
  {
    msg_.message = std::move(arg);
    return Init_SetAiMode_Response_current_mode(msg_);
  }

private:
  ::amr_interfaces::srv::SetAiMode_Response msg_;
};

class Init_SetAiMode_Response_success
{
public:
  Init_SetAiMode_Response_success()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_SetAiMode_Response_message success(::amr_interfaces::srv::SetAiMode_Response::_success_type arg)
  {
    msg_.success = std::move(arg);
    return Init_SetAiMode_Response_message(msg_);
  }

private:
  ::amr_interfaces::srv::SetAiMode_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::amr_interfaces::srv::SetAiMode_Response>()
{
  return amr_interfaces::srv::builder::Init_SetAiMode_Response_success();
}

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__SRV__DETAIL__SET_AI_MODE__BUILDER_HPP_
