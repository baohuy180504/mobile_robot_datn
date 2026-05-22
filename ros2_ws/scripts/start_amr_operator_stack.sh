#!/bin/bash
set -e

SESSION=amr_operator

source /opt/ros/humble/setup.bash
source ~/mobile_robot/ros2_ws/install/setup.bash

if tmux has-session -t ${SESSION} 2>/dev/null; then
  echo "AMR operator stack is already running in tmux session: ${SESSION}"
  exit 0
fi

MAP_YAML="$HOME/mobile_robot/ros2_ws/src/amr_slam/maps/map3.yaml"
OCTOMAP_BT="$HOME/mobile_robot/ros2_ws/src/amr_slam/maps/map3_3d.bt"
NAV_PARAMS="$HOME/mobile_robot/ros2_ws/src/amr_navigation/config/nav2_params_fusion.yaml"

tmux new-session -d -s ${SESSION} -n bringup
tmux send-keys -t ${SESSION}:bringup \
"source /opt/ros/humble/setup.bash && source ~/mobile_robot/ros2_ws/install/setup.bash && ros2 launch amr_bringup bringup_fusion.launch.py" C-m

tmux new-window -t ${SESSION} -n navigation
tmux send-keys -t ${SESSION}:navigation \
"sleep 5 && source /opt/ros/humble/setup.bash && source ~/mobile_robot/ros2_ws/install/setup.bash && ros2 launch amr_navigation nav_fusion.launch.py map:=${MAP_YAML} octomap:=${OCTOMAP_BT} params_file:=${NAV_PARAMS}" C-m

tmux new-window -t ${SESSION} -n ai
tmux send-keys -t ${SESSION}:ai \
"sleep 10 && source ~/mobile_robot/ai_ros_venv/bin/activate && source /opt/ros/humble/setup.bash && source ~/mobile_robot/ros2_ws/install/setup.bash && ~/mobile_robot/ros2_ws/scripts/run_ai_follow.sh" C-m

echo "AMR operator stack started."
echo "View logs: tmux attach -t ${SESSION}"
