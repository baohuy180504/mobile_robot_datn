#!/bin/bash

echo -e "\e[1;34m=== NAVIGATION KÍCH HOẠT (2D + 3D) ===\e[0m"

source /opt/ros/humble/setup.bash
source install/setup.bash

# 1. Xử lý tên bản đồ (Mặc định là my_perfect_map nếu không truyền tham số)
MAP_NAME=${1:-my_perfect_map}

# 2. Định nghĩa đường dẫn file 2D và 3D
MAP_2D_FILE="src/amr_slam/maps/$MAP_NAME.yaml"
MAP_3D_FILE="src/amr_slam/maps/${MAP_NAME}_3d.bt"

# 3. Kiểm tra file bản đồ 2D
if [ ! -f "$MAP_2D_FILE" ]; then
    echo -e "\e[1;31m[LỖI] Không tìm thấy file bản đồ 2D: $MAP_2D_FILE\e[0m"
    exit 1
fi

# 4. Kiểm tra file bản đồ 3D
if [ ! -f "$MAP_3D_FILE" ]; then
    echo -e "\e[1;31m[LỖI] Không tìm thấy file bản đồ 3D: $MAP_3D_FILE\e[0m"
    echo "Gợi ý: Kiểm tra xem bạn đã chạy script lưu map có phần lưu .bt chưa."
    exit 1
fi

# 5. Chuyển sang đường dẫn tuyệt đối
ABS_MAP_2D="$(pwd)/$MAP_2D_FILE"
ABS_MAP_3D="$(pwd)/$MAP_3D_FILE"

echo -e "[INFO] Đang tải bản đồ 2D: \e[1;33m$ABS_MAP_2D\e[0m"
echo -e "[INFO] Đang tải bản đồ 3D: \e[1;33m$ABS_MAP_3D\e[0m"

# 6. Chạy launch file và truyền cả 2 tham số bản đồ
# Lưu ý: Bạn cần cấu hình file navigation.launch.py để nhận thêm tham số 'map_3d'
ros2 launch amr_navigation nav_fusion.launch.py \
    map:="$ABS_MAP_2D" \
    octomap:="$ABS_MAP_3D"