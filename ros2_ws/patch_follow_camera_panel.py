#!/usr/bin/env python3
from pathlib import Path
import re
import sys

TARGET = Path.home() / "mobile_robot/ros2_ws/src/amr_ai/amr_ai/web/engineer_web_server.py"
if len(sys.argv) > 1:
    TARGET = Path(sys.argv[1]).expanduser()

s = TARGET.read_text()

# ---------------------------------------------------------------------
# 0) Safety check: this patch is for the CURRENT viewer file with camera panel
# ---------------------------------------------------------------------
if 'cameraTopicSelect' not in s or 'startCameraStream' not in s or 'stopCameraStream' not in s:
    raise RuntimeError(
        "File này chưa có camera panel hiện tại (không thấy cameraTopicSelect/startCameraStream). "
        "Hãy chạy patch trên đúng file engineer_web_server.py đang có CAMERA STREAM."
    )

# ---------------------------------------------------------------------
# 1) Backend API: toggle follow mode through /amr_ai/set_mode
# ---------------------------------------------------------------------
api_block = r'''
@app.post("/api/toggle_follow")
async def api_toggle_follow(request: Request):
    """
    Toggle FOLLOW from web viewer camera panel.

    If current mode is FOLLOW_DETECTING/FOLLOW_ACTIVE -> STOP_FOLLOW
    Otherwise -> START_FOLLOW

    Service:
      /amr_ai/set_mode amr_interfaces/srv/SetAiMode
      request: {mode: 0, command: "..."}
    """
    state = get_system_state()

    if not state.get("navigation", False):
        return JSONResponse({
            "ok": False,
            "command": "",
            "message": "FOLLOW chỉ hoạt động khi hệ thống đang ở chế độ NAVIGATION.",
            "state": state,
        })

    mode_text = get_mode()
    is_following = (
        "FOLLOW_DETECTING" in mode_text
        or "FOLLOW_ACTIVE" in mode_text
    )

    command = "STOP_FOLLOW" if is_following else "START_FOLLOW"

    service_cmd = (
        "ros2 service call /amr_ai/set_mode "
        "amr_interfaces/srv/SetAiMode "
        f"\"{{mode: 0, command: '{command}'}}\""
    )

    code, out = run_cmd(service_cmd, timeout=8.0)

    ok = (code == 0) and (
        "success=True" in out
        or "success: true" in out
        or "response:" in out
        or "SetAiMode_Response" in out
    )

    return JSONResponse({
        "ok": ok,
        "command": command,
        "message": out if out else ("FOLLOW command sent" if ok else "FOLLOW command failed"),
        "before_mode": mode_text,
        "state": state,
    })
'''

if '@app.post("/api/toggle_follow")' not in s:
    marker = '@app.get("/api/status")'
    if marker not in s:
        raise RuntimeError("Không tìm thấy @app.get(\"/api/status\") để chèn /api/toggle_follow")
    s = s.replace(marker, api_block + "\n" + marker, 1)

# ---------------------------------------------------------------------
# 2) CSS: camera topic on top, buttons CAMERA | STOP | FOLLOW below
# ---------------------------------------------------------------------
s = re.sub(
    r'(\.camera-toolbar\s*\{[^}]*?grid-template-columns:)\s*[^;]+;',
    r'\1 1fr;',
    s,
    count=1,
    flags=re.S,
)

camera_css = r'''
    .camera-button-row {
      display:grid;
      grid-template-columns:1fr 1fr 1fr;
      gap:8px;
      width:100%;
    }
    .camera-button-row button {
      width:100%;
      min-width:0;
    }
    #followCameraBtn {
      background:#facc15;
      color:#111827;
    }
    #followCameraBtn.following {
      background:#22c55e;
      color:#ffffff;
    }
'''
if ".camera-button-row" not in s:
    pos = s.find("    @media (max-width:1100px)")
    if pos != -1:
        s = s[:pos] + camera_css + s[pos:]
    else:
        s += "\n<style>\n" + camera_css + "\n</style>\n"

# ---------------------------------------------------------------------
# 3) HTML: add FOLLOW button under topic select
# ---------------------------------------------------------------------
patterns = [
    (
        r'(<div class="camera-toolbar">\s*<select id="cameraTopicSelect"></select>\s*)'
        r'(<button id="startCameraBtn" class="green" onclick="startCameraStream\(\)">CAMERA</button>\s*)'
        r'(<button id="stopCameraBtn" class="red" onclick="stopCameraStream\(\)">STOP</button>\s*)'
        r'(</div>)'
    ),
    (
        r'(<div class="camera-toolbar">\s*<input id="cameraTopicInput"[^>]*>\s*)'
        r'(<button id="startCameraBtn" class="green" onclick="startCameraStream\(\)">CAMERA</button>\s*)'
        r'(<button id="stopCameraBtn" class="red" onclick="stopCameraStream\(\)">STOP</button>\s*)'
        r'(</div>)'
    ),
]

if 'id="followCameraBtn"' not in s:
    replaced = False
    for pat in patterns:
        def repl(m):
            return (
                m.group(1)
                + '<div class="camera-button-row">\n'
                + '            ' + m.group(2).strip() + '\n'
                + '            ' + m.group(3).strip() + '\n'
                + '            <button id="followCameraBtn" class="yellow" onclick="toggleFollowMode()">FOLLOW</button>\n'
                + '          </div>\n'
                + '          ' + m.group(4)
            )
        s2, n = re.subn(pat, repl, s, count=1, flags=re.S)
        if n == 1:
            s = s2
            replaced = True
            break
    if not replaced:
        raise RuntimeError("Không tìm thấy block camera-toolbar để thêm nút FOLLOW.")

# ---------------------------------------------------------------------
# 4) JS: add toggleFollowMode()
# ---------------------------------------------------------------------
follow_js = r'''
async function toggleFollowMode(){
  const btn=document.getElementById("followCameraBtn");

  if(!viewerRosConnected){
    setCameraStatus("FOLLOW: hãy CONNECT ROSBridge trước.");
    return;
  }

  if(btn){
    btn.disabled=true;
    btn.textContent="WAIT...";
  }

  setCameraStatus("FOLLOW: đang gửi lệnh tới /amr_ai/set_mode...");

  try{
    const res=await fetch("/api/toggle_follow",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({})
    });

    const data=await res.json();

    if(data.ok){
      if(data.command==="START_FOLLOW"){
        setCameraStatus("FOLLOW: đã gửi START_FOLLOW. Robot đang chuẩn bị nhận diện/bám người.");
        if(btn){
          btn.textContent="FOLLOWING";
          btn.classList.add("following");
        }
      }else if(data.command==="STOP_FOLLOW"){
        setCameraStatus("FOLLOW: đã gửi STOP_FOLLOW.");
        if(btn){
          btn.textContent="FOLLOW";
          btn.classList.remove("following");
        }
      }else{
        setCameraStatus("FOLLOW: đã gửi lệnh.");
      }
      log("FOLLOW command: "+data.command);
    }else{
      setCameraStatus("FOLLOW lỗi: "+(data.message || "unknown error"));
      if(btn){
        btn.textContent="FOLLOW";
        btn.classList.remove("following");
      }
      log("FOLLOW failed: "+(data.message || "unknown error"));
    }

  }catch(e){
    setCameraStatus("FOLLOW lỗi kết nối webserver: "+e);
    log("FOLLOW error: "+e);

  }finally{
    if(btn){
      btn.disabled=false;
      if(btn.textContent==="WAIT..."){
        btn.textContent="FOLLOW";
      }
    }
  }
}

'''

if "async function toggleFollowMode()" not in s:
    marker = "function startCameraStream()"
    if marker not in s:
        raise RuntimeError("Không tìm thấy function startCameraStream() để chèn toggleFollowMode()")
    s = s.replace(marker, follow_js + "\n" + marker, 1)

TARGET.write_text(s)
print(f"Patched FOLLOW button in camera panel successfully: {TARGET}")
