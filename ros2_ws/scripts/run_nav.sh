#!/bin/bash

echo -e "\e[1;34m=== NAVIGATION KÍCH HOẠT ===\e[0m"

source /opt/ros/humble/setup.bash
source install/setup.bash

# Mặc định là my_perfect_map nếu không truyền tham số
MAP_NAME=${1:-my_perfect_map}

# Trỏ thẳng vào thư mục mã nguồn chứa map (Giả định bạn chạy ở ~/ros2_ws)
MAP_FILE="src/amr_slam/maps/$MAP_NAME.yaml"

if [ ! -f "$MAP_FILE" ]; then
    echo -e "\e[1;31m[LỖI] Không tìm thấy file map: $MAP_FILE\e[0m"
    echo "Hãy kiểm tra lại"
    exit 1
fi

# Nav2 cần đường dẫn tuyệt đối (Absolute Path) để đọc file
ABS_MAP_FILE="$(pwd)/$MAP_FILE"

echo -e "[INFO] Đang tải bản đồ: \e[1;33m$MAP_NAME\e[0m"

# Chạy launch file và truyền đường dẫn map vào
ros2 launch amr_navigation navigation.launch.py map:="$ABS_MAP_FILE"