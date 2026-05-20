#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};




// Corresponds to amr_interfaces__srv__SetAiMode_Request

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SetAiMode_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub mode: u8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub command: std::string::String,

}



impl Default for SetAiMode_Request {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::SetAiMode_Request::default())
  }
}

impl rosidl_runtime_rs::Message for SetAiMode_Request {
  type RmwMsg = super::srv::rmw::SetAiMode_Request;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        mode: msg.mode,
        command: msg.command.as_str().into(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      mode: msg.mode,
        command: msg.command.as_str().into(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      mode: msg.mode,
      command: msg.command.to_string(),
    }
  }
}


// Corresponds to amr_interfaces__srv__SetAiMode_Response

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SetAiMode_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub current_mode: u8,

}



impl Default for SetAiMode_Response {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::SetAiMode_Response::default())
  }
}

impl rosidl_runtime_rs::Message for SetAiMode_Response {
  type RmwMsg = super::srv::rmw::SetAiMode_Response;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        success: msg.success,
        message: msg.message.as_str().into(),
        current_mode: msg.current_mode,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      success: msg.success,
        message: msg.message.as_str().into(),
      current_mode: msg.current_mode,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      success: msg.success,
      message: msg.message.to_string(),
      current_mode: msg.current_mode,
    }
  }
}


// Corresponds to amr_interfaces__srv__SelectZone_Request

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SelectZone_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub zone_name: std::string::String,

}



impl Default for SelectZone_Request {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::SelectZone_Request::default())
  }
}

impl rosidl_runtime_rs::Message for SelectZone_Request {
  type RmwMsg = super::srv::rmw::SelectZone_Request;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        zone_name: msg.zone_name.as_str().into(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        zone_name: msg.zone_name.as_str().into(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      zone_name: msg.zone_name.to_string(),
    }
  }
}


// Corresponds to amr_interfaces__srv__SelectZone_Response

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SelectZone_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: geometry_msgs::msg::PoseStamped,

}



impl Default for SelectZone_Response {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::SelectZone_Response::default())
  }
}

impl rosidl_runtime_rs::Message for SelectZone_Response {
  type RmwMsg = super::srv::rmw::SelectZone_Response;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        accepted: msg.accepted,
        message: msg.message.as_str().into(),
        goal: geometry_msgs::msg::PoseStamped::into_rmw_message(std::borrow::Cow::Owned(msg.goal)).into_owned(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      accepted: msg.accepted,
        message: msg.message.as_str().into(),
        goal: geometry_msgs::msg::PoseStamped::into_rmw_message(std::borrow::Cow::Borrowed(&msg.goal)).into_owned(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      accepted: msg.accepted,
      message: msg.message.to_string(),
      goal: geometry_msgs::msg::PoseStamped::from_rmw_message(msg.goal),
    }
  }
}






#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__amr_interfaces__srv__SetAiMode() -> *const std::ffi::c_void;
}

// Corresponds to amr_interfaces__srv__SetAiMode
#[allow(missing_docs, non_camel_case_types)]
pub struct SetAiMode;

impl rosidl_runtime_rs::Service for SetAiMode {
    type Request = SetAiMode_Request;
    type Response = SetAiMode_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__amr_interfaces__srv__SetAiMode() }
    }
}




#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__amr_interfaces__srv__SelectZone() -> *const std::ffi::c_void;
}

// Corresponds to amr_interfaces__srv__SelectZone
#[allow(missing_docs, non_camel_case_types)]
pub struct SelectZone;

impl rosidl_runtime_rs::Service for SelectZone {
    type Request = SelectZone_Request;
    type Response = SelectZone_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__amr_interfaces__srv__SelectZone() }
    }
}


