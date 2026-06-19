#!/usr/bin/env python3
"""
AMR Web Control - dieu khien tay khan cap, gui lenh thang xuong Arduino qua
serial, KHONG di qua ROS2 / Nav2 / cmd_vel_safety_mux / lidar / camera.

Dung khi cac cam bien (lidar, camera) hoac toan bo stack ROS bi hong nhung
van can lai xe bang tay qua Arduino. File nay khong import rclpy va khong
phu thuoc bat ky node ROS nao de hoat dong - chi can cong serial toi Arduino
con song la du.

CANH BAO: cmd_vel_safety_mux_node.py binh thuong yeu cau du lieu LiDAR moi
moi cho phep xe chay (require_scan_for_motion=True), nen khi lidar hong,
duong di qua /cmd_vel_safe se luon bi chan ve 0. Vi vay tool nay BO QUA toan
bo duong do, mo thang serial - dong nghia KHONG CON LOP AN TOAN LIDAR/E-STOP
nao ca khi dung tool nay. Chi dung khi thuc su can thiet va da quan sat
truc tiep xe bang mat.

Neu arduino_bridge (node ROS binh thuong) dang con giu cong serial, tool nay
co the khong mo duoc cong, hoac trong truong hop xau hon ca 2 cung viet vao
cong serial gay du lieu lan nhau. Luon dung toan bo stack chinh truoc khi
dung tool nay.
"""

import argparse
import fcntl
import math
import os
import secrets
import select
import struct
import subprocess
import termios
import threading
import time
from typing import Optional
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response


APP_TITLE = "AMR Emergency Control"
FILE_VERSION = "2026-06-19-v7-no-write-until-active"

# ==========================================================
# Config (override bang environment variable, khong can sua code)
# ==========================================================
SERIAL_PORT = os.environ.get("AMR_ARDUINO_SERIAL_PORT", "/dev/arduino_mega")
SERIAL_BAUD = termios.B115200

WEB_PASSWORD = os.environ.get("AMR_CONTROL_PASSWORD", "123")
AUTH_COOKIE_NAME = "amr_control_auth"
AUTH_COOKIE_VALUE = os.environ.get("AMR_CONTROL_AUTH_TOKEN", secrets.token_urlsafe(32))
AUTH_PUBLIC_PATHS = {"/login", "/api/login", "/api/logout", "/favicon.ico"}

LINEAR_MIN, LINEAR_MAX, LINEAR_DEFAULT = 0.03, 0.40, 0.12
ANGULAR_MIN, ANGULAR_MAX, ANGULAR_DEFAULT = 0.05, 0.80, 0.28

CMD_TIMEOUT_S = 0.4       # khong co lenh moi trong khoang nay -> tu dong ve 0
LOOP_HZ = 20.0
ARDUINO_READY_TIMEOUT_S = 8.0  # cho toi da ngan nay giay de thay telemetry
                                # that tu Arduino truoc khi cho phep dieu
                                # khien (xem wait_until_telemetry_seen).
                                # Thay the cho STARTUP_SETTLE_S co dinh truoc
                                # day - vi mo cong serial co the khien Arduino
                                # tu reset (DTR->RESET), va thoi gian boot lai
                                # (gom ca khoi tao BNO055 qua I2C) dao dong,
                                # khong doan truoc duoc mot con so co dinh nao
                                # la chac chan du moi luc.


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ==========================================================
# Serial link toi Arduino - thuan stdlib, khong dung pyserial,
# cau hinh giong dung arduino_bridge.cpp (8N1, raw mode).
# ==========================================================
class ArduinoSerialLink:
    def __init__(self, port: str, baud=SERIAL_BAUD):
        self.port = port
        self.baud = baud
        self.fd: Optional[int] = None
        self.lock = threading.Lock()
        self.last_error: str = ""

    def is_open(self) -> bool:
        return self.fd is not None

    def open(self) -> bool:
        with self.lock:
            if self.fd is not None:
                return True

            try:
                fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            except OSError as exc:
                self.last_error = f"Khong mo duoc cong serial {self.port}: {exc}"
                print(f"[web_control] OPEN FAILED: {self.last_error}", flush=True)
                return False

            try:
                attrs = termios.tcgetattr(fd)
                # attrs = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
                attrs[4] = self.baud
                attrs[5] = self.baud

                cflag = attrs[2]
                cflag |= (termios.CLOCAL | termios.CREAD)
                cflag &= ~termios.PARENB
                cflag &= ~termios.CSTOPB
                cflag &= ~termios.CSIZE
                cflag |= termios.CS8
                # QUAN TRONG: tat hardware flow control (RTS/CTS). Arduino
                # chi noi day TX/RX/GND, khong co RTS/CTS. Neu CRTSCTS con
                # bat (mac dinh tuy driver USB-serial), kernel se cho doi
                # tin hieu CTS truoc khi day byte ra day TX that - os.write()
                # van bao thanh cong (vao buffer) nhung byte khong bao gio
                # ra toi Arduino. Loi nay khong the phat hien qua test bang
                # pty vi pty khong co co che bat tay phan cung.
                if hasattr(termios, "CRTSCTS"):
                    cflag &= ~termios.CRTSCTS
                attrs[2] = cflag

                lflag = attrs[3]
                lflag &= ~(termios.ICANON | termios.ECHO | termios.ECHOE | termios.ISIG)
                attrs[3] = lflag

                oflag = attrs[1]
                oflag &= ~termios.OPOST
                attrs[1] = oflag

                iflag = attrs[0]
                iflag &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
                attrs[0] = iflag

                termios.tcsetattr(fd, termios.TCSANOW, attrs)
                termios.tcflush(fd, termios.TCIOFLUSH)

                # QUAN TRONG: O_NONBLOCK chi can luc open() de tranh treo
                # neu modem-control line chua san sang. Sau khi da bat
                # CLOCAL (bo qua modem-control), PHAI go O_NONBLOCK de cac
                # lan write() sau do quay lai kieu blocking binh thuong.
                # Neu de sot O_NONBLOCK (loi truoc day): khi buffer driver
                # USB-serial tam day (de xay ra khi gui lien tuc 20 lan/giay
                # trong luc Arduino dang ban doc 3 cam bien sieu am), write()
                # co the chi ghi duoc MOT PHAN chuoi lenh roi tra ve ngay,
                # phan con thieu bi mat - Arduino nhan dong lenh bi cat cut,
                # khong co dau ',' hop le nen bo qua am tham. Day chinh la
                # ly do "sending linear=..." luon bao thanh cong nhung xe
                # khong chay: lenh gui xuong qua serial bi gay giua chung.
                fd_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fd_flags & ~os.O_NONBLOCK)

                try:
                    fcntl.ioctl(fd, termios.TIOCEXCL)
                except Exception:
                    pass

            except Exception as exc:
                os.close(fd)
                self.last_error = f"Loi cau hinh serial: {exc}"
                print(f"[web_control] CONFIG FAILED: {self.last_error}", flush=True)
                return False

            self.fd = fd
            self.last_error = ""
            crtscts_state = "khong ro (Python termios khong co hang so nay)"
            if hasattr(termios, "CRTSCTS"):
                crtscts_state = "DA TAT (ok)" if not (cflag & termios.CRTSCTS) else "VAN BAT (loi!)"
            print(f"[web_control] Serial OPENED OK: {self.port} | CRTSCTS: {crtscts_state}", flush=True)
            return True

    def write_twist(self, linear_x: float, angular_z: float) -> bool:
        with self.lock:
            if self.fd is None:
                return False
            try:
                line = f"{linear_x:.6f},{angular_z:.6f}\n".encode("ascii")
                total_written = 0
                while total_written < len(line):
                    n = os.write(self.fd, line[total_written:])
                    if n <= 0:
                        self.last_error = "Write tra ve 0 byte, dung lai de tranh treo"
                        print(f"[web_control] WRITE STALLED: {self.last_error}", flush=True)
                        return False
                    total_written += n
                return True
            except OSError as exc:
                self.last_error = f"Loi viet serial: {exc}"
                print(f"[web_control] WRITE FAILED: {self.last_error}", flush=True)
                return False

    def close(self):
        with self.lock:
            if self.fd is not None:
                try:
                    os.close(self.fd)
                except OSError:
                    pass
                self.fd = None

    def read_raw_for_diagnosis(self, timeout_s: float = 1.5) -> bytes:
        """
        Tu doc thu vai trieu telemetry qua DUNG fd va cau hinh ma chinh
        code nay vua thiet lap - khong qua cat/stty/tien trinh nao khac.
        Day la cach duy nhat xac nhan chac chan baud/parity ma code Python
        nay tu cau hinh la dung, vi cat doc duoc khong co nghia gi neu no
        chi dang ke thua cau hinh sot lai tu lan stty thu cong truoc do.
        Dung select() vi fd hien dang o che do blocking (da go O_NONBLOCK).
        """
        if self.fd is None:
            return b""
        try:
            collected = b""
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                ready, _, _ = select.select([self.fd], [], [], remaining)
                if not ready:
                    break
                chunk = os.read(self.fd, 256)
                if not chunk:
                    break
                collected += chunk
                if len(collected) >= 256:
                    break
            return collected
        except OSError as exc:
            print(f"[web_control] DIAG READ FAILED: {exc}", flush=True)
            return b""

    def wait_until_telemetry_seen(self, max_wait_s: float = 8.0) -> bool:
        """
        Cho TICH CUC toi khi thuc su thay duoc 1 dong telemetry hop le
        ('e:' o dau dong) tu Arduino, thay vi doan mot khoang thoi gian co
        dinh roi hy vong la du. Mo cong serial co the khien Arduino tu
        RESET (mach DTR->RESET pho bien tren cac board dung adapter
        USB-serial CH340/CP2102), va thoi gian boot lai (gom ca khoi tao
        cam bien BNO055 qua I2C trong setup()) co the dao dong, khong co
        gia tri co dinh nao chac chan du moi luc. Cho toi khi thay du lieu
        that, hoac het max_wait_s thi bao that bai ro rang - khong bao gio
        am tham coi nhu "chac la xong roi" khi chua co bang chung.
        """
        if self.fd is None:
            return False

        buffer = b""
        deadline = time.monotonic() + max_wait_s

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                ready, _, _ = select.select([self.fd], [], [], min(remaining, 0.5))
            except OSError:
                return False

            if not ready:
                continue

            try:
                chunk = os.read(self.fd, 256)
            except OSError:
                return False

            if not chunk:
                continue

            buffer += chunk
            if len(buffer) > 1024:
                buffer = buffer[-1024:]

            if b"e:" in buffer:
                return True

        return False


serial_link = ArduinoSerialLink(SERIAL_PORT)


# ==========================================================
# Trang thai dieu khien (thread-safe)
# ==========================================================
class ControlState:
    def __init__(self):
        self.lock = threading.Lock()
        self.control_active = False
        self.last_cmd_linear = 0.0
        self.last_cmd_angular = 0.0
        self.last_cmd_time = 0.0

    def set_active(self, active: bool):
        with self.lock:
            self.control_active = active
            self.last_cmd_linear = 0.0
            self.last_cmd_angular = 0.0
            self.last_cmd_time = 0.0

    def update_cmd(self, linear: float, angular: float):
        with self.lock:
            self.last_cmd_linear = linear
            self.last_cmd_angular = angular
            self.last_cmd_time = time.monotonic()

    def read(self):
        with self.lock:
            return (
                self.control_active,
                self.last_cmd_linear,
                self.last_cmd_angular,
                self.last_cmd_time,
            )


control_state = ControlState()
_stop_worker = threading.Event()


def serial_writer_loop():
    period = 1.0 / max(1.0, LOOP_HZ)
    last_debug_print = 0.0

    while not _stop_worker.is_set():
        time.sleep(period)

        if not serial_link.is_open():
            continue

        active, lin, ang, last_time = control_state.read()

        if not active:
            # KHONG gui gi ca khi chua active - truoc day o day co
            # write_twist(0,0) lien tuc 20Hz ngay khi cong vua mo, kha
            # nang cao day chinh la nguyen nhan goc: no chay CHONG LEN
            # giai doan wait_until_telemetry_seen() dang co doc "yen
            # lang", doi lien tuc hang nghin lenh vao dung luc Arduino
            # con dang khoi dong lai / con dang duoc cho phep on dinh.
            # Watchdog 1 giay co san tren Arduino (lastCmdTime) da tu lo
            # viec dung dong co khi khong co lenh - khong can gia vo gui
            # 0 lien tuc o day.
            continue

        if last_time <= 0.0 or (time.monotonic() - last_time) > CMD_TIMEOUT_S:
            serial_link.write_twist(0.0, 0.0)
            continue

        serial_link.write_twist(lin, ang)

        now = time.monotonic()
        if (lin != 0.0 or ang != 0.0) and (now - last_debug_print) > 0.5:
            print(f"[web_control] sending linear={lin:.3f} angular={ang:.3f}", flush=True)
            last_debug_print = now


writer_thread = threading.Thread(target=serial_writer_loop, daemon=True)
writer_thread.start()


def check_arduino_bridge_running() -> Optional[bool]:
    """
    Kiem tra best-effort xem node ROS 'arduino_bridge' binh thuong co dang
    chay khong, de canh bao xung dot cong serial. Tra ve None neu khong the
    kiem tra (vd ROS chua source trong shell nay) - khong coi la loi.
    """
    try:
        result = subprocess.run(
            ["ros2", "node", "list"],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        if result.returncode != 0:
            return None
        return "arduino_bridge" in result.stdout
    except Exception:
        return None


# ==========================================================
# Auth (cung kieu voi engineer_web_server.py, cookie rieng)
# ==========================================================
def is_authenticated(request: Request) -> bool:
    return request.cookies.get(AUTH_COOKIE_NAME) == AUTH_COOKIE_VALUE


LOGIN_HTML = r'''
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>AMR Emergency Control - Login</title>
<style>
  :root{--bg:#020617;--card:rgba(15,23,42,.9);--border:#334155;--red:#ef4444;--text:#e5e7eb;--muted:#94a3b8;}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;min-height:100dvh;display:flex;align-items:center;justify-content:center;
    background:var(--bg);color:var(--text);font-family:-apple-system,Arial,Helvetica,sans-serif;
    padding:max(16px,env(safe-area-inset-top)) max(16px,env(safe-area-inset-right))
      max(16px,env(safe-area-inset-bottom)) max(16px,env(safe-area-inset-left));}
  .gate{width:min(380px,88vw);padding:26px 24px;border:1px solid var(--border);
    border-radius:18px;background:var(--card);box-shadow:0 14px 42px rgba(0,0,0,.4);}
  h1{margin:0 0 4px;text-align:center;font-size:22px;color:var(--red);}
  .sub{text-align:center;color:var(--muted);margin:0 0 20px;font-size:13px;}
  label{display:block;margin-bottom:8px;font-size:14px;font-weight:bold;}
  input{width:100%;padding:12px 14px;border-radius:12px;border:1px solid #475569;
    background:#0b1220;color:white;font-size:16px;outline:none;}
  button{width:100%;margin-top:14px;padding:13px;border:0;border-radius:12px;
    background:linear-gradient(90deg,#b91c1c,#ef4444);color:white;font-weight:900;
    font-size:15px;cursor:pointer;letter-spacing:.5px;}
  .status{min-height:18px;margin-top:10px;text-align:center;color:#facc15;font-size:13px;}
</style>
</head>
<body>
  <div class="gate">
    <h1>EMERGENCY CONTROL</h1>
    <div class="sub">Dieu khien khan cap - khong qua sensor</div>
    <label for="password">Mat khau</label>
    <input id="password" type="password" autocomplete="current-password" placeholder="Nhap mat khau">
    <button onclick="login()">LOGIN</button>
    <div class="status" id="status"></div>
  </div>
<script>
async function login(){
  const status=document.getElementById("status");
  const password=document.getElementById("password").value;
  status.textContent="Dang xac thuc...";
  try{
    const res=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({password})});
    const data=await res.json();
    if(data.ok){
      const next=new URLSearchParams(window.location.search).get("next") || "/";
      window.location.href=next;
    }else{
      status.textContent=data.message || "Sai mat khau.";
    }
  }catch(e){ status.textContent="Khong ket noi duoc."; }
}
document.getElementById("password").addEventListener("keydown",e=>{ if(e.key==="Enter") login(); });
document.getElementById("password").focus();
</script>
</body>
</html>
'''


CONTROL_HTML = r'''
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>AMR Emergency Control</title>
<style>
  :root{--bg:#020617;--card:rgba(15,23,42,.92);--border:#334155;--red:#ef4444;--green:#22c55e;
    --text:#e5e7eb;--muted:#94a3b8;--amber:#f59e0b;}
  *{box-sizing:border-box;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;}
  html,body{height:100%;}
  body{margin:0;min-height:100vh;min-height:100dvh;background:var(--bg);color:var(--text);
    font-family:-apple-system,Arial,Helvetica,sans-serif;display:flex;flex-direction:column;
    align-items:center;overscroll-behavior:none;
    padding:max(10px,env(safe-area-inset-top)) max(10px,env(safe-area-inset-right))
      max(12px,env(safe-area-inset-bottom)) max(10px,env(safe-area-inset-left));}
  .page{width:min(420px,96vw);display:flex;flex-direction:column;gap:8px;}
  h1{color:var(--red);font-size:17px;margin:2px 0 0;text-align:center;letter-spacing:.5px;}
  .warn{color:var(--amber);font-size:11px;text-align:center;margin:0 0 2px;line-height:1.35;opacity:.9;}
  .status-banner{text-align:center;font-size:13px;font-weight:600;padding:9px 10px;border-radius:10px;
    min-height:18px;background:#0b1220;color:var(--muted);border:1px solid var(--border);
    transition:background .15s,color .15s;}
  .status-banner.bad{color:#fecaca;background:#3f1212;border-color:#7f1d1d;}
  .status-banner.good{color:#bbf7d0;background:#0f2d1a;border-color:#14532d;}
  .status-banner.busy{color:#fde68a;background:#3a2c0a;border-color:#78350f;}
  .row{display:flex;gap:10px;}
  .startstop{flex:1;padding:16px 8px;border:0;border-radius:14px;font-weight:900;font-size:17px;
    letter-spacing:.5px;cursor:pointer;color:white;touch-action:manipulation;}
  .startstop:disabled{opacity:.5;cursor:not-allowed;}
  #btnStart{background:linear-gradient(180deg,#22c55e,#15803d);}
  #btnStart.active{background:#14532d;color:#86efac;}
  #btnStop{background:linear-gradient(180deg,#ef4444,#b91c1c);}
  .pad{display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:1fr 1fr 1fr;
    gap:9px;margin:4px 0;aspect-ratio:1/1;}
  .pad .blank{visibility:hidden;}
  .pad button{font-size:30px;border-radius:16px;border:1px solid var(--border);
    background:#0b1220;color:var(--text);cursor:pointer;touch-action:none;
    display:flex;align-items:center;justify-content:center;}
  .pad button:disabled{opacity:.3;cursor:not-allowed;}
  .pad button:active:not(:disabled){background:#1e293b;transform:scale(.96);}
  .pad .stop-symbol{color:var(--red);font-size:24px;}
  .sliders{display:flex;flex-direction:column;gap:10px;background:var(--card);
    border:1px solid var(--border);border-radius:14px;padding:12px 14px;}
  .slider-row label{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:4px;color:var(--muted);}
  .slider-row label span:last-child{color:var(--text);font-weight:700;}
  .slider-row input[type="range"]{width:100%;height:30px;touch-action:manipulation;}
  .slider-row input:disabled{opacity:.4;}
</style>
</head>
<body>
<div class="page">
  <h1>AMR EMERGENCY CONTROL</h1>
  <div class="warn">
    Gui lenh thang xuong Arduino qua serial - khong qua lidar/camera/Nav2,
    khong con lop an toan tu dong. Luon quan sat truc tiep xe.
  </div>

  <div class="status-banner" id="statusLine">Chua bat dieu khien.</div>

  <div class="row">
    <button id="btnStart" class="startstop" onclick="startControl()">START</button>
    <button id="btnStop" class="startstop" onclick="stopControl()">STOP</button>
  </div>

  <div class="pad" oncontextmenu="return false;">
    <div class="blank"></div>
    <button id="btnUp" disabled title="Tien"
      onpointerdown="beginMove('forward')" onpointerup="endMove()" onpointerleave="endMove()" onpointercancel="endMove()">&#9650;</button>
    <div class="blank"></div>

    <button id="btnLeft" disabled title="Quay trai"
      onpointerdown="beginMove('left')" onpointerup="endMove()" onpointerleave="endMove()" onpointercancel="endMove()">&#9664;</button>
    <button id="btnCenterStop" disabled class="stop-symbol" title="Dung" onclick="endMove(true)">&#9632;</button>
    <button id="btnRight" disabled title="Quay phai"
      onpointerdown="beginMove('right')" onpointerup="endMove()" onpointerleave="endMove()" onpointercancel="endMove()">&#9654;</button>

    <div class="blank"></div>
    <button id="btnDown" disabled title="Lui"
      onpointerdown="beginMove('backward')" onpointerup="endMove()" onpointerleave="endMove()" onpointercancel="endMove()">&#9660;</button>
    <div class="blank"></div>
  </div>

  <div class="sliders">
    <div class="slider-row">
      <label><span>Toc do tien/lui (linear)</span><span id="linearValue">__LINEAR_DEFAULT__</span></label>
      <input id="linearSlider" type="range" disabled
        min="__LINEAR_MIN__" max="__LINEAR_MAX__" step="0.01" value="__LINEAR_DEFAULT__"
        oninput="document.getElementById('linearValue').textContent=this.value">
    </div>
    <div class="slider-row">
      <label><span>Toc do xoay (angular)</span><span id="angularValue">__ANGULAR_DEFAULT__</span></label>
      <input id="angularSlider" type="range" disabled
        min="__ANGULAR_MIN__" max="__ANGULAR_MAX__" step="0.01" value="__ANGULAR_DEFAULT__"
        oninput="document.getElementById('angularValue').textContent=this.value">
    </div>
  </div>
</div>

<script>
let controlActive = false;
let moveTimer = null;

const padButtons = ["btnUp","btnDown","btnLeft","btnRight","btnCenterStop"];
const sliderInputs = ["linearSlider","angularSlider"];

document.addEventListener("touchmove", function(e){ e.preventDefault(); }, {passive:false});

function setControlsEnabled(enabled){
  for(const id of padButtons){ document.getElementById(id).disabled = !enabled; }
  for(const id of sliderInputs){ document.getElementById(id).disabled = !enabled; }
}

function setStatus(text, kind){
  const el = document.getElementById("statusLine");
  el.textContent = text;
  el.className = "status-banner" + (kind ? " " + kind : "");
}

async function startControl(){
  const btnStart = document.getElementById("btnStart");
  const btnStop = document.getElementById("btnStop");
  btnStart.disabled = true;
  btnStop.disabled = true;
  setStatus("Dang doi Arduino san sang (toi da 8s)...", "busy");
  try{
    const res = await fetch("/api/start", {method:"POST"});
    const data = await res.json();
    if(data.ok){
      controlActive = true;
      btnStart.classList.add("active");
      setControlsEnabled(true);
      setStatus(data.message || "Da bat dieu khien.", "good");
    }else{
      setStatus(data.message || "Khong bat duoc dieu khien.", "bad");
    }
  }catch(e){ setStatus("Khong ket noi duoc server.", "bad"); }
  finally{ btnStart.disabled = false; btnStop.disabled = false; }
}

async function stopControl(){
  endMove(true);
  try{
    const res = await fetch("/api/stop", {method:"POST"});
    const data = await res.json();
    controlActive = false;
    document.getElementById("btnStart").classList.remove("active");
    setControlsEnabled(false);
    setStatus(data.message || "Da dung.", "");
  }catch(e){ setStatus("Khong ket noi duoc server.", "bad"); }
}

function currentLinear(){ return parseFloat(document.getElementById("linearSlider").value); }
function currentAngular(){ return parseFloat(document.getElementById("angularSlider").value); }

function twistForDirection(dir){
  const v = currentLinear();
  const w = currentAngular();
  if(dir === "forward")  return {linear: v,  angular: 0.0};
  if(dir === "backward") return {linear: -v, angular: 0.0};
  if(dir === "left")     return {linear: 0.0, angular: w};
  if(dir === "right")    return {linear: 0.0, angular: -w};
  return {linear: 0.0, angular: 0.0};
}

async function sendMove(linear, angular){
  try{
    await fetch("/api/move", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({linear, angular})
    });
  }catch(e){ /* keepalive loop se tu the gui lai, bo qua loi tam thoi */ }
}

function beginMove(dir){
  if(!controlActive) return;
  if(moveTimer) clearInterval(moveTimer);
  const send = () => {
    const t = twistForDirection(dir);
    sendMove(t.linear, t.angular);
  };
  send();
  moveTimer = setInterval(send, 100);
}

function endMove(forceZero){
  if(moveTimer){ clearInterval(moveTimer); moveTimer = null; }
  if(controlActive || forceZero){ sendMove(0.0, 0.0); }
}

async function refreshStatus(){
  try{
    const res = await fetch("/api/status");
    const data = await res.json();
    if(data.bridge_conflict === true){
      setStatus("CANH BAO: arduino_bridge (ROS) co the dang giu cong serial - dung stack chinh truoc.", "bad");
    }
  }catch(e){}
}
refreshStatus();
</script>
</body>
</html>
'''

CONTROL_HTML = (
    CONTROL_HTML
    .replace("__LINEAR_MIN__", str(LINEAR_MIN))
    .replace("__LINEAR_MAX__", str(LINEAR_MAX))
    .replace("__LINEAR_DEFAULT__", str(LINEAR_DEFAULT))
    .replace("__ANGULAR_MIN__", str(ANGULAR_MIN))
    .replace("__ANGULAR_MAX__", str(ANGULAR_MAX))
    .replace("__ANGULAR_DEFAULT__", str(ANGULAR_DEFAULT))
)


# ==========================================================
# FastAPI app
# ==========================================================
app = FastAPI(title=APP_TITLE)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if path in AUTH_PUBLIC_PATHS:
        return await call_next(request)

    if is_authenticated(request):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"ok": False, "message": "Unauthorized. Please login first."}, status_code=401)

    next_path = path
    if request.url.query:
        next_path += "?" + request.url.query
    return RedirectResponse(url=f"/login?next={quote(next_path, safe='')}", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(LOGIN_HTML)


@app.post("/api/login")
async def api_login(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    password = str(data.get("password", ""))
    if password != WEB_PASSWORD:
        return JSONResponse({"ok": False, "message": "Sai mat khau truy cap."}, status_code=401)

    response = JSONResponse({"ok": True, "message": "Authenticated."})
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=AUTH_COOKIE_VALUE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@app.post("/api/logout")
def api_logout():
    response = JSONResponse({"ok": True, "message": "Logged out."})
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=404)


@app.get("/", response_class=HTMLResponse)
def control_page():
    return HTMLResponse(CONTROL_HTML)


@app.get("/api/status")
def api_status():
    active, lin, ang, last_time = control_state.read()
    return JSONResponse({
        "ok": True,
        "serial_open": serial_link.is_open(),
        "serial_port": SERIAL_PORT,
        "control_active": active,
        "last_cmd_linear": lin,
        "last_cmd_angular": ang,
        "last_serial_error": serial_link.last_error,
        "bridge_conflict": check_arduino_bridge_running(),
    })


@app.post("/api/start")
def api_start():
    conflict = check_arduino_bridge_running()

    was_already_open = serial_link.is_open()

    if not serial_link.open():
        return JSONResponse({
            "ok": False,
            "message": f"Khong mo duoc serial: {serial_link.last_error}",
        })

    if not was_already_open:
        # Cong serial vua mo lan dau. O nhieu board/adapter USB-serial,
        # hanh dong open() co the khien Arduino TU RESET (mach DTR->RESET
        # qua tu dien). Thay vi doan mot khoang thoi gian co dinh roi hy
        # vong la du (co the qua ngan neu BNO055 init lau hon binh
        # thuong), CHO TICH CUC toi khi thuc su thay duoc telemetry that
        # tu Arduino - day la bang chung khach quan duy nhat cho biet
        # Arduino da chay xong setup() va vao den loop().
        print(
            f"[web_control] Dang cho Arduino gui telemetry (toi da "
            f"{ARDUINO_READY_TIMEOUT_S:.0f}s, co the no dang tu reset/khoi dong lai)...",
            flush=True,
        )
        arduino_ready = serial_link.wait_until_telemetry_seen(max_wait_s=ARDUINO_READY_TIMEOUT_S)

        if not arduino_ready:
            print(
                "[web_control] KHONG thay telemetry tu Arduino sau "
                f"{ARDUINO_READY_TIMEOUT_S:.0f}s - TU CHOI bat dieu khien de "
                "tranh gui lenh vao luc Arduino chua san sang.",
                flush=True,
            )
            return JSONResponse({
                "ok": False,
                "message": (
                    f"Da mo serial nhung khong nhan duoc telemetry tu Arduino "
                    f"sau {ARDUINO_READY_TIMEOUT_S:.0f}s. Co the Arduino dang "
                    "tu reset/khoi dong lai cham hon binh thuong, hoac day "
                    "cam bien/nguon co van de. Thu bam START lai sau vai giay, "
                    "hoac kiem tra Arduino truc tiep."
                ),
            })

        print("[web_control] Da xac nhan Arduino san sang (co telemetry).", flush=True)

    control_state.set_active(True)

    message = f"Da mo serial {SERIAL_PORT}, dieu khien dang BAT."
    if conflict:
        message += " CANH BAO: arduino_bridge (ROS) co the dang chay cung - nen dung stack chinh truoc."

    return JSONResponse({"ok": True, "message": message, "bridge_conflict": conflict})


@app.post("/api/stop")
def api_stop():
    control_state.set_active(False)
    serial_link.write_twist(0.0, 0.0)
    return JSONResponse({"ok": True, "message": "Da dung dieu khien, gui lenh dung ve 0."})


@app.post("/api/move")
async def api_move(request: Request):
    if not control_state.read()[0]:
        return JSONResponse({"ok": False, "message": "Chua bat dieu khien. Bam START truoc."}, status_code=400)

    try:
        data = await request.json()
    except Exception:
        data = {}

    try:
        linear = float(data.get("linear", 0.0))
        angular = float(data.get("angular", 0.0))
    except (TypeError, ValueError):
        linear, angular = 0.0, 0.0

    if not math.isfinite(linear):
        linear = 0.0
    if not math.isfinite(angular):
        angular = 0.0

    linear = clamp(linear, -LINEAR_MAX, LINEAR_MAX)
    angular = clamp(angular, -ANGULAR_MAX, ANGULAR_MAX)

    control_state.update_cmd(linear, angular)
    return JSONResponse({"ok": True, "linear": linear, "angular": angular})


@app.on_event("shutdown")
def on_shutdown():
    _stop_worker.set()
    control_state.set_active(False)
    serial_link.write_twist(0.0, 0.0)
    serial_link.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8090, type=int)
    args = parser.parse_args()
    print(f"[web_control] FILE_VERSION = {FILE_VERSION}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port)