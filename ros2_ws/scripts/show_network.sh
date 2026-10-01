#!/bin/bash
# Hiển thị thông tin mạng khi đổi WiFi:
#   - IP hiện tại của Jetson  -> nạp vào firmware 2 ESP32 nút bấm (jetson_ip)
#   - IP ESP32 màn hình đang cấu hình trong network.env, và kiểm tra ESP32 có phản hồi không
# Chỉ ĐỌC, không sửa gì. (Cổng UDP thử nghiệm gửi ký tự '?': firmware bỏ qua nhưng vẫn trả ACK.)

WS="$HOME/mobile_robot/ros2_ws"
NETWORK_ENV="$WS/config/network.env"
WAYPOINT_PORT=5000

read_key() {   # read_key KEY  -> in giá trị (bỏ comment cuối dòng, khoảng trắng, dấu nháy)
  grep -E "^[[:space:]]*(export[[:space:]]+)?$1[[:space:]]*=" "$NETWORK_ENV" 2>/dev/null | tail -1 \
    | sed -E 's/^[^=]*=//; s/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//; s/^"//; s/"$//' \
    | sed -E "s/^'//; s/'\$//"
}

echo "=================== THÔNG TIN MẠNG ==================="

# ---- Jetson -----------------------------------------------------------------
JETSON_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"
[ -z "$JETSON_IP" ] && JETSON_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
SSID="$(nmcli -t -f active,ssid dev wifi 2>/dev/null | awk -F: '$1=="yes"{print $2; exit}')"

echo "[Jetson]"
echo "  Hostname : $(hostname)"
echo "  WiFi     : ${SSID:-<không rõ>}"
echo "  IP       : ${JETSON_IP:-<KHÔNG CÓ MẠNG>}"
echo "  -> Nạp vào firmware ESP32 NÚT BẤM (code_esp32_node.ino):"
echo "       const char* jetson_ip = \"${JETSON_IP:-...}\";"
if ss -ltn 2>/dev/null | grep -q ":${WAYPOINT_PORT}[[:space:]]"; then
  echo "  Cổng $WAYPOINT_PORT (nhận lệnh WP từ nút bấm): ĐANG MỞ"
else
  echo "  Cổng $WAYPOINT_PORT (nhận lệnh WP từ nút bấm): chưa mở (chỉ mở khi đã vào NAVIGATION)"
fi

# mDNS: 2 ESP32 nút bấm tìm Jetson theo tên "<hostname>.local"
AVAHI="$(systemctl is-active avahi-daemon 2>/dev/null)"
[ -z "$AVAHI" ] && AVAHI="không có"
if grep -qE '^hosts:.*mdns' /etc/nsswitch.conf 2>/dev/null; then NSS_MDNS="có"; else NSS_MDNS="KHÔNG (cần libnss-mdns để Jetson tìm được amr-display.local)"; fi
echo "  mDNS     : $(hostname).local  | avahi-daemon: $AVAHI | libnss-mdns: $NSS_MDNS"
[ "$AVAHI" != "active" ] && echo "             -> cài/bật:  sudo apt install avahi-daemon libnss-mdns"

resolve_host() {   # resolve_host <ip|hostname> -> in IPv4 hoặc rỗng
  if [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then echo "$1"; else getent ahostsv4 "$1" 2>/dev/null | awk '{print $1; exit}'; fi
}

# ---- ESP32 màn hình ---------------------------------------------------------
echo
echo "[ESP32 màn hình cảnh báo]  (file: $NETWORK_ENV)"
if [ ! -f "$NETWORK_ENV" ]; then
  echo "  KHÔNG thấy network.env. Tạo bằng: scripts/set_esp32_ip.sh <IP màn hình>"
  exit 0
fi

ESP32_IP="$(read_key ESP32_ALERT_IP)"
UDP_PORT="$(read_key ESP32_ALERT_UDP_PORT)"; UDP_PORT="${UDP_PORT:-4210}"

if [ -z "$ESP32_IP" ]; then
  echo "  ESP32_ALERT_IP: <chưa đặt>. Đặt bằng: scripts/set_esp32_ip.sh <IP màn hình>"
  exit 0
fi

echo "  ESP32_ALERT_IP : $ESP32_IP   (UDP $UDP_PORT)"

TARGET_IP="$(resolve_host "$ESP32_IP")"
if [ -z "$TARGET_IP" ]; then
  echo "  Phân giải tên   : KHÔNG phân giải được '$ESP32_IP' (ESP32 chưa lên WiFi, hoặc Jetson thiếu mDNS)"
  echo "======================================================"
  exit 0
fi
[ "$TARGET_IP" != "$ESP32_IP" ] && echo "  Phân giải tên   : $ESP32_IP -> $TARGET_IP"

# Cùng mạng /24 chưa? (giả định mặt nạ 255.255.255.0)
if [ -n "$JETSON_IP" ]; then
  if [ "${JETSON_IP%.*}" = "${TARGET_IP%.*}" ]; then
    echo "  Mạng           : cùng dải ${JETSON_IP%.*}.x  (OK)"
  else
    echo "  Mạng           : KHÁC DẢI (Jetson ${JETSON_IP%.*}.x / ESP32 ${TARGET_IP%.*}.x)"
    echo "                   -> Kiểm tra ESP32 đã nối cùng WiFi với Jetson chưa, và IP đã đúng chưa."
  fi
fi

# Thử thật kênh cảnh báo: gửi '?' và chờ ESP32_ACK
REPLY="$(python3 - "$TARGET_IP" "$UDP_PORT" <<'PY' 2>/dev/null
import socket, sys
ip, port = sys.argv[1], int(sys.argv[2])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(1.5)
try:
    s.sendto(b'?', (ip, port))
    data, _ = s.recvfrom(64)
    print('OK ' + data.decode(errors='ignore').strip())
except Exception:
    print('NO_REPLY')
PY
)"

case "$REPLY" in
  OK*) echo "  Phản hồi UDP   : OK  (${REPLY#OK })" ;;
  *)   echo "  Phản hồi UDP   : KHÔNG có phản hồi -> sai IP, ESP32 chưa lên WiFi, hoặc mạng chặn UDP" ;;
esac
# Gợi ý: nếu đang dùng IP mà amr-display.local tìm được -> có thể chuyển sang tên để khỏi sửa mỗi lần đổi WiFi
if [[ "$ESP32_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  MDNS_IP="$(getent ahostsv4 amr-display.local 2>/dev/null | awk '{print $1; exit}')"
  if [ -n "$MDNS_IP" ]; then
    echo "  Gợi ý          : amr-display.local -> $MDNS_IP tìm được. Dùng tên thay IP để khỏi sửa khi đổi WiFi:"
    echo "                   scripts/set_esp32_ip.sh amr-display.local"
  fi
fi
echo "======================================================"
