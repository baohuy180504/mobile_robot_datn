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
  MAP_DIR="$WS/src/amr_slam/maps"
  NAV_PARAMS="$WS/src/amr_navigation/config/nav2_params_fusion.yaml"
  AI_PARAMS="$WS/install/amr_ai/share/amr_ai/config/ai_params.yaml"

  # ==========================================================
  # ESP32 Alert Display config
  # ==========================================================
  ESP32_ALERT_IP="${ESP32_ALERT_IP:-192.168.0.146}"
  ESP32_ALERT_UDP_PORT="${ESP32_ALERT_UDP_PORT:-4210}"
  ESP32_ALERT_TCP_PORT="${ESP32_ALERT_TCP_PORT:-4211}"

  MAP_NAME=""
  MAP_YAML=""
  OCTOMAP_BT=""

  if [ -f "$ACTIVE_ENV" ]; then
    echo "[INFO] Loading active map env: $ACTIVE_ENV"
    # shellcheck disable=SC1090
    source "$ACTIVE_ENV"

    if [ -z "${MAP_YAML:-}" ] && [ -n "${MAP_FILE:-}" ]; then
      MAP_YAML="$MAP_FILE"
    fi

    if [ -z "${OCTOMAP_BT:-}" ] && [ -n "${OCTOMAP_FILE:-}" ]; then
      OCTOMAP_BT="$OCTOMAP_FILE"
    fi

    if [ -z "${MAP_NAME:-}" ] && [ -n "${MAP_YAML:-}" ]; then
      MAP_NAME="$(basename "$MAP_YAML" .yaml)"
    fi
  else
    echo "[WARN] Active map env not found. Searching newest valid fusion map."
  fi

  valid_map() {
    [ -n "${MAP_NAME:-}" ] && [ -f "${MAP_YAML:-}" ] && [ -f "${OCTOMAP_BT:-}" ]
  }

  # Nếu active map bị thiếu/xóa hoặc chưa chọn, tự chọn map 2D+3D mới nhất.
  # Điều này đồng bộ hành vi GUI operator với webserver NAVIGATION.
  if ! valid_map; then
    echo "[WARN] Active map missing/invalid. Searching newest valid 2D+3D map in $MAP_DIR"

    MAP_NAME=""
    MAP_YAML=""
    OCTOMAP_BT=""

    while IFS= read -r yaml_file; do
      name="$(basename "$yaml_file" .yaml)"
      pgm_file="$MAP_DIR/${name}.pgm"
      bt_file="$MAP_DIR/${name}_3d.bt"

      if [ -f "$pgm_file" ] && [ -f "$bt_file" ]; then
        MAP_NAME="$name"
        MAP_YAML="$yaml_file"
        OCTOMAP_BT="$bt_file"
        break
      fi
    done < <(find "$MAP_DIR" -maxdepth 1 -name "*.yaml" -printf "%T@ %p\n" 2>/dev/null | sort -nr | cut -d' ' -f2-)
  fi

  if ! valid_map; then
    echo "[ERROR] No valid fusion map found in $MAP_DIR"
    echo "[ERROR] Need files: <map>.yaml, <map>.pgm, <map>_3d.bt"
    exit 4
  fi

  if [ ! -f "$NAV_PARAMS" ]; then
    echo "[ERROR] Nav2 params not found: $NAV_PARAMS"
    exit 6
  fi

  if [ ! -f "$AI_PARAMS" ]; then
    echo "[ERROR] AI params not found: $AI_PARAMS"
    exit 7
  fi

  # Ghi lại active map thật sự được dùng để webserver/operator đồng bộ.
  mkdir -p "$(dirname "$ACTIVE_ENV")"
  cat > "$ACTIVE_ENV" <<EOF_ACTIVE
MAP_NAME="$MAP_NAME"
MAP_YAML="$MAP_YAML"
OCTOMAP_BT="$OCTOMAP_BT"
PARAMS_FILE="$NAV_PARAMS"
EOF_ACTIVE

  echo "[INFO] MAP_NAME   = $MAP_NAME"
  echo "[INFO] MAP_YAML   = $MAP_YAML"
  echo "[INFO] OCTOMAP_BT = $OCTOMAP_BT"
  echo "[INFO] NAV_PARAMS = $NAV_PARAMS"
  echo "[INFO] AI_PARAMS  = $AI_PARAMS"

  tmux new-session -d -s "${SESSION}" -n bringup
  tmux send-keys -t "${SESSION}:bringup" \
"cd $WS && \
source $HOME/mobile_robot/ai_ros_venv/bin/activate 2>/dev/null || true; \
source /opt/ros/humble/setup.bash; \
source install/setup.bash; \
export ROS_DOMAIN_ID=$ROS_DOMAIN_ID; \
export ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; \
export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; \
ros2 launch amr_bringup bringup_fusion.launch.py" C-m

  tmux new-window -t "${SESSION}" -n navigation
  tmux send-keys -t "${SESSION}:navigation" \
"sleep 6; \
cd $WS && \
source $HOME/mobile_robot/ai_ros_venv/bin/activate 2>/dev/null || true; \
source /opt/ros/humble/setup.bash; \
source install/setup.bash; \
export ROS_DOMAIN_ID=$ROS_DOMAIN_ID; \
export ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; \
export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; \
ros2 launch amr_navigation nav_fusion.launch.py \
map:=$MAP_YAML \
octomap:=$OCTOMAP_BT \
params_file:=$NAV_PARAMS" C-m

  tmux new-window -t "${SESSION}" -n ai
  tmux send-keys -t "${SESSION}:ai" \
"sleep 12; \
cd $WS && \
source $HOME/mobile_robot/ai_ros_venv/bin/activate; \
source /opt/ros/humble/setup.bash; \
source install/setup.bash; \
export ROS_DOMAIN_ID=$ROS_DOMAIN_ID; \
export ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; \
export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; \
ros2 launch amr_ai amr_ai.launch.py \
params_file:=$AI_PARAMS \
start_mode_manager:=true \
start_person_tracker:=true \
start_follow_goal:=false \
start_follow_servo:=true \
start_cmd_vel_safety_mux:=true \
start_ai_detector:=true \
start_auto_initial_pose:=true \
start_auto_localizer:=true \
start_esp32_gateway:=true" C-m

  tmux new-window -t "${SESSION}" -n esp32_alert
  tmux send-keys -t "${SESSION}:esp32_alert" \
"sleep 18; \
cd $WS && \
source $HOME/mobile_robot/ai_ros_venv/bin/activate 2>/dev/null || true; \
source /opt/ros/humble/setup.bash; \
source install/setup.bash; \
export ROS_DOMAIN_ID=$ROS_DOMAIN_ID; \
export ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; \
export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; \
ros2 run amr_ai esp32_alert_bridge --ros-args \
-p esp32_ip:=$ESP32_ALERT_IP \
-p esp32_udp_port:=$ESP32_ALERT_UDP_PORT \
-p esp32_tcp_port:=$ESP32_ALERT_TCP_PORT \
-p alert_topic:=/amr_ai/alert \
-p debug_image_topic:=/amr_ai/debug/alert/image" C-m

  echo "[INFO] Started esp32_alert_bridge:"
  echo "       ESP32 IP   = $ESP32_ALERT_IP"
  echo "       UDP port   = $ESP32_ALERT_UDP_PORT"
  echo "       TCP port   = $ESP32_ALERT_TCP_PORT"

  echo "[OK] AMR operator stack started."
  echo "[INFO] View logs: tmux attach -t ${SESSION}"

} 2>&1 | tee -a "$LOG"
