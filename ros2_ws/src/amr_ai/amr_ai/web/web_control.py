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

                # Co gang xin quyen truy cap doc quyen (best-effort). Khong
                # bao ve duoc truong hop arduino_bridge.cpp da mo cong TRUOC
                # do roi (no khong dung TIOCEXCL), nhung ngan duoc tien trinh
                # MOI khac mo trung trong luc tool nay dang chay.
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
            print(f"[web_control] Serial OPENED OK: {self.port}", flush=True)
            return True

    def write_twist(self, linear_x: float, angular_z: float) -> bool:
        with self.lock:
            if self.fd is None:
                return False
            try:
                line = f"{linear_x:.6f},{angular_z:.6f}\n".encode("ascii")
                os.write(self.fd, line)
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
            serial_link.write_twist(0.0, 0.0)
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
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AMR Emergency Control - Login</title>
<style>
  :root{--bg:#020617;--card:rgba(15,23,42,.9);--border:#334155;--red:#ef4444;--text:#e5e7eb;--muted:#94a3b8;}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif;}
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
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AMR Emergency Control</title>
<style>
  :root{--bg:#020617;--card:rgba(15,23,42,.9);--border:#334155;--red:#ef4444;--green:#22c55e;
    --text:#e5e7eb;--muted:#94a3b8;--amber:#f59e0b;}
  *{box-sizing:border-box;-webkit-user-select:none;user-select:none;}
  body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);
    font-family:Arial,Helvetica,sans-serif;display:flex;flex-direction:column;align-items:center;
    padding:18px 14px 30px;}
  h1{color:var(--red);font-size:19px;margin:4px 0 2px;text-align:center;}
  .warn{color:var(--amber);font-size:12px;text-align:center;max-width:420px;margin:0 0 14px;line-height:1.4;}
  .panel{width:min(420px,94vw);border:1px solid var(--border);border-radius:18px;
    background:var(--card);padding:18px;margin-bottom:14px;}
  .row{display:flex;gap:10px;margin-bottom:14px;}
  .startstop{flex:1;padding:14px;border:0;border-radius:12px;font-weight:900;font-size:15px;
    letter-spacing:.5px;cursor:pointer;color:white;}
  #btnStart{background:linear-gradient(90deg,#15803d,#22c55e);}
  #btnStart.active{background:#14532d;color:#86efac;}
  #btnStop{background:linear-gradient(90deg,#b91c1c,#ef4444);}
  .status-line{text-align:center;font-size:13px;color:var(--muted);margin-bottom:14px;min-height:18px;}
  .status-line.bad{color:var(--red);}
  .status-line.good{color:var(--green);}
  .pad{display:grid;grid-template-columns:64px 64px 64px;grid-template-rows:64px 64px 64px;
    gap:8px;justify-content:center;margin-bottom:18px;}
  .pad .blank{visibility:hidden;}
  .pad button{font-size:22px;border-radius:14px;border:1px solid var(--border);
    background:#0b1220;color:var(--text);cursor:pointer;}
  .pad button:disabled{opacity:.35;cursor:not-allowed;}
  .pad button:active:not(:disabled){background:#1e293b;}
  .pad .stop-symbol{color:var(--red);font-size:20px;}
  .sliders{display:flex;flex-direction:column;gap:14px;}
  .slider-row label{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;}
  .slider-row input[type="range"]{width:100%;}
  .slider-row input:disabled{opacity:.4;}
</style>
</head>
<body>
  <h1>AMR EMERGENCY CONTROL</h1>
  <div class="warn">
    Gui lenh thang xuong Arduino qua serial, khong qua lidar/camera/Nav2.
    Khong con lop an toan tu dong nao - chi dung khi can thiet va luon quan
    sat truc tiep xe.
  </div>

  <div class="panel">
    <div class="row">
      <button id="btnStart" class="startstop" onclick="startControl()">START</button>
      <button id="btnStop" class="startstop" onclick="stopControl()">STOP</button>
    </div>
    <div class="status-line" id="statusLine">Chua bat dieu khien.</div>

    <div class="pad">
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

function setControlsEnabled(enabled){
  for(const id of padButtons){ document.getElementById(id).disabled = !enabled; }
  for(const id of sliderInputs){ document.getElementById(id).disabled = !enabled; }
}

function setStatus(text, kind){
  const el = document.getElementById("statusLine");
  el.textContent = text;
  el.className = "status-line" + (kind ? " " + kind : "");
}

async function startControl(){
  try{
    const res = await fetch("/api/start", {method:"POST"});
    const data = await res.json();
    if(data.ok){
      controlActive = true;
      document.getElementById("btnStart").classList.add("active");
      setControlsEnabled(true);
      setStatus(data.message || "Da bat dieu khien.", "good");
    }else{
      setStatus(data.message || "Khong bat duoc dieu khien.", "bad");
    }
  }catch(e){ setStatus("Khong ket noi duoc server.", "bad"); }
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

    if not serial_link.open():
        return JSONResponse({
            "ok": False,
            "message": f"Khong mo duoc serial: {serial_link.last_error}",
        })

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
    uvicorn.run(app, host=args.host, port=args.port)