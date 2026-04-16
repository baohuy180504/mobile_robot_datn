#!/bin/bash
echo "=== CLEAN & BUILD ==="

# Xoa cac thu muc build cu de tranh loi cache
rm -rf build/ install/ log/
source /opt/ros/humble/setup.bash
# Build code
colcon build --symlink-install

# Nap lai moi truong
source install/setup.bash

echo "=== BUILD SUCCESS! ==="
