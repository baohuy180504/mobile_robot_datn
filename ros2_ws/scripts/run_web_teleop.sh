#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"
CMD_TOPIC="/cmd_vel_safe"

cd "$WS"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true
source /opt/ros/humble/setup.bash
source install/setup.bash

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "=== AMR WEB TELEOP ==="
echo "Publish topic: $CMD_TOPIC"
echo "Key topic: /amr_web_teleop/key"
echo "Speed topic: /amr_web_teleop/speed"

python3 "$WS/scripts/web_teleop_node.py" --ros-args \
  -p cmd_vel_topic:="$CMD_TOPIC" \
  -p publish_rate_hz:=20.0 \
  -p key_timeout_s:=0.35
