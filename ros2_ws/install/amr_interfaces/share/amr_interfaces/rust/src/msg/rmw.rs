#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__msg__AiAlert() -> *const std::ffi::c_void;
}

#[link(name = "amr_interfaces__rosidl_generator_c")]
extern "C" {
    fn amr_interfaces__msg__AiAlert__init(msg: *mut AiAlert) -> bool;
    fn amr_interfaces__msg__AiAlert__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<AiAlert>, size: usize) -> bool;
    fn amr_interfaces__msg__AiAlert__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<AiAlert>);
    fn amr_interfaces__msg__AiAlert__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<AiAlert>, out_seq: *mut rosidl_runtime_rs::Sequence<AiAlert>) -> bool;
}

// Corresponds to amr_interfaces__msg__AiAlert
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]

/// AI alert message: fall, fire, smoke

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct AiAlert {

    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,

    /// FALL / FIRE / SMOKE / PERSON / UNKNOWN
    pub alert_type: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub confidence: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub active: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub robot_pose: geometry_msgs::msg::rmw::PoseStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub image_path: rosidl_runtime_rs::String,

}



impl Default for AiAlert {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !amr_interfaces__msg__AiAlert__init(&mut msg as *mut _) {
        panic!("Call to amr_interfaces__msg__AiAlert__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for AiAlert {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__AiAlert__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__AiAlert__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__AiAlert__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for AiAlert {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for AiAlert where Self: Sized {
  const TYPE_NAME: &'static str = "amr_interfaces/msg/AiAlert";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__msg__AiAlert() }
  }
}


#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__msg__AiMode() -> *const std::ffi::c_void;
}

#[link(name = "amr_interfaces__rosidl_generator_c")]
extern "C" {
    fn amr_interfaces__msg__AiMode__init(msg: *mut AiMode) -> bool;
    fn amr_interfaces__msg__AiMode__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<AiMode>, size: usize) -> bool;
    fn amr_interfaces__msg__AiMode__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<AiMode>);
    fn amr_interfaces__msg__AiMode__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<AiMode>, out_seq: *mut rosidl_runtime_rs::Sequence<AiMode>) -> bool;
}

// Corresponds to amr_interfaces__msg__AiMode
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]

/// AMR operation mode

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct AiMode {

    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::rmw::Time,


    // This member is not documented.
    #[allow(missing_docs)]
    pub mode: u8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub mode_name: rosidl_runtime_rs::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub detail: rosidl_runtime_rs::String,

}

impl AiMode {

    // This constant is not documented.
    #[allow(missing_docs)]
    pub const IDLE: u8 = 0;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const NAV_TO_ZONE: u8 = 1;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const FOLLOW_DETECTING: u8 = 2;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const FOLLOW_ACTIVE: u8 = 3;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const FOLLOW_STOPPED: u8 = 4;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const RETURN_TO_ZONE: u8 = 5;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const EMERGENCY_STOP: u8 = 6;

}


impl Default for AiMode {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !amr_interfaces__msg__AiMode__init(&mut msg as *mut _) {
        panic!("Call to amr_interfaces__msg__AiMode__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for AiMode {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__AiMode__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__AiMode__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__AiMode__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for AiMode {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for AiMode where Self: Sized {
  const TYPE_NAME: &'static str = "amr_interfaces/msg/AiMode";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__msg__AiMode() }
  }
}


#[link(name = "amr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__msg__PersonTarget() -> *const std::ffi::c_void;
}

#[link(name = "amr_interfaces__rosidl_generator_c")]
extern "C" {
    fn amr_interfaces__msg__PersonTarget__init(msg: *mut PersonTarget) -> bool;
    fn amr_interfaces__msg__PersonTarget__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<PersonTarget>, size: usize) -> bool;
    fn amr_interfaces__msg__PersonTarget__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<PersonTarget>);
    fn amr_interfaces__msg__PersonTarget__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<PersonTarget>, out_seq: *mut rosidl_runtime_rs::Sequence<PersonTarget>) -> bool;
}

// Corresponds to amr_interfaces__msg__PersonTarget
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]

/// Locked person target for following behavior

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct PersonTarget {

    // This member is not documented.
    #[allow(missing_docs)]
    pub header: std_msgs::msg::rmw::Header,


    // This member is not documented.
    #[allow(missing_docs)]
    pub target_id: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub locked: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub lost: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub confidence: f32,

    /// Bounding box on RGB image
    pub bbox_x: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub bbox_y: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub bbox_w: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub bbox_h: i32,

    /// Estimated target position
    pub position_camera: geometry_msgs::msg::rmw::PointStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub position_base: geometry_msgs::msg::rmw::PointStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub position_map: geometry_msgs::msg::rmw::PointStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub distance_m: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub angle_rad: f32,

}



impl Default for PersonTarget {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !amr_interfaces__msg__PersonTarget__init(&mut msg as *mut _) {
        panic!("Call to amr_interfaces__msg__PersonTarget__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for PersonTarget {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__PersonTarget__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__PersonTarget__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { amr_interfaces__msg__PersonTarget__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for PersonTarget {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for PersonTarget where Self: Sized {
  const TYPE_NAME: &'static str = "amr_interfaces/msg/PersonTarget";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__amr_interfaces__msg__PersonTarget() }
  }
}


