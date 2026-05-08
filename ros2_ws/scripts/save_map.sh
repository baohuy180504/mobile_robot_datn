#!/bin/bash

echo -e "\e[1;32m=== MAP SAVER ===\e[0m"

source /opt/ros/humble/setup.bash
source install/setup.bash

# 1. Đường dẫn tuyệt đối tới folder maps trong package amr_slam
# Giả định bạn luôn chạy script này ở thư mục gốc của workspace (ví dụ: ~/ros2_ws)
MAP_DIR="src/amr_slam/maps"

# Kiểm tra xem thư mục có tồn tại không (Tránh việc chạy sai chỗ)
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

# 3. Gọi lệnh lưu map thẳng vào thư mục package
echo "[INFO] Đang lưu bản đồ vào package amr_slam..."
ros2 run nav2_map_server map_saver_cli -f $MAP_DIR/$MAP_NAME

# 4. Báo cáo
echo -e "\e[1;32m-------------------------------------------\e[0m"
echo -e "\e[1;32m[SUCCESS] Bản đồ đã được lưu an toàn tại mã nguồn:\e[0m"
echo "   1. $MAP_DIR/$MAP_NAME.pgm "
echo "   2. $MAP_DIR/$MAP_NAME.yaml "
echo -e "\e[1;32m-------------------------------------------\e[0m"