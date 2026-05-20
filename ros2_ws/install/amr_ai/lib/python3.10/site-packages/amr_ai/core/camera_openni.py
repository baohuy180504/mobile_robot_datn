# =============================
# camera_openni.py
# Camera Astra/OpenNI: tách riêng để dễ thay bằng USB/CSI camera khi lên Jetson
# =============================

import platform
import cv2
import numpy as np
from openni import openni2
from amr_ai.core import config as cfg


class OpenNICamera:
    def __init__(self, openni_path=None):
        if openni_path is None:
            if platform.system().lower().startswith("win"):
                openni_path = cfg.OPENNI_PATH_WINDOWS
            else:
                openni_path = cfg.OPENNI_PATH_LINUX

        self.openni_path = openni_path
        self.dev = None
        self.depth_stream = None
        self.color_stream = None

    def start(self):
        openni2.initialize(self.openni_path)
        self.dev = openni2.Device.open_any()
        self.depth_stream = self.dev.create_depth_stream()
        self.color_stream = self.dev.create_color_stream()
        self.depth_stream.start()
        self.color_stream.start()
        print("OpenNI camera started OK")

    def read(self):
        color_frame = self.color_stream.read_frame()
        depth_frame = self.depth_stream.read_frame()

        if color_frame is None or depth_frame is None:
            return None, None

        color_data = color_frame.get_buffer_as_uint8()
        frame = np.frombuffer(color_data, dtype=np.uint8).reshape((cfg.COLOR_H, cfg.COLOR_W, 3))
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        depth_data = depth_frame.get_buffer_as_uint16()
        depth = np.frombuffer(depth_data, dtype=np.uint16).reshape((cfg.DEPTH_H, cfg.DEPTH_W))

        if cfg.ENABLE_FLIP:
            frame = cv2.flip(frame, cfg.FLIP_CODE)
            depth = cv2.flip(depth, cfg.FLIP_CODE)

        frame = cv2.resize(frame, (cfg.CAM_W, cfg.CAM_H))
        depth = cv2.resize(depth, (cfg.CAM_W, cfg.CAM_H), interpolation=cv2.INTER_NEAREST)

        return frame, depth

    def stop(self):
        if self.depth_stream is not None:
            self.depth_stream.stop()
        if self.color_stream is not None:
            self.color_stream.stop()
        openni2.unload()
