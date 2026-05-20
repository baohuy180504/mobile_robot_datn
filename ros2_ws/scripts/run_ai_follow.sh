#!/bin/bash
set -e

source ~/mobile_robot/ai_ros_venv/bin/activate
source /opt/ros/humble/setup.bash
source ~/mobile_robot/ros2_ws/install/setup.bash

ros2 launch amr_ai amr_ai.launch.py \
  params_file:=$HOME/mobile_robot/ros2_ws/install/amr_ai/share/amr_ai/config/ai_params.yaml \
  start_mode_manager:=true \
  start_person_tracker:=true \
  start_follow_goal:=false \
  start_follow_servo:=true \
  start_cmd_vel_safety_mux:=true \
  start_esp32_gateway:=true
