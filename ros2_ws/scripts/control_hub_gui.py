#!/usr/bin/env python3
"""
control_hub_gui.py — Giao diện nhỏ trên màn hình xe cho AMR Control Hub.

Hiển thị địa chỉ IP:port của engineer webserver và nút STOP để dừng
toàn bộ: webserver + các tmux session AMR đang chạy.

Chạy từ run_engineer_web.sh sau khi engineer_web_server đã được khởi
động ở background. Nhận PID của server qua --server-pid.

Phụ thuộc: tkinter (python3-tk) — thư viện chuẩn, không cần cài thêm.
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import tkinter as tk

# ==========================================================
# Cấu hình
# ==========================================================
WEB_PORT = 8080

# Các tmux session AMR cần dừng khi nhấn STOP
AMR_TMUX_SESSIONS = [
    "amr_operator",
    "amr_navigation",
    "amr_device",
    "amr_slam",
    "amr_web_rosbridge",
    "amr_web_teleop",
    "amr_manual_override_hb",
]

# Màu sắc — dark theme khớp với engineer webserver
COLOR_BG      = "#0f172a"
COLOR_PANEL   = "#1e293b"
COLOR_BORDER  = "#334155"
COLOR_BLUE    = "#3b82f6"
COLOR_BLUE_H  = "#2563eb"
COLOR_RED     = "#dc2626"
COLOR_RED_H   = "#b91c1c"
COLOR_TEXT    = "#e5e7eb"
COLOR_MUTED   = "#64748b"
COLOR_GREEN   = "#22c55e"
COLOR_YELLOW  = "#facc15"


# ==========================================================
# Helpers
# ==========================================================
def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    except Exception as exc:
        print(f"[control_hub_gui] Kill PID {pid}: {exc}", file=sys.stderr)


def kill_tmux_sessions() -> list[str]:
    """Dừng tất cả tmux session AMR, trả về danh sách đã kill."""
    killed = []
    for name in AMR_TMUX_SESSIONS:
        try:
            ret = subprocess.run(
                ["tmux", "has-session", "-t", name],
                capture_output=True,
            )
            if ret.returncode == 0:
                subprocess.run(
                    ["tmux", "kill-session", "-t", name],
                    capture_output=True,
                )
                killed.append(name)
        except Exception:
            pass
    return killed


def copy_to_clipboard(root: tk.Tk, text: str) -> None:
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
    except Exception:
        pass


# ==========================================================
# GUI
# ==========================================================
class ControlHubGui:

    def __init__(self, root: tk.Tk, server_pid: int) -> None:
        self.root = root
        self.server_pid = server_pid
        self.ip = get_local_ip()
        self.url = f"http://{self.ip}:{WEB_PORT}"
        self._stopping = False

        self._build_window()
        self._build_ui()
        self._center_window()

    # ----------------------------------------------------------
    def _build_window(self) -> None:
        self.root.title("Control Hub")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_stop)

    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.root.geometry(f"+{x}+{y}")

    # ----------------------------------------------------------
    def _build_ui(self) -> None:
        pad = 16

        # ── Tiêu đề ──────────────────────────────────────────
        tk.Label(
            self.root,
            text="⚙  CONTROL HUB",
            bg=COLOR_BG,
            fg=COLOR_BLUE,
            font=("Arial", 13, "bold"),
        ).pack(pady=(pad, 6))

        # ── Separator ─────────────────────────────────────────
        tk.Frame(self.root, bg=COLOR_BORDER, height=1).pack(
            fill="x", padx=pad, pady=(0, 10)
        )

        # ── Panel thông tin ───────────────────────────────────
        info_frame = tk.Frame(self.root, bg=COLOR_PANEL, bd=0)
        info_frame.pack(padx=pad, fill="x")

        tk.Label(
            info_frame,
            text="Web đang chạy tại:",
            bg=COLOR_PANEL,
            fg=COLOR_MUTED,
            font=("Arial", 10),
        ).pack(pady=(10, 2))

        # URL — click để copy
        self.url_label = tk.Label(
            info_frame,
            text=self.url,
            bg=COLOR_PANEL,
            fg=COLOR_GREEN,
            font=("Arial", 15, "bold"),
            cursor="hand2",
        )
        self.url_label.pack(pady=(0, 4))
        self.url_label.bind("<Button-1>", lambda _e: self._copy_url())

        self.copy_hint = tk.Label(
            info_frame,
            text="↑ Click để copy địa chỉ",
            bg=COLOR_PANEL,
            fg=COLOR_MUTED,
            font=("Arial", 9),
        )
        self.copy_hint.pack(pady=(0, 10))

        # ── Status label ──────────────────────────────────────
        self.status_var = tk.StringVar(value="✓ Server đang chạy")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=COLOR_BG,
            fg=COLOR_YELLOW,
            font=("Arial", 10),
        ).pack(pady=(10, 0))

        # ── Nút bấm ──────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=COLOR_BG)
        btn_frame.pack(padx=pad, pady=(10, pad), fill="x")

        copy_btn = self._make_btn(
            btn_frame,
            text="COPY URL",
            bg=COLOR_BLUE,
            hover=COLOR_BLUE_H,
            command=self._copy_url,
        )
        copy_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.stop_btn = self._make_btn(
            btn_frame,
            text="STOP",
            bg=COLOR_RED,
            hover=COLOR_RED_H,
            command=self._on_stop,
        )
        self.stop_btn.pack(side="left", fill="x", expand=True)

    def _make_btn(self, parent, text, bg, hover, command) -> tk.Button:
        btn = tk.Button(
            parent,
            text=text,
            bg=bg,
            fg=COLOR_TEXT,
            activebackground=hover,
            activeforeground=COLOR_TEXT,
            font=("Arial", 12, "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=10,
            cursor="hand2",
            command=command,
        )
        btn.bind("<Enter>", lambda _e, b=btn, c=hover: b.configure(bg=c))
        btn.bind("<Leave>", lambda _e, b=btn, c=bg:   b.configure(bg=c))
        return btn

    # ----------------------------------------------------------
    def _copy_url(self) -> None:
        copy_to_clipboard(self.root, self.url)
        self.copy_hint.configure(text="✓ Đã copy!", fg=COLOR_GREEN)
        self.root.after(2000, lambda: self.copy_hint.configure(
            text="↑ Click để copy địa chỉ", fg=COLOR_MUTED
        ))

    # ----------------------------------------------------------
    def _on_stop(self) -> None:
        if self._stopping:
            return
        self._stopping = True

        self.stop_btn.configure(text="Đang dừng...", state="disabled")
        self.status_var.set("Đang dừng tất cả...")
        self.root.update_idletasks()

        # 1. Dừng tmux sessions AMR
        killed = kill_tmux_sessions()
        if killed:
            self.status_var.set(f"Đã dừng: {', '.join(killed)}")
            self.root.update_idletasks()

        # 2. Dừng webserver (engineer_web_server)
        kill_pid(self.server_pid)

        # Đóng cửa sổ
        self.root.after(600, self.root.destroy)


# ==========================================================
# Entry point
# ==========================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="AMR Control Hub — GUI trạng thái webserver"
    )
    parser.add_argument(
        "--server-pid",
        type=int,
        default=0,
        metavar="PID",
        help="PID của engineer_web_server để dừng khi nhấn STOP",
    )
    args = parser.parse_args()

    if not os.environ.get("DISPLAY") and sys.platform != "win32":
        print(
            "[control_hub_gui] Không tìm thấy DISPLAY — bỏ qua GUI.",
            file=sys.stderr,
        )
        return

    root = tk.Tk()
    _app = ControlHubGui(root, server_pid=args.server_pid)
    root.mainloop()


if __name__ == "__main__":
    main()