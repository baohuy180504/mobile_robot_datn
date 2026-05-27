#!/bin/bash
set -e

echo "=== AMR WEB / KEYBOARD TELEOP ==="

WS="$HOME/mobile_robot/ros2_ws"
TOPIC="${1:-${AMR_TELEOP_TOPIC:-/cmd_vel_safe}}"

cd "$WS"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true
source /opt/ros/humble/setup.bash
source install/setup.bash

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "[INFO] teleop_twist_keyboard output topic: $TOPIC"
echo "[INFO] Use keyboard in this terminal/tmux if attached."
echo "[INFO] Web buttons publish to the same topic when START CONTROL is ON."

ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:="$TOPIC"