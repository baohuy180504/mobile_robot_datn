#!/usr/bin/env python3
"""
web_control.py — AMR Worker Control Panel
Giao diện tối giản cho công nhân:
  - Đăng nhập (cùng thiết kế với engineer_web_server.py)
  - START : khởi động device stack (bringup_fusion)
  - STOP  : dừng hẳn
  - 4 nút điều hướng: tiến / lùi / trái / phải

Chạy: python3 web_control.py --port 8081
"""

import os
import re
import json
import shlex
import time
import secrets
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, FileResponse


# ==========================================================
# Paths & config
# ==========================================================
HOME_PATH = Path.home()
WORKSPACE = Path(os.environ.get("AMR_WS", str(HOME_PATH / "mobile_robot/ros2_ws")))

START_DEVICE_SCRIPT = WORKSPACE / "scripts" / "start_device_stack.sh"
STOP_SYSTEM_SCRIPT  = WORKSPACE / "scripts" / "stop_system_stack.sh"

ROS_SETUP = (
    "source ~/.bashrc >/dev/null 2>&1 || true; "
    f"source {HOME_PATH}/mobile_robot/ai_ros_venv/bin/activate && "
    "source /opt/ros/humble/setup.bash && "
    f"source {WORKSPACE}/install/setup.bash && "
    "export ROS_DOMAIN_ID=0; "
    "export ROS_LOCALHOST_ONLY=0; "
    "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; "
)

WORKER_SESSION   = "amr_worker_teleop"
WORKER_CMD_FILE  = Path("/tmp/amr_worker_cmd.json")
WORKER_PY_FILE   = Path("/tmp/amr_worker_teleop.py")

# Tốc độ di chuyển (có thể override qua env)
LINEAR_SPEED  = float(os.environ.get("AMR_WORKER_LINEAR",  "0.12"))
ANGULAR_SPEED = float(os.environ.get("AMR_WORKER_ANGULAR", "0.40"))

# Mapping phím → (linear_x, angular_z)
KEY_TO_TWIST: Dict[str, Tuple[float, float]] = {
    "i":  ( LINEAR_SPEED,   0.0),          # tiến
    ",":  (-LINEAR_SPEED,   0.0),          # lùi
    "j":  ( 0.0,            ANGULAR_SPEED),# trái
    "l":  ( 0.0,           -ANGULAR_SPEED),# phải
    "k":  ( 0.0,            0.0),          # dừng
}

# ==========================================================
# Script Python nhúng sẵn — chạy trong tmux, publish Twist
# qua rclpy, đọc lệnh từ shared JSON file mỗi 50ms.
# Không cần ROSBridge, không đọc stdin.
# ==========================================================
WORKER_TELEOP_PY = r"""#!/usr/bin/env python3
\"\"\"
amr_worker_teleop.py  —  Worker control background publisher.
Đọc lệnh từ /tmp/amr_worker_cmd.json, publish Twist tới ROS topic 20Hz.
Tự dừng (zero) nếu không có lệnh mới trong 0.5s (safety timeout).
\"\"\"
import sys, json, time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

CMD_FILE = "/tmp/amr_worker_cmd.json"
TIMEOUT  = 0.5   # seconds

class WorkerTeleop(Node):
    def __init__(self, topic):
        super().__init__("amr_worker_teleop")
        self.pub = self.create_publisher(Twist, topic, 10)
        self.create_timer(0.05, self.tick)   # 20 Hz
        self.get_logger().info(f"Worker teleop publisher: {topic}")

    def tick(self):
        try:
            with open(CMD_FILE) as f:
                d = json.load(f)
            age = time.time() - float(d.get("ts", 0))
            if age > TIMEOUT:
                lx = az = 0.0
            else:
                lx = float(d.get("lx", 0.0))
                az = float(d.get("az", 0.0))
        except Exception:
            lx = az = 0.0

        msg = Twist()
        msg.linear.x  = lx
        msg.angular.z = az
        self.pub.publish(msg)

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "/cmd_vel"
    rclpy.init()
    node = WorkerTeleop(topic)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        msg = Twist()
        node.pub.publish(msg)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
"""

# ==========================================================
# FastAPI app
# ==========================================================
app = FastAPI(title="AMR Worker Control")

STATIC_DIR = WORKSPACE / "src" / "amr_ai" / "amr_ai" / "web" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

WEB_PASSWORD      = os.environ.get("AMR_WEB_PASSWORD", "123")
AUTH_COOKIE_NAME  = "amr_worker_auth"
AUTH_COOKIE_VALUE = os.environ.get("AMR_WORKER_AUTH_TOKEN", secrets.token_urlsafe(32))
AUTH_PUBLIC_PATHS = {"/login", "/api/login", "/api/logout", "/login_background", "/favicon.ico"}

LOGIN_BG_PATH = Path(
    os.environ.get("AMR_LOGIN_BG_PATH", str(STATIC_DIR / "pic2.png"))
).expanduser()


def is_authenticated(request: Request) -> bool:
    return request.cookies.get(AUTH_COOKIE_NAME) == AUTH_COOKIE_VALUE


# ==========================================================
# Login HTML  (cùng thiết kế engineer_web_server.py)
# ==========================================================
LOGIN_HTML = r'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AMR Worker Access</title>
  <style>
    :root{--bg0:#020617;--bg1:#0f172a;--card:rgba(15,23,42,.84);--border:#334155;
      --blue:#38bdf8;--green:#22c55e;--red:#ef4444;--text:#e5e7eb;--muted:#94a3b8}
    *{box-sizing:border-box}
    html,body{height:100%}
    body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
      color:var(--text);font-family:Arial,Helvetica,sans-serif;overflow:hidden;
      background-color:#020617;background-image:url('/login_background');
      background-size:contain;background-position:center center;background-repeat:no-repeat}
    body:before,body:after{display:none}
    .gate{position:relative;z-index:1;width:min(430px,88vw);padding:22px 24px 20px;
      border:1px solid rgba(148,163,184,.26);border-radius:20px;
      background:rgba(15,23,42,.48);
      box-shadow:0 14px 42px rgba(0,0,0,.34),inset 0 0 22px rgba(56,189,248,.035);
      backdrop-filter:blur(4px)}
    .logo{width:84px;height:84px;margin:0 auto 8px;border-radius:22px;
      display:flex;align-items:center;justify-content:center;
      background:rgba(8,47,73,.46);border:1px solid rgba(56,189,248,.34);
      box-shadow:0 0 22px rgba(56,189,248,.16),inset 0 0 14px rgba(34,197,94,.06);overflow:hidden}
    .logo img{width:74px;height:74px;max-width:74px;max-height:74px;object-fit:contain;display:block}
    h1{margin:0;text-align:center;font-size:27px;letter-spacing:.35px}
    .sub{text-align:center;color:#cbd5e1;margin:8px 0 20px;font-size:14px;line-height:1.35}
    label{display:block;color:#e5e7eb;font-size:14px;margin-bottom:8px;font-weight:bold}
    input{width:100%;padding:12px 14px;border-radius:13px;border:1px solid rgba(148,163,184,.46);
      background:rgba(2,6,23,.62);color:white;font-size:17px;outline:none}
    input:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(56,189,248,.22)}
    button{width:100%;margin-top:14px;padding:13px 14px;border:0;border-radius:13px;
      background:linear-gradient(90deg,#16a34a,#22c55e);color:white;font-weight:900;
      font-size:16px;cursor:pointer;letter-spacing:.6px}
    button:hover{filter:brightness(1.08)}
    .status{min-height:20px;margin-top:12px;text-align:center;color:#facc15;font-size:14px}
    .foot{margin-top:18px;text-align:center;color:#cbd5e1;font-size:12px}
    .scanline{height:2px;width:100%;border-radius:999px;
      background:linear-gradient(90deg,transparent,var(--blue),var(--green),transparent);
      margin:0 0 20px;opacity:.62}
  </style>
</head>
<body>
<div class="gate">
  <div class="logo"><img src="/static/pic1.png" alt="AMR Logo"></div>
  <h1>AMR WORKER CONTROL</h1>
  <div class="sub">Worker Control Panel · Điều khiển xe tự động</div>
  <div class="scanline"></div>
  <label for="password">Mật khẩu truy cập</label>
  <input id="password" type="password" autocomplete="current-password" placeholder="Nhập mật khẩu">
  <button onclick="login()">LOGIN</button>
  <div class="status" id="status"></div>
  <div class="foot">Autonomous Mobile Robot · Secure Local Panel</div>
</div>
<script>
async function login(){
  const s=document.getElementById("status"),pw=document.getElementById("password").value;
  s.textContent="Đang xác thực...";
  try{
    const r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({password:pw})});
    const d=await r.json();
    if(d.ok){window.location.href=new URLSearchParams(window.location.search).get("next")||"/";}
    else{s.textContent=d.message||"Sai mật khẩu.";document.getElementById("password").focus();}
  }catch(e){s.textContent="Không kết nối được webserver.";}
}
document.getElementById("password").addEventListener("keydown",e=>{if(e.key==="Enter")login();});
document.getElementById("password").focus();
</script>
</body></html>'''


# ==========================================================
# Control page HTML
# ==========================================================
CONTROL_HTML = r'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
  <title>AMR Worker Control</title>
  <style>
    :root{
      --bg:#0f172a; --card:#1e293b; --border:#334155;
      --text:#e2e8f0; --muted:#94a3b8;
      --green:#22c55e; --green-dk:#15803d;
      --red:#ef4444;   --red-dk:#b91c1c;
      --blue:#3b82f6;  --blue-dk:#1d4ed8;
      --yellow:#facc15;
    }
    *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
    html,body{margin:0;padding:0;min-height:100dvh;
      background:var(--bg);color:var(--text);
      font-family:Arial,Helvetica,sans-serif;
      touch-action:manipulation;overscroll-behavior:none}
    body{display:flex;flex-direction:column;align-items:center;
      padding:14px 12px 28px;gap:12px}

    /* Header */
    .hdr{width:100%;max-width:380px;display:flex;align-items:center;gap:10px}
    .hdr-logo{width:40px;height:40px;border-radius:10px;flex-shrink:0;
      background:rgba(8,47,73,.6);border:1px solid rgba(56,189,248,.3);
      display:flex;align-items:center;justify-content:center;overflow:hidden}
    .hdr-logo img{width:34px;height:34px;object-fit:contain}
    .hdr-txt{flex:1}
    .hdr-title{font-size:15px;font-weight:900;letter-spacing:.3px}
    .hdr-sub{font-size:11px;color:var(--muted);margin-top:1px}
    .logout{margin-left:auto;background:none;border:1px solid var(--border);
      color:var(--muted);border-radius:8px;padding:5px 11px;font-size:12px;cursor:pointer}
    .logout:hover{color:var(--text);border-color:#64748b}

    /* Status */
    .status-bar{width:100%;max-width:380px;
      background:var(--card);border:1px solid var(--border);
      border-radius:12px;padding:10px 14px;
      display:flex;align-items:center;gap:10px}
    .dot{width:11px;height:11px;border-radius:50%;background:#334155;
      flex-shrink:0;transition:background .4s}
    .dot.on {background:var(--green);box-shadow:0 0 7px rgba(34,197,94,.5)}
    .dot.off{background:var(--red)}
    .dot.busy{background:var(--yellow);animation:blink .7s infinite}
    @keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}
    .st-main{font-size:14px}
    .st-sub{font-size:11px;color:var(--muted);margin-top:2px}

    /* START / STOP */
    .row{width:100%;max-width:380px;display:flex;gap:10px}
    .btn-start,.btn-stop{flex:1;height:66px;border:none;border-radius:16px;
      font-size:19px;font-weight:900;cursor:pointer;letter-spacing:.6px;
      transition:filter .1s,transform .08s;
      display:flex;align-items:center;justify-content:center;gap:6px}
    .btn-start{background:linear-gradient(135deg,var(--green-dk),var(--green));color:#fff}
    .btn-stop {background:linear-gradient(135deg,var(--red-dk),var(--red));color:#fff}
    .btn-start:disabled,.btn-stop:disabled{opacity:.32;cursor:not-allowed}
    .btn-start:not(:disabled):active{filter:brightness(.88);transform:scale(.97)}
    .btn-stop:not(:disabled):active {filter:brightness(.88);transform:scale(.97)}

    /* D-pad */
    .dpad{display:grid;grid-template-columns:repeat(3,90px);
      grid-template-rows:repeat(3,90px);gap:8px}
    .db{background:var(--card);border:1px solid var(--border);border-radius:16px;
      color:var(--text);font-size:32px;cursor:pointer;
      display:flex;align-items:center;justify-content:center;
      user-select:none;touch-action:none;-webkit-user-select:none;
      transition:background .08s,transform .06s,border-color .1s}
    .db:disabled{opacity:.22;cursor:not-allowed}
    .db.pressed,.db:not(:disabled):active{
      background:var(--blue-dk);border-color:var(--blue);transform:scale(.93)}
    .db.center{background:#2d1b1b;border-color:var(--red);color:var(--red)}
    .db.center.pressed,.db.center:not(:disabled):active{
      background:#7f1d1d;border-color:#f87171;transform:scale(.93)}
    .de{visibility:hidden}   /* empty corner */

    /* Log bar */
    .logbar{width:100%;max-width:380px;min-height:36px;
      background:var(--card);border:1px solid var(--border);
      border-radius:10px;padding:7px 12px;
      font-size:12px;color:var(--muted);text-align:center;line-height:1.45}
    .logbar.ok  {color:var(--green)}
    .logbar.err {color:var(--red)}
    .logbar.warn{color:var(--yellow)}
  </style>
</head>
<body>

<div class="hdr">
  <div class="hdr-logo"><img src="/static/pic1.png" alt="AMR"></div>
  <div class="hdr-txt">
    <div class="hdr-title">AMR WORKER CONTROL</div>
    <div class="hdr-sub">Điều khiển xe tự động</div>
  </div>
  <button class="logout" onclick="doLogout()">Đăng xuất</button>
</div>

<div class="status-bar">
  <div class="dot" id="dot"></div>
  <div>
    <div class="st-main" id="stMain">Đang kiểm tra...</div>
    <div class="st-sub"  id="stSub"></div>
  </div>
</div>

<div class="row">
  <button class="btn-start" id="btnStart" disabled onclick="doStart()">▶ START</button>
  <button class="btn-stop"  id="btnStop"  disabled onclick="doStop()">■ STOP</button>
</div>

<div class="dpad">
  <div class="de"></div>
  <button class="db" id="dF" disabled
    onpointerdown="startMove(event,'i')"  onpointerup="endMove(event)"
    onpointerleave="endMove(event)"       onpointercancel="endMove(event)">▲</button>
  <div class="de"></div>

  <button class="db" id="dL" disabled
    onpointerdown="startMove(event,'j')"  onpointerup="endMove(event)"
    onpointerleave="endMove(event)"       onpointercancel="endMove(event)">◄</button>
  <button class="db center" id="dS" disabled
    onpointerdown="doHardStop(event)"     onpointerup="clearPress(event)"
    onpointerleave="clearPress(event)"    onpointercancel="clearPress(event)">■</button>
  <button class="db" id="dR" disabled
    onpointerdown="startMove(event,'l')"  onpointerup="endMove(event)"
    onpointerleave="endMove(event)"       onpointercancel="endMove(event)">►</button>

  <div class="de"></div>
  <button class="db" id="dB" disabled
    onpointerdown="startMove(event,',')"  onpointerup="endMove(event)"
    onpointerleave="endMove(event)"       onpointercancel="endMove(event)">▼</button>
  <div class="de"></div>
</div>

<div class="logbar" id="logbar">Sẵn sàng.</div>

<script>
'use strict';
// ─── State ─────────────────────────────────────────────────
let sysOn    = false;
let driveOk  = false;
let moveTimer= null;
let curKey   = null;
let busy     = false;
let pollTimer= null;
const DRIVE_IDS = ['dF','dL','dR','dB','dS'];

// ─── UI ────────────────────────────────────────────────────
function log(msg,cls=''){
  const el=document.getElementById('logbar');
  el.textContent=msg; el.className='logbar'+(cls?' '+cls:'');
}
function setDrive(en){
  DRIVE_IDS.forEach(id=>{const b=document.getElementById(id);if(b)b.disabled=!en;});
}
function updateUI(d){
  sysOn=!!d.device;
  const dot=document.getElementById('dot');
  const m=document.getElementById('stMain');
  const s=document.getElementById('stSub');
  if(busy){
    dot.className='dot busy'; m.textContent='Đang xử lý...'; s.textContent='';
  }else if(sysOn){
    dot.className='dot on'; m.textContent='Hệ thống: ĐANG CHẠY'; s.textContent=d.active_mode||'';
  }else{
    dot.className='dot off'; m.textContent='Hệ thống: ĐÃ DỪNG'; s.textContent='Nhấn START để khởi động';
  }
  document.getElementById('btnStart').disabled = busy||sysOn;
  document.getElementById('btnStop').disabled  = busy||!sysOn;
  setDrive(sysOn && driveOk && !busy);
}
// ─── API ────────────────────────────────────────────────────
async function api(url,opts={}){
  try{const r=await fetch(url,opts);return await r.json();}
  catch(e){return{ok:false,message:'Lỗi mạng: '+e};}
}
async function pollStatus(){const d=await api('/api/wc/status');updateUI(d);}

// ─── START ──────────────────────────────────────────────────
async function doStart(){
  if(busy||sysOn)return;
  busy=true; driveOk=false;
  updateUI({device:false,active_mode:''});
  log('Đang khởi động hệ thống...','warn');

  const r1=await api('/api/wc/start',{method:'POST'});
  if(!r1.ok){
    log('START thất bại: '+(r1.message||''),'err');
    busy=false; await pollStatus(); return;
  }
  log('Hệ thống đang lên, chờ 3 giây...','warn');
  await new Promise(r=>setTimeout(r,3000));

  log('Đang khởi động teleop...','warn');
  const r2=await api('/api/wc/start_teleop',{method:'POST'});
  driveOk=!!r2.ok;

  busy=false; await pollStatus();
  if(driveOk) log('Sẵn sàng điều khiển.','ok');
  else log('Teleop lỗi: '+(r2.message||'Kiểm tra log'),'err');
}

// ─── STOP ───────────────────────────────────────────────────
async function doStop(){
  if(busy||!sysOn)return;
  endMove();
  busy=true; driveOk=false;
  updateUI({device:true,active_mode:''});
  log('Đang dừng hệ thống...','warn');

  // Dừng teleop ngay lập tức
  await api('/api/wc/stop_teleop',{method:'POST'});
  setDrive(false);

  // Gọi stop (backend trả lời ngay, script chạy background)
  await api('/api/wc/stop',{method:'POST'});

  // Poll cho đến khi dừng hẳn (tối đa 20 giây)
  let waited=0;
  while(waited<20){
    await new Promise(r=>setTimeout(r,1000));
    waited++;
    const d=await api('/api/wc/status');
    if(!d.device){
      busy=false; driveOk=false; updateUI(d);
      log('Hệ thống đã dừng hoàn toàn.','ok'); return;
    }
    log(`Đang dừng... (${waited}s)`,'warn');
  }
  // Hết timeout — cập nhật lại trạng thái thực
  busy=false;
  await pollStatus();
  log('Kiểm tra lại: hệ thống có thể chưa dừng hoàn toàn.','warn');
}

// ─── D-pad ─────────────────────────────────────────────────
function startMove(ev,key){
  ev.preventDefault();
  if(!sysOn||!driveOk||busy)return;
  ev.currentTarget.classList.add('pressed');
  ev.currentTarget.setPointerCapture(ev.pointerId);
  curKey=key;
  sendKey(key);
  if(moveTimer)clearInterval(moveTimer);
  moveTimer=setInterval(()=>{if(curKey)sendKey(curKey);},80);
}
function endMove(ev){
  if(ev&&ev.currentTarget){
    ev.currentTarget.classList.remove('pressed');
    try{ev.currentTarget.releasePointerCapture(ev.pointerId);}catch(_){}
  }
  if(moveTimer){clearInterval(moveTimer);moveTimer=null;}
  curKey=null;
  if(sysOn&&driveOk)sendKey('k');
}
function doHardStop(ev){
  ev.preventDefault();
  if(ev.currentTarget){
    ev.currentTarget.classList.add('pressed');
    ev.currentTarget.setPointerCapture(ev.pointerId);
  }
  endMove();
}
function clearPress(ev){
  if(ev&&ev.currentTarget)ev.currentTarget.classList.remove('pressed');
  try{ev.currentTarget.releasePointerCapture(ev.pointerId);}catch(_){}
}

async function sendKey(key){
  // fire-and-forget: không await để không lag button
  fetch('/api/wc/key',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({key})
  }).catch(()=>{});
}

// ─── Keyboard (desktop) ─────────────────────────────────────
const KB={'ArrowUp':'i','w':'i','W':'i',
  'ArrowDown':',','s':',','S':',',
  'ArrowLeft':'j','a':'j','A':'j',
  'ArrowRight':'l','d':'l','D':'l',
  ' ':'k','k':'k','K':'k'};
const kbSet=new Set();

window.addEventListener('keydown',e=>{
  const el=document.activeElement;
  if(el&&(el.tagName==='INPUT'||el.tagName==='BUTTON'))return;
  const key=KB[e.key]; if(!key||!sysOn||!driveOk||busy)return;
  e.preventDefault();
  if(key==='k'){endMove();return;}
  if(kbSet.has(e.key)&&e.repeat)return;
  kbSet.add(e.key); curKey=key; sendKey(key);
  if(moveTimer)clearInterval(moveTimer);
  moveTimer=setInterval(()=>{if(curKey)sendKey(curKey);},80);
});
window.addEventListener('keyup',e=>{
  const key=KB[e.key]; if(!key||key==='k')return;
  kbSet.delete(e.key); if(kbSet.size===0)endMove();
});
window.addEventListener('blur',()=>{if(curKey)endMove();});

// ─── Auto-stop khi thoát trang ──────────────────────────────
document.addEventListener('visibilitychange',()=>{
  if(document.hidden&&(curKey||driveOk)){
    endMove();
    navigator.sendBeacon('/api/wc/beacon_stop');
  }
});
window.addEventListener('beforeunload',()=>{
  endMove();
  navigator.sendBeacon('/api/wc/beacon_stop');
});

// ─── Logout ─────────────────────────────────────────────────
async function doLogout(){
  endMove();
  await api('/api/wc/stop_teleop',{method:'POST'}).catch(()=>{});
  await api('/api/logout',{method:'POST'});
  window.location.href='/login';
}

// ─── Init ────────────────────────────────────────────────────
(async()=>{
  await pollStatus();
  // Nếu teleop đang chạy từ trước (page reload)
  if(sysOn){
    const ts=await api('/api/wc/teleop_status');
    driveOk=!!ts.running;
    setDrive(driveOk);
    log(driveOk?'Sẵn sàng điều khiển.':'Nhấn START để bật điều khiển.', driveOk?'ok':'warn');
  }
  pollTimer=setInterval(pollStatus,5000);
})();
</script>
</body></html>'''


# ==========================================================
# Auth middleware
# ==========================================================
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in AUTH_PUBLIC_PATHS or path.startswith("/static/"):
        return await call_next(request)
    if is_authenticated(request):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"ok": False, "message": "Unauthorized."}, status_code=401)
    next_path = path + ("?" + request.url.query if request.url.query else "")
    return RedirectResponse(url=f"/login?next={quote(next_path, safe='')}", status_code=302)


# ==========================================================
# Page routes
# ==========================================================
@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(CONTROL_HTML)


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(LOGIN_HTML)


@app.get("/login_background")
def login_background():
    if LOGIN_BG_PATH.exists() and LOGIN_BG_PATH.is_file():
        return FileResponse(str(LOGIN_BG_PATH))
    return Response(status_code=404)


# ==========================================================
# Auth API
# ==========================================================
@app.post("/api/login")
async def api_login(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if str(data.get("password", "")) != WEB_PASSWORD:
        return JSONResponse({"ok": False, "message": "Sai mật khẩu truy cập."}, status_code=401)
    response = JSONResponse({"ok": True, "message": "Authenticated."})
    response.set_cookie(key=AUTH_COOKIE_NAME, value=AUTH_COOKIE_VALUE,
                        httponly=True, samesite="lax", secure=False)
    return response


@app.post("/api/logout")
def api_logout():
    response = JSONResponse({"ok": True, "message": "Logged out."})
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response


# ==========================================================
# Helper functions
# ==========================================================
def run_cmd(cmd: str, timeout: float = 15.0, source_ros: bool = True) -> Tuple[int, str]:
    full_cmd = (ROS_SETUP + cmd) if source_ros else cmd
    try:
        proc = subprocess.run(
            ["bash", "-lc", full_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip()
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        return 124, (str(out) + "\n[TIMEOUT]").strip()
    except Exception as exc:
        return 1, f"[ERROR] {exc}"


def tmux_running(name: str) -> bool:
    code, _ = run_cmd(f"tmux has-session -t {name}", timeout=1.5, source_ros=False)
    return code == 0


def get_system_state() -> Dict[str, Any]:
    device     = tmux_running("amr_device")
    navigation = tmux_running("amr_navigation")
    slam       = tmux_running("amr_slam")
    if navigation:   mode = "NAVIGATION"
    elif slam:       mode = "SLAM"
    elif device:     mode = "DEVICE_READY"
    else:            mode = "STOPPED"
    return {"device": device, "navigation": navigation, "slam": slam, "active_mode": mode}


def choose_topic() -> str:
    """
    Chọn topic phù hợp, tránh conflict với cmd_vel_safety_mux_node.
    Khi mux đang chạy (navigation mode) dùng /cmd_vel_localize.
    """
    state = get_system_state()
    if state.get("navigation", False):
        return "/cmd_vel_localize"
    code, out = run_cmd("ros2 topic info /cmd_vel_safe", timeout=2.0)
    if code == 0 and "Subscription count:" in out:
        m = re.search(r"Subscription count:\s*(\d+)", out)
        if m and int(m.group(1)) > 0:
            return "/cmd_vel_safe"
    return "/cmd_vel"


def write_cmd(lx: float, az: float) -> None:
    """Ghi lệnh vận tốc vào shared file để background teleop đọc."""
    WORKER_CMD_FILE.write_text(json.dumps({"lx": lx, "az": az, "ts": time.time()}))


def stop_cmd() -> None:
    """Ghi zero và timestamp cũ để teleop dừng ngay."""
    WORKER_CMD_FILE.write_text(json.dumps({"lx": 0.0, "az": 0.0, "ts": 0.0}))


def stop_worker_teleop() -> None:
    """Gửi zero và kill tmux session teleop."""
    stop_cmd()
    if tmux_running(WORKER_SESSION):
        run_cmd(f"tmux send-keys -t {shlex.quote(WORKER_SESSION)} C-c", timeout=1.0, source_ros=False)
        time.sleep(0.15)
    run_cmd(f"tmux kill-session -t {shlex.quote(WORKER_SESSION)} 2>/dev/null || true",
            timeout=2.0, source_ros=False)
    stop_cmd()


# ==========================================================
# Worker Control API  (/api/wc/)
# ==========================================================
@app.get("/api/wc/status")
def wc_status():
    return JSONResponse(get_system_state())


@app.post("/api/wc/start")
def wc_start():
    """Khởi động device stack (bringup_fusion)."""
    state = get_system_state()
    if state["device"]:
        return JSONResponse({"ok": True, "message": "Hệ thống đã chạy rồi.", "state": state})
    if not START_DEVICE_SCRIPT.exists():
        return JSONResponse({"ok": False, "message": f"Script not found: {START_DEVICE_SCRIPT}"})
    code, out = run_cmd(f"bash {START_DEVICE_SCRIPT}", timeout=20.0, source_ros=False)
    return JSONResponse({
        "ok": code == 0,
        "message": out.splitlines()[-1] if out else ("OK" if code == 0 else "Failed"),
        "state": get_system_state(),
    })


@app.post("/api/wc/stop")
def wc_stop():
    """
    Dừng hệ thống. Trả lời ngay, script chạy background.
    JS sẽ poll /api/wc/status cho đến khi device=false.
    """
    stop_worker_teleop()

    if not STOP_SYSTEM_SCRIPT.exists():
        return JSONResponse({"ok": False, "message": f"Script not found: {STOP_SYSTEM_SCRIPT}"})

    # Chạy stop script trong background (nohup) để không block response
    bg_cmd = (
        "nohup bash -lc "
        + shlex.quote(f"bash {STOP_SYSTEM_SCRIPT}")
        + " >/tmp/amr_worker_stop.log 2>&1 &"
    )
    run_cmd(bg_cmd, timeout=3.0, source_ros=False)

    return JSONResponse({"ok": True, "message": "Đang dừng hệ thống (background)..."})


@app.post("/api/wc/start_teleop")
def wc_start_teleop():
    """
    Khởi động background teleop publisher.
    Dùng script Python nhúng sẵn (không phụ thuộc run_web_teleop.sh hay ROSBridge).
    Script đọc /tmp/amr_worker_cmd.json và publish Twist qua rclpy tại 20Hz.
    """
    if tmux_running(WORKER_SESSION):
        return JSONResponse({"ok": True, "message": "Teleop already running.",
                             "topic": choose_topic()})

    topic = choose_topic()

    # Ghi script ra file tạm
    WORKER_PY_FILE.write_text(WORKER_TELEOP_PY)

    # Khởi tạo file lệnh với zero
    stop_cmd()

    # Chạy script trong tmux với môi trường ROS đầy đủ
    inner_cmd = (
        f"source {HOME_PATH}/mobile_robot/ai_ros_venv/bin/activate && "
        "source /opt/ros/humble/setup.bash && "
        f"source {WORKSPACE}/install/setup.bash && "
        "export ROS_DOMAIN_ID=0 && "
        "export ROS_LOCALHOST_ONLY=0 && "
        "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && "
        f"python3 {WORKER_PY_FILE} {shlex.quote(topic)}"
    )
    tmux_cmd = (
        f"tmux new-session -d -s {shlex.quote(WORKER_SESSION)} -n teleop "
        + shlex.quote(inner_cmd)
    )
    code, out = run_cmd(tmux_cmd, timeout=3.0, source_ros=False)

    return JSONResponse({
        "ok": code == 0,
        "message": "Teleop started." if code == 0 else f"Teleop failed: {out}",
        "topic": topic,
        "script": str(WORKER_PY_FILE),
    })


@app.post("/api/wc/stop_teleop")
def wc_stop_teleop():
    """Dừng teleop ngay lập tức và publish zero."""
    stop_worker_teleop()
    return JSONResponse({"ok": True, "message": "Teleop stopped."})


@app.get("/api/wc/teleop_status")
def wc_teleop_status():
    return JSONResponse({
        "running": tmux_running(WORKER_SESSION),
        "session": WORKER_SESSION,
        "topic": choose_topic(),
    })


@app.post("/api/wc/key")
async def wc_key(request: Request):
    """
    Nhận key từ browser, ghi Twist tương ứng vào shared file.
    Background teleop script đọc file này và publish đến ROS topic.
    Không dùng tmux send-keys (không work với ROS node).
    """
    try:
        data = await request.json()
        key = str(data.get("key", "")).strip()
    except Exception:
        return JSONResponse({"ok": False, "message": "Invalid JSON"})

    if key not in KEY_TO_TWIST:
        return JSONResponse({"ok": False, "message": f"Unknown key: {key}"})

    lx, az = KEY_TO_TWIST[key]
    write_cmd(lx, az)

    return JSONResponse({"ok": True, "key": key, "lx": lx, "az": az})


@app.post("/api/wc/beacon_stop")
def wc_beacon_stop():
    """Endpoint cho navigator.sendBeacon khi trang đóng."""
    stop_cmd()  # ghi zero — teleop script sẽ tự dừng sau timeout 0.5s
    return Response(status_code=204)


# ==========================================================
# Main
# ==========================================================
def main():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="AMR Worker Control Panel")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8081, type=int)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()