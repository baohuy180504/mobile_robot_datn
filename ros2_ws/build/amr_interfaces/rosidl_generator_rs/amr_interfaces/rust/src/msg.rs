#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



// Corresponds to amr_interfaces__msg__AiAlert
/// AI alert message: fall, fire, smoke

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct AiAlert {

    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::Time,

    /// FALL / FIRE / SMOKE / PERSON / UNKNOWN
    pub alert_type: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub confidence: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub message: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub active: bool,


    // This member is not documented.
    #[allow(missing_docs)]
    pub robot_pose: geometry_msgs::msg::PoseStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub image_path: std::string::String,

}



impl Default for AiAlert {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::AiAlert::default())
  }
}

impl rosidl_runtime_rs::Message for AiAlert {
  type RmwMsg = super::msg::rmw::AiAlert;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Owned(msg.stamp)).into_owned(),
        alert_type: msg.alert_type.as_str().into(),
        confidence: msg.confidence,
        message: msg.message.as_str().into(),
        active: msg.active,
        robot_pose: geometry_msgs::msg::PoseStamped::into_rmw_message(std::borrow::Cow::Owned(msg.robot_pose)).into_owned(),
        image_path: msg.image_path.as_str().into(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Borrowed(&msg.stamp)).into_owned(),
        alert_type: msg.alert_type.as_str().into(),
      confidence: msg.confidence,
        message: msg.message.as_str().into(),
      active: msg.active,
        robot_pose: geometry_msgs::msg::PoseStamped::into_rmw_message(std::borrow::Cow::Borrowed(&msg.robot_pose)).into_owned(),
        image_path: msg.image_path.as_str().into(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      stamp: builtin_interfaces::msg::Time::from_rmw_message(msg.stamp),
      alert_type: msg.alert_type.to_string(),
      confidence: msg.confidence,
      message: msg.message.to_string(),
      active: msg.active,
      robot_pose: geometry_msgs::msg::PoseStamped::from_rmw_message(msg.robot_pose),
      image_path: msg.image_path.to_string(),
    }
  }
}


// Corresponds to amr_interfaces__msg__AiMode
/// AMR operation mode

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct AiMode {

    // This member is not documented.
    #[allow(missing_docs)]
    pub stamp: builtin_interfaces::msg::Time,


    // This member is not documented.
    #[allow(missing_docs)]
    pub mode: u8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub mode_name: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub detail: std::string::String,

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
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::AiMode::default())
  }
}

impl rosidl_runtime_rs::Message for AiMode {
  type RmwMsg = super::msg::rmw::AiMode;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Owned(msg.stamp)).into_owned(),
        mode: msg.mode,
        mode_name: msg.mode_name.as_str().into(),
        detail: msg.detail.as_str().into(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Borrowed(&msg.stamp)).into_owned(),
      mode: msg.mode,
        mode_name: msg.mode_name.as_str().into(),
        detail: msg.detail.as_str().into(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      stamp: builtin_interfaces::msg::Time::from_rmw_message(msg.stamp),
      mode: msg.mode,
      mode_name: msg.mode_name.to_string(),
      detail: msg.detail.to_string(),
    }
  }
}


// Corresponds to amr_interfaces__msg__PersonTarget
/// Locked person target for following behavior

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct PersonTarget {

    // This member is not documented.
    #[allow(missing_docs)]
    pub header: std_msgs::msg::Header,


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
    pub position_camera: geometry_msgs::msg::PointStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub position_base: geometry_msgs::msg::PointStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub position_map: geometry_msgs::msg::PointStamped,


    // This member is not documented.
    #[allow(missing_docs)]
    pub distance_m: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub angle_rad: f32,

}



impl Default for PersonTarget {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::PersonTarget::default())
  }
}

impl rosidl_runtime_rs::Message for PersonTarget {
  type RmwMsg = super::msg::rmw::PersonTarget;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        header: std_msgs::msg::Header::into_rmw_message(std::borrow::Cow::Owned(msg.header)).into_owned(),
        target_id: msg.target_id,
        locked: msg.locked,
        lost: msg.lost,
        confidence: msg.confidence,
        bbox_x: msg.bbox_x,
        bbox_y: msg.bbox_y,
        bbox_w: msg.bbox_w,
        bbox_h: msg.bbox_h,
        position_camera: geometry_msgs::msg::PointStamped::into_rmw_message(std::borrow::Cow::Owned(msg.position_camera)).into_owned(),
        position_base: geometry_msgs::msg::PointStamped::into_rmw_message(std::borrow::Cow::Owned(msg.position_base)).into_owned(),
        position_map: geometry_msgs::msg::PointStamped::into_rmw_message(std::borrow::Cow::Owned(msg.position_map)).into_owned(),
        distance_m: msg.distance_m,
        angle_rad: msg.angle_rad,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        header: std_msgs::msg::Header::into_rmw_message(std::borrow::Cow::Borrowed(&msg.header)).into_owned(),
      target_id: msg.target_id,
      locked: msg.locked,
      lost: msg.lost,
      confidence: msg.confidence,
      bbox_x: msg.bbox_x,
      bbox_y: msg.bbox_y,
      bbox_w: msg.bbox_w,
      bbox_h: msg.bbox_h,
        position_camera: geometry_msgs::msg::PointStamped::into_rmw_message(std::borrow::Cow::Borrowed(&msg.position_camera)).into_owned(),
        position_base: geometry_msgs::msg::PointStamped::into_rmw_message(std::borrow::Cow::Borrowed(&msg.position_base)).into_owned(),
        position_map: geometry_msgs::msg::PointStamped::into_rmw_message(std::borrow::Cow::Borrowed(&msg.position_map)).into_owned(),
      distance_m: msg.distance_m,
      angle_rad: msg.angle_rad,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      header: std_msgs::msg::Header::from_rmw_message(msg.header),
      target_id: msg.target_id,
      locked: msg.locked,
      lost: msg.lost,
      confidence: msg.confidence,
      bbox_x: msg.bbox_x,
      bbox_y: msg.bbox_y,
      bbox_w: msg.bbox_w,
      bbox_h: msg.bbox_h,
      position_camera: geometry_msgs::msg::PointStamped::from_rmw_message(msg.position_camera),
      position_base: geometry_msgs::msg::PointStamped::from_rmw_message(msg.position_base),
      position_map: geometry_msgs::msg::PointStamped::from_rmw_message(msg.position_map),
      distance_m: msg.distance_m,
      angle_rad: msg.angle_rad,
    }
  }
}


