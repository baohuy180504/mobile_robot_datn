#!/bin/bash

source /opt/ros/humble/setup.bash
source ~/mobile_robot/ros2_ws/install/setup.bash

timeout 1 ros2 topic pub /cmd_vel_safe geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true

timeout 2 ros2 service call /amr_ai/set_mode amr_interfaces/srv/SetAiMode "{mode: 0, command: 'STOP_FOLLOW'}" >/dev/null 2>&1 || true

sleep 0.3

tmux kill-session -t amr_operator 2>/dev/null || true

timeout 1 ros2 topic pub /cmd_vel_safe geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true

echo "AMR operator stack stopped."
