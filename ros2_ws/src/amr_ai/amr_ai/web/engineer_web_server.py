#!/usr/bin/env python3

import os
import re
import shlex
import socket
import math
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse


APP_TITLE = "AMR Engineer Web"

HOME_PATH = Path.home()
WORKSPACE = Path(os.environ.get("AMR_WS", str(HOME_PATH / "mobile_robot/ros2_ws")))

# State-machine scripts
START_DEVICE_SCRIPT = WORKSPACE / "scripts" / "start_device_stack.sh"
START_NAVIGATION_SCRIPT = WORKSPACE / "scripts" / "start_navigation_mode.sh"
START_SLAM_SCRIPT = WORKSPACE / "scripts" / "start_slam_mode.sh"
STOP_SYSTEM_SCRIPT = WORKSPACE / "scripts" / "stop_system_stack.sh"

# Web viewer bridge: browser -> rosbridge websocket
START_ROSBRIDGE_SCRIPT = WORKSPACE / "scripts" / "start_web_rosbridge.sh"
STOP_ROSBRIDGE_SCRIPT = WORKSPACE / "scripts" / "stop_web_rosbridge.sh"

# Manual teleop script used by START CONTROL
TELEOP_SCRIPT = WORKSPACE / "scripts" / "run_web_teleop.sh"

# Optional map saver scripts.
SAVE_FUSION_MAP_SCRIPT = WORKSPACE / "scripts" / "save_fusion_map.sh"
SAVE_2D_MAP_SCRIPT = WORKSPACE / "scripts" / "save_2d_map.sh"

MAP_DIR = WORKSPACE / "src" / "amr_slam" / "maps"
ACTIVE_MAP_FILE = WORKSPACE / "config" / "active_fusion_map.env"
NAV2_FUSION_PARAMS_FILE = WORKSPACE / "src" / "amr_navigation" / "config" / "nav2_params_fusion.yaml"
RUNTIME_WAYPOINTS_FILE = WORKSPACE / "config" / "waypoints_runtime.json"

ROS_SETUP = (
    "source ~/.bashrc >/dev/null 2>&1 || true; "
    f"source {HOME_PATH}/mobile_robot/ai_ros_venv/bin/activate && "
    "source /opt/ros/humble/setup.bash && "
    f"source {WORKSPACE}/install/setup.bash && "
    "export ROS_DOMAIN_ID=0; "
    "export ROS_LOCALHOST_ONLY=0; "
    "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; "
)

app = FastAPI(title=APP_TITLE)


def run_cmd(cmd: str, timeout: float = 15.0, source_ros: bool = True) -> Tuple[int, str]:
    full_cmd = (ROS_SETUP + cmd) if source_ros else cmd

    try:
        proc = subprocess.run(
            ["bash", "-lc", full_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip()

    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if exc.stdout else ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        return 124, (str(out) + "\n[TIMEOUT]").strip()

    except Exception as exc:
        return 1, f"[ERROR] {exc}"


def run_script(script_path: Path, timeout: float = 20.0) -> Dict[str, Any]:
    if not script_path.exists():
        return {
            "ok": False,
            "message": f"Script not found: {script_path}",
        }

    code, out = run_cmd(f"bash {script_path}", timeout=timeout, source_ros=False)
    return {
        "ok": code == 0,
        "returncode": code,
        "script": str(script_path),
        "output": out,
        "message": out.splitlines()[-1] if out else ("OK" if code == 0 else "Failed"),
    }


def get_ip_address() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip_addr = sock.getsockname()[0]
        sock.close()
        return ip_addr
    except Exception:
        return "unknown"


def tmux_session_running(name: str) -> bool:
    code, _ = run_cmd(f"tmux has-session -t {name}", timeout=1.0, source_ros=False)
    return code == 0


def get_system_state() -> Dict[str, Any]:
    device = tmux_session_running("amr_device")
    navigation = tmux_session_running("amr_navigation")
    slam = tmux_session_running("amr_slam")
    rosbridge = tmux_session_running("amr_web_rosbridge")

    if navigation:
        active_mode = "NAVIGATION"
    elif slam:
        active_mode = "SLAM"
    elif device:
        active_mode = "DEVICE_READY"
    else:
        active_mode = "STOPPED"

    return {
        "device": device,
        "navigation": navigation,
        "slam": slam,
        "rosbridge": rosbridge,
        "active_mode": active_mode,
    }


def choose_manual_teleop_topic() -> str:
    """
    Chọn topic teleop theo graph hiện tại:
    - Nếu /cmd_vel_safe có subscriber thì ưu tiên /cmd_vel_safe.
      Trường hợp này đúng với bringup_fusion, arduino_bridge đang nghe /cmd_vel_safe.
    - Nếu không có /cmd_vel_safe subscriber thì dùng /cmd_vel.
      Trường hợp này đúng với bringup_fusion_direct, arduino_bridge đang nghe /cmd_vel.
    """
    code, out = run_cmd("ros2 topic info /cmd_vel_safe", timeout=2.0)
    if code == 0 and "Subscription count:" in out:
        match = re.search(r"Subscription count:\s*(\d+)", out)
        if match and int(match.group(1)) > 0:
            return "/cmd_vel_safe"
    return "/cmd_vel"


def publish_zero_twist_once(topic_name: str) -> None:
    safe_topic = "/cmd_vel_safe" if topic_name == "/cmd_vel_safe" else "/cmd_vel"
    run_cmd(
        f"timeout 1 ros2 topic pub {safe_topic} geometry_msgs/msg/Twist '{{}}' --once >/dev/null 2>&1 || true",
        timeout=2.0,
    )


def publish_zero_twist_all() -> None:
    publish_zero_twist_once("/cmd_vel")
    publish_zero_twist_once("/cmd_vel_safe")


def tmux_send_key(session: str, key: str) -> Tuple[int, str]:
    safe_key = shlex.quote(key)
    return run_cmd(f"tmux send-keys -t {shlex.quote(session)} {safe_key}", timeout=1.0, source_ros=False)



def get_mode() -> str:
    _, out = run_cmd("timeout 8 ros2 topic echo /amr_ai/mode --once", timeout=10.0)
    return out if out else "No /amr_ai/mode data"


def get_lifecycle_status() -> str:
    nodes = ["/amcl", "/map_server", "/planner_server", "/controller_server", "/bt_navigator"]
    lines = []

    for node in nodes:
        code, out = run_cmd(f"ros2 lifecycle get {node}", timeout=8.0)
        lines.append(f"{node}: {out if code == 0 else 'unavailable'}")

    return "\n".join(lines)


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(INDEX_HTML)


@app.get("/viewer", response_class=HTMLResponse)
def viewer():
    return HTMLResponse(VIEWER_HTML)


@app.get("/api/status")
def api_status():
    state = get_system_state()
    ip_addr = get_ip_address()

    status = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "jetson_ip": ip_addr,
        **state,
        "viewer_url": f"http://{ip_addr}:8080/viewer",
        "rosbridge_websocket": f"ws://{ip_addr}:9090",
    }

    if state["navigation"]:
        status["mode_detail"] = get_mode()
    elif state["slam"]:
        status["mode_detail"] = "SLAM mode active. /map is expected to be live SLAM map."
    elif state["device"]:
        status["mode_detail"] = "Device ready. Select NAVIGATION or SLAM."
    else:
        status["mode_detail"] = "System stopped."

    return JSONResponse(status)

@app.get("/api/list_fusion_maps")
def api_list_fusion_maps():
    MAP_DIR.mkdir(parents=True, exist_ok=True)

    maps = []

    for yaml_file in sorted(MAP_DIR.glob("*.yaml")):
        name = yaml_file.stem
        pgm_file = yaml_file.with_suffix(".pgm")
        bt_file = MAP_DIR / f"{name}_3d.bt"

        maps.append({
            "name": name,
            "yaml": str(yaml_file),
            "pgm": str(pgm_file),
            "pgm_exists": pgm_file.exists(),
            "octomap": str(bt_file),
            "octomap_exists": bt_file.exists(),
            "valid": yaml_file.exists() and pgm_file.exists() and bt_file.exists(),
        })

    active = None
    if ACTIVE_MAP_FILE.exists():
        active = ACTIVE_MAP_FILE.read_text()

    return JSONResponse({
        "map_dir": str(MAP_DIR),
        "active_map_file": str(ACTIVE_MAP_FILE),
        "active_map_env": active,
        "maps": maps,
    })


@app.post("/api/set_active_fusion_map")
async def api_set_active_fusion_map(request: Request):
    state = get_system_state()

    if not state.get("navigation", False):
        return JSONResponse({
            "ok": False,
            "message": "SET ACTIVE MAP chỉ hoạt động khi hệ thống đang ở chế độ NAVIGATION.",
            "state": state,
        })

    try:
        data = await request.json()
    except Exception:
        data = {}

    raw_name = str(data.get("map_name", "")).strip()
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "", raw_name)

    if not safe_name:
        return JSONResponse({
            "ok": False,
            "message": "Map name is empty or invalid.",
        })

    yaml_file = MAP_DIR / f"{safe_name}.yaml"
    pgm_file = MAP_DIR / f"{safe_name}.pgm"
    bt_file = MAP_DIR / f"{safe_name}_3d.bt"

    if not yaml_file.exists():
        return JSONResponse({
            "ok": False,
            "message": f"Missing 2D yaml: {yaml_file}",
        })

    if not pgm_file.exists():
        return JSONResponse({
            "ok": False,
            "message": f"Missing 2D pgm: {pgm_file}",
        })

    if not bt_file.exists():
        return JSONResponse({
            "ok": False,
            "message": f"Missing 3D octomap: {bt_file}",
        })

    ACTIVE_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)

    env_text = (
        f'MAP_NAME="{safe_name}"\n'
        f'MAP_YAML="{yaml_file}"\n'
        f'OCTOMAP_BT="{bt_file}"\n'
        f'PARAMS_FILE="{NAV2_FUSION_PARAMS_FILE}"\n'
    )

    ACTIVE_MAP_FILE.write_text(env_text)

    return JSONResponse({
        "ok": True,
        "message": f"Active fusion map set to: {safe_name}",
        "map_name": safe_name,
        "yaml": str(yaml_file),
        "octomap": str(bt_file),
        "active_map_file": str(ACTIVE_MAP_FILE),
    })


@app.get("/api/active_fusion_map")
def api_active_fusion_map():
    if not ACTIVE_MAP_FILE.exists():
        return JSONResponse({
            "ok": False,
            "message": "No active fusion map selected.",
            "active_map_file": str(ACTIVE_MAP_FILE),
        })

    return JSONResponse({
        "ok": True,
        "active_map_file": str(ACTIVE_MAP_FILE),
        "content": ACTIVE_MAP_FILE.read_text(),
    })



@app.post("/api/send_nav_goal")
async def api_send_nav_goal(request: Request):
    state = get_system_state()

    if not state.get("navigation", False):
        return JSONResponse({
            "ok": False,
            "message": "NAV GOAL chỉ hoạt động khi hệ thống đang ở chế độ NAVIGATION.",
            "state": state,
        })

    try:
        data = await request.json()
        x = float(data.get("x", 0.0))
        y = float(data.get("y", 0.0))
        yaw = float(data.get("yaw", 0.0))
    except Exception as exc:
        return JSONResponse({
            "ok": False,
            "message": f"Invalid goal pose: {exc}",
            "state": state,
        })

    z = math.sin(yaw / 2.0)
    w = math.cos(yaw / 2.0)

    goal_yaml = (
        "{pose: {"
        "header: {frame_id: 'map'}, "
        "pose: {"
        f"position: {{x: {x:.6f}, y: {y:.6f}, z: 0.0}}, "
        f"orientation: {{x: 0.0, y: 0.0, z: {z:.8f}, w: {w:.8f}}}"
        "}"
        "}}"
    )

    goal_cmd = (
        "ros2 action send_goal "
        "/navigate_to_pose "
        "nav2_msgs/action/NavigateToPose "
        f"{shlex.quote(goal_yaml)}"
    )

    bg_cmd = (
        "nohup bash -lc "
        + shlex.quote(ROS_SETUP + goal_cmd)
        + " > /tmp/amr_web_nav_goal.log 2>&1 &"
    )

    code, out = run_cmd(bg_cmd, timeout=2.0, source_ros=False)

    return JSONResponse({
        "ok": code == 0,
        "message": "NAV GOAL sent." if code == 0 else "Failed to send NAV GOAL.",
        "x": x,
        "y": y,
        "yaw": yaw,
        "returncode": code,
        "output": out,
        "log_file": "/tmp/amr_web_nav_goal.log",
        "state": get_system_state(),
    })


@app.get("/api/manual_control_status")
def api_manual_control_status():
    return JSONResponse({
        "running": tmux_session_running("amr_web_teleop"),
        "topic": choose_manual_teleop_topic(),
        "session": "amr_web_teleop",
    })


@app.post("/api/start_manual_control")
def api_start_manual_control():
    if not TELEOP_SCRIPT.exists():
        return JSONResponse({
            "ok": False,
            "message": f"Web teleop script not found: {TELEOP_SCRIPT}",
        })

    topic = choose_manual_teleop_topic()

    if tmux_session_running("amr_web_teleop"):
        return JSONResponse({
            "ok": True,
            "message": "Manual teleop already running.",
            "topic": topic,
            "session": "amr_web_teleop",
        })

    publish_zero_twist_all()

    cmd = (
        f"tmux new-session -d -s amr_web_teleop -n teleop "
        + shlex.quote(
            f"cd {WORKSPACE} && "
            f"source {HOME_PATH}/mobile_robot/ai_ros_venv/bin/activate && "
            "source /opt/ros/humble/setup.bash && "
            "source install/setup.bash && "
            "export ROS_DOMAIN_ID=0 && "
            "export ROS_LOCALHOST_ONLY=0 && "
            "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && "
            f"bash {TELEOP_SCRIPT} {topic}"
        )
    )

    code, out = run_cmd(cmd, timeout=2.0, source_ros=False)

    return JSONResponse({
        "ok": code == 0,
        "message": "Web manual teleop node started." if code == 0 else "Failed to start web manual teleop node.",
        "topic": topic,
        "session": "amr_web_teleop",
        "returncode": code,
        "output": out,
    })


@app.post("/api/stop_manual_control")
def api_stop_manual_control():
    if tmux_session_running("amr_web_teleop"):
        for _ in range(3):
            tmux_send_key("amr_web_teleop", "k")
            time.sleep(0.05)

    publish_zero_twist_all()
    run_cmd("tmux kill-session -t amr_web_teleop 2>/dev/null || true", timeout=1.0, source_ros=False)
    publish_zero_twist_all()

    return JSONResponse({
        "ok": True,
        "message": "Manual teleop stopped.",
        "session": "amr_web_teleop",
    })


@app.post("/api/manual_teleop_key")
async def api_manual_teleop_key(request: Request):
    if not tmux_session_running("amr_web_teleop"):
        return JSONResponse({
            "ok": False,
            "message": "Manual teleop is not running. Press START CONTROL first.",
        })

    try:
        data = await request.json()
        key = str(data.get("key", "")).strip()
    except Exception:
        key = ""

    allowed = {
        "i", ",", "j", "l", "k",
        "u", "o", "m", ".",
        "q", "z", "w", "x", "e", "c"
    }

    if key not in allowed:
        return JSONResponse({
            "ok": False,
            "message": f"Invalid teleop key: {key}",
        })

    code, out = tmux_send_key("amr_web_teleop", key)

    if key == "k":
        publish_zero_twist_all()

    return JSONResponse({
        "ok": code == 0,
        "key": key,
        "returncode": code,
        "output": out,
    })





def normalize_runtime_waypoints_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chuẩn hóa file waypoint runtime theo quy chuẩn thống nhất:
      WP0/HOME fixed = (0,0,0), locked
      WP1, WP2, WP3... là các điểm chỉnh được
    Không sinh alias A/B/C nữa. ESP32 gửi trực tiếp WP1/WP2/...
    Vẫn đọc được format cũ có zones, nhưng chỉ lấy các zone tên WPn.
    """
    frame_id = str(data.get("frame_id", "map")).strip() or "map"

    home = {
        "name": "WP0",
        "x": 0.0,
        "y": 0.0,
        "yaw": 0.0,
        "locked": True,
        "source": "fixed_home",
    }

    by_wp: Dict[int, Dict[str, Any]] = {}

    raw_waypoints = data.get("waypoints", [])
    if isinstance(raw_waypoints, list):
        for item in raw_waypoints:
            if not isinstance(item, dict):
                continue

            raw_name = str(item.get("name", "")).strip().upper()
            match = re.match(r"^WP([1-9][0-9]*)$", raw_name)
            if not match:
                continue

            idx = int(match.group(1))
            try:
                by_wp[idx] = {
                    "name": f"WP{idx}",
                    "x": float(item.get("x", 0.0)),
                    "y": float(item.get("y", 0.0)),
                    "yaw": float(item.get("yaw", 0.0)),
                    "locked": False,
                    "source": item.get("source", f"WP{idx}"),
                }
            except Exception:
                continue

    raw_zones = data.get("zones", [])
    if isinstance(raw_zones, list):
        for item in raw_zones:
            if not isinstance(item, dict):
                continue

            raw_name = str(item.get("name", "")).strip().upper()
            match = re.match(r"^WP([1-9][0-9]*)$", raw_name)
            if not match:
                continue

            idx = int(match.group(1))
            if idx in by_wp:
                continue

            try:
                by_wp[idx] = {
                    "name": f"WP{idx}",
                    "x": float(item.get("x", 0.0)),
                    "y": float(item.get("y", 0.0)),
                    "yaw": float(item.get("yaw", 0.0)),
                    "locked": False,
                    "source": item.get("source", raw_name),
                }
            except Exception:
                continue

    waypoints = [by_wp[i] for i in sorted(by_wp.keys())]

    zones = [
        {"name": "H", "x": 0.0, "y": 0.0, "yaw": 0.0, "source": "WP0"},
        {"name": "HOME", "x": 0.0, "y": 0.0, "yaw": 0.0, "source": "WP0"},
        {"name": "WP0", "x": 0.0, "y": 0.0, "yaw": 0.0, "source": "WP0"},
    ]

    for wp in waypoints:
        zones.append({
            "name": wp["name"],
            "x": wp["x"],
            "y": wp["y"],
            "yaw": wp["yaw"],
            "source": wp["name"],
        })

    return {
        "frame_id": frame_id,
        "updated_at": str(data.get("updated_at", "")),
        "mapping_note": "WP0=HOME=(0,0,0) fixed. ESP32 sends WP1/WP2/WP3/... directly.",
        "home": home,
        "waypoints": waypoints,
        "zones": zones,
    }

def read_runtime_waypoints_file() -> Dict[str, Any]:
    if not RUNTIME_WAYPOINTS_FILE.exists():
        return normalize_runtime_waypoints_data({
            "frame_id": "map",
            "waypoints": [],
        })

    try:
        raw = json.loads(RUNTIME_WAYPOINTS_FILE.read_text())
        if not isinstance(raw, dict):
            raw = {}
        return normalize_runtime_waypoints_data(raw)
    except Exception as exc:
        return {
            "frame_id": "map",
            "updated_at": "",
            "mapping_note": f"Read error: {exc}",
            "home": {
                "name": "WP0",
                "alias": "H",
                "x": 0.0,
                "y": 0.0,
                "yaw": 0.0,
                "locked": True,
                "source": "fixed_home",
            },
            "waypoints": [],
            "zones": [
                {"name": "H", "x": 0.0, "y": 0.0, "yaw": 0.0, "source": "WP0"},
                {"name": "HOME", "x": 0.0, "y": 0.0, "yaw": 0.0, "source": "WP0"},
                {"name": "WP0", "x": 0.0, "y": 0.0, "yaw": 0.0, "source": "WP0"},
            ],
        }


@app.get("/api/runtime_waypoints")
def api_runtime_waypoints():
    data = read_runtime_waypoints_file()
    return JSONResponse({
        "ok": True,
        "path": str(RUNTIME_WAYPOINTS_FILE),
        "data": data,
    })


@app.post("/api/save_runtime_waypoints")
async def api_save_runtime_waypoints(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({
            "ok": False,
            "message": f"Invalid JSON: {exc}",
        })

    frame_id = str(payload.get("frame_id", "map")).strip() or "map"
    raw_waypoints = payload.get("waypoints", [])

    if not isinstance(raw_waypoints, list):
        return JSONResponse({
            "ok": False,
            "message": "waypoints must be a list",
        })

    by_idx: Dict[int, Dict[str, Any]] = {}

    for item in raw_waypoints:
        if not isinstance(item, dict):
            continue

        raw_name = str(item.get("name", "")).strip().upper()
        match = re.match(r"^WP([1-9][0-9]*)$", raw_name)

        if not match:
            # WP0 hoặc tên không hợp lệ đều bỏ qua. HOME luôn cố định.
            continue

        idx = int(match.group(1))

        try:
            by_idx[idx] = {
                "name": f"WP{idx}",
                "x": float(item.get("x", 0.0)),
                "y": float(item.get("y", 0.0)),
                "yaw": float(item.get("yaw", 0.0)),
                "locked": False,
                "source": f"WP{idx}",
            }
        except Exception:
            continue

    normalized = normalize_runtime_waypoints_data({
        "frame_id": frame_id,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "waypoints": [by_idx[i] for i in sorted(by_idx.keys())],
    })

    normalized["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    RUNTIME_WAYPOINTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_WAYPOINTS_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n"
    )

    return JSONResponse({
        "ok": True,
        "message": f"Saved {len(normalized['waypoints'])} editable waypoint(s). WP0/HOME is fixed.",
        "path": str(RUNTIME_WAYPOINTS_FILE),
        "mapping": "WP0=HOME fixed. ESP32 sends WP1/WP2/WP3/... directly.",
        "data": normalized,
    })

@app.get("/api/system_state")
def api_system_state():
    return api_status()


@app.post("/api/start_system")
def api_start_system():
    device_result = run_script(START_DEVICE_SCRIPT, timeout=15.0)

    # Start ROSBridge together with START so the built-in web viewer is ready.
    rosbridge_result = run_script(START_ROSBRIDGE_SCRIPT, timeout=10.0)

    return JSONResponse({
        "ok": bool(device_result.get("ok")),
        "message": "START executed: device stack requested; web viewer bridge requested.",
        "device": device_result,
        "rosbridge": rosbridge_result,
        "state": get_system_state(),
    })


@app.post("/api/stop_system")
def api_stop_system():
    stop_result = run_script(STOP_SYSTEM_SCRIPT, timeout=15.0)
    rosbridge_result = run_script(STOP_ROSBRIDGE_SCRIPT, timeout=10.0)

    return JSONResponse({
        "ok": bool(stop_result.get("ok")),
        "message": "STOP executed: navigation/slam/device stopped; web viewer bridge stopped.",
        "stop_system": stop_result,
        "rosbridge": rosbridge_result,
        "state": get_system_state(),
    })


@app.post("/api/start_navigation_mode")
def api_start_navigation_mode():
    state = get_system_state()

    if not state["device"]:
        return JSONResponse({
            "ok": False,
            "message": "Device is not started. Press START first.",
            "state": state,
        })

    if state["slam"]:
        return JSONResponse({
            "ok": False,
            "message": "SLAM is already active. Press STOP before switching to NAVIGATION.",
            "state": state,
        })

    if state["navigation"]:
        return JSONResponse({
            "ok": True,
            "message": "NAVIGATION is already active.",
            "state": state,
        })

    result = run_script(START_NAVIGATION_SCRIPT, timeout=20.0)
    return JSONResponse({
        **result,
        "message": result.get("message", "Navigation mode requested."),
        "state": get_system_state(),
    })


@app.post("/api/start_slam_mode")
def api_start_slam_mode():
    state = get_system_state()

    if not state["device"]:
        return JSONResponse({
            "ok": False,
            "message": "Device is not started. Press START first.",
            "state": state,
        })

    if state["navigation"]:
        return JSONResponse({
            "ok": False,
            "message": "NAVIGATION is already active. Press STOP before switching to SLAM.",
            "state": state,
        })

    if state["slam"]:
        return JSONResponse({
            "ok": True,
            "message": "SLAM is already active.",
            "state": state,
        })

    result = run_script(START_SLAM_SCRIPT, timeout=20.0)
    return JSONResponse({
        **result,
        "message": result.get("message", "SLAM mode requested."),
        "state": get_system_state(),
    })


@app.post("/api/save_map")
@app.post("/api/save_fusion_map")
async def api_save_map(request: Request):
    state = get_system_state()

    if not state["slam"]:
        return JSONResponse({
            "ok": False,
            "message": "SAVE MAP chỉ hoạt động khi đang ở chế độ SLAM.",
            "state": state,
        })

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    raw_name = str(payload.get("map_name", "")).strip()
    if raw_name:
        map_name = re.sub(r"[^A-Za-z0-9_-]", "", raw_name)
    else:
        map_name = "fusion_map_" + time.strftime("%Y%m%d_%H%M%S")

    if not map_name:
        map_name = "fusion_map_" + time.strftime("%Y%m%d_%H%M%S")

    if SAVE_FUSION_MAP_SCRIPT.exists():
        script = SAVE_FUSION_MAP_SCRIPT
    elif SAVE_2D_MAP_SCRIPT.exists():
        script = SAVE_2D_MAP_SCRIPT
    else:
        return JSONResponse({
            "ok": False,
            "message": "No map saver script found. Expected save_fusion_map.sh or save_2d_map.sh.",
            "state": state,
        })

    cmd = f"bash {shlex.quote(str(script))} {shlex.quote(map_name)}"
    code, out = run_cmd(cmd, timeout=120.0, source_ros=False)

    return JSONResponse({
        "ok": code == 0,
        "returncode": code,
        "map_name": map_name,
        "script": str(script),
        "output": out,
        "state": get_system_state(),
    })


@app.post("/api/start_rosbridge")
def api_start_rosbridge():
    return JSONResponse(run_script(START_ROSBRIDGE_SCRIPT, timeout=10.0))


@app.post("/api/stop_rosbridge")
def api_stop_rosbridge():
    return JSONResponse(run_script(STOP_ROSBRIDGE_SCRIPT, timeout=10.0))


@app.get("/api/rosbridge_info")
def api_rosbridge_info():
    ip_addr = get_ip_address()

    return JSONResponse({
        "running": tmux_session_running("amr_web_rosbridge"),
        "websocket": f"ws://{ip_addr}:9090",
        "viewer": f"http://{ip_addr}:8080/viewer",
        "default_topics": {
            "map": "/map",
            "pose": "/amcl_pose",
            "scan": "/scan_filtered",
        },
    })


@app.get("/api/ros_env")
def api_ros_env():
    _, out = run_cmd(
        'echo ROS_DOMAIN_ID=$ROS_DOMAIN_ID; '
        'echo ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY; '
        'echo RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION; '
        'which ros2; '
        'python3 -c "import sys; print(sys.executable)"',
        timeout=8.0,
    )
    return JSONResponse({"output": out})


@app.get("/api/ros_nodes")
def api_ros_nodes():
    _, out = run_cmd("ros2 node list --no-daemon", timeout=15.0)
    return JSONResponse({"output": out if out else "(no nodes)"})


@app.get("/api/ros_topics")
def api_ros_topics():
    _, out = run_cmd("ros2 topic list --no-daemon", timeout=15.0)
    return JSONResponse({"output": out if out else "(no topics)"})


@app.get("/api/ros_topics_typed")
def api_ros_topics_typed():
    _, out = run_cmd("ros2 topic list -t --no-daemon", timeout=15.0)

    topics = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^(.+?)\s+\[(.+?)\]$", line)
        if match:
            topics.append({
                "name": match.group(1).strip(),
                "type": match.group(2).strip(),
            })
        else:
            topics.append({
                "name": line,
                "type": "",
            })

    return JSONResponse({
        "topics": topics,
        "raw": out,
    })


@app.get("/api/ros_services")
def api_ros_services():
    _, out = run_cmd("ros2 service list --no-daemon", timeout=15.0)
    return JSONResponse({"output": out if out else "(no services)"})


@app.get("/api/mode")
def api_mode():
    return JSONResponse({"output": get_mode()})


@app.get("/api/lifecycle")
def api_lifecycle():
    return JSONResponse({"output": get_lifecycle_status()})


INDEX_HTML = r'''
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>AMR Engineer Web</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg:#0f172a; --panel:#111827; --card:#1f2937; --text:#e5e7eb;
      --muted:#9ca3af; --green:#16a34a; --red:#dc2626; --blue:#2563eb;
      --orange:#f97316; --purple:#9333ea; --border:#374151;
    }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font-family:Arial, Helvetica, sans-serif; }
    header { padding:18px 24px; background:#020617; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }
    header h1 { margin:0; font-size:24px; }
    header .ip { color:var(--muted); font-size:14px; }
    main { padding:20px; display:grid; grid-template-columns:360px 1fr; gap:20px; }
    .panel { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; box-shadow:0 10px 30px rgba(0,0,0,.25); }
    .panel h2 { margin:0 0 14px 0; font-size:18px; }
    .btn-grid { display:grid; grid-template-columns:1fr; gap:12px; }
    button { border:none; border-radius:10px; padding:14px 16px; color:white; font-weight:bold; font-size:15px; cursor:pointer; }
    button:active { transform:scale(.98); }
    button:hover { opacity:.9; }
    button:disabled { cursor:not-allowed; opacity:.42; }
    .start { background:var(--green); }
    .stop { background:var(--red); }
    .blue { background:var(--blue); }
    .orange { background:var(--orange); color:#111827; }
    .purple { background:var(--purple); }
    .status-line { display:flex; gap:10px; align-items:center; margin-bottom:10px; color:var(--muted); font-size:14px; }
    .badge { display:inline-block; padding:5px 9px; border-radius:999px; background:#334155; color:white; font-size:12px; font-weight:bold; }
    .badge.ok { background:var(--green); }
    .badge.bad { background:var(--red); }
    .badge.warn { background:var(--orange); color:#111827; }
    pre { margin:0; white-space:pre-wrap; word-break:break-word; background:#020617; border:1px solid var(--border); border-radius:10px; padding:12px; min-height:120px; max-height:560px; overflow:auto; font-size:13px; line-height:1.4; color:#d1d5db; }
    .cards { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }
    .card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:12px; }
    .card .title { font-size:13px; color:var(--muted); margin-bottom:8px; }
    .card .value { font-size:15px; font-weight:bold; }
    .section-title { margin-top:12px; margin-bottom:4px; color:#cbd5e1; font-size:13px; font-weight:bold; }
    @media (max-width:900px) { main { grid-template-columns:1fr; } .cards { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>AMR Engineer Web</h1>
    <div class="ip" id="ipText">Jetson IP: loading...</div>
  </header>

  <main>
    <section class="panel">
      <h2>Control</h2>

      <div class="btn-grid">
        <button class="start" onclick="startSystem()">START</button>
        <button class="stop" onclick="stopSystem()">STOP</button>

        <div class="section-title">Mode selection</div>
        <button class="purple" id="navBtn" onclick="startNavigationMode()">NAVIGATION</button>
        <button class="purple" id="slamBtn" onclick="startSlamMode()">SLAM</button>

        <label style="margin-top:10px;color:#9ca3af;font-size:13px;">Fusion map for NAVIGATION</label>
        <select id="fusionMapSelect" style="width:100%;padding:10px;border-radius:8px;background:#020617;color:#e5e7eb;border:1px solid #374151;"></select>

        <button class="blue" id="listMapsBtn" onclick="listFusionMaps()">LIST MAPS</button>
        <button class="orange" id="setActiveMapBtn" onclick="setActiveFusionMap()">SET ACTIVE MAP</button>

        <div class="section-title">Viewer</div>
        <button class="blue" onclick="openViewer()">OPEN VIEWER</button>
        <button class="blue" onclick="rosbridgeInfo()">ROSBRIDGE INFO</button>

        <div class="section-title">Diagnostics</div>
        <button class="blue" onclick="loadStatus()">REFRESH STATUS</button>
        <button class="blue" onclick="loadNodes()">ROS NODES</button>
        <button class="blue" onclick="loadTopics()">ROS TOPICS</button>
        <button class="blue" onclick="loadLifecycle()">NAV2 LIFECYCLE</button>
        <button class="blue" onclick="loadServices()">ROS SERVICES</button>
      </div>
    </section>

    <section class="panel">
      <h2>Dashboard</h2>

      <div class="cards">
        <div class="card">
          <div class="title">System State</div>
          <div class="value" id="stackState">unknown</div>
        </div>
        <div class="card">
          <div class="title">Last Update</div>
          <div class="value" id="lastUpdate">unknown</div>
        </div>
      </div>

      <div class="status-line">
        <span class="badge" id="stackBadge">UNKNOWN</span>
        <span id="messageText">Ready</span>
      </div>

      <pre id="output">Press REFRESH STATUS to load current state.</pre>
    </section>
  </main>

<script>
const output=document.getElementById('output');
const messageText=document.getElementById('messageText');
const stackBadge=document.getElementById('stackBadge');
const stackState=document.getElementById('stackState');
const lastUpdate=document.getElementById('lastUpdate');
const ipText=document.getElementById('ipText');

function showMessage(msg){ messageText.textContent=msg; }
function pretty(obj){ return JSON.stringify(obj,null,2); }

async function getJson(url){
  const res=await fetch(url);
  return await res.json();
}

async function postJson(url){
  showMessage('Sending command...');
  const res=await fetch(url,{method:'POST'});
  const data=await res.json();
  output.textContent=pretty(data);
  showMessage(data.message || 'Done');
  setTimeout(loadStatus,1500);
}

async function listFusionMaps() {
  const state = await getJson("/api/status");

  if (!state.navigation) {
    output.textContent = "LIST MAPS chỉ hoạt động khi hệ thống đang ở chế độ NAVIGATION.";
    showMessage("LIST MAPS disabled outside NAVIGATION");
    updateButtons(state);
    return;
  }

  const data = await getJson("/api/list_fusion_maps");

  const sel = document.getElementById("fusionMapSelect");
  if (sel) {
    sel.innerHTML = "";

    data.maps.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m.name;
      opt.textContent = m.valid
        ? `${m.name} [2D+3D OK]`
        : `${m.name} [missing file]`;
      opt.disabled = !m.valid;
      sel.appendChild(opt);
    });
  }

  output.textContent = pretty(data);
  showMessage("Fusion map list loaded");
  updateButtons(state);
}


async function setActiveFusionMap() {
  const state = await getJson("/api/status");

  if (!state.navigation) {
    output.textContent = "SET ACTIVE MAP chỉ hoạt động khi hệ thống đang ở chế độ NAVIGATION.";
    showMessage("SET ACTIVE MAP disabled outside NAVIGATION");
    updateButtons(state);
    return;
  }

  const sel = document.getElementById("fusionMapSelect");

  if (!sel || !sel.value) {
    showMessage("No map selected");
    return;
  }

  const res = await fetch("/api/set_active_fusion_map", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      map_name: sel.value
    })
  });

  const data = await res.json();
  output.textContent = pretty(data);
  showMessage(data.ok ? "Active map selected" : "Set active map failed");

  const newState = await getJson("/api/status");
  updateButtons(newState);
}


async function startSystem(){ await postJson('/api/start_system'); }
async function stopSystem(){ await postJson('/api/stop_system'); }
async function startNavigationMode(){ await postJson('/api/start_navigation_mode'); }
async function startSlamMode(){ await postJson('/api/start_slam_mode'); }
async function saveMap(){ output.textContent='SAVE MAP đã được chuyển sang trang Viewer.'; showMessage('Open Viewer để lưu map khi đang SLAM'); }

async function rosbridgeInfo(){
  const data=await getJson('/api/rosbridge_info');
  output.textContent=pretty(data);
  showMessage('ROSBridge info loaded');
}

async function openViewer(){
  const data=await getJson('/api/rosbridge_info');
  window.open(data.viewer,'_blank');
}

function updateButtons(data) {
  const navBtn = document.getElementById('navBtn');
  const slamBtn = document.getElementById('slamBtn');

  const fusionMapSelect = document.getElementById('fusionMapSelect');
  const listMapsBtn = document.getElementById('listMapsBtn');
  const setActiveMapBtn = document.getElementById('setActiveMapBtn');

  const device = !!data.device;
  const navigation = !!data.navigation;
  const slam = !!data.slam;

  if (navBtn) {
    navBtn.disabled = !device || slam || navigation;
    navBtn.style.opacity = navBtn.disabled ? 0.45 : 1.0;
  }

  if (slamBtn) {
    slamBtn.disabled = !device || navigation || slam;
    slamBtn.style.opacity = slamBtn.disabled ? 0.45 : 1.0;
  }

  // LIST MAPS / SET ACTIVE MAP chỉ có hiệu lực khi đang NAVIGATION
  const mapControlEnabled = navigation && !slam;

  if (fusionMapSelect) {
    fusionMapSelect.disabled = !mapControlEnabled;
    fusionMapSelect.style.opacity = fusionMapSelect.disabled ? 0.45 : 1.0;
  }

  if (listMapsBtn) {
    listMapsBtn.disabled = !mapControlEnabled;
    listMapsBtn.style.opacity = listMapsBtn.disabled ? 0.45 : 1.0;
  }

  if (setActiveMapBtn) {
    setActiveMapBtn.disabled = !mapControlEnabled;
    setActiveMapBtn.style.opacity = setActiveMapBtn.disabled ? 0.45 : 1.0;
  }
}


function updateStateView(data){
  lastUpdate.textContent=data.time || 'unknown';
  ipText.textContent='Jetson IP: '+(data.jetson_ip || 'unknown');

  const mode=data.active_mode || 'STOPPED';
  stackState.textContent=mode;
  stackBadge.textContent=mode;

  if(mode === 'STOPPED'){
    stackBadge.className='badge bad';
  } else if(mode === 'DEVICE_READY'){
    stackBadge.className='badge warn';
  } else {
    stackBadge.className='badge ok';
  }

  updateButtons(data);
}

async function loadStatus(){
  showMessage('Loading status...');
  const data=await getJson('/api/status');
  output.textContent=pretty(data);
  updateStateView(data);
  showMessage('Status updated');
}

async function loadNodes(){
  const data=await getJson('/api/ros_nodes');
  output.textContent=data.output;
  showMessage('ROS nodes loaded');
}

async function loadTopics(){
  const data=await getJson('/api/ros_topics');
  output.textContent=data.output;
  showMessage('ROS topics loaded');
}

async function loadServices(){
  const data=await getJson('/api/ros_services');
  output.textContent=data.output;
  showMessage('ROS services loaded');
}

async function loadLifecycle(){
  const data=await getJson('/api/lifecycle');
  output.textContent=data.output;
  showMessage('Lifecycle loaded');
}

loadStatus();


</script>
</body>
</html>
'''


VIEWER_HTML = r'''
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>AMR Map Viewer</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.jsdelivr.net/npm/roslib/build/roslib.min.js"></script>
  <style>
    :root {
      --bg:#0f172a;
      --panel:#111827;
      --card:#020617;
      --border:#374151;
      --text:#e5e7eb;
      --muted:#9ca3af;
      --green:#16a34a;
      --red:#dc2626;
      --blue:#2563eb;
      --purple:#9333ea;
      --orange:#f97316;
    }
    * { box-sizing:border-box; }
    body {
      margin:0;
      background:var(--bg);
      color:var(--text);
      font-family:Arial, Helvetica, sans-serif;
      overflow:hidden;
    }
    header {
      height:62px;
      background:#020617;
      border-bottom:1px solid var(--border);
      padding:14px 20px;
      display:flex;
      justify-content:space-between;
      align-items:center;
    }
    h1 { margin:0; font-size:22px; }
    main {
      height:calc(100vh - 62px);
      display:grid;
      grid-template-columns:460px 1fr;
      gap:14px;
      padding:14px;
    }
    .panel {
      background:var(--panel);
      border:1px solid var(--border);
      border-radius:12px;
      padding:12px;
      overflow:auto;
    }
    label {
      display:block;
      margin-top:10px;
      margin-bottom:5px;
      font-size:13px;
      color:var(--muted);
    }
    input, select {
      width:100%;
      padding:9px;
      border-radius:8px;
      border:1px solid var(--border);
      background:#020617;
      color:var(--text);
      font-size:14px;
    }
    button {
      border:none;
      border-radius:9px;
      padding:11px;
      font-weight:bold;
      cursor:pointer;
      color:white;
      background:var(--blue);
    }
    button:hover { opacity:.92; }
    button:disabled {
      opacity:.45;
      cursor:not-allowed;
    }
    button.green { background:var(--green); }
    button.red { background:var(--red); }
    button.purple { background:var(--purple); }
    button.orange { background:var(--orange); color:#111827; }
    .row {
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:8px;
      margin-top:9px;
    }

    .section-title {
      margin-top:14px;
      margin-bottom:8px;
      color:#e5e7eb;
      font-weight:bold;
      font-size:15px;
      border-top:1px solid #1f2937;
      padding-top:12px;
    }
    .tool-grid {
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:8px;
      margin-top:8px;
    }
    #toolWaypointBtn {
      grid-column:1 / 3;
    }
    .tool-btn {
      background:#334155;
      color:#e5e7eb;
    }
    .tool-btn.active {
      background:#16a34a;
      color:#ffffff;
      outline:2px solid #bbf7d0;
    }
    .waypoint-actions {
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:8px;
      margin-top:8px;
    }
    .tool-action-btn:disabled {
      opacity:0.42;
      cursor:not-allowed;
      filter:grayscale(0.25);
    }
    .waypoint-list {
      margin-top:9px;
      background:#020617;
      border:1px solid var(--border);
      border-radius:10px;
      padding:8px;
      min-height:80px;
      max-height:230px;
      overflow:auto;
    }
    .waypoint-row.locked { border-color:#64748b; background:#0f172a; }
    .waypoint-row.locked .waypoint-name { color:#facc15; }
    .waypoint-row {
      display:grid;
      grid-template-columns:82px 1fr 46px 32px;
      gap:7px;
      align-items:center;
      padding:6px 4px;
      border-bottom:1px solid #1f2937;
      font-size:12px;
    }
    .waypoint-row:last-child { border-bottom:none; }
    .waypoint-name {
      color:#e5e7eb;
      font-weight:bold;
      white-space:nowrap;
    }
    .waypoint-input {
      background:#ffffff;
      color:#111827;
      border:1px solid #cbd5e1;
      font-weight:bold;
      padding:7px;
      font-size:12px;
    }
    .waypoint-get {
      background:#16a34a;
      padding:7px 5px;
      font-size:12px;
    }
    .waypoint-remove {
      background:#dc2626;
      padding:6px;
      border-radius:7px;
      width:28px;
      height:28px;
      line-height:16px;
    }
    .tool-status {
      margin-top:8px;
      color:#facc15;
      font-size:12px;
      line-height:1.35;
      min-height:34px;
    }


    .manual-control {
      margin-top:14px;
      padding-top:12px;
      border-top:1px solid #253044;
    }

    .manual-start-btn {
      width:100%;
      margin-top:8px;
      background:#16a34a;
      color:#ffffff;
      border-radius:10px;
      font-size:14px;
      font-weight:900;
      padding:12px 0;
    }
    .manual-start-btn.ready {
      background:#22c55e;
      box-shadow:0 0 0 2px rgba(34,197,94,0.25) inset;
    }
    .manual-start-btn.active {
      background:#dc2626;
      box-shadow:0 0 0 2px rgba(220,38,38,0.25) inset;
    }
    .manual-btn:disabled,
    .manual-slider-row input:disabled {
      opacity:0.42;
      cursor:not-allowed;
    }

    .manual-pad {
      display:grid;
      grid-template-columns:1fr 1fr 1fr;
      grid-template-rows:46px 46px 46px;
      gap:8px;
      margin-top:8px;
      touch-action:none;
    }
    .manual-pad .blank {
      min-height:46px;
    }
    .manual-btn {
      border-radius:10px;
      font-size:22px;
      font-weight:900;
      padding:8px 0;
      user-select:none;
      touch-action:none;
      background:#2563eb;
    }
    .manual-btn.stop-symbol {
      background:#dc2626;
      font-size:21px;
      color:#ffffff;
    }
    .manual-btn:active {
      transform:scale(0.97);
      filter:brightness(1.12);
    }
    .manual-sliders {
      margin-top:12px;
      background:#020617;
      border:1px solid var(--border);
      border-radius:10px;
      padding:10px;
    }
    .manual-slider-row {
      display:grid;
      grid-template-columns:95px 1fr 58px;
      gap:8px;
      align-items:center;
      margin:6px 0;
      font-size:12px;
      color:#cbd5e1;
    }
    .manual-slider-row input[type="range"] {
      padding:0;
      height:22px;
      accent-color:#22c55e;
    }
    .manual-value {
      color:#facc15;
      font-weight:bold;
      text-align:right;
    }
    .manual-status {
      margin-top:8px;
      color:#9ca3af;
      font-size:12px;
      line-height:1.35;
      min-height:18px;
    }

    .right-panel {
      display:flex;
      flex-direction:column;
      min-width:0;
      overflow:hidden;
    }
    .viewer-display-grid {
      display:grid;
      grid-template-columns: 60fr 40fr;
      gap:10px;
      height:calc(100vh - 190px);
      min-height:420px;
    }
    .display-card {
      background:#020617;
      border:1px solid var(--border);
      border-radius:12px;
      overflow:hidden;
      min-width:0;
      position:relative;
      display:flex;
      flex-direction:column;
    }
    .display-title {
      position:absolute;
      top:8px;
      left:10px;
      z-index:3;
      background:rgba(2,6,23,0.72);
      color:#e5e7eb;
      border:1px solid rgba(148,163,184,0.28);
      border-radius:8px;
      padding:4px 8px;
      font-size:12px;
      font-weight:bold;
      pointer-events:none;
    }
    #mapCanvas {
      width:100%;
      height:100%;
      background:#020617;
      border:0;
      border-radius:0;
      flex:1;
    }
    .camera-panel {
      display:flex;
      flex-direction:column;
      height:100%;
      background:#020617;
    }
    .camera-toolbar {
      display:grid;
      grid-template-columns:1fr 92px 92px;
      gap:8px;
      padding:10px;
      border-bottom:1px solid var(--border);
      background:#111827;
      z-index:2;
    }
    .camera-toolbar input {
      height:38px;
      margin:0;
      font-size:12px;
    }
    .camera-toolbar button {
      height:38px;
      padding:6px;
      margin:0;
      font-size:12px;
    }
    .camera-view {
      position:relative;
      flex:1;
      display:flex;
      align-items:center;
      justify-content:center;
      min-height:0;
      overflow:hidden;
    }
    #cameraImage, #cameraCanvas {
      max-width:100%;
      max-height:100%;
      object-fit:contain;
      display:none;
    }
    #cameraStatus {
      position:absolute;
      left:10px;
      bottom:10px;
      right:10px;
      color:#facc15;
      background:rgba(2,6,23,0.72);
      border:1px solid rgba(148,163,184,0.28);
      border-radius:8px;
      padding:6px 8px;
      font-size:12px;
      line-height:1.35;
    }

    .camera-card .display-title {
      position:static;
      top:auto;
      left:auto;
      margin:10px 10px 0;
      align-self:flex-start;
      pointer-events:none;
    }
    .camera-toolbar select {
      height:38px;
      margin:0;
      font-size:12px;
      background:#020617;
      color:#e5e7eb;
      border:1px solid var(--border);
      border-radius:8px;
      padding:0 8px;
      min-width:0;
    }
    @media (max-width:1100px){
      .viewer-display-grid { grid-template-columns:1fr; height:auto; }
      .display-card { min-height:360px; }
    }
    .save-bar {
      margin-top:10px;
      display:grid;
      grid-template-columns:230px 1fr 160px;
      gap:10px;
      align-items:center;
    }
    #mapNameInput {
      background:#ffffff;
      color:#111827;
      border:2px solid #cbd5e1;
      font-weight:bold;
    }
    #saveFusionMapBtn {
      background:var(--orange);
      color:#111827;
    }
    #viewerModeText {
      color:var(--muted);
      font-size:13px;
    }
    .topic-list {
      margin-top:10px;
      background:#020617;
      border:1px solid var(--border);
      border-radius:10px;
      padding:8px;
      min-height:120px;
      max-height:250px;
      overflow:auto;
    }
    .topic-row {
      display:grid;
      grid-template-columns:26px 1fr 32px;
      gap:7px;
      align-items:center;
      padding:7px;
      border-bottom:1px solid #1f2937;
      font-size:12px;
    }
    .topic-row:last-child { border-bottom:none; }
    .topic-name {
      color:#e5e7eb;
      font-weight:bold;
      word-break:break-all;
    }
    .topic-type {
      color:#9ca3af;
      font-size:11px;
      margin-top:2px;
      word-break:break-all;
    }
    .remove-topic {
      background:#dc2626;
      padding:6px;
      border-radius:7px;
      width:28px;
      height:28px;
      line-height:16px;
    }
    .topic-visible {
      width:18px;
      height:18px;
    }
    pre {
      white-space:pre-wrap;
      word-break:break-word;
      overflow:auto;
      background:#020617;
      border:1px solid var(--border);
      border-radius:8px;
      padding:9px;
      font-size:12px;
      max-height:135px;
    }
    .hint {
      color:#9ca3af;
      font-size:12px;
      line-height:1.35;
    }
  </style>
</head>

<body>
<header>
  <h1>AMR Web Map Viewer</h1>
  <div id="connState">Disconnected</div>
</header>

<main>
  <section class="panel">
    <label>ROSBridge URL</label>
    <input id="rosbridgeUrl" value="">

    <div class="row">
      <button class="green" id="connectBtn" onclick="connectRos()">CONNECT</button>
      <button class="red" id="disconnectBtn" onclick="disconnectRos()">DISCONNECT</button>
    </div>

    <div class="section-title">Map Tool</div>
    <div class="tool-grid">
      <button id="toolPanBtn" class="tool-btn active" onclick="setMapTool('PAN')">ZOOM/PAN</button>
      <button id="toolNavGoalBtn" class="tool-btn" onclick="setMapTool('NAV_GOAL')">NAV GOAL</button>
      <button id="toolWaypointBtn" class="tool-btn" onclick="setMapTool('WAYPOINT')">WAYPOINT</button>
    </div>

    <div class="waypoint-actions">
      <button id="waypointSetBtn" class="purple tool-action-btn" onclick="setWaypointsOnMap()" disabled>SET</button>
      <button id="waypointAddBtn" class="tool-action-btn" onclick="addWaypointRow()" disabled>ADD</button>
    </div>

    <div id="mapToolStatus" class="tool-status">
      Tool: ZOOM/PAN. Lăn chuột để phóng to/thu nhỏ, kéo chuột để di chuyển bản đồ.
    </div>

    <label>Waypoint list</label>
    <div class="waypoint-list" id="waypointList">
      <div class="hint">Chưa có waypoint. Nhấn ADD hoặc chọn WAYPOINT rồi click/kéo trên map.</div>
    </div>


    <div class="manual-control">
      <div class="section-title">Manual Control</div>
      <button id="manualStartBtn" class="manual-start-btn" onclick="startManualControlSystem()">START CONTROL</button>

      <div class="manual-pad">
        <div class="blank"></div>
        <button class="manual-btn" title="Forward" disabled onpointerdown="startManualControl(event,'forward')" onpointerup="stopManualControl()" onpointerleave="stopManualControl()" onpointercancel="stopManualControl()">▲</button>
        <div class="blank"></div>

        <button class="manual-btn" title="Turn left" disabled onpointerdown="startManualControl(event,'left')" onpointerup="stopManualControl()" onpointerleave="stopManualControl()" onpointercancel="stopManualControl()">◀</button>
        <button class="manual-btn stop-symbol" title="Stop" disabled onclick="stopManualControl(true)">■</button>
        <button class="manual-btn" title="Turn right" disabled onpointerdown="startManualControl(event,'right')" onpointerup="stopManualControl()" onpointerleave="stopManualControl()" onpointercancel="stopManualControl()">▶</button>

        <div class="blank"></div>
        <button class="manual-btn" title="Backward" disabled onpointerdown="startManualControl(event,'backward')" onpointerup="stopManualControl()" onpointerleave="stopManualControl()" onpointercancel="stopManualControl()">▼</button>
        <div class="blank"></div>
      </div>

      <div class="manual-sliders">
        <div class="manual-slider-row">
          <span>Linear</span>
          <input id="manualLinearSlider" type="range" disabled min="0.03" max="0.40" step="0.01" value="0.12" oninput="updateManualSliderLabels()">
          <span id="manualLinearValue" class="manual-value">0.12</span>
        </div>
        <div class="manual-slider-row">
          <span>Angular</span>
          <input id="manualAngularSlider" type="range" disabled min="0.05" max="0.80" step="0.01" value="0.28" oninput="updateManualSliderLabels()">
          <span id="manualAngularValue" class="manual-value">0.28</span>
        </div>
      </div>

      <div id="manualStatus" class="manual-status">Teleop: nhấn START CONTROL trước. Nút web hoặc phím mặc định i/j/k/l/, . Space/k = dừng.</div>
    </div>


    <label>Available topics</label>
    <select id="topicSelect"></select>

    <div class="row">
      <button onclick="refreshTopicList()">REFRESH LIST</button>
      <button class="purple" onclick="loadSelectedTopic()">LOAD TOPIC</button>
    </div>

    <label>Loaded topics</label>
    <div class="topic-list" id="loadedTopicList">
      <div class="hint">Chưa có topic nào. Chọn topic ở trên rồi nhấn LOAD TOPIC.</div>
    </div>

    <button class="orange" onclick="clearCanvas()">CLEAR VIEW</button>

    <pre id="poseBox">Pose:
x: -
y: -
yaw: -</pre>

    <pre id="logBox">Ready.</pre>

    <p class="hint">
      Map Tool: ZOOM/PAN để phóng to/thu nhỏ và kéo bản đồ, NAV GOAL để gửi goal Nav2, WAYPOINT để tạo danh sách điểm dừng.
      Viewer hỗ trợ /map, /tf, /scan, costmap và path; 3D sẽ thêm ở bước sau.
    </p>
  </section>

  <section class="right-panel">
    <div class="viewer-display-grid">
      <div class="display-card map-card">
        <div class="display-title">MAP / COSTMAP / TF</div>
        <canvas id="mapCanvas" width="900" height="720"></canvas>
      </div>

      <div class="display-card camera-card">
        <div class="display-title">CAMERA STREAM</div>
        <div class="camera-panel">
          <div class="camera-toolbar">
            <select id="cameraTopicSelect"></select>
            <button id="startCameraBtn" class="green" onclick="startCameraStream()">CAMERA</button>
            <button id="stopCameraBtn" class="red" onclick="stopCameraStream()">STOP</button>
          </div>
          <div class="camera-view">
            <img id="cameraImage" alt="camera stream">
            <canvas id="cameraCanvas" width="640" height="480"></canvas>
            <div id="cameraStatus">Camera: chưa CONNECT hoặc chưa chọn topic ảnh.</div>
          </div>
        </div>
      </div>
    </div>

    <div class="save-bar">
      <div id="viewerModeText">Mode: checking...</div>
      <input id="mapNameInput" placeholder="Nhập tên map, ví dụ: kho_A_01">
      <button id="saveFusionMapBtn" onclick="saveFusionMap()" disabled>SAVE MAP</button>
    </div>

    <pre id="saveMapResult">SAVE MAP chỉ hoạt động khi hệ thống đang ở chế độ SLAM.</pre>
  </section>
</main>

<script>
let ros=null;
let availableTopics=[];
let layers={};
let layerSeq=0;
let autoPresetLoaded=false;

// 2D view transform
let viewZoom=1.0;
let viewPanX=0.0;
let viewPanY=0.0;
let viewRotation=0.0;
let isPanning=false;
let isRotating=false;
let lastMouseX=0.0;
let lastMouseY=0.0;

// Map tool state
let activeMapTool="PAN";
let toolDragging=false;
let toolStartWorld=null;
let toolCurrentWorld=null;
let waypointSeq=0;
let activeWaypointId=null;
let waypointRows=[];

// Manual control state
let manualControlStarted=false;
let manualCmdTimer=null;
let manualCmdActive=false;
let manualCmdLinear=0.0;
let manualCmdAngular=0.0;
let manualCmdTopicName="";
let manualCmdPub=null;
let manualZeroBurstTimer=null;
let manualKeyPub=null;
let manualSpeedPub=null;

// Camera stream state
let cameraSub=null;
let cameraActive=false;
let cameraFrameCount=0;
let cameraLastTopic="";
let cameraLastType="";
let cameraLastRenderMs=0;
let cameraRawMinIntervalMs=160;
let cameraCompressedMinIntervalMs=80;

// Keyboard teleop state
let manualKeySet=new Set();
let manualKeyboardReady=false;


// TF buffer: child_frame_id -> latest transform parent_T_child
let tfBuffer={};
let tfStaticBuffer={};

const canvas=document.getElementById("mapCanvas");
const ctx=canvas.getContext("2d");
const logBox=document.getElementById("logBox");
const poseBox=document.getElementById("poseBox");
const connState=document.getElementById("connState");
const loadedTopicList=document.getElementById("loadedTopicList");
const cameraTopicSelect=document.getElementById("cameraTopicSelect");
const cameraTopicInput=document.getElementById("cameraTopicInput") || cameraTopicSelect;
const cameraImage=document.getElementById("cameraImage");
const cameraCanvas=document.getElementById("cameraCanvas");
const cameraCtx=cameraCanvas ? cameraCanvas.getContext("2d") : null;
const cameraStatus=document.getElementById("cameraStatus");

function log(msg){
  const t=new Date().toLocaleTimeString();
  logBox.textContent=`[${t}] ${msg}
`+logBox.textContent;
}


let viewerRosConnected = false;

function setViewerControlsEnabled(enabled){
  viewerRosConnected = !!enabled;

  const allowIds = new Set([
    "rosbridgeUrl",
    "connectBtn",
    "disconnectBtn"
  ]);

  const controls = document.querySelectorAll(
    "main button, main input, main select, main textarea"
  );

  controls.forEach(el => {
    if(allowIds.has(el.id)){
      el.disabled = false;
      el.style.opacity = 1.0;
      return;
    }

    el.disabled = !viewerRosConnected;
    el.style.opacity = viewerRosConnected ? 1.0 : 0.45;
  });

  const manualStatus = document.getElementById("manualStatus");
  if(manualStatus && !viewerRosConnected){
    manualStatus.textContent = "Teleop: hãy CONNECT ROSBridge trước.";
  }

  const modeText = document.getElementById("viewerModeText");
  if(modeText && !viewerRosConnected){
    modeText.textContent = "Viewer: chưa CONNECT ROSBridge. Các chức năng đang bị khóa.";
    modeText.style.color = "#f97316";
  }

  // Quan trọng:
  // setViewerControlsEnabled(true) sẽ mở các control chung,
  // nhưng Manual Control phải tuân theo START CONTROL riêng.
  if(typeof setManualUiEnabled === "function"){
    setManualUiEnabled(manualControlStarted);
  }

  if(typeof updateWaypointActionButtons === "function"){
    updateWaypointActionButtons();
  }
}

function defaultWsUrl(){
  return `ws://${window.location.hostname}:9090`;
}

function setDefaultRosbridgeUrl(){
  const input=document.getElementById("rosbridgeUrl");
  if(input && !input.value.trim()){
    input.value=defaultWsUrl();
  }
}
setDefaultRosbridgeUrl();

function rosTypeToRoslibType(type){
  if(!type) return "";
  return type.replace("/msg/","/");
}

function isSupportedType(type){
  return [
    "nav_msgs/msg/OccupancyGrid",
    "geometry_msgs/msg/PoseWithCovarianceStamped",
    "sensor_msgs/msg/LaserScan",
    "nav_msgs/msg/Path",
    "tf2_msgs/msg/TFMessage"
  ].includes(type);
}

function connectRos(){
  const input = document.getElementById("rosbridgeUrl");
  let url = input ? input.value.trim() : "";

  if(!url){
    url = defaultWsUrl();
    if(input){
      input.value = url;
    }
  }

  if(typeof ROSLIB === "undefined"){
    log("ROSLIB chưa tải được. Kiểm tra kết nối mạng hoặc roslib.min.js.");
    connState.textContent = "ROSLIB load error";
    connState.style.color = "#ef4444";
    return;
  }

  ros = new ROSLIB.Ros({url});

  ros.on("connection", async ()=>{
    connState.textContent = "Connected: " + url;
    connState.style.color = "#22c55e";
    log("Connected to " + url);
    setViewerControlsEnabled(true);

    // Sau CONNECT chỉ mở nút START CONTROL.
    // Nút lái + slider vẫn khóa cho đến khi START CONTROL được bấm.
    if(!manualControlStarted){
      setManualUiEnabled(false);
    }

    await refreshTopicList();
    await refreshViewerSaveState();
    await autoLoadModePreset();
    await loadRuntimeWaypointsToViewer();
  });

  ros.on("error", (err)=>{
    connState.textContent = "Error";
    connState.style.color = "#ef4444";
    log("Connection error: " + JSON.stringify(err));
  });

  ros.on("close", ()=>{
    connState.textContent = "Disconnected";
    connState.style.color = "#e5e7eb";
    if(typeof stopManualControlSystem === "function" && manualControlStarted){
      stopManualControlSystem();
    }

    setViewerControlsEnabled(false);
    log("Connection closed");
  });
}

function disconnectRos(){
  stopManualControl();

  if(typeof stopManualControlSystem === "function" && manualControlStarted){
    stopManualControlSystem();
  }

  autoPresetLoaded=false;
  Object.keys(layers).forEach(id=>removeLayer(id));

  setViewerControlsEnabled(false);

  if(ros){ ros.close(); }
}

async function refreshTopicList(){
  const res=await fetch("/api/ros_topics_typed");
  const data=await res.json();

  availableTopics=data.topics || [];
  availableTopics.sort((a,b)=>a.name.localeCompare(b.name));

  const sel=document.getElementById("topicSelect");
  sel.innerHTML="";

  availableTopics.forEach(t=>{
    const opt=document.createElement("option");
    opt.value=t.name;
    opt.textContent=t.type ? `${t.name}  [${t.type}]` : t.name;
    sel.appendChild(opt);
  });

  log("Loaded "+availableTopics.length+" topics");
  refreshCameraTopicSelect();
  autoFillCameraTopic();
}

function getSelectedTopicInfo(){
  const name=document.getElementById("topicSelect").value;
  return availableTopics.find(t=>t.name===name) || {name, type:""};
}






function isCameraTopicType(type){
  return ["sensor_msgs/msg/CompressedImage", "sensor_msgs/msg/Image"].includes(type);
}

function isLikelyCameraTopicName(name){
  if(!name) return false;
  const n=name.toLowerCase();
  return n.includes("image") || n.includes("rgb") || n.includes("color") || n.includes("camera") || n.includes("tracker") || n.includes("alert");
}

function findCameraTopicInfo(topicName){
  if(!topicName) return null;
  return availableTopics.find(t=>t.name===topicName) || null;
}

function cameraTopicPriority(t){
  const n=(t.name || "").toLowerCase();
  const compressed=t.type==="sensor_msgs/msg/CompressedImage" ? 0 : 100;
  let p=compressed;

  if(n.includes("person_tracker")) p += 0;
  else if(n.includes("alert")) p += 2;
  else if(n.includes("color") || n.includes("rgb")) p += 5;
  else if(n.includes("depth")) p += 50;
  else p += 20;

  return p;
}

function getCameraTopicOptions(){
  return availableTopics
    .filter(t=>isCameraTopicType(t.type) && isLikelyCameraTopicName(t.name))
    .sort((a,b)=>cameraTopicPriority(a)-cameraTopicPriority(b) || a.name.localeCompare(b.name));
}

function refreshCameraTopicSelect(){
  if(!cameraTopicSelect) return;

  const oldValue=cameraTopicSelect.value;
  const opts=getCameraTopicOptions();
  cameraTopicSelect.innerHTML="";

  if(opts.length===0){
    const opt=document.createElement("option");
    opt.value="";
    opt.textContent="Không có Image topic";
    cameraTopicSelect.appendChild(opt);
    return;
  }

  opts.forEach(t=>{
    const opt=document.createElement("option");
    opt.value=t.name;
    opt.textContent=`${t.name} [${t.type.split('/').pop()}]`;
    cameraTopicSelect.appendChild(opt);
  });

  if(oldValue && opts.find(t=>t.name===oldValue)){
    cameraTopicSelect.value=oldValue;
  }
}

function autoFillCameraTopic(){
  refreshCameraTopicSelect();

  if(!cameraTopicInput) return;
  if(cameraTopicInput.value && cameraTopicInput.value.trim()) return;

  const preferred=[
    "/amr_ai/debug/person_tracker/image/compressed",
    "/amr_ai/debug/alert/image/compressed",
    "/camera/color/image_raw_web/compressed",
    "/camera/color/image_raw/compressed",
    "/camera/rgb/image_raw/compressed",
    "/camera/image_raw/compressed",
    "/amr_ai/debug/person_tracker/image",
    "/amr_ai/debug/alert/image",
    "/camera/color/image_raw",
    "/camera/rgb/image_raw",
    "/camera/image_raw"
  ];

  for(const name of preferred){
    const info=findCameraTopicInfo(name);
    if(info && isCameraTopicType(info.type)){
      cameraTopicInput.value=name;
      setCameraStatus("Camera topic tự chọn: "+name);
      return;
    }
  }

  const opts=getCameraTopicOptions();
  if(opts.length>0){
    cameraTopicInput.value=opts[0].name;
    const rawNote=opts[0].type==="sensor_msgs/msg/Image" ? ". Topic raw có thể lag, nên dùng topic compressed." : "";
    setCameraStatus("Camera topic tự chọn: "+opts[0].name+rawNote);
  }
}

function setCameraStatus(text){
  if(cameraStatus){ cameraStatus.textContent=text; }
}

function bytesToBase64(data){
  if(!data) return "";
  if(typeof data === "string") return data;

  let binary="";
  const chunkSize=0x8000;
  for(let i=0;i<data.length;i+=chunkSize){
    binary += String.fromCharCode.apply(null, data.slice(i,i+chunkSize));
  }
  return btoa(binary);
}

function bytesToUint8(data){
  if(!data) return new Uint8Array(0);
  if(typeof data === "string"){
    const bin=atob(data);
    const out=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++) out[i]=bin.charCodeAt(i);
    return out;
  }
  return new Uint8Array(data);
}

function shouldRenderCameraFrame(isCompressed){
  const now=performance.now();
  const minInterval=isCompressed ? cameraCompressedMinIntervalMs : cameraRawMinIntervalMs;
  if(now-cameraLastRenderMs < minInterval){
    return false;
  }
  cameraLastRenderMs=now;
  return true;
}

function renderCompressedCamera(msg){
  const format=(msg.format || "jpeg").toLowerCase();
  const mime=format.includes("png") ? "image/png" : "image/jpeg";
  const b64=bytesToBase64(msg.data);

  if(cameraCanvas){ cameraCanvas.style.display="none"; }
  if(cameraImage){
    cameraImage.style.display="block";
    cameraImage.src=`data:${mime};base64,${b64}`;
  }
}

function renderRawCamera(msg){
  if(!cameraCanvas || !cameraCtx) return;

  const w=msg.width;
  const h=msg.height;
  const enc=(msg.encoding || "rgb8").toLowerCase();
  const src=bytesToUint8(msg.data);

  cameraCanvas.width=w;
  cameraCanvas.height=h;

  const img=cameraCtx.createImageData(w,h);
  const step=msg.step || (w*3);

  for(let y=0;y<h;y++){
    for(let x=0;x<w;x++){
      const dst=(y*w+x)*4;
      let r=0,g=0,b=0,a=255;

      if(enc==="rgb8"){
        const i=y*step+x*3;
        r=src[i]; g=src[i+1]; b=src[i+2];
      }else if(enc==="bgr8"){
        const i=y*step+x*3;
        b=src[i]; g=src[i+1]; r=src[i+2];
      }else if(enc==="rgba8"){
        const i=y*step+x*4;
        r=src[i]; g=src[i+1]; b=src[i+2]; a=src[i+3];
      }else if(enc==="bgra8"){
        const i=y*step+x*4;
        b=src[i]; g=src[i+1]; r=src[i+2]; a=src[i+3];
      }else if(enc==="mono8"){
        const v=src[y*step+x];
        r=v; g=v; b=v;
      }else{
        if(cameraFrameCount%30===0){
          setCameraStatus("Camera raw encoding chưa hỗ trợ: "+enc+". Nên dùng topic compressed.");
        }
        return;
      }

      img.data[dst]=r;
      img.data[dst+1]=g;
      img.data[dst+2]=b;
      img.data[dst+3]=a;
    }
  }

  if(cameraImage){ cameraImage.style.display="none"; }
  cameraCanvas.style.display="block";
  cameraCtx.putImageData(img,0,0);
}

function startCameraStream(){
  if(!ros){
    setCameraStatus("Camera: hãy CONNECT ROSBridge trước.");
    return;
  }

  refreshCameraTopicSelect();

  const topicName=(cameraTopicInput ? cameraTopicInput.value.trim() : "");
  if(!topicName){
    setCameraStatus("Camera: chưa có topic ảnh. Bấm REFRESH LIST hoặc kiểm tra node camera.");
    return;
  }

  const info=findCameraTopicInfo(topicName) || {
    name:topicName,
    type: topicName.includes("compressed") ? "sensor_msgs/msg/CompressedImage" : "sensor_msgs/msg/Image"
  };

  if(!isCameraTopicType(info.type)){
    setCameraStatus(`Camera: topic ${topicName} không phải Image/CompressedImage. Type=${info.type || "unknown"}`);
    return;
  }

  stopCameraStream(false);

  cameraLastTopic=topicName;
  cameraLastType=info.type;
  cameraFrameCount=0;
  cameraLastRenderMs=0;
  cameraActive=true;

  cameraSub=new ROSLIB.Topic({
    ros:ros,
    name:topicName,
    messageType:rosTypeToRoslibType(info.type),
    throttle_rate: info.type==="sensor_msgs/msg/CompressedImage" ? 80 : 160,
    queue_length: 1,
    queue_size: 1
  });

  cameraSub.subscribe((msg)=>{
    cameraFrameCount += 1;
    const isCompressed=cameraLastType==="sensor_msgs/msg/CompressedImage";
    if(!shouldRenderCameraFrame(isCompressed)) return;

    try{
      if(isCompressed) renderCompressedCamera(msg);
      else renderRawCamera(msg);

      if(cameraFrameCount===1 || cameraFrameCount%30===0){
        const typeLabel=isCompressed ? "compressed" : "raw";
        setCameraStatus(`Camera: ${cameraLastTopic} | ${typeLabel} | frame ${cameraFrameCount}`);
      }
    }catch(e){
      setCameraStatus("Camera render error: "+e);
    }
  });

  const rawNote=info.type==="sensor_msgs/msg/Image" ? " | RAW: dễ lag, nên dùng compressed" : "";
  setCameraStatus("Camera: đang subscribe "+topicName+rawNote);
  log("Camera subscribed: "+topicName+" ["+info.type+"]");
}

function stopCameraStream(updateStatus=true){
  if(cameraSub){
    try{ cameraSub.unsubscribe(); }catch(e){}
  }
  cameraSub=null;
  cameraActive=false;

  if(updateStatus){
    setCameraStatus("Camera: stopped.");
  }
}

function updateManualSliderLabels(){
  const lin=document.getElementById("manualLinearSlider");
  const ang=document.getElementById("manualAngularSlider");
  const linVal=document.getElementById("manualLinearValue");
  const angVal=document.getElementById("manualAngularValue");

  if(lin && linVal){ linVal.textContent=Number(lin.value).toFixed(2); }
  if(ang && angVal){ angVal.textContent=Number(ang.value).toFixed(2); }

  if(manualControlStarted){
    publishTeleopSpeed();
  }
}

function getManualSpeeds(){
  const lin=document.getElementById("manualLinearSlider");
  const ang=document.getElementById("manualAngularSlider");

  return {
    linear: lin ? Number(lin.value) : 0.12,
    angular: ang ? Number(ang.value) : 0.28
  };
}

function setManualUiEnabled(enabled){
  const btn=document.getElementById("manualStartBtn");
  const status=document.getElementById("manualStatus");

  // START CONTROL chỉ được bấm sau khi CONNECT.
  // Các nút lái + slider chỉ được bấm khi đã START CONTROL.
  const startButtonEnabled = viewerRosConnected;
  const driveEnabled = viewerRosConnected && manualControlStarted;

  document.querySelectorAll(".manual-btn").forEach(b=>{
    b.disabled = !driveEnabled;
    b.style.opacity = driveEnabled ? 1.0 : 0.45;
  });

  const lin=document.getElementById("manualLinearSlider");
  const ang=document.getElementById("manualAngularSlider");

  if(lin){
    lin.disabled = !driveEnabled;
    lin.style.opacity = driveEnabled ? 1.0 : 0.45;
  }

  if(ang){
    ang.disabled = !driveEnabled;
    ang.style.opacity = driveEnabled ? 1.0 : 0.45;
  }

  if(btn){
    btn.disabled = !startButtonEnabled;
    btn.style.opacity = startButtonEnabled ? 1.0 : 0.45;

    if(manualControlStarted){
      btn.textContent = "STOP CONTROL";
      btn.classList.add("active");
      btn.classList.add("ready");
    }else{
      btn.textContent = "START CONTROL";
      btn.classList.remove("active");
      btn.classList.remove("ready");
    }
  }

  if(status){
    if(!viewerRosConnected){
      status.textContent = "Teleop: hãy CONNECT ROSBridge trước.";
    }else if(!manualControlStarted){
      status.textContent = "Teleop: nhấn START CONTROL để bật điều khiển.";
    }else{
      status.textContent = "Teleop: đã bật. Giữ nút web hoặc dùng phím i/j/k/l, W/A/S/D, mũi tên.";
    }
  }
}

function getManualPublisher(topicName){
  if(!ros){ return null; }

  if(manualCmdPub && manualCmdTopicName===topicName){
    return manualCmdPub;
  }

  manualCmdTopicName=topicName;
  manualCmdPub=new ROSLIB.Topic({
    ros,
    name:topicName,
    messageType:"geometry_msgs/Twist"
  });

  return manualCmdPub;
}

function makeTwist(linearX, angularZ){
  return new ROSLIB.Message({
    linear:{x:linearX, y:0.0, z:0.0},
    angular:{x:0.0, y:0.0, z:angularZ}
  });
}

function publishManualTwist(linearX, angularZ, topicName=null){
  if(!ros){ return; }

  const topic=topicName || manualCmdTopicName || "/cmd_vel";
  const pub=getManualPublisher(topic);
  if(!pub){ return; }

  pub.publish(makeTwist(linearX, angularZ));
}

function publishZeroToTopic(topicName){
  if(!ros){ return; }
  const pub=new ROSLIB.Topic({
    ros,
    name:topicName,
    messageType:"geometry_msgs/Twist"
  });
  pub.publish(makeTwist(0.0, 0.0));
}

function publishManualZeroAll(){
  if(!ros){ return; }
  publishZeroToTopic("/cmd_vel");
  publishZeroToTopic("/cmd_vel_safe");
}

function burstStopZero(count=8){
  if(manualZeroBurstTimer){
    clearInterval(manualZeroBurstTimer);
    manualZeroBurstTimer=null;
  }

  let sent=0;
  publishManualZeroAll();

  manualZeroBurstTimer=setInterval(()=>{
    publishManualZeroAll();
    sent++;

    if(sent>=count){
      clearInterval(manualZeroBurstTimer);
      manualZeroBurstTimer=null;
    }
  }, 40);
}



function getManualKeyPublisher(){
  if(!ros){ return null; }

  if(!manualKeyPub){
    manualKeyPub = new ROSLIB.Topic({
      ros: ros,
      name: "/amr_web_teleop/key",
      messageType: "std_msgs/msg/String"
    });

    if(typeof manualKeyPub.advertise === "function"){
      manualKeyPub.advertise();
    }

    log("Manual key publisher ready: /amr_web_teleop/key");
  }

  return manualKeyPub;
}

function getManualSpeedPublisher(){
  if(!ros){ return null; }

  if(!manualSpeedPub){
    manualSpeedPub = new ROSLIB.Topic({
      ros: ros,
      name: "/amr_web_teleop/speed",
      messageType: "geometry_msgs/msg/Twist"
    });

    if(typeof manualSpeedPub.advertise === "function"){
      manualSpeedPub.advertise();
    }

    log("Manual speed publisher ready: /amr_web_teleop/speed");
  }

  return manualSpeedPub;
}

function publishTeleopSpeed(){
  const pub=getManualSpeedPublisher();
  if(!pub){ return; }

  const sp=getManualSpeeds();
  pub.publish(new ROSLIB.Message({
    linear:{x:sp.linear, y:0.0, z:0.0},
    angular:{x:0.0, y:0.0, z:sp.angular}
  }));
}

async function startManualControlSystem(){
  const status=document.getElementById("manualStatus");

  if(manualControlStarted){
    await stopManualControlSystem();
    return;
  }

  try{
    if(status){ status.textContent="Teleop: đang chạy scripts/run_web_teleop.sh trong tmux..."; }

    const res=await fetch("/api/start_manual_control", {method:"POST"});
    const data=await res.json();

    if(!data.ok){
      if(status){ status.textContent="Teleop: START CONTROL lỗi. "+(data.message || ""); }
      log("START CONTROL failed: "+JSON.stringify(data));
      setManualUiEnabled(false);
      return;
    }

    manualCmdTopicName=data.topic || "/cmd_vel_safe";
    manualControlStarted=true;
    manualKeyPub=null;
    manualSpeedPub=null;
    manualCmdActive=false;
    manualCmdLinear=0.0;
    manualCmdAngular=0.0;
    manualKeySet.clear();

    setManualUiEnabled(true);

    publishTeleopSpeed();
    await sendTeleopKey("k");
    setTimeout(()=>sendTeleopKey("k"), 80);
    setTimeout(()=>sendTeleopKey("k"), 160);

    if(status){
      status.textContent=`Teleop ON | web_teleop_node | topic=${manualCmdTopicName} | nút web: ▲▼◀▶, phím mặc định: i/j/k/l/,`;
    }

    log("Manual control ON. Web gửi phím qua ROSBridge đến web_teleop_node.");

  }catch(e){
    if(status){ status.textContent="Teleop: START CONTROL lỗi kết nối webserver."; }
    log("START CONTROL error: "+e);
    setManualUiEnabled(false);
  }
}

async function stopManualControlSystem(){
  const status=document.getElementById("manualStatus");

  await stopManualControl(true);

  try{
    await fetch("/api/stop_manual_control", {method:"POST"});
  }catch(e){
    log("STOP CONTROL API error: "+e);
  }

  manualControlStarted=false;
  manualCmdActive=false;
  manualCmdLinear=0.0;
  manualCmdAngular=0.0;
  manualKeySet.clear();
  manualKeyPub=null;
  manualSpeedPub=null;

  setManualUiEnabled(false);

  if(status){
    status.textContent="Teleop OFF. Nút điều khiển và bàn phím đã khóa.";
  }

  log("Manual control OFF");
}

function ensureManualControlReady(){
  const status=document.getElementById("manualStatus");

  if(!manualControlStarted){
    if(status){ status.textContent="Teleop: hãy nhấn START CONTROL trước."; }
    return false;
  }

  return true;
}

function teleopKeyForDirection(direction){
  if(direction==="forward") return "i";
  if(direction==="backward") return ",";
  if(direction==="left") return "j";
  if(direction==="right") return "l";
  if(direction==="stop") return "k";
  return "k";
}

async function sendTeleopKey(key){
  if(!manualControlStarted && key !== "k"){
    return;
  }

  const pub = getManualKeyPublisher();

  if(!pub){
    log("Manual key publish ignored: ROSBridge chưa CONNECT");
    return;
  }

  const msg = new ROSLIB.Message({
    data: String(key)
  });

  pub.publish(msg);
  log("Teleop key sent: " + key);
}

function ensureManualLoop(){
  // Không publish Twist trực tiếp. Web điều khiển bằng cách gửi phím vào tmux teleop_twist_keyboard.
}

function startTeleopKeyHold(key, sourceLabel="web"){
  if(!ensureManualControlReady()) return;

  if(manualCmdTimer){
    clearInterval(manualCmdTimer);
    manualCmdTimer=null;
  }

  manualCmdActive=true;
  sendTeleopKey(key);

  manualCmdTimer=setInterval(()=>{
    if(manualCmdActive && manualControlStarted){
      sendTeleopKey(key);
    }
  }, 60);

  const status=document.getElementById("manualStatus");
  if(status){
    status.textContent=`Teleop ${sourceLabel}: key='${key}' đang giữ | script=run_teleop.sh`;
  }
}

function setManualCommand(direction, sourceLabel="web"){
  const key=teleopKeyForDirection(direction);
  startTeleopKeyHold(key, sourceLabel);
}

function startManualControl(event, direction){
  if(event){
    event.preventDefault();
    event.stopPropagation();
  }

  setManualCommand(direction, "web");
}

async function stopManualControl(forceLog=false){
  manualCmdActive=false;
  manualCmdLinear=0.0;
  manualCmdAngular=0.0;
  manualKeySet.clear();

  if(manualCmdTimer){
    clearInterval(manualCmdTimer);
    manualCmdTimer=null;
  }

  if(manualControlStarted){
    await sendTeleopKey("k");
    setTimeout(()=>sendTeleopKey("k"), 60);
    setTimeout(()=>sendTeleopKey("k"), 120);
  }

  const status=document.getElementById("manualStatus");
  if(status){
    status.textContent=manualControlStarted ? "Teleop: dừng." : "Teleop: dừng.";
  }

  if(forceLog){
    log("Manual STOP: sent key 'k' to teleop_twist_keyboard");
  }
}

function isKeyboardTypingTarget(el){
  if(!el) return false;
  const tag=(el.tagName || "").toLowerCase();
  if(tag==="input" || tag==="textarea" || tag==="select") return true;
  return !!el.isContentEditable;
}

function normalizeManualKey(e){
  const k=e.key;

  if(k==="ArrowUp" || k==="w" || k==="W" || k==="i" || k==="I") return "i";
  if(k==="ArrowDown" || k==="s" || k==="S" || k===",") return ",";
  if(k==="ArrowLeft" || k==="a" || k==="A" || k==="j" || k==="J") return "j";
  if(k==="ArrowRight" || k==="d" || k==="D" || k==="l" || k==="L") return "l";
  if(k===" " || k==="Spacebar" || k==="Space" || k==="k" || k==="K") return "k";

  return null;
}

function updateManualControlFromKeyboard(){
  if(manualKeySet.size===0){
    stopManualControl();
    return;
  }

  if(!ensureManualControlReady()) return;

  const keys=[...manualKeySet];
  const key=keys[keys.length-1];
  startTeleopKeyHold(key, "bàn phím");
}

function setupKeyboardManualControl(){
  if(manualKeyboardReady) return;
  manualKeyboardReady=true;

  window.addEventListener("keydown", (e)=>{
    const key=normalizeManualKey(e);
    if(!key) return;

    if(isKeyboardTypingTarget(document.activeElement)){
      return;
    }

    e.preventDefault();

    if(!manualControlStarted){
      const status=document.getElementById("manualStatus");
      if(status){ status.textContent="Teleop: hãy nhấn START CONTROL trước."; }
      return;
    }

    if(key==="k"){
      stopManualControl(true);
      return;
    }

    if(manualKeySet.has(key) && e.repeat){
      return;
    }

    manualKeySet.add(key);
    updateManualControlFromKeyboard();
  });

  window.addEventListener("keyup", (e)=>{
    const key=normalizeManualKey(e);
    if(!key || key==="k") return;

    if(isKeyboardTypingTarget(document.activeElement)){
      return;
    }

    e.preventDefault();
    manualKeySet.delete(key);
    updateManualControlFromKeyboard();
  });

  window.addEventListener("blur", ()=>{
    if(manualKeySet.size>0 || manualCmdActive){
      stopManualControl();
    }
  });

  document.addEventListener("visibilitychange", ()=>{
    if(document.hidden){
      stopManualControl();
    }
  });

  log("Keyboard teleop ready: phím mặc định i/j/k/l/, .; cũng hỗ trợ W/A/S/D và mũi tên. Space/k để dừng.");
}

updateManualSliderLabels();
setManualUiEnabled(false);


function updateWaypointActionButtons(){
  const setBtn=document.getElementById("waypointSetBtn");
  const addBtn=document.getElementById("waypointAddBtn");

  const enabled = viewerRosConnected && activeMapTool === "WAYPOINT";

  if(setBtn){
    setBtn.disabled = !enabled;
    setBtn.style.opacity = enabled ? 1.0 : 0.45;
  }

  if(addBtn){
    addBtn.disabled = !enabled;
    addBtn.style.opacity = enabled ? 1.0 : 0.45;
  }
}

function setMapTool(tool){
  activeMapTool=tool;
  toolDragging=false;
  toolStartWorld=null;
  toolCurrentWorld=null;

  const buttons={
    "PAN":"toolPanBtn",
    "NAV_GOAL":"toolNavGoalBtn",
    "WAYPOINT":"toolWaypointBtn"
  };

  Object.entries(buttons).forEach(([name,id])=>{
    const btn=document.getElementById(id);
    if(btn){
      btn.classList.toggle("active", name===tool);
    }
  });

  const status=document.getElementById("mapToolStatus");
  if(status){
    if(tool==="PAN"){
      status.textContent="Tool: ZOOM/PAN. Lăn chuột để phóng to/thu nhỏ, kéo chuột để di chuyển bản đồ.";
    }else if(tool==="NAV_GOAL"){
      status.textContent="Tool: NAV GOAL. Click/kéo trên map để chọn vị trí và hướng goal.";
    }else if(tool==="WAYPOINT"){
      status.textContent="Tool: WAYPOINT. Nhấn ADD rồi click/kéo trên map để lấy tọa độ waypoint, hoặc nhấn Get để lấy pose hiện tại.";
    }
  }

  updateWaypointActionButtons();

  log("Map tool: "+tool);
}

function poseToText(pose){
  if(!pose) return "";
  return `${pose.x.toFixed(3)}, ${pose.y.toFixed(3)}, ${pose.yaw.toFixed(3)}`;
}

function parseWaypointText(text){
  if(!text) return null;
  const nums=(text.match(/-?\d+(\.\d+)?/g) || []).map(Number);
  if(nums.length < 3) return null;
  return {x:nums[0], y:nums[1], yaw:nums[2]};
}

function getCurrentRobotPose2D(){
  const poseLayer=getFirstVisibleLayer("geometry_msgs/msg/PoseWithCovarianceStamped");
  if(poseLayer && poseLayer.msg){
    const p=poseLayer.msg.pose.pose.position;
    const yaw=getYaw(poseLayer.msg.pose.pose.orientation);
    return {x:p.x, y:p.y, yaw:yaw};
  }

  const tfPose=resolveFramePose("base_footprint","map") || resolveFramePose("base_link","map");
  if(tfPose){
    return {x:tfPose.x, y:tfPose.y, yaw:tfPose.yaw};
  }

  return null;
}

function nextEditableWaypointIndex(){
  let maxIdx=0;

  waypointRows.forEach(row=>{
    const m=String(row.name || "").match(/^WP([0-9]+)$/);
    if(m){
      maxIdx=Math.max(maxIdx, Number(m[1]));
    }
  });

  return Math.max(1, maxIdx+1);
}

function aliasForWpIndex(index){
  return "WP"+index;
}

function rowLabel(row){
  if(row.locked){
    return "HOME";
  }
  return row.name || "WP";
}

function addWaypointRow(initialPose=null){
  const idx=nextEditableWaypointIndex();

  const row={
    id:"wp_"+idx+"_"+Date.now(),
    name:"WP"+idx,
    text:initialPose ? poseToText(initialPose) : "",
    confirmed:false,
    locked:false
  };

  waypointRows.push(row);
  activeWaypointId=row.id;
  renderWaypointList();
  log("Added "+row.name);
  return row;
}

function updateWaypointText(id, value){
  const row=waypointRows.find(w=>w.id===id);
  if(!row || row.locked) return;

  row.text=value;
  row.confirmed=false;
  activeWaypointId=id;
  drawAll();
}

function getWaypointPose(id){
  const row=waypointRows.find(w=>w.id===id);
  if(!row || row.locked) return;

  const pose=getCurrentRobotPose2D();
  if(!pose){
    log("Không lấy được pose hiện tại. Hãy load /amcl_pose hoặc /tf trước.");
    return;
  }

  row.text=poseToText(pose);
  row.confirmed=false;
  activeWaypointId=id;
  renderWaypointList();
  drawAll();
  log(row.name+" <= current robot pose");
}

function removeWaypointRow(id){
  const row=waypointRows.find(w=>w.id===id);

  if(row && row.locked){
    log("WP0/HOME is fixed and cannot be removed.");
    return;
  }

  waypointRows=waypointRows.filter(w=>w.id!==id);

  if(activeWaypointId===id){
    const editable=waypointRows.filter(w=>!w.locked);
    activeWaypointId=editable.length ? editable[editable.length-1].id : null;
  }

  renderWaypointList();
  drawAll();

  if(row) log("Removed "+row.name);
}

function renderWaypointList(){
  const list=document.getElementById("waypointList");
  if(!list) return;

  if(waypointRows.length===0){
    list.innerHTML='<div class="hint">Chưa có waypoint. WP0/HOME sẽ tự nạp từ file runtime khi CONNECT ở NAVIGATION.</div>';
    return;
  }

  list.innerHTML="";

  waypointRows.forEach(row=>{
    const div=document.createElement("div");
    div.className="waypoint-row";
    if(row.locked){
      div.classList.add("locked");
    }

    const name=document.createElement("div");
    name.className="waypoint-name";
    name.textContent=rowLabel(row);

    const input=document.createElement("input");
    input.className="waypoint-input";
    input.value=row.text;
    input.placeholder="x, y, yaw";
    input.disabled=!!row.locked;
    input.style.opacity=row.locked ? 0.65 : 1.0;
    input.onfocus=()=>{
      if(!row.locked){
        activeWaypointId=row.id;
      }
    };
    input.oninput=()=>updateWaypointText(row.id, input.value);

    const getBtn=document.createElement("button");
    getBtn.className="waypoint-get";
    getBtn.textContent="Get";
    getBtn.disabled=!!row.locked;
    getBtn.style.opacity=row.locked ? 0.45 : 1.0;
    getBtn.onclick=()=>getWaypointPose(row.id);

    const rmBtn=document.createElement("button");
    rmBtn.className="waypoint-remove";
    rmBtn.textContent="×";
    rmBtn.disabled=!!row.locked;
    rmBtn.style.opacity=row.locked ? 0.45 : 1.0;
    rmBtn.onclick=()=>removeWaypointRow(row.id);

    div.appendChild(name);
    div.appendChild(input);
    div.appendChild(getBtn);
    div.appendChild(rmBtn);
    list.appendChild(div);
  });
}

function getActiveWaypointRow(){
  let row=waypointRows.find(w=>w.id===activeWaypointId && !w.locked);

  if(!row){
    const editable=waypointRows.filter(w=>!w.locked);
    row=editable.length ? editable[editable.length-1] : addWaypointRow();
  }

  return row;
}

function setWaypointFromMapPose(pose){
  let row=getActiveWaypointRow();

  if(!row || row.locked){
    row=addWaypointRow();
  }

  row.text=poseToText(pose);
  row.confirmed=false;
  activeWaypointId=row.id;
  renderWaypointList();
  log(row.name+" <= map click pose");
}

async function setWaypointsOnMap(){
  let okCount=0;
  const validWaypoints=[];

  waypointRows.forEach(row=>{
    if(row.locked){
      row.confirmed=true;
      return;
    }

    const pose=parseWaypointText(row.text);

    if(pose){
      row.confirmed=true;
      okCount += 1;

      validWaypoints.push({
        name: row.name,
        x: pose.x,
        y: pose.y,
        yaw: pose.yaw
      });

    }else{
      row.confirmed=false;
    }
  });

  renderWaypointList();
  drawAll();

  const status=document.getElementById("mapToolStatus");

  if(status){
    status.textContent=`WAYPOINT: đang lưu ${okCount} waypoint. WP0/HOME luôn cố định tại (0,0,0)...`;
  }

  try{
    const res=await fetch("/api/save_runtime_waypoints",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        frame_id:"map",
        waypoints:validWaypoints
      })
    });

    const data=await res.json();

    if(status){
      if(data.ok){
        status.textContent=
          `WAYPOINT: đã lưu ${okCount} waypoint. ` +
          `WP0/HOME cố định. ESP32 gửi trực tiếp WP1, WP2, WP3...`;
      }else{
        status.textContent="WAYPOINT: lưu thất bại: "+(data.message || "unknown error");
      }
    }

    log(data.ok ? "Runtime waypoints saved" : "Save runtime waypoints failed: "+(data.message || "unknown error"));

  }catch(e){
    if(status){
      status.textContent="WAYPOINT: lưu thất bại. Kiểm tra webserver.";
    }
    log("Save runtime waypoints error: "+e);
  }
}

async function loadRuntimeWaypointsToViewer(){
  if(!viewerRosConnected){
    return;
  }

  const state=await getSystemStateForViewer();

  if(!state.navigation){
    return;
  }

  try{
    const res=await fetch("/api/runtime_waypoints");
    const data=await res.json();

    if(!data.ok || !data.data){
      log("Runtime waypoint load failed");
      return;
    }

    const rt=data.data;
    const rows=[];

    rows.push({
      id:"wp0_home",
      name:"WP0",
      text:"0.000, 0.000, 0.000",
      confirmed:true,
      locked:true
    });

    const wps=rt.waypoints || [];

    wps.forEach((wp)=>{
      rows.push({
        id:String(wp.name || "WP")+"_"+Date.now()+"_"+Math.random().toString(16).slice(2),
        name:String(wp.name || "WP").toUpperCase(),
        text:poseToText({
          x:Number(wp.x || 0.0),
          y:Number(wp.y || 0.0),
          yaw:Number(wp.yaw || 0.0)
        }),
        confirmed:true,
        locked:false
      });
    });

    waypointRows=rows;
    waypointSeq=0;

    waypointRows.forEach(row=>{
      const m=String(row.name).match(/^WP([0-9]+)$/);
      if(m){
        waypointSeq=Math.max(waypointSeq, Number(m[1]));
      }
    });

    const editable=waypointRows.filter(w=>!w.locked);
    activeWaypointId=editable.length ? editable[editable.length-1].id : null;

    renderWaypointList();
    drawAll();

    const status=document.getElementById("mapToolStatus");
    if(status){
      status.textContent=`WAYPOINT: đã nạp ${wps.length} waypoint từ runtime. WP0/HOME cố định.`;
    }

    log("Loaded runtime waypoints: WP0 + "+wps.length+" editable waypoint(s)");

  }catch(e){
    log("Load runtime waypoints error: "+e);
  }
}

async function sendNavGoalPose(pose){
  if(!pose){
    return;
  }

  const status=document.getElementById("mapToolStatus");
  if(status){
    status.textContent=`Đang gửi NAV GOAL: x=${pose.x.toFixed(3)}, y=${pose.y.toFixed(3)}, yaw=${pose.yaw.toFixed(3)}`;
  }

  try{
    const res=await fetch("/api/send_nav_goal",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(pose)
    });

    const data=await res.json();

    if(status){
      status.textContent=data.ok
        ? `Đã gửi NAV GOAL: x=${pose.x.toFixed(3)}, y=${pose.y.toFixed(3)}, yaw=${pose.yaw.toFixed(3)}`
        : `Gửi NAV GOAL thất bại: ${data.message || "unknown error"}`;
    }

    log(data.ok ? "NAV GOAL sent" : "NAV GOAL failed: "+(data.message || "unknown error"));

  }catch(e){
    if(status){
      status.textContent="Gửi NAV GOAL thất bại. Kiểm tra webserver.";
    }
    log("NAV GOAL error: "+e);
  }
}

function poseFromDrag(startWorld, endWorld){
  if(!startWorld || !endWorld) return null;
  const dx=endWorld.x-startWorld.x;
  const dy=endWorld.y-startWorld.y;
  const yaw=Math.atan2(dy, dx);
  return {x:startWorld.x, y:startWorld.y, yaw:yaw};
}

function getPresetTopicsForState(state){
  const activeMode = (state.active_mode || "").toUpperCase();

  if(state.navigation || activeMode === "NAVIGATION"){
    return [
      "/map",
      "/tf",
      "/tf_static",
      "/amcl_pose",
      "/scan_filtered",
      "/global_costmap/costmap",
      "/local_costmap/costmap",
      "/plan",
      "/plan_smoothed",
      "/transformed_global_plan"
    ];
  }

  if(state.slam || activeMode === "SLAM"){
    return [
      "/map",
      "/tf",
      "/tf_static",
      "/scan_filtered"
    ];
  }

  return [];
}

function findTopicInfoByName(topicName){
  return availableTopics.find(t => t.name === topicName) || null;
}

async function autoLoadModePreset(){
  if(autoPresetLoaded){
    return;
  }

  if(!ros){
    log("ROSBridge is not connected, skip auto preset.");
    return;
  }

  const state = await getSystemStateForViewer();
  const presetTopics = getPresetTopicsForState(state);

  if(presetTopics.length === 0){
    log("No auto preset because mode is: " + (state.active_mode || "UNKNOWN"));
    return;
  }

  log("Auto loading viewer preset for mode: " + (state.active_mode || "UNKNOWN"));

  // Viewer mới mở thì tự add preset. Nếu đã có topic do người dùng add thủ công thì không xóa.
  for(const topicName of presetTopics){
    const exists = Object.values(layers).find(l => l.topic === topicName);
    if(exists){
      continue;
    }

    const info = findTopicInfoByName(topicName);

    if(!info){
      log("Preset topic not found, skip: " + topicName);
      continue;
    }

    if(!isSupportedType(info.type)){
      log("Preset topic found but type is not drawable yet, skip: " + topicName + " [" + info.type + "]");
      continue;
    }

    addLayer(info.name, info.type);
  }

  autoPresetLoaded = true;
}

function loadSelectedTopic(){
  if(!ros){
    log("ROSBridge is not connected");
    return;
  }

  const info=getSelectedTopicInfo();
  if(!info.name){
    log("No topic selected");
    return;
  }

  addLayer(info.name, info.type);
}

function addLayer(topicName, topicType){
  const exists=Object.values(layers).find(l=>l.topic===topicName);
  if(exists){
    log("Topic already loaded: "+topicName);
    return;
  }

  const id="layer_"+(++layerSeq);
  const supported=isSupportedType(topicType);
  const roslibType=rosTypeToRoslibType(topicType);

  const layer={
    id,
    topic:topicName,
    type:topicType,
    roslibType,
    visible:true,
    supported,
    sub:null,
    msg:null,
    image:null
  };

  layers[id]=layer;
  renderLayerList();

  if(!supported){
    log("Loaded but not drawable yet: "+topicName+" ["+topicType+"]");
    return;
  }

  let throttle=250;
  if(topicType==="nav_msgs/msg/OccupancyGrid") throttle=1000;
  if(topicType==="tf2_msgs/msg/TFMessage") throttle=100;
  if(topicType==="nav_msgs/msg/Path") throttle=300;

  layer.sub=new ROSLIB.Topic({
    ros,
    name:topicName,
    messageType:roslibType,
    throttle_rate:throttle
  });

  layer.sub.subscribe((msg)=>{
    layer.msg=msg;

    if(layer.type==="nav_msgs/msg/OccupancyGrid"){
      layer.image=buildMapImage(msg, layer.topic);
      log(`OccupancyGrid received: ${layer.topic} ${msg.info.width}x${msg.info.height}, res=${msg.info.resolution}`);
    }

    if(layer.type==="tf2_msgs/msg/TFMessage"){
      updateTfBuffer(msg, layer.topic);
    }

    drawAll();
  });

  log("Subscribed: "+topicName+" ["+topicType+"]");
}

function removeLayer(id){
  const layer=layers[id];
  if(!layer) return;

  if(layer.sub){
    try { layer.sub.unsubscribe(); } catch(e) {}
  }

  delete layers[id];
  renderLayerList();
  drawAll();
  log("Removed topic: "+layer.topic);
}

function toggleLayerVisible(id){
  const layer=layers[id];
  if(!layer) return;

  layer.visible=!layer.visible;
  renderLayerList();
  drawAll();
}

function renderLayerList(){
  const ids=Object.keys(layers);

  if(ids.length===0){
    loadedTopicList.innerHTML='<div class="hint">Chưa có topic nào. Chọn topic ở trên rồi nhấn LOAD TOPIC.</div>';
    return;
  }

  loadedTopicList.innerHTML="";

  ids.forEach(id=>{
    const layer=layers[id];

    const row=document.createElement("div");
    row.className="topic-row";

    const cb=document.createElement("input");
    cb.type="checkbox";
    cb.className="topic-visible";
    cb.checked=layer.visible;
    cb.title="Hiện / ẩn topic";
    cb.onchange=()=>toggleLayerVisible(id);

    const text=document.createElement("div");
    const name=document.createElement("div");
    name.className="topic-name";
    name.textContent=layer.topic;

    const type=document.createElement("div");
    type.className="topic-type";
    type.textContent=layer.supported ? layer.type : `${layer.type || "unknown type"} | chưa hỗ trợ vẽ`;

    text.appendChild(name);
    text.appendChild(type);

    const rm=document.createElement("button");
    rm.className="remove-topic";
    rm.textContent="×";
    rm.title="Loại bỏ topic";
    rm.onclick=()=>removeLayer(id);

    row.appendChild(cb);
    row.appendChild(text);
    row.appendChild(rm);

    loadedTopicList.appendChild(row);
  });
}

function getFirstVisibleLayer(type){
  return Object.values(layers).find(l=>l.visible && l.type===type && l.msg);
}

function getVisibleLayers(type){
  return Object.values(layers).filter(l=>l.visible && l.type===type && l.msg);
}

function isCostmapTopic(topic){
  return topic && topic.toLowerCase().includes("costmap");
}

// Palette costmap gần RViz/Nav2 hơn:
// free/unknown: trong suốt
// inflation rộng: cyan
// gần vật cản: hồng
// lethal obstacle: tím đậm/đen
function rvizLikeCostmapColor(v, topicName=""){
  // Unknown/free: trong suốt để không che map nền
  if(v < 0 || v === 0){
    return [0, 0, 0, 0];
  }

  // Lõi obstacle thật
  if(v >= 100){
    return [35, 0, 70, 235];        // tím đậm / gần đen
  }

  // Ngay sát obstacle
  if(v >= 92){
    return [55, 245, 245, 215];     // cyan đậm
  }

  // Inflation chính
  if(v >= 35){
    return [95, 255, 255, 185];     // cyan sáng
  }

  // Cost thấp vẫn cho cyan nhẹ, còn viền hồng ngoài cùng sẽ tạo riêng bằng halo
  return [125, 255, 255, 130];
}

function buildMapImage(msg, topicName=""){
  const w=msg.info.width;
  const h=msg.info.height;
  const data=msg.data;
  const isCostmap=isCostmapTopic(topicName);

  const imageCanvas=document.createElement("canvas");
  imageCanvas.width=w;
  imageCanvas.height=h;

  const mctx=imageCanvas.getContext("2d");
  const image=mctx.createImageData(w,h);

  const costMask = isCostmap ? new Uint8Array(w*h) : null;

  for(let y=0; y<h; y++){
    for(let x=0; x<w; x++){
      const srcIdx=y*w+x;
      const dstY=h-1-y;
      const dstIdx=(dstY*w+x)*4;
      const v=data[srcIdx];

      if(isCostmap){
        if(v > 0){
          costMask[srcIdx] = 1;
        }

        const c = rvizLikeCostmapColor(v, topicName);

        image.data[dstIdx+0]=c[0];
        image.data[dstIdx+1]=c[1];
        image.data[dstIdx+2]=c[2];
        image.data[dstIdx+3]=c[3];

      }else{
        let c=180;

        if(v<0) c=95;          // unknown
        else if(v===0) c=245;  // free
        else if(v>50) c=20;    // occupied
        else c=150;

        image.data[dstIdx+0]=c;
        image.data[dstIdx+1]=c;
        image.data[dstIdx+2]=c;
        image.data[dstIdx+3]=255;
      }
    }
  }

  if(isCostmap && costMask){
    const haloRadius = 3;

    for(let y=0; y<h; y++){
      for(let x=0; x<w; x++){
        const srcIdx = y*w+x;

        if(costMask[srcIdx]){
          continue;
        }

        let nearCost = false;

        for(let dy=-haloRadius; dy<=haloRadius && !nearCost; dy++){
          const yy = y + dy;
          if(yy < 0 || yy >= h) continue;

          for(let dx=-haloRadius; dx<=haloRadius; dx++){
            const xx = x + dx;
            if(xx < 0 || xx >= w) continue;
            if((dx*dx + dy*dy) > haloRadius*haloRadius) continue;

            if(costMask[yy*w + xx]){
              nearCost = true;
              break;
            }
          }
        }

        if(nearCost){
          const dstY=h-1-y;
          const dstIdx=(dstY*w+x)*4;

          if(image.data[dstIdx+3] === 0){
            image.data[dstIdx+0]=245;
            image.data[dstIdx+1]=145;
            image.data[dstIdx+2]=185;
            image.data[dstIdx+3]=150;
          }
        }
      }
    }
  }

  mctx.putImageData(image,0,0);
  return imageCanvas;
}

function getYaw(q){
  const siny=2.0*(q.w*q.z+q.x*q.y);
  const cosy=1.0-2.0*(q.y*q.y+q.z*q.z);
  return Math.atan2(siny,cosy);
}

function getBaseMapLayer(){
  const grids=Object.values(layers).filter(
    l=>l.visible && l.type==="nav_msgs/msg/OccupancyGrid" && l.msg && l.image
  );

  let base=grids.find(l=>l.topic==="/map");
  if(base) return base;

  base=grids.find(l=>!isCostmapTopic(l.topic));
  if(base) return base;

  return grids.length>0 ? grids[0] : null;
}

function getCostmapLayers(){
  return Object.values(layers).filter(
    l=>l.visible && l.type==="nav_msgs/msg/OccupancyGrid" && l.msg && l.image && isCostmapTopic(l.topic)
  );
}

function getMapTransform(){
  const mapLayer=getBaseMapLayer();
  if(!mapLayer) return null;

  const mapMsg=mapLayer.msg;
  const mw=mapMsg.info.width*mapMsg.info.resolution;
  const mh=mapMsg.info.height*mapMsg.info.resolution;

  const baseScale=Math.min(canvas.width/mw, canvas.height/mh)*0.92;
  const scale=baseScale*viewZoom;

  const ox=mapMsg.info.origin.position.x;
  const oy=mapMsg.info.origin.position.y;

  const offsetX=(canvas.width-mw*scale)/2 + viewPanX;
  const offsetY=(canvas.height-mh*scale)/2 + viewPanY;

  return {scale, ox, oy, mw, mh, offsetX, offsetY};
}

function getViewCenter(){
  return {
    x: canvas.width/2,
    y: canvas.height/2
  };
}

function rotateCanvasPoint(px, py, angle){
  const c=getViewCenter();
  const dx=px-c.x;
  const dy=py-c.y;
  const ca=Math.cos(angle);
  const sa=Math.sin(angle);

  return {
    x: c.x + ca*dx - sa*dy,
    y: c.y + sa*dx + ca*dy
  };
}

function worldToCanvasRaw(x,y){
  const tf=getMapTransform();
  if(!tf) return {x:0, y:0};

  return {
    x: tf.offsetX+(x-tf.ox)*tf.scale,
    y: tf.offsetY+(tf.mh-(y-tf.oy))*tf.scale
  };
}

function worldToCanvas(x,y){
  const raw=worldToCanvasRaw(x,y);
  return rotateCanvasPoint(raw.x, raw.y, viewRotation);
}


function addScreenDeltaToPan(dx, dy){
  // viewPanX/Y nằm trong hệ raw canvas, nên phải đổi delta màn hình về raw delta
  const ca=Math.cos(-viewRotation);
  const sa=Math.sin(-viewRotation);

  viewPanX += ca*dx - sa*dy;
  viewPanY += sa*dx + ca*dy;
}

function normalizeFrame(frame){
  if(!frame) return "";
  return frame.startsWith("/") ? frame.slice(1) : frame;
}

function quatToYaw(q){
  if(!q) return 0;
  return getYaw(q);
}

function normalizeAngle(a){
  while(a>Math.PI) a-=2*Math.PI;
  while(a<-Math.PI) a+=2*Math.PI;
  return a;
}

function composePose2D(a,b){
  const ca=Math.cos(a.yaw);
  const sa=Math.sin(a.yaw);
  return {
    x:a.x + ca*b.x - sa*b.y,
    y:a.y + sa*b.x + ca*b.y,
    yaw:normalizeAngle(a.yaw + b.yaw)
  };
}

function updateTfBuffer(msg, topicName){
  if(!msg || !msg.transforms) return;

  msg.transforms.forEach(t=>{
    const parent=normalizeFrame(t.header.frame_id);
    const child=normalizeFrame(t.child_frame_id);
    if(!parent || !child) return;

    const tr=t.transform.translation;
    const rot=t.transform.rotation;

    const item={
      parent,
      child,
      x:tr.x || 0,
      y:tr.y || 0,
      yaw:quatToYaw(rot),
      stamp:t.header.stamp,
      topic:topicName
    };

    if(topicName==="/tf_static") tfStaticBuffer[child]=item;
    else tfBuffer[child]=item;
  });
}

function getTfItem(child){
  child=normalizeFrame(child);
  return tfBuffer[child] || tfStaticBuffer[child] || null;
}

function resolveFramePose(source, target="map", visited=null){
  source=normalizeFrame(source);
  target=normalizeFrame(target);
  if(!visited) visited=new Set();

  if(source===target) return {x:0,y:0,yaw:0};
  if(!source || visited.has(source)) return null;
  visited.add(source);

  const t=getTfItem(source);
  if(!t) return null;

  const parentPose=resolveFramePose(t.parent, target, visited);
  if(!parentPose) return null;

  return composePose2D(parentPose, {x:t.x, y:t.y, yaw:t.yaw});
}

function transformPoint2D(pose, x, y){
  const c=Math.cos(pose.yaw);
  const ss=Math.sin(pose.yaw);
  return {
    x:pose.x + c*x - ss*y,
    y:pose.y + ss*x + c*y
  };
}


function canvasToWorld(cx, cy){
  const tf=getMapTransform();
  if(!tf) return {x:0, y:0};

  return {
    x: ((cx - tf.offsetX) / tf.scale) + tf.ox,
    y: tf.oy + tf.mh - ((cy - tf.offsetY) / tf.scale)
  };
}

function clamp(v, minV, maxV){
  return Math.max(minV, Math.min(maxV, v));
}

function setupCanvasInteraction(){
  canvas.addEventListener("contextmenu", (e)=>{
    e.preventDefault();
  });

  canvas.addEventListener("wheel", (e)=>{
    e.preventDefault();

    if(!getBaseMapLayer()){
      return;
    }

    const rect=canvas.getBoundingClientRect();
    const mx=(e.clientX-rect.left)*(canvas.width/rect.width);
    const my=(e.clientY-rect.top)*(canvas.height/rect.height);

    const before=canvasToWorld(mx,my);

    if(e.shiftKey){
      // Shift + wheel: xoay map quanh vị trí con trỏ
      const delta=e.deltaY<0 ? -0.08 : 0.08;
      viewRotation += delta;
      log("Map rotation: " + (viewRotation*180/Math.PI).toFixed(1) + " deg");
    }else{
      // Wheel thường: zoom
      const factor=e.deltaY<0 ? 1.18 : 0.85;
      viewZoom=clamp(viewZoom*factor, 0.35, 8.0);
    }

    // Giữ điểm dưới con trỏ không bị trôi quá nhiều sau zoom/rotate
    const afterCanvas=worldToCanvas(before.x,before.y);
    addScreenDeltaToPan(mx-afterCanvas.x, my-afterCanvas.y);

    drawAll();
  }, {passive:false});

  canvas.addEventListener("mousedown", (e)=>{
    const rect=canvas.getBoundingClientRect();
    const mx=(e.clientX-rect.left)*(canvas.width/rect.width);
    const my=(e.clientY-rect.top)*(canvas.height/rect.height);

    if(activeMapTool==="PAN"){
      if(e.button===2){
        isRotating=true;
        lastMouseX=e.clientX;
        lastMouseY=e.clientY;
        return;
      }

      if(e.button===0){
        isPanning=true;
        lastMouseX=e.clientX;
        lastMouseY=e.clientY;
        return;
      }
    }

    if(!getBaseMapLayer()){
      return;
    }

    if(e.button!==0){
      return;
    }

    toolDragging=true;
    toolStartWorld=canvasToWorld(mx,my);
    toolCurrentWorld=toolStartWorld;
    drawAll();
  });

  window.addEventListener("mousemove", (e)=>{
    if(isPanning && activeMapTool==="PAN"){
      const rect=canvas.getBoundingClientRect();
      const sx=canvas.width/rect.width;
      const sy=canvas.height/rect.height;

      const dx=(e.clientX-lastMouseX)*sx;
      const dy=(e.clientY-lastMouseY)*sy;

      addScreenDeltaToPan(dx, dy);

      lastMouseX=e.clientX;
      lastMouseY=e.clientY;

      drawAll();
      return;
    }

    if(isRotating && activeMapTool==="PAN"){
      const dx=e.clientX-lastMouseX;

      viewRotation += dx*0.01;

      lastMouseX=e.clientX;
      lastMouseY=e.clientY;

      drawAll();
      return;
    }

    if(toolDragging && activeMapTool!=="PAN"){
      const rect=canvas.getBoundingClientRect();
      const mx=(e.clientX-rect.left)*(canvas.width/rect.width);
      const my=(e.clientY-rect.top)*(canvas.height/rect.height);
      toolCurrentWorld=canvasToWorld(mx,my);
      drawAll();
    }
  });

  window.addEventListener("mouseup", async ()=>{
    if(isPanning){
      isPanning=false;
      return;
    }

    if(isRotating){
      isRotating=false;
      return;
    }

    if(toolDragging && activeMapTool!=="PAN"){
      const pose=poseFromDrag(toolStartWorld, toolCurrentWorld || toolStartWorld);
      toolDragging=false;
      toolStartWorld=null;
      toolCurrentWorld=null;

      if(activeMapTool==="NAV_GOAL"){
        await sendNavGoalPose(pose);
      }else if(activeMapTool==="WAYPOINT"){
        setWaypointFromMapPose(pose);
      }

      drawAll();
    }
  });

  canvas.addEventListener("dblclick", ()=>{
    viewZoom=1.0;
    viewPanX=0.0;
    viewPanY=0.0;
    viewRotation=0.0;
    drawAll();
    log("View reset: zoom/pan/rotation");
  });
}

function drawOccupancyLayer(layer, isBase=false){
  if(!layer || !layer.msg || !layer.image) return;

  const tf=getMapTransform();
  if(!tf) return;

  const msg=layer.msg;
  const wMeters=msg.info.width*msg.info.resolution;
  const hMeters=msg.info.height*msg.info.resolution;
  const origin=msg.info.origin.position;

  // Dùng raw canvas để draw image, sau đó rotate toàn bộ canvas layer quanh tâm view.
  const topLeftRaw=worldToCanvasRaw(origin.x, origin.y+hMeters);
  const center=getViewCenter();

  ctx.save();
  ctx.globalAlpha=isBase ? 1.0 : 0.75;

  ctx.translate(center.x, center.y);
  ctx.rotate(viewRotation);
  ctx.translate(-center.x, -center.y);

  ctx.drawImage(
    layer.image,
    topLeftRaw.x,
    topLeftRaw.y,
    wMeters*tf.scale,
    hMeters*tf.scale
  );

  ctx.restore();
}


function drawArrowPose(pose, color="#22c55e", label=""){
  if(!pose) return;

  const c=worldToCanvas(pose.x, pose.y);
  const len=0.45;
  const tip=worldToCanvas(
    pose.x + Math.cos(pose.yaw)*len,
    pose.y + Math.sin(pose.yaw)*len
  );

  ctx.save();
  ctx.strokeStyle=color;
  ctx.fillStyle=color;
  ctx.lineWidth=3;

  ctx.beginPath();
  ctx.moveTo(c.x,c.y);
  ctx.lineTo(tip.x,tip.y);
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(c.x,c.y,5,0,Math.PI*2);
  ctx.fill();

  const head=10;
  const a=Math.atan2(tip.y-c.y, tip.x-c.x);
  ctx.beginPath();
  ctx.moveTo(tip.x,tip.y);
  ctx.lineTo(tip.x-head*Math.cos(a-0.45), tip.y-head*Math.sin(a-0.45));
  ctx.lineTo(tip.x-head*Math.cos(a+0.45), tip.y-head*Math.sin(a+0.45));
  ctx.closePath();
  ctx.fill();

  if(label){
    ctx.font="13px Arial";
    ctx.fillText(label, c.x+8, c.y-8);
  }

  ctx.restore();
}

function drawWaypoints(){
  waypointRows.forEach(row=>{
    if(!row.confirmed) return;
    const pose=parseWaypointText(row.text);
    if(!pose) return;
    drawArrowPose(pose, "#facc15", row.name);
  });
}

function drawToolPreview(){
  if(!toolDragging || !toolStartWorld || !toolCurrentWorld) return;

  const pose=poseFromDrag(toolStartWorld, toolCurrentWorld);
  if(!pose) return;

  if(activeMapTool==="NAV_GOAL"){
    drawArrowPose(pose, "#22c55e", "NAV GOAL");
  }else if(activeMapTool==="WAYPOINT"){
    const row=getActiveWaypointRow();
    drawArrowPose(pose, "#facc15", row ? row.name : "Waypoint");
  }
}

function drawAll(){
  ctx.clearRect(0,0,canvas.width,canvas.height);

  const mapLayer=getBaseMapLayer();

  if(!mapLayer){
    ctx.fillStyle="#94a3b8";
    ctx.font="26px Arial";
    ctx.fillText("Chưa có map. Hãy LOAD TOPIC /map hoặc OccupancyGrid.",40,60);
    return;
  }

  drawOccupancyLayer(mapLayer, true);

  getCostmapLayers().forEach(layer=>drawOccupancyLayer(layer, false));

  drawPaths();
  drawScans();
  drawWaypoints();
  drawToolPreview();
  drawPose();
  drawTfFrames();
}

function drawPose(){
  const poseLayer=getFirstVisibleLayer("geometry_msgs/msg/PoseWithCovarianceStamped");

  let p=null;
  let yaw=0;
  let label="";

  if(poseLayer){
    const msg=poseLayer.msg;
    p=msg.pose.pose.position;
    yaw=getYaw(msg.pose.pose.orientation);
    label=`topic: ${poseLayer.topic}`;
  }else{
    const tfPose=resolveFramePose("base_footprint","map") || resolveFramePose("base_link","map");
    if(tfPose){
      p={x:tfPose.x, y:tfPose.y};
      yaw=tfPose.yaw;
      label="TF: map -> base_footprint/base_link";
    }
  }

  if(!p) return;

  const c=worldToCanvas(p.x,p.y);

  if(poseBox){
    poseBox.textContent =
      `Pose estimate
` +
      `${label}
` +
      `x: ${p.x.toFixed(3)} m
` +
      `y: ${p.y.toFixed(3)} m
` +
      `yaw: ${yaw.toFixed(3)} rad`;
  }

  ctx.save();
  ctx.translate(c.x,c.y);
  ctx.rotate(viewRotation - yaw);

  ctx.fillStyle="#22c55e";
  ctx.beginPath();
  ctx.moveTo(18,0);
  ctx.lineTo(-12,-10);
  ctx.lineTo(-12,10);
  ctx.closePath();
  ctx.fill();

  ctx.strokeStyle="#052e16";
  ctx.lineWidth=2;
  ctx.stroke();

  ctx.restore();

  ctx.fillStyle="#22c55e";
  ctx.font="14px Arial";
  ctx.fillText(`x=${p.x.toFixed(2)} y=${p.y.toFixed(2)} yaw=${yaw.toFixed(2)}`, c.x+14, c.y-14);
}

function drawScans(){
  const scans=getVisibleLayers("sensor_msgs/msg/LaserScan");

  scans.forEach(layer=>{
    const scanMsg=layer.msg;
    const ranges=scanMsg.ranges;
    const frame=normalizeFrame(scanMsg.header && scanMsg.header.frame_id ? scanMsg.header.frame_id : "");

    let sensorPose=null;

    if(frame){
      sensorPose=resolveFramePose(frame,"map");
    }

    if(!sensorPose){
      const poseLayer=getFirstVisibleLayer("geometry_msgs/msg/PoseWithCovarianceStamped");
      if(!poseLayer) return;
      const p=poseLayer.msg.pose.pose.position;
      const yaw=getYaw(poseLayer.msg.pose.pose.orientation);
      sensorPose={x:p.x, y:p.y, yaw:yaw};
    }

    const step=Math.max(1,Math.floor(ranges.length/420));

    ctx.fillStyle="#ef4444";

    for(let i=0; i<ranges.length; i+=step){
      const r=ranges[i];

      if(!Number.isFinite(r)) continue;
      if(r<scanMsg.range_min || r>scanMsg.range_max) continue;

      const a=scanMsg.angle_min+i*scanMsg.angle_increment;
      const lx=r*Math.cos(a);
      const ly=r*Math.sin(a);
      const wp=transformPoint2D(sensorPose,lx,ly);
      const c=worldToCanvas(wp.x,wp.y);

      ctx.fillRect(c.x-1,c.y-1,2,2);
    }
  });
}

function drawPaths(){
  const pathLayers=getVisibleLayers("nav_msgs/msg/Path");
  if(pathLayers.length===0) return;

  const colors=["#3b82f6", "#a855f7", "#06b6d4", "#f97316"];

  pathLayers.forEach((layer,idx)=>{
    const msg=layer.msg;
    if(!msg || !msg.poses || msg.poses.length<2) return;

    const frame=normalizeFrame(msg.header && msg.header.frame_id ? msg.header.frame_id : "map");
    const framePose = frame==="map" ? {x:0,y:0,yaw:0} : resolveFramePose(frame,"map");
    if(!framePose) return;

    ctx.save();
    ctx.strokeStyle=colors[idx%colors.length];
    ctx.lineWidth=3;
    ctx.beginPath();

    let started=false;

    msg.poses.forEach(ps=>{
      const pp=ps.pose.position;
      const wp=transformPoint2D(framePose, pp.x, pp.y);
      const c=worldToCanvas(wp.x,wp.y);

      if(!started){
        ctx.moveTo(c.x,c.y);
        started=true;
      }else{
        ctx.lineTo(c.x,c.y);
      }
    });

    ctx.stroke();
    ctx.restore();
  });
}

function drawAxisAtPose(pose, name, color="#22c55e"){
  if(!pose) return;

  const c=worldToCanvas(pose.x,pose.y);

  const xEnd=worldToCanvas(
    pose.x + Math.cos(pose.yaw)*0.35,
    pose.y + Math.sin(pose.yaw)*0.35
  );

  const yEnd=worldToCanvas(
    pose.x + Math.cos(pose.yaw+Math.PI/2)*0.25,
    pose.y + Math.sin(pose.yaw+Math.PI/2)*0.25
  );

  ctx.save();

  ctx.lineWidth=2;

  ctx.strokeStyle="#ef4444";
  ctx.beginPath();
  ctx.moveTo(c.x,c.y);
  ctx.lineTo(xEnd.x,xEnd.y);
  ctx.stroke();

  ctx.strokeStyle="#22c55e";
  ctx.beginPath();
  ctx.moveTo(c.x,c.y);
  ctx.lineTo(yEnd.x,yEnd.y);
  ctx.stroke();

  ctx.fillStyle=color;
  ctx.font="12px Arial";
  ctx.fillText(name,c.x+5,c.y+13);

  ctx.restore();
}

function drawTfFrames(){
  const tfLayers=getVisibleLayers("tf2_msgs/msg/TFMessage");
  if(tfLayers.length===0) return;

  const preferred=[
    "odom",
    "base_footprint",
    "base_link",
    "laser_frame",
    "camera_link",
    "camera_color_frame",
    "camera_depth_frame"
  ];

  preferred.forEach(frame=>{
    const pose=resolveFramePose(frame,"map");
    if(pose) drawAxisAtPose(pose, frame, "#facc15");
  });
}

function clearCanvas(){
  stopManualControl();
  Object.keys(layers).forEach(id=>removeLayer(id));
  tfBuffer={};
  tfStaticBuffer={};
  waypointRows=[];
  activeWaypointId=null;
  renderWaypointList();

  if(poseBox){
    poseBox.textContent="Pose:\nx: -\ny: -\nyaw: -";
  }

  viewZoom=1.0;
  viewPanX=0.0;
  viewPanY=0.0;
  viewRotation=0.0;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  log("View cleared");
}

async function getSystemStateForViewer(){
  try{
    const res=await fetch("/api/system_state");
    return await res.json();
  }catch(e){
    return {active_mode:"UNKNOWN", slam:false, navigation:false, device:false};
  }
}

async function refreshViewerSaveState(){
  const saveBtn=document.getElementById("saveFusionMapBtn");
  const modeText=document.getElementById("viewerModeText");

  if(!viewerRosConnected){
    if(saveBtn){
      saveBtn.disabled = true;
      saveBtn.style.opacity = 0.45;
    }

    if(modeText){
      modeText.textContent = "Viewer: chưa CONNECT ROSBridge. Các chức năng đang bị khóa.";
      modeText.style.color = "#f97316";
    }

    return;
  }

  const data=await getSystemStateForViewer();
  const isSlam=!!data.slam;

  if(saveBtn){
    saveBtn.disabled=!isSlam;
    saveBtn.style.opacity = isSlam ? 1.0 : 0.45;
  }

  if(modeText){
    modeText.textContent =
      `Mode: ${data.active_mode || "UNKNOWN"} | ` +
      `SAVE MAP: ${isSlam ? "ENABLED" : "DISABLED - chỉ lưu khi đang SLAM"}`;

    modeText.style.color=isSlam ? "#22c55e" : "#f97316";
  }
}

async function saveFusionMap() {
  const resultBox = document.getElementById("saveMapResult");
  const input = document.getElementById("mapNameInput");

  const mapName = input ? input.value.trim() : "";

  if (resultBox) {
    resultBox.textContent = "Đang tiến hành lưu map...";
  }

  try {
    const res = await fetch("/api/save_fusion_map", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        map_name: mapName
      })
    });

    const data = await res.json();

    if (data.ok) {
      if (resultBox) {
        resultBox.textContent = "Đã lưu map thành công.";
      }
      log("Save map success: " + data.map_name);
    } else {
      if (resultBox) {
        resultBox.textContent = "Lưu map thất bại. Kiểm tra terminal/log hệ thống.";
      }
      log("Save map failed: " + (data.message || "unknown error"));
    }

    await refreshViewerSaveState();

  } catch (e) {
    if (resultBox) {
      resultBox.textContent = "Lưu map thất bại. Kiểm tra kết nối webserver hoặc ROSBridge.";
    }
    log("Save map error: " + e);
  }
}


window.addEventListener("resize", drawAll);
refreshViewerSaveState();
setInterval(refreshViewerSaveState,2500);

function initViewerPage(){
  setDefaultRosbridgeUrl();

  setViewerControlsEnabled(false);

  if(typeof setupCanvasInteraction === "function" && !window.__amrCanvasInteractionReady){
    setupCanvasInteraction();
    window.__amrCanvasInteractionReady=true;
  }

  if(typeof refreshViewerSaveState === "function"){
    refreshViewerSaveState();
  }

  if(typeof updateWaypointActionButtons === "function"){
    updateWaypointActionButtons();
  }

  if(typeof setupKeyboardManualControl === "function"){
    setupKeyboardManualControl();
  }
}

window.addEventListener("load", initViewerPage);

</script>
</body>
</html>
'''


def main():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
