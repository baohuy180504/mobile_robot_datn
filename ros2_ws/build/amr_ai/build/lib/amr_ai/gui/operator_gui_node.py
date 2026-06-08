#!/usr/bin/env python3

import os
import subprocess
import threading
import time
from typing import Optional

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

import tkinter as tk
from PIL import Image as PILImage
from PIL import ImageTk

from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist

from amr_interfaces.msg import AiMode, PersonTarget, AiAlert
from amr_interfaces.srv import SetAiMode, SelectZone


class OperatorGuiNode(Node):
    def __init__(self):
        super().__init__('operator_gui_node')

        self.declare_parameter('debug_image_topic', '/amr_ai/debug/person_tracker/image')
        self.declare_parameter('mode_topic', '/amr_ai/mode')
        self.declare_parameter('person_target_topic', '/amr_ai/person_target')
        self.declare_parameter('alert_topic', '/amr_ai/alert')
        self.declare_parameter('alert_image_topic', '/amr_ai/debug/alert/image')
        self.declare_parameter('alert_hold_sec', 3.0)

        self.declare_parameter(
            'start_script',
            '/home/huyjetson/mobile_robot/ros2_ws/scripts/start_amr_operator_stack.sh'
        )
        self.declare_parameter(
            'stop_script',
            '/home/huyjetson/mobile_robot/ros2_ws/scripts/stop_amr_operator_stack.sh'
        )

        self.debug_image_topic = self.get_parameter('debug_image_topic').value
        self.mode_topic = self.get_parameter('mode_topic').value
        self.person_target_topic = self.get_parameter('person_target_topic').value
        self.alert_topic = self.get_parameter('alert_topic').value
        self.alert_image_topic = self.get_parameter('alert_image_topic').value
        self.alert_hold_sec = float(self.get_parameter('alert_hold_sec').value)

        self.start_script = self.get_parameter('start_script').value
        self.stop_script = self.get_parameter('stop_script').value

        self.bridge = CvBridge()
        self.lock = threading.Lock()

        # Ảnh debug follow: chỉ dùng để hiển thị khi mode FOLLOW_DETECTING/FOLLOW_ACTIVE.
        self.latest_frame = None
        self.latest_frame_time = 0.0

        # Ảnh debug cảnh báo: chỉ ưu tiên hiển thị khi có alert active.
        self.latest_alert_frame = None
        self.latest_alert_frame_time = 0.0

        self.latest_alert_type = 'NORMAL'
        self.latest_alert_message = 'No AI alert'
        self.latest_alert_confidence = 0.0
        self.latest_alert_active = False
        self.latest_alert_time = 0.0

        self.current_mode = AiMode.IDLE
        self.current_mode_name = 'IDLE'
        self.target_locked = False
        self.target_lost = False

        self.status_text = 'READY'
        self.status_color = '#0ea5e9'
        self.follow_button_text = 'FOLLOW'
        self.follow_button_color = '#ffff00'

        self.image_sub = self.create_subscription(
            Image,
            self.debug_image_topic,
            self.image_callback,
            qos_profile_sensor_data
        )

        self.mode_sub = self.create_subscription(
            AiMode,
            self.mode_topic,
            self.mode_callback,
            10
        )

        self.target_sub = self.create_subscription(
            PersonTarget,
            self.person_target_topic,
            self.target_callback,
            10
        )

        self.alert_sub = self.create_subscription(
            AiAlert,
            self.alert_topic,
            self.alert_callback,
            10
        )

        self.alert_image_sub = self.create_subscription(
            Image,
            self.alert_image_topic,
            self.alert_image_callback,
            qos_profile_sensor_data
        )

        self.set_mode_client = self.create_client(SetAiMode, '/amr_ai/set_mode')
        self.select_zone_client = self.create_client(SelectZone, '/amr_ai/select_zone')

        self.cmd_vel_safe_pub = self.create_publisher(Twist, '/cmd_vel_safe', 10)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.get_logger().warn('Operator GUI node started')

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().warn(f'Failed to convert follow debug image: {exc}')
            return

        with self.lock:
            self.latest_frame = frame
            self.latest_frame_time = time.time()

    def alert_image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().warn(f'Failed to convert alert debug image: {exc}')
            return

        with self.lock:
            self.latest_alert_frame = frame
            self.latest_alert_frame_time = time.time()

    def alert_callback(self, msg: AiAlert):
        alert_type = str(msg.alert_type).strip().upper()
        now = time.time()

        with self.lock:
            if msg.active and alert_type not in ['', 'NORMAL']:
                self.latest_alert_type = alert_type
                self.latest_alert_message = str(msg.message).strip()
                self.latest_alert_confidence = float(msg.confidence)
                self.latest_alert_active = True
                self.latest_alert_time = now
            elif alert_type == 'NORMAL' and (now - self.latest_alert_time) > self.alert_hold_sec:
                self.latest_alert_active = False

    def mode_callback(self, msg: AiMode):
        mode = int(msg.mode)

        with self.lock:
            self.current_mode = mode
            self.current_mode_name = str(msg.mode_name) if msg.mode_name else self.mode_to_name(mode)

            if mode == AiMode.IDLE:
                self.follow_button_text = 'FOLLOW'
                self.follow_button_color = '#ffff00'
                self.status_text = 'NAV READY'
                self.status_color = '#0ea5e9'
            elif mode == AiMode.FOLLOW_ACTIVE:
                self.follow_button_text = 'FOLLOWING'
                self.follow_button_color = '#22c55e'
                self.status_text = 'FOLLOWING'
                self.status_color = '#16a34a'
            elif mode == AiMode.FOLLOW_DETECTING:
                self.follow_button_text = 'DETECTING'
                self.follow_button_color = '#facc15'
                self.status_text = 'DETECTING TARGET'
                self.status_color = '#f59e0b'
            elif mode == AiMode.FOLLOW_STOPPED:
                self.follow_button_text = 'FOLLOW'
                self.follow_button_color = '#ffff00'
                self.status_text = 'FOLLOW STOPPED'
                self.status_color = '#f97316'
            elif mode in [AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE]:
                self.follow_button_text = 'FOLLOW'
                self.follow_button_color = '#ffff00'
                self.status_text = 'NAVIGATION'
                self.status_color = '#2563eb'
            elif mode == AiMode.EMERGENCY_STOP:
                self.follow_button_text = 'FOLLOW'
                self.follow_button_color = '#ffff00'
                self.status_text = 'EMERGENCY STOP'
                self.status_color = '#dc2626'

    def target_callback(self, msg: PersonTarget):
        with self.lock:
            self.target_locked = bool(msg.locked)
            self.target_lost = bool(msg.lost)

    @staticmethod
    def mode_to_name(mode: int) -> str:
        mapping = {
            AiMode.IDLE: 'IDLE',
            AiMode.NAV_TO_ZONE: 'NAV_TO_ZONE',
            AiMode.FOLLOW_DETECTING: 'FOLLOW_DETECTING',
            AiMode.FOLLOW_ACTIVE: 'FOLLOW_ACTIVE',
            AiMode.FOLLOW_STOPPED: 'FOLLOW_STOPPED',
            AiMode.RETURN_TO_ZONE: 'RETURN_TO_ZONE',
            AiMode.EMERGENCY_STOP: 'EMERGENCY_STOP',
        }
        return mapping.get(mode, f'MODE_{mode}')

    def set_status(self, text: str, color: str):
        with self.lock:
            self.status_text = text
            self.status_color = color

    def run_script(self, script_path: str, label: str):
        script = os.path.expanduser(script_path)

        if not os.path.exists(script):
            self.set_status(f'{label} SCRIPT NOT FOUND', '#dc2626')
            self.get_logger().error(f'{label} script not found: {script}')
            return

        log_file = f'/tmp/amr_operator_{label.lower()}.log'

        try:
            with open(log_file, 'a') as log:
                subprocess.Popen(
                    ['bash', script],
                    stdout=log,
                    stderr=log,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )

            self.set_status(label, '#0ea5e9')
            self.get_logger().warn(f'Run script: {script}, log={log_file}')

        except Exception as exc:
            self.set_status(f'{label} ERROR', '#dc2626')
            self.get_logger().error(f'Failed to run {script}: {exc}')

    def start_stack(self):
        self.run_script(self.start_script, 'STARTING')

    def stop_stack(self):
        self.publish_zero_velocity()
        self.call_set_mode('STOP_FOLLOW')
        self.run_script(self.stop_script, 'STOPPING')

    def publish_zero_velocity(self):
        msg = Twist()
        for _ in range(3):
            self.cmd_vel_safe_pub.publish(msg)
            self.cmd_vel_pub.publish(msg)
            time.sleep(0.03)

    def toggle_follow(self):
        with self.lock:
            mode = self.current_mode

        self.get_logger().warn(
            f'FOLLOW button pressed. current_mode={mode} ({self.mode_to_name(mode)})'
        )

        if mode in [AiMode.FOLLOW_DETECTING, AiMode.FOLLOW_ACTIVE]:
            self.set_status('SEND STOP FOLLOW', '#f97316')
            self.call_set_mode('STOP_FOLLOW')
        else:
            self.set_status('SEND START FOLLOW', '#f59e0b')
            self.call_set_mode('START_FOLLOW')

    def call_set_mode(self, command: str):
        self.get_logger().warn(f'Calling /amr_ai/set_mode command={command}')

        # 0.3s hơi ngắn khi Nav2/AI vừa khởi động. Dùng 2s để nút FOLLOW ổn định hơn.
        if not self.set_mode_client.wait_for_service(timeout_sec=2.0):
            self.set_status('SET_MODE NOT READY', '#dc2626')
            self.get_logger().error('/amr_ai/set_mode service not ready')
            return

        req = SetAiMode.Request()
        req.mode = 0
        req.command = command

        future = self.set_mode_client.call_async(req)
        future.add_done_callback(lambda fut: self.set_mode_done(fut, command))

    def set_mode_done(self, future, command: str):
        try:
            res = future.result()
            self.get_logger().warn(
                f'set_mode response: command={command}, success={res.success}, '
                f'message={res.message}, current_mode={res.current_mode}'
            )

            if res.success:
                if command == 'START_FOLLOW':
                    self.set_status('FOLLOW STARTED', '#16a34a')
                elif command == 'STOP_FOLLOW':
                    self.set_status('FOLLOW STOPPED', '#f97316')
                else:
                    self.set_status('MODE OK', '#16a34a')
            else:
                # Hiển thị lý do reject để công nhân/kỹ sư biết ngay.
                msg = str(res.message).strip()
                self.set_status(msg[:28] if msg else 'MODE REJECTED', '#dc2626')
        except Exception as exc:
            self.set_status('MODE ERROR', '#dc2626')
            self.get_logger().error(f'set_mode failed: {exc}')

    def select_zone(self, zone: str):
        with self.lock:
            mode = self.current_mode

        if mode in [AiMode.FOLLOW_DETECTING, AiMode.FOLLOW_ACTIVE]:
            self.set_status('STOP FOLLOW FIRST', '#f97316')
            return

        if not self.select_zone_client.wait_for_service(timeout_sec=1.0):
            self.set_status('SELECT_ZONE NOT READY', '#dc2626')
            return

        req = SelectZone.Request()
        req.zone_name = zone

        future = self.select_zone_client.call_async(req)
        future.add_done_callback(lambda fut: self.select_zone_done(fut, zone))

    def select_zone_done(self, future, zone: str):
        try:
            res = future.result()
            if res.accepted:
                self.set_status(f'GO TO {zone}', '#2563eb')
            else:
                self.set_status(f'{zone} REJECTED', '#dc2626')
        except Exception as exc:
            self.set_status('ZONE ERROR', '#dc2626')
            self.get_logger().error(f'select_zone failed: {exc}')


    def get_active_alert_snapshot(self):
        with self.lock:
            age = time.time() - self.latest_alert_time

            if not self.latest_alert_active or age > self.alert_hold_sec:
                return None

            return {
                'type': self.latest_alert_type,
                'message': self.latest_alert_message,
                'confidence': self.latest_alert_confidence,
                'age': age,
            }


class OperatorGuiApp:
    def __init__(self, node: OperatorGuiNode):
        self.node = node

        self.root = tk.Tk()
        self.root.title('AMR Operator')
        self.root.configure(bg='#f8fafc')

        # 7 inch screen: 1024x600
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # Màn hình 7 inch 1024x600, nhưng lấy theo kích thước thật để tránh lệch layout
        self.root.geometry(f'{self.screen_w}x{self.screen_h}+0+0')
        self.root.minsize(800, 480)
        self.root.resizable(False, False)

        # Mở full màn hình ngay khi chạy
        self.is_fullscreen = True
        self.root.attributes('-fullscreen', True)

        # Phím tắt fullscreen
        self.root.bind('<F11>', self.toggle_fullscreen_event)
        self.root.bind('<Escape>', self.exit_fullscreen_event)

        self.font_big = ('Arial', 22, 'bold')
        self.font_mid = ('Arial', 18, 'bold')
        self.font_small = ('Arial', 13, 'bold')

        self.photo = None

        self.build_ui()
        self.update_ui_loop()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def build_ui(self):
        # Nút fullscreen / thoát fullscreen góc trên phải
        self.fullscreen_btn = tk.Button(
            self.root,
            text='🗗',
            command=self.toggle_fullscreen,
            bg='#e5e7eb',
            fg='#111827',
            activebackground='#d1d5db',
            activeforeground='#111827',
            relief='solid',
            bd=1,
            font=('Arial', 13, 'bold'),
            cursor='hand2'
        )

        self.outer = tk.Frame(
            self.root,
            bg='#ffffff',
            highlightthickness=5,
            highlightbackground='#000000'
        )

        # Left image panel
        self.left = tk.Frame(
            self.outer,
            bg='#ffffff',
            highlightthickness=3,
            highlightbackground='#1e3a5f'
        )

        self.image_label = tk.Label(
            self.left,
            bg='#ffffff',
            text='No Image',
            fg='#111827',
            font=('Arial', 20)
        )
        self.image_label.pack(fill='both', expand=True)

        # Right control panel
        self.right = tk.Frame(
            self.outer,
            bg='#ffffff',
            highlightthickness=3,
            highlightbackground='#1e3a5f'
        )

        self.start_btn = self.make_button(
            self.right,
            'START',
            '#00b050',
            self.node.start_stack
        )

        self.stop_btn = self.make_button(
            self.right,
            'STOP',
            '#ff0000',
            self.node.stop_stack
        )

        self.zone_a_btn = self.make_button(
            self.right,
            'WP1',
            '#4472c4',
            lambda: self.node.select_zone('WP1')
        )

        self.zone_b_btn = self.make_button(
            self.right,
            'WP2',
            '#4472c4',
            lambda: self.node.select_zone('WP2')
        )

        self.zone_h_btn = self.make_button(
            self.right,
            'HOME',
            '#4472c4',
            lambda: self.node.select_zone('WP0')
        )

        self.follow_btn = self.make_button(
            self.right,
            'FOLLOW',
            '#ffff00',
            self.node.toggle_follow,
            fg='#000000'
        )

        self.status_label = tk.Label(
            self.outer,
            text='READY',
            bg='#0ea5e9',
            fg='white',
            font=self.font_small,
            anchor='center'
        )

        self.layout_widgets()

    def layout_widgets(self):
        # Lấy kích thước hiện tại của màn hình/cửa sổ
        if self.is_fullscreen:
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()
        else:
            w = 1024
            h = 600

        # Nút fullscreen nhỏ ở góc trên phải
        self.fullscreen_btn.place(
            x=w - 48,
            y=8,
            width=34,
            height=28
        )

        # Khung ngoài
        margin_x = 28
        margin_y = 28

        outer_w = w - 2 * margin_x
        outer_h = h - 2 * margin_y

        self.outer.place(
            x=margin_x,
            y=margin_y,
            width=outer_w,
            height=outer_h
        )

        # Layout bên trong khung ngoài
        pad_x = 42
        pad_top = 55
        gap = 55
        status_h = 38
        status_gap = 20

        content_h = outer_h - pad_top - status_h - status_gap - 35

        # Chia trái/phải cân hơn cho màn 1024x600
        left_w = int((outer_w - 2 * pad_x - gap) * 0.44)
        right_w = outer_w - 2 * pad_x - gap - left_w

        left_x = pad_x
        right_x = pad_x + left_w + gap

        self.left.place(
            x=left_x,
            y=pad_top,
            width=left_w,
            height=content_h
        )

        self.right.place(
            x=right_x,
            y=pad_top,
            width=right_w,
            height=content_h
        )

        self.status_label.place(
            x=pad_x,
            y=outer_h - status_h - 22,
            width=outer_w - 2 * pad_x,
            height=status_h
        )

        # Bố trí nút trong panel phải
        rp_w = right_w
        rp_h = content_h

        btn_h = 58
        top_y = 42

        start_w = int(rp_w * 0.40)
        stop_w = int(rp_w * 0.40)
        btn_gap = int(rp_w * 0.08)

        self.start_btn.place(
            x=int(rp_w * 0.07),
            y=top_y,
            width=start_w,
            height=btn_h
        )

        self.stop_btn.place(
            x=int(rp_w * 0.07) + start_w + btn_gap,
            y=top_y,
            width=stop_w,
            height=btn_h
        )

        zone_y = int(rp_h * 0.42)
        zone_h = 56
        zone_w = int(rp_w * 0.24)
        zone_gap = int(rp_w * 0.08)

        self.zone_a_btn.place(
            x=int(rp_w * 0.07),
            y=zone_y,
            width=zone_w,
            height=zone_h
        )

        self.zone_b_btn.place(
            x=int(rp_w * 0.07) + zone_w + zone_gap,
            y=zone_y,
            width=zone_w,
            height=zone_h
        )

        self.zone_h_btn.place(
            x=int(rp_w * 0.07) + 2 * (zone_w + zone_gap),
            y=zone_y,
            width=zone_w,
            height=zone_h
        )

        follow_w = int(rp_w * 0.42)
        follow_h = 60

        self.follow_btn.place(
            x=int((rp_w - follow_w) / 2),
            y=int(rp_h * 0.72),
            width=follow_w,
            height=follow_h
        )

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes('-fullscreen', self.is_fullscreen)

        if self.is_fullscreen:
            self.root.geometry(f'{self.screen_w}x{self.screen_h}+0+0')
            self.fullscreen_btn.configure(text='🗗')
        else:
            self.root.geometry('1024x600+0+0')
            self.fullscreen_btn.configure(text='⛶')

        self.root.after(100, self.layout_widgets)

    def toggle_fullscreen_event(self, event=None):
        self.toggle_fullscreen()

    def exit_fullscreen_event(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes('-fullscreen', False)
            self.root.geometry('1024x600+0+0')
            self.fullscreen_btn.configure(text='⛶')
            self.root.after(100, self.layout_widgets)


    def make_button(self, parent, text, color, command, fg='#000000'):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg=fg,
            activebackground=color,
            activeforeground=fg,
            relief='solid',
            bd=1,
            font=self.font_big,
            cursor='hand2'
        )
        return btn

    def update_ui_loop(self):
        self.update_status()
        self.update_image()
        self.root.after(100, self.update_ui_loop)

    def update_status(self):
        with self.node.lock:
            status_text = self.node.status_text
            status_color = self.node.status_color
            follow_text = self.node.follow_button_text
            follow_color = self.node.follow_button_color
            mode = self.node.current_mode
            alert_active = self.node.latest_alert_active
            alert_age = time.time() - self.node.latest_alert_time
            alert_type = self.node.latest_alert_type
            alert_message = self.node.latest_alert_message
            alert_conf = self.node.latest_alert_confidence

        if alert_active and alert_age <= self.node.alert_hold_sec:
            alert_text, alert_color = self.format_alert_status(
                alert_type,
                alert_message,
                alert_conf
            )
            self.status_label.configure(text=alert_text, bg=alert_color)
        else:
            self.status_label.configure(text=status_text, bg=status_color)

        self.follow_btn.configure(text=follow_text, bg=follow_color, activebackground=follow_color)

        # Disable zone buttons while following/detecting
        zone_enabled = mode not in [AiMode.FOLLOW_DETECTING, AiMode.FOLLOW_ACTIVE]
        state = tk.NORMAL if zone_enabled else tk.DISABLED

        for btn in [self.zone_a_btn, self.zone_b_btn, self.zone_h_btn]:
            btn.configure(state=state)

    def format_alert_status(self, alert_type: str, alert_message: str, alert_conf: float):
        alert_type = str(alert_type).upper()

        if alert_type == 'FALL':
            text = 'CANH BAO: TE NGA'
            color = '#dc2626'
        elif alert_type == 'FIRE':
            text = 'CANH BAO: LUA'
            color = '#dc2626'
        elif alert_type == 'SMOKE':
            text = 'CANH BAO: KHOI'
            color = '#f97316'
        else:
            text = f'CANH BAO: {alert_type}'
            color = '#dc2626'

        if alert_conf > 0.0:
            text = f'{text} {alert_conf:.2f}'

        if alert_message:
            msg = alert_message[:32]
            text = f'{text} - {msg}'

        return text, color

    def update_image(self):
        with self.node.lock:
            mode = self.node.current_mode

            follow_frame = None if self.node.latest_frame is None else self.node.latest_frame.copy()
            follow_age = time.time() - self.node.latest_frame_time

            alert_frame = None if self.node.latest_alert_frame is None else self.node.latest_alert_frame.copy()
            alert_frame_age = time.time() - self.node.latest_alert_frame_time

            alert_active = self.node.latest_alert_active
            alert_age = time.time() - self.node.latest_alert_time
            alert_type = self.node.latest_alert_type
            alert_message = self.node.latest_alert_message
            alert_conf = self.node.latest_alert_confidence

        # Ưu tiên cao nhất: cảnh báo sự cố. AI detector chạy nền trong Navigation.
        if alert_active and alert_age <= self.node.alert_hold_sec:
            if alert_frame is not None and alert_frame_age <= 2.0:
                self.show_frame(alert_frame)
            else:
                self.show_alert_screen(alert_type, alert_message, alert_conf)
            return

        # Chỉ hiển thị camera follow khi công nhân đã nhấn FOLLOW.
        if mode in [AiMode.FOLLOW_DETECTING, AiMode.FOLLOW_ACTIVE]:
            if follow_frame is None or follow_age > 2.0:
                self.show_message(
                    'FOLLOW CAMERA\nWAITING IMAGE',
                    bg='#ffffff',
                    fg='#111827',
                    font=('Arial', 22, 'bold')
                )
                return

            self.show_frame(follow_frame)
            return

        # Navigation bình thường: không hiện camera AI để tránh gây rối cho công nhân.
        self.show_navigation_screen(mode)

    def show_frame(self, frame):
        # Sửa hướng hiển thị trái/phải cho màn hình công nhân
        frame = cv2.flip(frame, 1)

        # Convert BGR to RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PILImage.fromarray(rgb)

        box_w = max(1, self.image_label.winfo_width())
        box_h = max(1, self.image_label.winfo_height())

        if box_w <= 5 or box_h <= 5:
            box_w, box_h = 374, 389

        img_w, img_h = img.size
        scale = min(box_w / img_w, box_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        img = img.resize((new_w, new_h))

        canvas = PILImage.new('RGB', (box_w, box_h), (255, 255, 255))
        left = (box_w - new_w) // 2
        top = (box_h - new_h) // 2
        canvas.paste(img, (left, top))

        self.photo = ImageTk.PhotoImage(canvas)
        self.image_label.configure(image=self.photo, text='', bg='#ffffff')

    def show_navigation_screen(self, mode: int):
        if mode in [AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE]:
            text = 'NAVIGATION\nRUNNING'
        elif mode == AiMode.FOLLOW_STOPPED:
            text = 'FOLLOW STOPPED\nSELECT WP/HOME'
        elif mode == AiMode.EMERGENCY_STOP:
            text = 'EMERGENCY STOP'
        else:
            text = 'NAVIGATION READY\nHOME POSE SET'

        self.show_message(
            text,
            bg='#ffffff',
            fg='#111827',
            font=('Arial', 24, 'bold')
        )

    def show_alert_screen(self, alert_type: str, alert_message: str, alert_conf: float):
        alert_type = str(alert_type).upper()

        if alert_type == 'FALL':
            main_text = 'CANH BAO\nTE NGA'
            bg = '#fee2e2'
            fg = '#991b1b'
        elif alert_type == 'FIRE':
            main_text = 'CANH BAO\nCO LUA'
            bg = '#fee2e2'
            fg = '#991b1b'
        elif alert_type == 'SMOKE':
            main_text = 'CANH BAO\nCO KHOI'
            bg = '#ffedd5'
            fg = '#9a3412'
        else:
            main_text = f'CANH BAO\n{alert_type}'
            bg = '#fee2e2'
            fg = '#991b1b'

        if alert_conf > 0.0:
            main_text += f'\nCONF {alert_conf:.2f}'

        if alert_message:
            main_text += f'\n{alert_message[:36]}'

        self.show_message(
            main_text,
            bg=bg,
            fg=fg,
            font=('Arial', 24, 'bold')
        )

    def show_message(self, text: str, bg: str, fg: str, font):
        self.image_label.configure(
            image='',
            text=text,
            bg=bg,
            fg=fg,
            font=font,
            justify='center'
        )
        self.photo = None

    def show_no_image(self):
        self.show_message(
            'No Image',
            bg='#ffffff',
            fg='#111827',
            font=('Arial', 22)
        )

    def on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main(args=None):
    rclpy.init(args=args)
    node = OperatorGuiNode()

    executor_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    executor_thread.start()

    app = OperatorGuiApp(node)
    try:
        app.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
