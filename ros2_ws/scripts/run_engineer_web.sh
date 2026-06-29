#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"
GUI_SCRIPT="$WS/scripts/control_hub_gui.py"
SERVER_LOG="/tmp/amr_engineer_web.log"

source ~/mobile_robot/ai_ros_venv/bin/activate
source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"

export AMR_WS="$WS"
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "=== AMR CONTROL HUB ==="
echo "Web port : 8080"
echo "Log      : $SERVER_LOG"

# ── Chạy webserver ở background ───────────────────────────────
~/mobile_robot/ai_ros_venv/bin/python3 -m amr_ai.web.engineer_web_server \
    --host 0.0.0.0 \
    --port 8080 \
    > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

echo "engineer_web_server PID: $SERVER_PID"

# ── Cleanup khi script thoát ──────────────────────────────────
cleanup() {
    echo "Dang dung Control Hub (PID $SERVER_PID)..."
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    echo "Da dung."
}
trap cleanup EXIT INT TERM

# ── Hiển thị GUI (block cho đến khi nhấn STOP / đóng cửa sổ) ─
if [ -f "$GUI_SCRIPT" ]; then
    python3 "$GUI_SCRIPT" --server-pid "$SERVER_PID" || true
else
    echo "[WARN] GUI script không tìm thấy: $GUI_SCRIPT"
    echo "Chạy không có GUI. Nhấn Ctrl+C để dừng."
    wait "$SERVER_PID"
fi

# Khi GUI đóng → trap cleanup dừng webserver