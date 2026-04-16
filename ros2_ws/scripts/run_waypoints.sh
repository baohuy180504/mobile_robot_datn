#!/bin/bash
echo "=== RUNNING WAYPOINTS ==="

# 1. Source môi trường (Dùng đường dẫn tuyệt đối cho chắc chắn)
source /opt/ros/humble/setup.bash
source ~/test_ros/ros2_ws/install/setup.bash

# 2. Hàm dọn dẹp: Tự động kill tất cả tiến trình nền khi bạn nhấn Ctrl+C
cleanup() {
    echo -e "\n[HỆ THỐNG] Đang tắt Gazebo, Nav2 và các node liên quan..."
    kill 0
    exit
}
trap cleanup SIGINT SIGTERM

# 3. Khởi chạy từng thành phần
echo "[HỆ THỐNG] 1. Đang khởi động Gazebo..."
ros2 launch amr_description gazebo.launch.py &
sleep 6 # Đợi 6 giây cho Gazebo load xong model và TF

echo "[HỆ THỐNG] 2. Đang khởi động Navigation..."
ros2 launch amr_navigation navigation.launch.py &
sleep 8 # Đợi 8 giây cho Nav2 load xong Costmap và amcl

echo "[HỆ THỐNG] 3. Chạy kịch bản Waypoints..."
python3 ~/test_ros/ros2_ws/src/amr_navigation/scripts/follow_waypoints.py &

# 4. Giữ cho file script chính không bị tắt
wait
