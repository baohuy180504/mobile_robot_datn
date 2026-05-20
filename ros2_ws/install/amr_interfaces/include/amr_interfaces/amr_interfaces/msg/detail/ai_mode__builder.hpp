// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from amr_interfaces:msg/AiMode.idl
// generated code does not contain a copyright notice

#ifndef AMR_INTERFACES__MSG__DETAIL__AI_MODE__BUILDER_HPP_
#define AMR_INTERFACES__MSG__DETAIL__AI_MODE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "amr_interfaces/msg/detail/ai_mode__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace amr_interfaces
{

namespace msg
{

namespace builder
{

class Init_AiMode_detail
{
public:
  explicit Init_AiMode_detail(::amr_interfaces::msg::AiMode & msg)
  : msg_(msg)
  {}
  ::amr_interfaces::msg::AiMode detail(::amr_interfaces::msg::AiMode::_detail_type arg)
  {
    msg_.detail = std::move(arg);
    return std::move(msg_);
  }

private:
  ::amr_interfaces::msg::AiMode msg_;
};

class Init_AiMode_mode_name
{
public:
  explicit Init_AiMode_mode_name(::amr_interfaces::msg::AiMode & msg)
  : msg_(msg)
  {}
  Init_AiMode_detail mode_name(::amr_interfaces::msg::AiMode::_mode_name_type arg)
  {
    msg_.mode_name = std::move(arg);
    return Init_AiMode_detail(msg_);
  }

private:
  ::amr_interfaces::msg::AiMode msg_;
};

class Init_AiMode_mode
{
public:
  explicit Init_AiMode_mode(::amr_interfaces::msg::AiMode & msg)
  : msg_(msg)
  {}
  Init_AiMode_mode_name mode(::amr_interfaces::msg::AiMode::_mode_type arg)
  {
    msg_.mode = std::move(arg);
    return Init_AiMode_mode_name(msg_);
  }

private:
  ::amr_interfaces::msg::AiMode msg_;
};

class Init_AiMode_stamp
{
public:
  Init_AiMode_stamp()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_AiMode_mode stamp(::amr_interfaces::msg::AiMode::_stamp_type arg)
  {
    msg_.stamp = std::move(arg);
    return Init_AiMode_mode(msg_);
  }

private:
  ::amr_interfaces::msg::AiMode msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::amr_interfaces::msg::AiMode>()
{
  return amr_interfaces::msg::builder::Init_AiMode_stamp();
}

}  // namespace amr_interfaces

#endif  // AMR_INTERFACES__MSG__DETAIL__AI_MODE__BUILDER_HPP_
