#!/usr/bin/env python3
"""
web_teleop_gui.py — GUI nhỏ trên màn hình xe khi chạy web teleop.

Hiển thị QR code để người vận hành dùng điện thoại quét vào
địa chỉ web điều khiển khẩn cấp (web_control.py, port 8090).

Chạy từ run_web_teleop.sh sau khi web_teleop_node.py đã được khởi
động ở background. Nhận PID của teleop node qua --teleop-pid để
dừng đúng process khi nhấn STOP.

Phụ thuộc: tkinter (python3-tk), qrcode, Pillow (PIL)
"""

import argparse
import os
import signal
import socket
import sys
import tkinter as tk
from tkinter import font as tkfont

# Import qrcode và PIL — báo lỗi rõ ràng nếu thiếu thư viện
try:
    import qrcode
    from PIL import Image, ImageTk
except ImportError as _err:
    print(
        f"[web_teleop_gui] Thiếu thư viện: {_err}\n"
        "Cài đặt bằng: pip install qrcode[pil] Pillow",
        file=sys.stderr,
    )
    sys.exit(1)

# ==========================================================
# Cấu hình
# ==========================================================
CONTROL_PORT = 8090          # Port của web_control.py
QR_LIFETIME_S = 30           # QR tự xóa sau n giây
WINDOW_TITLE = "AMR Emergency Control"

# Màu sắc — dark theme khớp với webserver
COLOR_BG = "#0f172a"
COLOR_PANEL = "#1e293b"
COLOR_BORDER = "#334155"
COLOR_GREEN = "#16a34a"
COLOR_GREEN_HOVER = "#15803d"
COLOR_RED = "#dc2626"
COLOR_RED_HOVER = "#b91c1c"
COLOR_TEXT = "#e5e7eb"
COLOR_MUTED = "#64748b"
COLOR_YELLOW = "#facc15"


# ==========================================================
# Helpers
# ==========================================================
def get_local_ip() -> str:
    """Lấy IP của interface kết nối mạng (không phải 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def make_qr_photo(url: str, size: int = 260) -> ImageTk.PhotoImage:
    """Tạo QR code trong bộ nhớ, trả về PhotoImage cho tkinter."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def kill_pid_gracefully(pid: int) -> None:
    """Gửi SIGTERM cho process, bỏ qua nếu đã dừng."""
    if pid <= 0:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    except Exception as exc:
        print(f"[web_teleop_gui] Kill PID {pid}: {exc}", file=sys.stderr)


# ==========================================================
# GUI
# ==========================================================
class TeleopGui:
    QR_SIZE = 260   # pixel, kích thước ảnh QR trong khung

    def __init__(self, root: tk.Tk, teleop_pid: int) -> None:
        self.root = root
        self.teleop_pid = teleop_pid

        # Timer handles (after ID)
        self._qr_clear_timer = None
        self._countdown_timer = None
        self._countdown_left = 0

        # Giữ reference ảnh để tránh bị garbage-collected
        self._qr_photo: ImageTk.PhotoImage | None = None

        self._build_window()
        self._build_ui()
        # Canh giữa SAU khi UI đã build xong —
        # lúc này tkinter mới biết kích thước thực tế cần thiết.
        self._center_window()

    # ----------------------------------------------------------
    # Window setup
    # ----------------------------------------------------------
    def _build_window(self) -> None:
        self.root.title(WINDOW_TITLE)
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_stop)
        # Không đặt geometry ở đây — sẽ canh giữa sau khi _build_ui() xong
        # để tkinter tự tính đúng kích thước cần thiết.

    def _center_window(self) -> None:
        """Canh giữa màn hình dựa trên kích thước thực tế của content."""
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        # Chỉ đặt vị trí, không ép kích thước — để tkinter giữ đúng auto-size
        self.root.geometry(f"+{x}+{y}")

    # ----------------------------------------------------------
    # Widget layout
    # ----------------------------------------------------------
    def _build_ui(self) -> None:
        pad = 14

        # ── Tiêu đề nhỏ ──────────────────────────────────────
        title_lbl = tk.Label(
            self.root,
            text="⚠  ĐIỀU KHIỂN KHẨN CẤP",
            bg=COLOR_BG,
            fg=COLOR_RED,
            font=("Arial", 12, "bold"),
        )
        title_lbl.pack(pady=(pad, 4))

        # ── Khung hiển thị QR ────────────────────────────────
        qr_frame = tk.Frame(
            self.root,
            bg=COLOR_PANEL,
            bd=1,
            relief="flat",
            width=self.QR_SIZE + 20,
            height=self.QR_SIZE + 20,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
        )
        qr_frame.pack(padx=pad, pady=(4, 0))
        qr_frame.pack_propagate(False)

        self.qr_label = tk.Label(
            qr_frame,
            text="Nhấn  QR CODE\nđể tạo mã quét",
            bg=COLOR_PANEL,
            fg=COLOR_MUTED,
            font=("Arial", 13),
            justify="center",
        )
        self.qr_label.place(relx=0.5, rely=0.5, anchor="center")

        # ── Đếm ngược ────────────────────────────────────────
        self.countdown_var = tk.StringVar(value="")
        countdown_lbl = tk.Label(
            self.root,
            textvariable=self.countdown_var,
            bg=COLOR_BG,
            fg=COLOR_YELLOW,
            font=("Arial", 11),
        )
        countdown_lbl.pack(pady=(6, 0))

        # ── URL hiển thị ──────────────────────────────────────
        self.url_var = tk.StringVar(value="")
        url_lbl = tk.Label(
            self.root,
            textvariable=self.url_var,
            bg=COLOR_BG,
            fg=COLOR_MUTED,
            font=("Arial", 9),
        )
        url_lbl.pack()

        # ── Nút bấm ──────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=COLOR_BG)
        btn_frame.pack(padx=pad, pady=(10, pad), fill="x")

        self.qr_btn = self._make_button(
            btn_frame,
            text="QR CODE",
            bg=COLOR_GREEN,
            active_bg=COLOR_GREEN_HOVER,
            command=self._on_qr,
        )
        self.qr_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        stop_btn = self._make_button(
            btn_frame,
            text="STOP",
            bg=COLOR_RED,
            active_bg=COLOR_RED_HOVER,
            command=self._on_stop,
        )
        stop_btn.pack(side="left", fill="x", expand=True)

    def _make_button(
        self,
        parent,
        text: str,
        bg: str,
        active_bg: str,
        command,
    ) -> tk.Button:
        btn = tk.Button(
            parent,
            text=text,
            bg=bg,
            fg=COLOR_TEXT,
            activebackground=active_bg,
            activeforeground=COLOR_TEXT,
            font=("Arial", 13, "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=11,
            cursor="hand2",
            command=command,
        )
        # Hover effect
        btn.bind("<Enter>", lambda _e, b=btn, c=active_bg: b.configure(bg=c))
        btn.bind("<Leave>", lambda _e, b=btn, c=bg: b.configure(bg=c))
        return btn

    # ----------------------------------------------------------
    # Xử lý nút QR CODE
    # ----------------------------------------------------------
    def _on_qr(self) -> None:
        """Tạo QR trỏ vào web_control.py, hiển thị 30s rồi tự xóa."""
        self._cancel_timers()

        ip = get_local_ip()
        url = f"http://{ip}:{CONTROL_PORT}/login?next=%2F"

        # Đổi nhãn nút thành trạng thái đang tạo
        self.qr_btn.configure(text="Đang tạo...", state="disabled")
        self.root.update_idletasks()

        try:
            photo = make_qr_photo(url, size=self.QR_SIZE)
        except Exception as exc:
            self._show_placeholder(f"Lỗi tạo QR:\n{exc}", color=COLOR_RED)
            self.qr_btn.configure(text="QR CODE", state="normal")
            self.url_var.set("")
            return
        finally:
            self.qr_btn.configure(text="QR CODE", state="normal")

        # Hiển thị QR
        self._qr_photo = photo
        self.qr_label.configure(image=photo, text="", bg=COLOR_PANEL)
        self.qr_label.image = photo    # giữ reference
        self.url_var.set(url)

        # Bắt đầu đếm ngược
        self._countdown_left = QR_LIFETIME_S
        self._tick_countdown()

        # Hẹn giờ xóa QR
        self._qr_clear_timer = self.root.after(
            QR_LIFETIME_S * 1000, self._clear_qr
        )

    # ----------------------------------------------------------
    # Đếm ngược
    # ----------------------------------------------------------
    def _tick_countdown(self) -> None:
        if self._countdown_left <= 0:
            return
        self.countdown_var.set(f"QR hết hạn sau: {self._countdown_left}s")
        self._countdown_left -= 1
        self._countdown_timer = self.root.after(1000, self._tick_countdown)

    # ----------------------------------------------------------
    # Xóa QR sau khi hết hạn
    # ----------------------------------------------------------
    def _clear_qr(self) -> None:
        self._cancel_timers()
        self._qr_photo = None
        self.qr_label.image = None
        self._show_placeholder("QR đã hết hạn.\nNhấn  QR CODE  để lấy lại.")
        self.countdown_var.set("")
        self.url_var.set("")

    def _show_placeholder(self, text: str, color: str = COLOR_MUTED) -> None:
        self.qr_label.configure(image="", text=text, fg=color, bg=COLOR_PANEL)

    # ----------------------------------------------------------
    # Hủy timer
    # ----------------------------------------------------------
    def _cancel_timers(self) -> None:
        if self._qr_clear_timer is not None:
            self.root.after_cancel(self._qr_clear_timer)
            self._qr_clear_timer = None
        if self._countdown_timer is not None:
            self.root.after_cancel(self._countdown_timer)
            self._countdown_timer = None
        self.countdown_var.set("")

    # ----------------------------------------------------------
    # Nút STOP
    # ----------------------------------------------------------
    def _on_stop(self) -> None:
        """Dừng web_teleop_node.py và đóng cửa sổ."""
        self._cancel_timers()
        kill_pid_gracefully(self.teleop_pid)
        self.root.destroy()


# ==========================================================
# Entry point
# ==========================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="AMR Web Teleop — GUI QR trên màn hình xe"
    )
    parser.add_argument(
        "--teleop-pid",
        type=int,
        default=0,
        metavar="PID",
        help="PID của web_teleop_node.py để dừng khi nhấn STOP",
    )
    args = parser.parse_args()

    # Kiểm tra DISPLAY — nếu không có thì không thể hiển thị GUI
    if not os.environ.get("DISPLAY") and sys.platform != "win32":
        print(
            "[web_teleop_gui] Không tìm thấy biến DISPLAY.\n"
            "Thiếu màn hình hoặc chưa export DISPLAY. "
            "Bỏ qua GUI, teleop node tiếp tục chạy bình thường.",
            file=sys.stderr,
        )
        # Không exit — teleop node vẫn đang chạy ở background
        return

    root = tk.Tk()
    _app = TeleopGui(root, teleop_pid=args.teleop_pid)
    root.mainloop()


if __name__ == "__main__":
    main()