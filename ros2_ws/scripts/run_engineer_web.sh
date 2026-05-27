#!/bin/bash
set -e

source ~/mobile_robot/ai_ros_venv/bin/activate
source /opt/ros/humble/setup.bash
source ~/mobile_robot/ros2_ws/install/setup.bash

export AMR_WS="$HOME/mobile_robot/ros2_ws"

# Ép cùng môi trường ROS với terminal SSH đang chạy tốt
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

~/mobile_robot/ai_ros_venv/bin/python3 -m amr_ai.web.engineer_web_server \
  --host 0.0.0.0 \
  --port 8080