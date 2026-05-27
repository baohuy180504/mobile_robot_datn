#!/bin/bash
set -e

SESSION="amr_web_rosbridge"
WS="$HOME/mobile_robot/ros2_ws"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate"
source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "ROSBridge already running: $SESSION"
  echo "ROSBridge WebSocket: ws://$(hostname -I | awk '{print $1}'):9090"
  exit 0
fi

tmux new-session -d -s "$SESSION" -n rosbridge

tmux send-keys -t "$SESSION:rosbridge" \
"source $HOME/mobile_robot/ai_ros_venv/bin/activate && \
source /opt/ros/humble/setup.bash && \
source $WS/install/setup.bash && \
export ROS_DOMAIN_ID=0 && \
export ROS_LOCALHOST_ONLY=0 && \
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && \
ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090" C-m

sleep 1

echo "ROSBridge started."
echo "ROSBridge WebSocket: ws://$(hostname -I | awk '{print $1}'):9090"