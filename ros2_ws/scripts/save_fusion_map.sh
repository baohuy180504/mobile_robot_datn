#!/bin/bash

set -e

echo -e "\e[1;32m=== AMR MAP SAVER (2D & 3D) ===\e[0m"

WS_DIR="$HOME/mobile_robot/ros2_ws"
cd "$WS_DIR"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate"
source /opt/ros/humble/setup.bash
source install/setup.bash

export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

MAP_DIR="$WS_DIR/src/amr_slam/maps"

if [ ! -d "$MAP_DIR" ]; then
    echo -e "\e[1;33m[WARN] Không tìm thấy thư mục maps, đang tạo mới: $MAP_DIR\e[0m"
    mkdir -p "$MAP_DIR"
fi

if [ -z "$1" ]; then
    MAP_NAME="map_$(date +%Y%m%d_%H%M%S)"
    echo -e "[INFO] Bạn không nhập tên, tự động đặt tên là: \e[1;33m$MAP_NAME\e[0m"
else
    MAP_NAME="$1"
fi

# Chỉ lấy tên file, không cho truyền đường dẫn
MAP_NAME="$(basename "$MAP_NAME")"

# Lọc ký tự an toàn cho file name
MAP_NAME="$(echo "$MAP_NAME" | tr -cd 'A-Za-z0-9_-')"

if [ -z "$MAP_NAME" ]; then
    MAP_NAME="map_$(date +%Y%m%d_%H%M%S)"
fi

echo "[INFO] Map name: $MAP_NAME"
echo "[INFO] Map dir : $MAP_DIR"

echo "[INFO] Kiểm tra topic /map..."
if ! ros2 topic list | grep -q "^/map$"; then
    echo -e "\e[1;31m[LỖI] Không thấy topic /map. Hãy chạy SLAM Toolbox trước.\e[0m"
    exit 1
fi

echo "[INFO] Kiểm tra OctoMap..."
if ! ros2 topic list | grep -q "^/octomap_binary$"; then
    echo -e "\e[1;31m[LỖI] Không thấy topic /octomap_binary. Hãy kiểm tra octomap_server.\e[0m"
    exit 1
fi

echo -e "\e[1;36m[INFO] Đang lưu bản đồ 2D...\e[0m"
ros2 run nav2_map_server map_saver_cli -f "$MAP_DIR/$MAP_NAME"

echo -e "\e[1;36m[INFO] Đang lưu bản đồ 3D OctoMap...\e[0m"
ros2 run octomap_server octomap_saver_node --ros-args \
  -p octomap_path:=$MAP_DIR/${MAP_NAME}_3d.bt

echo -e "\e[1;32m-------------------------------------------\e[0m"
echo -e "\e[1;32m[SUCCESS] Đã lưu bản đồ:\e[0m"
echo "  [2D] $MAP_DIR/$MAP_NAME.pgm"
echo "  [2D] $MAP_DIR/$MAP_NAME.yaml"
echo "  [3D] $MAP_DIR/${MAP_NAME}_3d.bt"
echo -e "\e[1;32m-------------------------------------------\e[0m"