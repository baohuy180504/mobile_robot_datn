#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"
SESSION="amr_navigation"
ACTIVE_MAP_FILE="$WS/config/active_fusion_map.env"

# ==========================================================
# ESP32 Alert Display config
# ==========================================================
ESP32_ALERT_IP="${ESP32_ALERT_IP:-192.168.1.36}"
ESP32_ALERT_UDP_PORT="${ESP32_ALERT_UDP_PORT:-4210}"
ESP32_ALERT_TCP_PORT="${ESP32_ALERT_TCP_PORT:-4211}"

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

if tmux has-session -t amr_slam 2>/dev/null; then
  echo "SLAM is already running. Press STOP before switching to NAVIGATION."
  exit 3
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Navigation already running."
  exit 0
fi

MAP_DIR="$WS/src/amr_slam/maps"
PARAMS_FILE="$WS/src/amr_navigation/config/nav2_params_fusion.yaml"

# Nạp map active do web chọn hoặc do lần SAVE MAP gần nhất ghi lại.
MAP_NAME=""
MAP_YAML=""
OCTOMAP_BT=""

if [ -f "$ACTIVE_MAP_FILE" ]; then
  source "$ACTIVE_MAP_FILE"
fi

valid_map() {
  [ -n "$MAP_NAME" ] && [ -f "$MAP_YAML" ] && [ -f "$OCTOMAP_BT" ]
}

# Nếu active map không tồn tại nữa hoặc chưa chọn, tự chọn map 2D+3D mới nhất.
# Điều này xử lý trường hợp xóa hết map cũ rồi quét/lưu map mới.
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
  echo "No valid fusion map found in $MAP_DIR"
  echo "Need files: <map>.yaml, <map>.pgm, <map>_3d.bt"
  exit 4
fi

if [ ! -f "$PARAMS_FILE" ]; then
  echo "Nav2 params file not found: $PARAMS_FILE"
  exit 6
fi

# Ghi lại active map thật sự được chọn để web và lần chạy sau đồng bộ.
mkdir -p "$(dirname "$ACTIVE_MAP_FILE")"
cat > "$ACTIVE_MAP_FILE" <<EOF_ACTIVE
MAP_NAME="$MAP_NAME"
MAP_YAML="$MAP_YAML"
OCTOMAP_BT="$OCTOMAP_BT"
PARAMS_FILE="$PARAMS_FILE"
EOF_ACTIVE

echo "Starting navigation with fusion map:"
echo "  MAP_NAME   = $MAP_NAME"
echo "  MAP_YAML   = $MAP_YAML"
echo "  OCTOMAP_BT = $OCTOMAP_BT"
echo "  PARAMS     = $PARAMS_FILE"

tmux new-session -d -s "$SESSION" -n navigation

tmux send-keys -t "$SESSION:navigation" \
"cd $WS && \
source $HOME/mobile_robot/ai_ros_venv/bin/activate && \
source /opt/ros/humble/setup.bash && \
source install/setup.bash && \
export ROS_DOMAIN_ID=0 && \
export ROS_LOCALHOST_ONLY=0 && \
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && \
ros2 launch amr_navigation nav_fusion.launch.py \
map:=$MAP_YAML \
octomap:=$OCTOMAP_BT \
params_file:=$PARAMS_FILE" C-m

sleep 5

tmux new-window -t "$SESSION" -n ai

tmux send-keys -t "$SESSION:ai" \
"cd $WS && \
source $HOME/mobile_robot/ai_ros_venv/bin/activate && \
source /opt/ros/humble/setup.bash && \
source install/setup.bash && \
export ROS_DOMAIN_ID=0 && \
export ROS_LOCALHOST_ONLY=0 && \
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && \
ros2 launch amr_ai amr_ai.launch.py \
start_mode_manager:=true \
start_person_tracker:=true \
start_follow_goal:=false \
start_follow_servo:=true \
start_cmd_vel_safety_mux:=true \
start_ai_detector:=true \
start_auto_initial_pose:=true \
start_auto_localizer:=true \
start_esp32_gateway:=true" C-m

sleep 3

tmux new-window -t "$SESSION" -n esp32_alert

tmux send-keys -t "$SESSION:esp32_alert" \
"cd $WS && \
source $HOME/mobile_robot/ai_ros_venv/bin/activate && \
source /opt/ros/humble/setup.bash && \
source install/setup.bash && \
export ROS_DOMAIN_ID=0 && \
export ROS_LOCALHOST_ONLY=0 && \
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && \
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

# ==========================================================
# Alert / Tracker web streams: chỉ chạy trong NAVIGATION
# ==========================================================

if ! tmux has-session -t amr_alert_web 2>/dev/null; then
  tmux new-session -d -s amr_alert_web "$HOME/mobile_robot/ros2_ws/scripts/run_alert_web.sh"
  echo "[INFO] Started amr_alert_web"
else
  echo "[INFO] amr_alert_web already running"
fi

if ! tmux has-session -t amr_tracker_web 2>/dev/null; then
  tmux new-session -d -s amr_tracker_web "$HOME/mobile_robot/ros2_ws/scripts/run_tracker_web.sh"
  echo "[INFO] Started amr_tracker_web"
else
  echo "[INFO] amr_tracker_web already running"
fi

echo "Navigation mode started."