#!/bin/bash

echo -e "\e[1;32m=== AMR MAP SAVER (2D & 3D) ===\e[0m"

source /opt/ros/humble/setup.bash
source install/setup.bash

# 1. Đường dẫn tuyệt đối tới folder maps trong package amr_slam
MAP_DIR="src/amr_slam/maps"

if [ ! -d "$MAP_DIR" ]; then
    echo -e "\e[1;31m[LỖI] Không tìm thấy thư mục $MAP_DIR!\e[0m"
    echo "Vui lòng cd về thư mục gốc của workspace (ví dụ: cd ~/ros2_ws) rồi chạy lại lệnh."
    exit 1
fi

# 2. Xử lý tên bản đồ
if [ -z "$1" ]; then
    MAP_NAME="map_$(date +%Y%m%d_%H%M%S)"
    echo -e "[INFO] Bạn không nhập tên, tự động đặt tên là: \e[1;33m$MAP_NAME\e[0m"
else
    MAP_NAME=$1
fi

# 3. Lưu bản đồ 2D (từ SLAM Toolbox)
echo "[INFO] Đang lưu bản đồ 2D (Lidar)..."
ros2 run nav2_map_server map_saver_cli -f $MAP_DIR/$MAP_NAME

# 4. Lưu bản đồ 3D (từ Octomap Server)
echo "[INFO] Đang lưu bản đồ 3D (Octomap Voxel)..."
ros2 run octomap_server octomap_saver $MAP_DIR/${MAP_NAME}_3d.bt

# 5. Báo cáo
echo -e "\e[1;32m-------------------------------------------\e[0m"
echo -e "\e[1;32m[SUCCESS] Bản đồ đã được lưu an toàn tại:\e[0m"
echo "  [2D] $MAP_DIR/$MAP_NAME.pgm "
echo "  [2D] $MAP_DIR/$MAP_NAME.yaml "
echo "  [3D] $MAP_DIR/${MAP_NAME}_3d.bt "
echo -e "\e[1;32m-------------------------------------------\e[0m"