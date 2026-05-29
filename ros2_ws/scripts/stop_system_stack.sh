#!/bin/bash
set -e

source "$HOME/mobile_robot/ai_ros_venv/bin/activate"
source /opt/ros/humble/setup.bash
source "$HOME/mobile_robot/ros2_ws/install/setup.bash"

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

timeout 1 ros2 topic pub /cmd_vel_safe geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true

timeout 2 ros2 service call /amr_ai/set_mode amr_interfaces/srv/SetAiMode "{mode: 0, command: 'STOP_FOLLOW'}" >/dev/null 2>&1 || true

tmux kill-session -t amr_navigation 2>/dev/null || true
tmux kill-session -t amr_slam 2>/dev/null || true
tmux kill-session -t amr_web_teleop 2>/dev/null || true
tmux kill-session -t amr_device 2>/dev/null || true
# Web camera streams
tmux kill-session -t amr_camera_web 2>/dev/null || true
tmux kill-session -t amr_alert_web 2>/dev/null || true
tmux kill-session -t amr_tracker_web 2>/dev/null || true
timeout 1 ros2 topic pub /cmd_vel_safe geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true

echo "System stopped."