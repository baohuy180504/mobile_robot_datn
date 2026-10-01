#!/bin/bash
# Đặt IP ESP32 màn hình cảnh báo vào network.env (kiểm tra định dạng, giữ nguyên các dòng khác).
# Dùng:  scripts/set_esp32_ip.sh 192.168.1.50
set -e

WS="$HOME/mobile_robot/ros2_ws"
NETWORK_ENV="$WS/config/network.env"
NEW="$1"

if [ -z "$NEW" ]; then
  echo "Cách dùng: $0 <IP ESP32 màn hình>     ví dụ: $0 192.168.1.50"
  exit 1
fi

valid=0
if [[ "$NEW" =~ ^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})$ ]]; then
  valid=1
  for o in "${BASH_REMATCH[@]:1}"; do
    [ "$o" -le 255 ] || valid=0
  done
elif [[ "$NEW" =~ ^[A-Za-z][A-Za-z0-9.-]*[A-Za-z0-9]$ ]]; then
  valid=1    # hostname (vd amr-display.local)
fi

if [ "$valid" -ne 1 ]; then
  echo "[LỖI] '$NEW' không phải IPv4/hostname hợp lệ."
  exit 2
fi

mkdir -p "$(dirname "$NETWORK_ENV")"

if [ -f "$NETWORK_ENV" ] && grep -qE '^[[:space:]]*(export[[:space:]]+)?ESP32_ALERT_IP[[:space:]]*=' "$NETWORK_ENV"; then
  cp "$NETWORK_ENV" "$NETWORK_ENV.bak"
  sed -i -E "s|^[[:space:]]*(export[[:space:]]+)?ESP32_ALERT_IP[[:space:]]*=.*|ESP32_ALERT_IP=$NEW|" "$NETWORK_ENV"
else
  echo "ESP32_ALERT_IP=$NEW" >> "$NETWORK_ENV"
fi

echo "[OK] ESP32_ALERT_IP=$NEW  ->  $NETWORK_ENV"
echo "     esp32_alert_bridge sẽ dùng địa chỉ mới ở lần cảnh báo kế tiếp (không cần restart)."
echo "     Kiểm tra ESP32 có phản hồi: scripts/show_network.sh"
