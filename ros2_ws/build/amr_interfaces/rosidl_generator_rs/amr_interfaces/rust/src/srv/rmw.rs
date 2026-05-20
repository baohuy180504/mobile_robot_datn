#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SetAiMode_Request() -> *const std::ffi::c_void;
}

#[link(name = "amr_interfaces__rosidl_generator_c")]
extern "C" {
    fn amr_interfaces__srv__SetAiMode_Request__init(msg: *mut SetAiMode_Request) -> bool;
    fn amr_interfaces__srv__SetAiMode_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<SetAiMode_Request>, size: usize) -> bool;
    fn amr_interfaces__srv__SetAiMode_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<SetAiMode_Request>);
    fn amr_interfaces__srv__SetAiMode_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<SetAiMode_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<SetAiMode_Request>) -> bool;
}

// Corresponds to amr_interfaces__srv__SetAiMode_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SetAiMode_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub mode: u8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub command: rosidl_runtime_rs::String,

}



impl Default for SetAiMode_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !amr_interfaces__srv__SetAiMode_Request__init(&mut msg as *mut _) {
        panic!("Call to amr_interfaces__srv__SetAiMode_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for SetAiMode_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SetAiMode_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SetAiMode_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SetAiMode_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for SetAiMode_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for SetAiMode_Request where Self: Sized {
  const TYPE_NAME: &'static str = "amr_interfaces/srv/SetAiMode_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SetAiMode_Request() }
  }
}


#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SetAiMode_Response() -> *const std::ffi::c_void;
}

#[link(name = "amr_interfaces__rosidl_generator_c")]
extern "C" {
    fn amr_interfaces__srv__SetAiMode_Response__init(msg: *mut SetAiMode_Response) -> bool;
    fn amr_interfaces__srv__SetAiMode_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<SetAiMode_Response>, size: usize) -> bool;
    fn amr_interfaces__srv__SetAiMode_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<SetAiMode_Response>);
    fn amr_interfaces__srv__SetAiMode_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<SetAiMode_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<SetAiMode_Response>) -> bool;
}

// Corresponds to amr_interfaces__srv__SetAiMode_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SetAiMode_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub success: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub current_mode: u8,

}



impl Default for SetAiMode_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !amr_interfaces__srv__SetAiMode_Response__init(&mut msg as *mut _) {
        panic!("Call to amr_interfaces__srv__SetAiMode_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for SetAiMode_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SetAiMode_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SetAiMode_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SetAiMode_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for SetAiMode_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for SetAiMode_Response where Self: Sized {
  const TYPE_NAME: &'static str = "amr_interfaces/srv/SetAiMode_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SetAiMode_Response() }
  }
}


#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SelectZone_Request() -> *const std::ffi::c_void;
}

#[link(name = "amr_interfaces__rosidl_generator_c")]
extern "C" {
    fn amr_interfaces__srv__SelectZone_Request__init(msg: *mut SelectZone_Request) -> bool;
    fn amr_interfaces__srv__SelectZone_Request__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<SelectZone_Request>, size: usize) -> bool;
    fn amr_interfaces__srv__SelectZone_Request__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<SelectZone_Request>);
    fn amr_interfaces__srv__SelectZone_Request__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<SelectZone_Request>, out_seq: *mut rosidl_runtime_rs::Sequence<SelectZone_Request>) -> bool;
}

// Corresponds to amr_interfaces__srv__SelectZone_Request
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SelectZone_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub zone_name: rosidl_runtime_rs::String,

}



impl Default for SelectZone_Request {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !amr_interfaces__srv__SelectZone_Request__init(&mut msg as *mut _) {
        panic!("Call to amr_interfaces__srv__SelectZone_Request__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for SelectZone_Request {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SelectZone_Request__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SelectZone_Request__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SelectZone_Request__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for SelectZone_Request {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for SelectZone_Request where Self: Sized {
  const TYPE_NAME: &'static str = "amr_interfaces/srv/SelectZone_Request";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SelectZone_Request() }
  }
}


#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SelectZone_Response() -> *const std::ffi::c_void;
}

#[link(name = "amr_interfaces__rosidl_generator_c")]
extern "C" {
    fn amr_interfaces__srv__SelectZone_Response__init(msg: *mut SelectZone_Response) -> bool;
    fn amr_interfaces__srv__SelectZone_Response__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<SelectZone_Response>, size: usize) -> bool;
    fn amr_interfaces__srv__SelectZone_Response__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<SelectZone_Response>);
    fn amr_interfaces__srv__SelectZone_Response__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<SelectZone_Response>, out_seq: *mut rosidl_runtime_rs::Sequence<SelectZone_Response>) -> bool;
}

// Corresponds to amr_interfaces__srv__SelectZone_Response
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SelectZone_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub accepted: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub goal: geometry_msgs::msg::rmw::PoseStamped,

}



impl Default for SelectZone_Response {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !amr_interfaces__srv__SelectZone_Response__init(&mut msg as *mut _) {
        panic!("Call to amr_interfaces__srv__SelectZone_Response__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for SelectZone_Response {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SelectZone_Response__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SelectZone_Response__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__srv__SelectZone_Response__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for SelectZone_Response {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for SelectZone_Response where Self: Sized {
  const TYPE_NAME: &'static str = "amr_interfaces/srv/SelectZone_Response";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__srv__SelectZone_Response() }
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


