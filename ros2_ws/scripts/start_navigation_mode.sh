#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"
SESSION="amr_navigation"
ACTIVE_MAP_FILE="$WS/config/active_fusion_map.env"

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

# Mặc định nếu chưa chọn map
MAP_NAME="map3"
MAP_YAML="$WS/src/amr_slam/maps/map3.yaml"
OCTOMAP_BT="$WS/src/amr_slam/maps/map3_3d.bt"
PARAMS_FILE="$WS/src/amr_navigation/config/nav2_params_fusion.yaml"

# Nếu web đã chọn map thì nạp file active map
if [ -f "$ACTIVE_MAP_FILE" ]; then
  source "$ACTIVE_MAP_FILE"
fi

if [ ! -f "$MAP_YAML" ]; then
  echo "2D map yaml not found: $MAP_YAML"
  exit 4
fi

if [ ! -f "$OCTOMAP_BT" ]; then
  echo "3D octomap bt not found: $OCTOMAP_BT"
  exit 5
fi

if [ ! -f "$PARAMS_FILE" ]; then
  echo "Nav2 params file not found: $PARAMS_FILE"
  exit 6
fi

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