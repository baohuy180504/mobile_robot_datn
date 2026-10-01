#!/usr/bin/env python3
"""
Kiểm tra engine TensorRT và đo phần tốn thời gian của Ultralytics.

Chạy:   python3 trt_inspect.py                       (tự tìm *.engine trong thư mục models của amr_ai)
        python3 trt_inspect.py a.engine b.engine     (chỉ định file)
        IMG=/duong/dan/anh.jpg python3 trt_inspect.py   (dùng ảnh thật thay cho ảnh giả)
Chỉ ĐỌC, không sửa gì. Nên chạy khi hệ thống đã START (để đo trong điều kiện tải thật).
"""
import glob
import json
import os
import platform
import sys
import time

MODELS = sys.argv[1:] or sorted(glob.glob(os.path.expanduser(
    "~/mobile_robot/ros2_ws/install/amr_ai/share/amr_ai/models/*.engine")))


def versions():
    print("=== PHIÊN BẢN ===")
    print("python      :", platform.python_version())
    try:
        with open("/etc/nv_tegra_release") as f:
            print("L4T         :", f.readline().strip()[:110])
    except Exception:
        pass
    for name in ("tensorrt", "torch", "torchvision", "ultralytics", "cv2", "numpy"):
        try:
            mod = __import__(name)
            extra = ""
            if name == "torch":
                extra = f"  (cuda={mod.cuda.is_available()})"
            print(f"{name:12s}: {getattr(mod, '__version__', '?')}{extra}")
        except Exception as exc:
            print(f"{name:12s}: KHÔNG có ({exc.__class__.__name__})")


def read_engine(path):
    """File .engine của Ultralytics = [4 byte độ dài][JSON metadata][engine TensorRT]. Trả (metadata, engine_bytes)."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        n = int.from_bytes(raw[:4], "little")
        if 0 < n < 1_000_000:
            meta = json.loads(raw[4:4 + n].decode("utf-8"))
            if isinstance(meta, dict):
                return meta, raw[4 + n:]
    except Exception:
        pass
    return {}, raw


def inspect(path, meta, blob):
    import tensorrt as trt
    keys = {k: v for k, v in meta.items() if k != "names"}
    print("metadata   :", keys)
    if "names" in meta:
        names = meta["names"]
        print("số lớp     :", len(names) if hasattr(names, "__len__") else names)

    rt = trt.Runtime(trt.Logger(trt.Logger.WARNING))
    eng = rt.deserialize_cuda_engine(blob)
    if eng is None:
        print("KHÔNG nạp được engine (khác phiên bản TensorRT hoặc khác GPU so với lúc export?)")
        return False

    if hasattr(eng, "num_io_tensors"):                       # TensorRT >= 8.5: API theo tên tensor
        print("API        : tensor (execute_async_v3)")
        for i in range(eng.num_io_tensors):
            name = eng.get_tensor_name(i)
            mode = eng.get_tensor_mode(name).name
            shape = tuple(eng.get_tensor_shape(name))
            line = f"  {mode:6s} {name:12s} {str(eng.get_tensor_dtype(name)):18s} shape={shape}"
            if -1 in shape and mode == "INPUT":
                try:
                    line += f"  profile(min,opt,max)={eng.get_tensor_profile_shape(name, 0)}"
                except Exception:
                    pass
            print(line)
    else:                                                    # TensorRT cũ: API bindings
        print("API        : bindings (execute_async_v2)")
        for i in range(eng.num_bindings):
            kind = "INPUT " if eng.binding_is_input(i) else "OUTPUT"
            print(f"  {kind} {eng.get_binding_name(i):12s} {str(eng.get_binding_dtype(i)):18s} shape={tuple(eng.get_binding_shape(i))}")
    return True


def bench(path, meta):
    import numpy as np
    from ultralytics import YOLO

    task = meta.get("task", "detect")
    img_path = os.environ.get("IMG")
    if img_path:
        import cv2
        img = cv2.imread(img_path)
    elif task == "pose":
        img = np.random.randint(0, 255, (330, 150, 3), np.uint8)     # gần giống ảnh cắt 1 người
    else:
        img = np.random.randint(0, 255, (480, 640, 3), np.uint8)

    kwargs = {"verbose": False}
    if task == "pose":
        kwargs["imgsz"] = 192                                        # đúng như fall_detector đang gọi
    model = YOLO(path)

    for _ in range(20):                                              # làm nóng
        model.predict(img, **kwargs)
    speeds = [model.predict(img, **kwargs)[0].speed for _ in range(100)]
    avg = {k: round(sum(s[k] for s in speeds) / len(speeds), 2) for k in speeds[0]}
    t0 = time.perf_counter()
    for _ in range(100):
        model.predict(img, **kwargs)
    wall = (time.perf_counter() - t0) / 100 * 1000
    tot = sum(avg.values())
    over = avg.get("preprocess", 0) + avg.get("postprocess", 0)
    print(f"Ultralytics (ms, TB 100 lần): {avg}  | tổng thực tế mỗi lần gọi: {wall:.2f} ms")
    if tot > 0:
        print(f"  -> tiền + hậu xử lý = {over:.2f} ms = {100 * over / tot:.0f}% (phần này viết lại trực tiếp mới giảm được)")
    print(f"  -> ~{1000 / wall:.0f} lần/giây nếu chạy liên tục một luồng")


def main():
    versions()
    if not MODELS:
        print("\nKhông tìm thấy file .engine. Truyền đường dẫn làm tham số.")
        return
    for path in MODELS:
        print(f"\n=== {path}")
        meta, blob = read_engine(path)
        try:
            inspect(path, meta, blob)
        except Exception as exc:
            print("Lỗi khi đọc engine bằng TensorRT:", repr(exc))
        try:
            bench(path, meta)
        except Exception as exc:
            print("Không đo được Ultralytics:", repr(exc))


if __name__ == "__main__":
    main()