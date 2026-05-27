#!/bin/bash
set -e

source "$HOME/mobile_robot/ai_ros_venv/bin/activate"
source /opt/ros/humble/setup.bash
source "$HOME/mobile_robot/ros2_ws/install/setup.bash"

# Dừng xe an toàn
timeout 1 ros2 topic pub /cmd_vel_safe geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true

# Tắt các mode phụ trước rồi tắt device
tmux kill-session -t amr_navigation 2>/dev/null || true
tmux kill-session -t amr_slam 2>/dev/null || true
tmux kill-session -t amr_device 2>/dev/null || true

echo "AMR device stack stopped."