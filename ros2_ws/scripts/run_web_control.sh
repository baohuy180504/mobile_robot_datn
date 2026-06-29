#!/bin/bash
# Khong dung "set -e": tool nay phai chay duoc ke ca khi ROS/workspace dang
# loi, nen moi buoc source ROS chi la best-effort, khong lam script dung
# giua duong.

WS="$HOME/mobile_robot/ros2_ws"
WEB_SCRIPT="$WS/src/amr_ai/amr_ai/web/web_control.py"
GUI_SCRIPT="$WS/scripts/web_teleop_gui.py"
CONTROL_LOG="/tmp/amr_web_control.log"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true

# Best-effort: chi giup tinh nang canh bao "arduino_bridge dang chay" hoat
# dong, KHONG can thiet cho dieu khien Arduino qua serial.
source /opt/ros/humble/setup.bash 2>/dev/null || true
source "$WS/install/setup.bash" 2>/dev/null || true
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Doi cong serial / mat khau / port web tai day neu can, khong sua code:
# export AMR_ARDUINO_SERIAL_PORT="/dev/arduino_mega"
# export AMR_CONTROL_PASSWORD="123"

echo "=== AMR EMERGENCY WEB CONTROL ==="
echo "Serial port : ${AMR_ARDUINO_SERIAL_PORT:-/dev/arduino_mega}"
echo "Web port    : 8090"
echo "Log         : $CONTROL_LOG"

# ── Chạy web server ở background ──────────────────────────────
# Phải background để GUI QR có thể chạy song song.
# Log ra file để không spam terminal khi GUI đang hiện.
python3 "$WEB_SCRIPT" --host 0.0.0.0 --port 8090 \
    > "$CONTROL_LOG" 2>&1 &
CONTROL_PID=$!

echo "web_control.py PID: $CONTROL_PID"

# ── Dọn dẹp khi script thoát (bất kỳ lý do nào) ──────────────
# SIGTERM sẽ trigger on_shutdown() của web_control.py:
#   gửi zero xuống serial + đóng cổng → robot dừng an toàn.
cleanup() {
    echo "Dang dung emergency web control (PID $CONTROL_PID)..."
    kill "$CONTROL_PID" 2>/dev/null || true
    wait "$CONTROL_PID" 2>/dev/null || true
    echo "Da dung."
}
trap cleanup EXIT INT TERM

# ── Hiển thị GUI QR (block cho đến khi đóng cửa sổ / nhấn STOP) ──
# Nhấn STOP trên GUI → kill web_control.py + đóng cửa sổ.
# Đóng cửa sổ (X) → tương tự STOP → kill web_control.py.
# Không có DISPLAY (headless) → bỏ qua GUI, giữ server chạy.
if [ -f "$GUI_SCRIPT" ]; then
    python3 "$GUI_SCRIPT" --teleop-pid "$CONTROL_PID" || true
else
    echo "[WARN] GUI script không tìm thấy: $GUI_SCRIPT"
    echo "Chạy không có GUI. Nhấn Ctrl+C để dừng."
    wait "$CONTROL_PID"
fi

# Khi GUI đóng → trap cleanup tự động dừng web_control.py