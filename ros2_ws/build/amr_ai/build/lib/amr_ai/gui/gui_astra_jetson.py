import os
import cv2
import time
import torch
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from PIL import Image, ImageTk
from ultralytics import YOLO

from amr_ai.core import config as cfg
from camera_openni import OpenNICamera
from amr_ai.tracking.reid import ReIDManager
from amr_ai.detectors.fall_detector import FallDetector
from amr_ai.detectors.fire_smoke_detector import FireSmokeDetector
from amr_ai.core.utils import valid_box_size, center_distance_sq, estimate_depth_distance


# =============================
# ASTRA / OPENNI PATH ON JETSON
# =============================
ASTRA_OPENNI_PATH = (
    "/home/huyjetson/mobile_robot/ai/Orbbec_OpenNI_v2.3.0.86-beta6_linux_release/"
    "OpenNI_2.3.0.86_202210111155_4c8f5aa4_beta6_a311d_arm64/"
    "OpenNI_2.3.0.86_202210111155_4c8f5aa4_beta6_a311d/sdk/libs"
)

SIDE_WIDTH = 320
HEADER_HEIGHT = 76

# =============================
# FIRE / SMOKE CONFIG
# =============================
FIRE_SMOKE_ENGINE_NAME = "fire_smoke_s.engine"

FIRE_RUN_INTERVAL = 5
FIRE_ALERT_HOLD_SEC = 2.0

FIRE_IMGSZ = 640
FIRE_CONF = 0.5
SMOKE_CONF = 0.8


def get_nearest_track(boxes_xyxy, ids, center_x, center_y):
    nearest_track = None
    nearest_box = None
    nearest_dist = 10**18

    for box, tid in zip(boxes_xyxy, ids):
        if not valid_box_size(box):
            continue

        dist2 = center_distance_sq(box, center_x, center_y)

        if dist2 < nearest_dist:
            nearest_dist = dist2
            nearest_track = tid
            nearest_box = box

    return nearest_track, nearest_box


class AstraPeopleFollowingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI People Following System - Astra")
        self.root.configure(bg="#0f172a")
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{max(620, sh - 80)}+0+0")
        self.root.minsize(900, 500)

        self.base_dir = Path(__file__).resolve().parent

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.infer_device = 0 if torch.cuda.is_available() else "cpu"
        self.use_half = torch.cuda.is_available()

        self.detect_model = None
        self.reid = None
        self.fall_detector = None
        self.fire_smoke_detector = None
        self.camera = None
        self.running = False

        self.prepare_mode = False
        self.enroll_mode = False
        self.prepare_start_time = 0.0

        self.frame_count = 0
        self.fps_value = 0.0
        self.last_time = time.time()
        self.last_distance_cm = None

        self.fire_frame_id = 0
        self.last_fire_smoke_detections = []
        self.last_fire_time = 0.0
        self.last_smoke_time = 0.0

        self.status_var = tk.StringVar(value="READY")
        self.mode_var = tk.StringVar(value="Detecting")
        self.target_var = tk.StringVar(value="None")
        self.people_var = tk.StringVar(value="0")
        self.fps_var = tk.StringVar(value="0.0")
        self.distance_var = tk.StringVar(value="-- cm")
        self.enroll_var = tk.StringVar(value=f"0/{cfg.ENROLL_FRAMES}")
        self.device_var = tk.StringVar(value=self.device.upper())
        self.fire_smoke_var = tk.StringVar(value="Normal")

        self.build_ui()
        self.load_system()
        self.start_camera()

    # =============================
    # UI
    # =============================
    def build_ui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self.root, bg="#0f172a", height=HEADER_HEIGHT)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(8, 2))
        header.grid_propagate(False)

        tk.Label(
            header,
            text="AI People Following System",
            bg="#0f172a",
            fg="#f8fafc",
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Astra depth camera interface for target enrollment, tracking, fall detection and fire/smoke warning",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 0))

        main = tk.Frame(self.root, bg="#0f172a")
        main.grid(row=1, column=0, sticky="nsew", padx=18, pady=(4, 12))
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, minsize=SIDE_WIDTH)

        video_card = tk.Frame(
            main,
            bg="#020617",
            highlightthickness=1,
            highlightbackground="#334155"
        )
        video_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        video_card.grid_propagate(False)

        self.video_label = tk.Label(video_card, bg="#020617")
        self.video_label.pack(fill="both", expand=True, padx=6, pady=6)

        side = tk.Frame(
            main,
            bg="#111827",
            width=SIDE_WIDTH,
            highlightthickness=1,
            highlightbackground="#334155"
        )
        side.grid(row=0, column=1, sticky="ns")
        side.grid_propagate(False)
        side.pack_propagate(False)

        tk.Label(
            side,
            text="CONTROL",
            bg="#111827",
            fg="#f8fafc",
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", padx=16, pady=(14, 8))

        self.status_badge = tk.Label(
            side,
            textvariable=self.status_var,
            bg="#0ea5e9",
            fg="white",
            font=("Segoe UI", 14, "bold"),
            height=2,
            width=18
        )
        self.status_badge.pack(fill="x", padx=16, pady=(0, 12))

        row = tk.Frame(side, bg="#111827", height=42)
        row.pack(fill="x", padx=16, pady=(0, 8))
        row.pack_propagate(False)

        self.button(row, "ENROLL", "#2563eb", "#1d4ed8", self.start_enroll).pack(
            side="left", fill="both", expand=True, padx=(0, 5)
        )

        self.button(row, "RESET", "#f59e0b", "#d97706", self.reset_target).pack(
            side="left", fill="both", expand=True, padx=(5, 0)
        )

        self.button(side, "QUIT", "#dc2626", "#b91c1c", self.quit_app).pack(
            fill="x", padx=16, pady=(0, 12)
        )

        box = tk.Frame(
            side,
            bg="#1f2937",
            height=286,
            highlightthickness=1,
            highlightbackground="#334155"
        )
        box.pack(fill="x", padx=16, pady=(0, 12))
        box.pack_propagate(False)

        tk.Label(
            box,
            text="SYSTEM STATUS",
            bg="#1f2937",
            fg="#38bdf8",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.status_row(box, "Mode", self.mode_var)
        self.status_row(box, "Target", self.target_var)
        self.status_row(box, "People", self.people_var)
        self.status_row(box, "Distance", self.distance_var)
        self.status_row(box, "Fire/Smoke", self.fire_smoke_var)
        self.status_row(box, "FPS", self.fps_var)
        self.status_row(box, "Enroll", self.enroll_var)
        self.status_row(box, "Device", self.device_var)

        source = tk.Frame(
            side,
            bg="#0f172a",
            height=88,
            highlightthickness=1,
            highlightbackground="#334155"
        )
        source.pack(fill="x", padx=16, pady=(0, 12))
        source.pack_propagate(False)

        tk.Label(
            source,
            text="Camera",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=12, pady=(8, 0))

        tk.Label(
            source,
            text="Astra Mini S / OpenNI",
            bg="#0f172a",
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=12, pady=(2, 0))

        tk.Label(
            source,
            text="Fire/Smoke: TensorRT engine",
            bg="#0f172a",
            fg="#fbbf24",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=12, pady=(3, 6))

    def button(self, parent, text, color, hover_color, command):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=hover_color,
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_color))
        btn.bind("<Leave>", lambda e: btn.configure(bg=color))
        return btn

    def status_row(self, parent, title, variable):
        row = tk.Frame(parent, bg="#1f2937", height=26)
        row.pack(fill="x", padx=12, pady=3)
        row.pack_propagate(False)

        tk.Label(
            row,
            text=title,
            bg="#1f2937",
            fg="#94a3b8",
            font=("Segoe UI", 9),
            width=10,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            row,
            textvariable=variable,
            bg="#1f2937",
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            width=17,
            anchor="w"
        ).pack(side="left")

    def set_status(self, text, color):
        self.status_var.set(text)

        if hasattr(self, "status_badge"):
            self.status_badge.configure(bg=color)

    # =============================
    # SYSTEM INIT
    # =============================
    def load_system(self):
        try:
            self.set_status("LOADING", "#6366f1")

            os.environ["OPENNI2_REDIST"] = ASTRA_OPENNI_PATH
            os.environ["LD_LIBRARY_PATH"] = ASTRA_OPENNI_PATH + ":" + os.environ.get("LD_LIBRARY_PATH", "")

            fire_smoke_model_path = str(self.base_dir / "models" / FIRE_SMOKE_ENGINE_NAME)

            if not os.path.exists(fire_smoke_model_path):
                raise FileNotFoundError(f"Khong tim thay model fire/smoke: {fire_smoke_model_path}")

            self.detect_model = YOLO(cfg.MODEL_PATH)
            self.reid = ReIDManager(self.device)
            self.fall_detector = FallDetector(cfg.POSE_MODEL_PATH, self.infer_device, self.use_half)

            self.fire_smoke_detector = FireSmokeDetector(
                model_path=fire_smoke_model_path,
                infer_device=0,
                imgsz=FIRE_IMGSZ,
                fire_conf=FIRE_CONF,
                smoke_conf=SMOKE_CONF
            )

            self.camera = OpenNICamera(openni_path=ASTRA_OPENNI_PATH)

            self.fire_smoke_var.set("Normal")
            self.set_status("READY", "#0ea5e9")

        except Exception as exc:
            self.set_status("LOAD ERROR", "#dc2626")
            messagebox.showerror("System Load Error", str(exc))

    def start_camera(self):
        if self.camera is None:
            return

        try:
            self.camera.start()
            self.running = True
            self.mode_var.set("Detecting")
            self.set_status("DETECTING", "#0ea5e9")
            self.update_frame()

        except Exception as exc:
            self.set_status("CAM ERROR", "#dc2626")
            messagebox.showerror("Camera Error", str(exc))

    # =============================
    # BUTTON EVENTS
    # =============================
    def start_enroll(self):
        if not self.running:
            return

        self.reid.reset()
        self.fall_detector.reset()

        self.prepare_mode = True
        self.enroll_mode = False
        self.prepare_start_time = time.time()

        self.target_var.set("Preparing")
        self.enroll_var.set(f"0/{cfg.ENROLL_FRAMES}")
        self.distance_var.set("-- cm")
        self.mode_var.set("Preparing")
        self.set_status("PREPARING", "#f59e0b")

    def reset_target(self):
        if self.reid is not None:
            self.reid.reset()

        if self.fall_detector is not None:
            self.fall_detector.reset()

        self.prepare_mode = False
        self.enroll_mode = False

        self.target_var.set("None")
        self.enroll_var.set(f"0/{cfg.ENROLL_FRAMES}")
        self.distance_var.set("-- cm")
        self.mode_var.set("Detecting")

        self.last_fire_smoke_detections = []
        self.last_fire_time = 0.0
        self.last_smoke_time = 0.0
        self.fire_smoke_var.set("Normal")

        self.set_status("DETECTING", "#0ea5e9")

    # =============================
    # FRAME LOOP
    # =============================
    def update_frame(self):
        if not self.running or self.camera is None:
            return

        frame, depth = self.camera.read()

        if frame is None or depth is None:
            self.set_status("FRAME ERROR", "#dc2626")
            self.root.after(50, self.update_frame)
            return

        annotated = frame.copy()
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2
        now = time.time()

        self.frame_count += 1

        if self.prepare_mode:
            remaining = max(0, int(cfg.PREPARE_COUNTDOWN - (now - self.prepare_start_time)) + 1)
            self.mode_var.set(f"Preparing {remaining}s")
            self.set_status("PREPARING", "#f59e0b")

            cv2.putText(
                annotated,
                f"Prepare enroll: {remaining}s",
                (25, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 180, 255),
                2
            )

            if now - self.prepare_start_time >= cfg.PREPARE_COUNTDOWN:
                self.prepare_mode = False
                self.enroll_mode = True
                self.reid.enroll_embeddings = []
                self.reid.enroll_upper_embeddings = []
                self.reid.enroll_shirts = []
                self.mode_var.set("Enrolling")
                self.set_status("ENROLLING", "#2563eb")

        detections, nearest_track, nearest_box = self.run_detection(frame, center_x, center_y)

        if self.enroll_mode and nearest_box is not None:
            try:
                self.reid.add_enroll_sample(frame, nearest_box)
            except Exception:
                pass

            enroll_count = len(self.reid.enroll_embeddings)
            self.enroll_var.set(f"{enroll_count}/{cfg.ENROLL_FRAMES}")

            x1, y1, x2, y2 = map(int, nearest_box)

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 120, 0), 3)

            cv2.putText(
                annotated,
                "ENROLLING",
                (x1, max(25, y1 - 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 120, 0),
                2
            )

            if enroll_count >= cfg.ENROLL_FRAMES:
                self.reid.finish_enroll(nearest_track, nearest_box, now)
                self.enroll_mode = False
                self.target_var.set(f"ID {nearest_track}")
                self.mode_var.set("Following")
                self.set_status("FOLLOWING", "#16a34a")

        elif self.enroll_mode and nearest_box is None:
            self.mode_var.set("No person")

        selected_target = self.reid.select_target(
            frame,
            detections,
            center_x,
            center_y,
            now,
            self.frame_count
        )

        selected_distance_mm = None

        if selected_target is not None:
            raw_distance_mm, _ = estimate_depth_distance(depth, selected_target["box"])
            selected_distance_mm = self.reid.smooth_depth_distance(raw_distance_mm)

            self.target_var.set(f"ID {selected_target['id']}")
            self.mode_var.set("Following")
            self.set_status("FOLLOWING", "#16a34a")

            if selected_distance_mm is not None:
                self.distance_var.set(f"{selected_distance_mm / 10.0:.1f} cm")

        elif self.reid.target_profile is not None and not self.enroll_mode and not self.prepare_mode:
            self.target_var.set("Lost")
            self.mode_var.set("Lost")
            self.distance_var.set("-- cm")
            self.set_status("TARGET LOST", "#dc2626")

        detections = self.fall_detector.update(
            frame,
            depth,
            detections,
            center_x,
            center_y,
            h,
            self.frame_count,
            now
        )

        annotated = self.draw_results(
            annotated,
            detections,
            selected_target,
            selected_distance_mm
        )

        annotated = self.update_fire_smoke(
            frame,
            annotated,
            now
        )

        self.people_var.set(str(len(detections)))
        self.update_fps()
        self.show_on_gui(annotated)
        self.root.after(10, self.update_frame)

    def run_detection(self, frame, center_x, center_y):
        detections = []
        nearest_track = None
        nearest_box = None

        try:
            detect_results = self.detect_model.track(
                frame,
                persist=True,
                classes=[0],
                conf=0.4,
                tracker=cfg.TRACKER_CFG,
                verbose=False
            )

        except Exception:
            detect_results = self.detect_model.predict(
                frame,
                classes=[0],
                conf=0.4,
                verbose=False
            )

        boxes = detect_results[0].boxes if detect_results and len(detect_results) > 0 else None

        if boxes is None or boxes.xyxy is None:
            return detections, nearest_track, nearest_box

        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.int().cpu().tolist() if boxes.id is not None else list(range(1, len(xyxy) + 1))
        confs = boxes.conf.cpu().numpy() if boxes.conf is not None else [0.0] * len(xyxy)

        nearest_track, nearest_box = get_nearest_track(xyxy, ids, center_x, center_y)

        for box, tid, conf in zip(xyxy, ids, confs):
            detections.append({
                "id": tid,
                "box": box,
                "conf": float(conf),
                "emb_sim": None,
                "shirt_sim": None,
                "motion_sim": None,
                "score": None,
                "falling": False,
                "fall_mode": None
            })

        return detections, nearest_track, nearest_box

    # =============================
    # FIRE / SMOKE
    # =============================
    def update_fire_smoke(self, frame, annotated, now):
        if self.fire_smoke_detector is None:
            self.fire_smoke_var.set("Disabled")
            return annotated

        self.fire_frame_id += 1

        if self.fire_frame_id % FIRE_RUN_INTERVAL == 0:
            try:
                fire_detections, fire_now, smoke_now = self.fire_smoke_detector.detect(frame)

                self.last_fire_smoke_detections = fire_detections

                if fire_now:
                    self.last_fire_time = now

                if smoke_now:
                    self.last_smoke_time = now

            except Exception as exc:
                print("[FIRE/SMOKE ERROR]", exc)
                self.last_fire_smoke_detections = []

        fire_detected = (now - self.last_fire_time) <= FIRE_ALERT_HOLD_SEC
        smoke_detected = (now - self.last_smoke_time) <= FIRE_ALERT_HOLD_SEC

        if fire_detected and smoke_detected:
            self.fire_smoke_var.set("Fire + Smoke")
            self.set_status("FIRE + SMOKE", "#dc2626")

        elif fire_detected:
            self.fire_smoke_var.set("Fire")
            self.set_status("FIRE ALERT", "#dc2626")

        elif smoke_detected:
            self.fire_smoke_var.set("Smoke")
            self.set_status("SMOKE ALERT", "#f97316")

        else:
            self.fire_smoke_var.set("Normal")

        return self.draw_fire_smoke_results(
            annotated,
            self.last_fire_smoke_detections,
            fire_detected,
            smoke_detected
        )

    def draw_fire_smoke_results(self, annotated, fire_smoke_detections, fire_detected, smoke_detected):
        for det in fire_smoke_detections:
            x1, y1, x2, y2 = map(int, det["box"])
            class_name = det["class_name"]
            conf = float(det["conf"])

            if class_name == "fire":
                color = (0, 0, 255)
                label = f"FIRE {conf:.2f}"
            else:
                color = (160, 160, 160)
                label = f"SMOKE {conf:.2f}"

            cv2.rectangle(
                annotated,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            cv2.putText(
                annotated,
                label,
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2
            )

        if fire_detected and smoke_detected:
            alert_text = "CANH BAO: CO LUA VA KHOI"
            alert_color = (0, 0, 255)

        elif fire_detected:
            alert_text = "CANH BAO: CO LUA"
            alert_color = (0, 0, 255)

        elif smoke_detected:
            alert_text = "CANH BAO: CO KHOI"
            alert_color = (0, 140, 255)

        else:
            alert_text = None
            alert_color = (255, 255, 255)

        if alert_text is not None:
            cv2.putText(
                annotated,
                alert_text,
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                alert_color,
                3
            )

        return annotated

    # =============================
    # DRAW PEOPLE / FALL
    # =============================
    def draw_results(self, annotated, detections, selected_target, selected_distance_mm):
        h, _ = annotated.shape[:2]

        for det in detections:
            x1, y1, x2, y2 = map(int, det["box"])
            color = (0, 255, 255)
            text_top = None

            if selected_target is not None and det["id"] == selected_target["id"]:
                color = (0, 255, 0)

            if det["falling"]:
                color = (0, 0, 255)
                text_top = "FALL DETECTED"

            cv2.rectangle(
                annotated,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            if text_top is not None:
                cv2.putText(
                    annotated,
                    text_top,
                    (x1, max(25, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    color,
                    2
                )

            cv2.putText(
                annotated,
                f"Person ID: {det['id']}",
                (x1, max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )

        if selected_target is not None and selected_distance_mm is not None:
            x1, y1, x2, y2 = map(int, selected_target["box"])
            label = f"{selected_distance_mm / 10.0:.1f} cm"

            cv2.putText(
                annotated,
                label,
                (x1, max(25, y1 - 28)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 0),
                2
            )

        total_fall = sum(1 for det in detections if det["falling"])

        if total_fall > 0:
            cv2.putText(
                annotated,
                "CANH BAO: CO NGUOI TE NGA",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 0, 255),
                3
            )

        return annotated

    def update_fps(self):
        now = time.time()
        dt = now - self.last_time

        if dt > 0:
            current_fps = 1.0 / dt
            self.fps_value = 0.9 * self.fps_value + 0.1 * current_fps

        self.last_time = now
        self.fps_var.set(f"{self.fps_value:.1f}")

    def show_on_gui(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        video_w = self.video_label.winfo_width()
        video_h = self.video_label.winfo_height()

        if video_w <= 10 or video_h <= 10:
            video_w, video_h = 800, 500

        img_w, img_h = img.size
        scale = min(video_w / img_w, video_h / img_h)

        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        frame_rgb = cv2.resize(frame_rgb, (new_w, new_h))
        img = Image.fromarray(frame_rgb)

        canvas = Image.new("RGB", (video_w, video_h), (2, 6, 23))
        left = (video_w - new_w) // 2
        top = (video_h - new_h) // 2
        canvas.paste(img, (left, top))

        imgtk = ImageTk.PhotoImage(image=canvas)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def quit_app(self):
        self.running = False

        try:
            if self.camera is not None:
                self.camera.stop()
        except Exception:
            pass

        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    app = AstraPeopleFollowingGUI(app_root)
    app_root.mainloop()