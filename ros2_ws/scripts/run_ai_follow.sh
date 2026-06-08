#!/bin/bash
set -e

source ~/mobile_robot/ai_ros_venv/bin/activate
source /opt/ros/humble/setup.bash
source ~/mobile_robot/ros2_ws/install/setup.bash

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"

ros2 launch amr_ai amr_ai.launch.py \
  params_file:=$HOME/mobile_robot/ros2_ws/install/amr_ai/share/amr_ai/config/ai_params.yaml \
  start_mode_manager:=true \
  start_person_tracker:=true \
  start_follow_goal:=false \
  start_follow_servo:=true \
  start_cmd_vel_safety_mux:=true \
  start_ai_detector:=true \
  start_auto_initial_pose:=true \
  start_auto_localizer:=true \
  start_esp32_gateway:=true
