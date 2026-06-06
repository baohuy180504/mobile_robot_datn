#!/bin/bash
set -e

SESSION=amr_operator
WS="$HOME/mobile_robot/ros2_ws"
LOG="/tmp/amr_operator_stack.log"

{
  echo "=================================================="
  echo "$(date) - START AMR OPERATOR STACK"
  echo "=================================================="

  cd "$WS"

  source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true
  source /opt/ros/humble/setup.bash
  source install/setup.bash

  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
  export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
  export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"

  if tmux has-session -t "${SESSION}" 2>/dev/null; then
    echo "[INFO] AMR operator stack is already running in tmux session: ${SESSION}"
    exit 0
  fi

  ACTIVE_ENV="$WS/config/active_fusion_map.env"
  DEFAULT_MAP="$WS/src/amr_slam/maps/map3.yaml"
  DEFAULT_OCTOMAP="$WS/src/amr_slam/maps/map3_3d.bt"
  NAV_PARAMS="$WS/src/amr_navigation/config/nav2_params_fusion.yaml"

  MAP_YAML="$DEFAULT_MAP"
  OCTOMAP_BT="$DEFAULT_OCTOMAP"

  if [ -f "$ACTIVE_ENV" ]; then
    echo "[INFO] Loading active map env: $ACTIVE_ENV"
    # shellcheck disable=SC1090
    source "$ACTIVE_ENV"

    if [ -n "${MAP_YAML:-}" ]; then
      MAP_YAML="$MAP_YAML"
    elif [ -n "${MAP_FILE:-}" ]; then
      MAP_YAML="$MAP_FILE"
    fi

    if [ -n "${OCTOMAP_BT:-}" ]; then
      OCTOMAP_BT="$OCTOMAP_BT"
    elif [ -n "${OCTOMAP_FILE:-}" ]; then
      OCTOMAP_BT="$OCTOMAP_FILE"
    fi
  else
    echo "[WARN] Active map env not found, using default map3."
  fi

  if [ ! -f "$MAP_YAML" ]; then
    echo "[ERROR] 2D map YAML not found: $MAP_YAML"
    exit 1
  fi

  if [ ! -f "$OCTOMAP_BT" ]; then
    echo "[ERROR] 3D OctoMap BT not found: $OCTOMAP_BT"
    exit 1
  fi

  if [ ! -f "$NAV_PARAMS" ]; then
    echo "[ERROR] Nav2 params not found: $NAV_PARAMS"
    exit 1
  fi

  echo "[INFO] MAP_YAML   = $MAP_YAML"
  echo "[INFO] OCTOMAP_BT = $OCTOMAP_BT"
  echo "[INFO] NAV_PARAMS = $NAV_PARAMS"

  tmux new-session -d -s "${SESSION}" -n bringup
  tmux send-keys -t "${SESSION}:bringup" \
"cd $WS && source $HOME/mobile_robot/ai_ros_venv/bin/activate 2>/dev/null || true; source /opt/ros/humble/setup.bash; source install/setup.bash; export ROS_DOMAIN_ID=$ROS_DOMAIN_ID; export ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; ros2 launch amr_bringup bringup_fusion.launch.py" C-m

  tmux new-window -t "${SESSION}" -n navigation
  tmux send-keys -t "${SESSION}:navigation" \
"sleep 6; cd $WS && source $HOME/mobile_robot/ai_ros_venv/bin/activate 2>/dev/null || true; source /opt/ros/humble/setup.bash; source install/setup.bash; export ROS_DOMAIN_ID=$ROS_DOMAIN_ID; export ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; ros2 launch amr_navigation nav_fusion.launch.py map:=$MAP_YAML octomap:=$OCTOMAP_BT params_file:=$NAV_PARAMS" C-m

  tmux new-window -t "${SESSION}" -n ai
  tmux send-keys -t "${SESSION}:ai" \
"sleep 12; cd $WS && source $HOME/mobile_robot/ai_ros_venv/bin/activate; source /opt/ros/humble/setup.bash; source install/setup.bash; export ROS_DOMAIN_ID=$ROS_DOMAIN_ID; export ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; $WS/scripts/run_ai_follow.sh" C-m

  echo "[OK] AMR operator stack started."
  echo "[INFO] View logs: tmux attach -t ${SESSION}"
} 2>&1 | tee -a "$LOG"
