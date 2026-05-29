#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"
SESSION="amr_device"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate"
source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Device already running."
  exit 0
fi

tmux new-session -d -s "$SESSION" -n bringup

tmux send-keys -t "$SESSION:bringup" \
"cd $WS && source $HOME/mobile_robot/ai_ros_venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash && export ROS_DOMAIN_ID=0 && export ROS_LOCALHOST_ONLY=0 && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && ros2 launch amr_bringup bringup_fusion.launch.py" C-m

# ==========================================================
# Camera web stream: chạy ngay khi START, dùng cho mọi chế độ
# ==========================================================
if ! tmux has-session -t amr_camera_web 2>/dev/null; then
  tmux new-session -d -s amr_camera_web "$HOME/mobile_robot/ros2_ws/scripts/run_camera_web.sh"
  echo "[INFO] Started amr_camera_web"
else
  echo "[INFO] amr_camera_web already running"
fi

echo "Device started."