#!/bin/bash

echo -e "\e[1;34m=== LƯU BẢN ĐỒ LAI 2D & 3D (RTAB-MAP) ===\e[0m"

MAP_NAME=${1:-my_fusion_map}
WS_DIR=$(pwd)
MAP_DIR="$WS_DIR/src/amr_slam/maps"

# 1. Trích xuất bản đồ 2D từ Topic (Dành cho Nav2 & MPPI)
echo -e "\e[1;33m[1/2] Đang trích xuất ảnh 2D (.yaml & .pgm)...\e[0m"
ros2 run nav2_map_server map_saver_cli -f "$MAP_DIR/$MAP_NAME" --ros-args -p map_subscribe_transient_local:=true

# Sửa lỗi Magick tự động: Ép đường dẫn tuyệt đối vào file YAML
sed -i "s|image: $MAP_NAME.pgm|image: $MAP_DIR/$MAP_NAME.pgm|g" "$MAP_DIR/$MAP_NAME.yaml"

# 2. Sao lưu cơ sở dữ liệu 3D
echo -e "\e[1;33m[2/2] Đang sao lưu không gian 3D (rtabmap.db)...\e[0m"
if [ -f ~/.ros/rtabmap.db ]; then
    cp ~/.ros/rtabmap.db "$MAP_DIR/$MAP_NAME.db"
    echo -e "\e[1;32m[THÀNH CÔNG] Đã lưu 3D Database: $MAP_DIR/$MAP_NAME.db\e[0m"
else
    echo -e "\e[1;31m[LỖI] Không tìm thấy file ~/.ros/rtabmap.db. RTAB-Map đã chạy chưa?\e[0m"
fi

echo -e "\e[1;32m=== HOÀN TẤT ===\e[0m"