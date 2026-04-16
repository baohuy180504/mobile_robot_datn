#!/bin/bash
echo "=== HỆ THỐNG MÔ PHỎNG & ĐIỀU HƯỚNG AMR ==="

# 1. Nạp môi trường
source /opt/ros/jazzy/setup.bash
source ~/test_ros/ros2_ws/install/setup.bash

# 2. Hàm dọn dẹp khi bấm Ctrl+C
cleanup() {
    echo -e "\n[HỆ THỐNG] Đang tắt Gazebo và Nav2..."
    kill 0
    exit
}
trap cleanup SIGINT SIGTERM

# 3. Khởi chạy song song (Tiến trình nền)
echo "[HỆ THỐNG] 1. Đang gọi Gazebo (amr_description)..."
ros2 launch amr_description gazebo.launch.py &
sleep 5 # Chờ 5 giây cho vật lý ổn định

echo "[HỆ THỐNG] 2. Đang gọi Navigation..."
ros2 launch amr_navigation navigation.launch.py &

# 4. Giữ terminal không bị đóng
wait