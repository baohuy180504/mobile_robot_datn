#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"
SESSION="amr_slam"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate"
source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

if ! tmux has-session -t amr_device 2>/dev/null; then
  echo "Device is not running. Press START first."
  exit 2
fi

if tmux has-session -t amr_navigation 2>/dev/null; then
  echo "NAVIGATION is already running. Press STOP before switching to SLAM."
  exit 3
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "SLAM already running."
  exit 0
fi

tmux new-session -d -s "$SESSION" -n slam

tmux send-keys -t "$SESSION:slam" \
"cd $WS && source $HOME/mobile_robot/ai_ros_venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash && export ROS_DOMAIN_ID=0 && export ROS_LOCALHOST_ONLY=0 && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && ros2 launch amr_slam fusion_slam.launch.py" C-m

echo "SLAM mode started."