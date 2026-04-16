#!/bin/bash
echo "=== MAP SAVER ==="

source /opt/ros/jazzy/setup.bash
source install/setup.bash

# Kiem tra xem nguoi dung co nhap ten khong
if [ -z "$1" ]; then
    # Neu khong nhap ten -> Tu dong dat ten theo gio he thong
    MAP_NAME="map_$(date +%Y%m%d_%H%M%S)"
    echo "[INFO] Ban khong nhap ten, tu dong dat ten la: $MAP_NAME"
else
    # Neu co nhap ten -> Dung ten do
    MAP_NAME=$1
fi

# Goi lenh luu map
# Luu vao thu muc maps/
ros2 run nav2_map_server map_saver_cli -f maps/$MAP_NAME

echo "-------------------------------------------"
echo "[SUCCESS]"
echo "   1. maps/$MAP_NAME.pgm "
echo "   2. maps/$MAP_NAME.yaml "
echo "-------------------------------------------"
