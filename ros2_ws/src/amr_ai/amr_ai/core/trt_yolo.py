#!/usr/bin/env python3
"""
trt_yolo.py — suy luận trực tiếp bằng TensorRT cho engine YOLO26 (person detect, pose),
thay cho lớp Ultralytics (YOLO(...).track()/.predict()) vốn tốn thêm ~10 ms mỗi lần gọi
ngoài phần GPU thực sự tính (đã đo trên Jetson: GPU Compute Time person ~4.2 ms, pose ~2.0 ms,
trong khi Ultralytics báo "inference" ~14 ms / ~7 ms — chênh lệch là chi phí Python/framework,
không phải GPU chậm).

THIẾT KẾ: lớp TrtYOLO giả lập đúng bề mặt API mà code hiện tại đang gọi trên đối tượng
ultralytics.YOLO — .track(source=..., persist=True, classes=[0], conf=..., verbose=False)
và .predict(source=..., conf=..., classes=..., verbose=False) — cùng cấu trúc kết quả
results[0].boxes.xyxy/.conf/.cls/.id và results[0].keypoints.data (đều là tensor có .cpu()/.numpy()).
NHỜ VẬY, chỗ gọi trong ai_detector_node.py / fall_detector.py CHỈ CẦN ĐỔI DÒNG IMPORT:

    from ultralytics import YOLO
        ->
    from amr_ai.core.trt_yolo import TrtYOLO as YOLO

không cần sửa gì khác ở nơi gọi. Tracking (gán ID) không còn dùng BoT-SORT (có bù chuyển
động bằng optical flow, tốn CPU — xem ghi chú trước đó) mà dùng SimpleIouTracker nhẹ hơn;
xem simple_tracker.py để biết đánh đổi.

GIỚI HẠN (đọc trước khi dùng):
  - Chỉ chạy engine TĨNH (không có chiều động, batch=1) — đúng với 2 engine đang dùng
    (yolo26n.engine, yolo26n-pose.engine), xác nhận qua trt_inspect.py. Engine động sẽ báo lỗi rõ.
  - Cần TensorRT >= 8.5 (API execute_async_v3 theo tên tensor). Môi trường của bạn: TensorRT 10.3.0 — hợp.
  - Định dạng đầu ra giả định là kiểu "end2end" của Ultralytics export (nms:false, end2end:true):
    detect (1,300,6) = [x1,y1,x2,y2,conf,cls] đã NMS sẵn, pose (1,300,57) = 6 + 17*3 keypoint,
    tọa độ theo hệ pixel của ảnh ĐÃ letterbox (chưa quy đổi về ảnh gốc). Khớp với metadata
    engine đã đọc được (end2end: True, nms: False) — nhưng CHƯA đối chiếu bằng ảnh thật có
    người, chỉ mới kiểm bằng dữ liệu giả trên máy không có GPU. Việc đầu tiên cần làm trên
    Jetson là so sánh box/keypoint giữa bản Ultralytics cũ và bản này trên cùng một ảnh.
"""
import json
import os
import time

import cv2
import numpy as np
import torch

try:
    import tensorrt as trt
    _TRT_IMPORT_ERROR = None
except Exception as _exc:  # pragma: no cover - chỉ xảy ra khi thiếu TensorRT (vd chạy ngoài Jetson)
    trt = None
    _TRT_IMPORT_ERROR = _exc

from amr_ai.core.simple_tracker import SimpleIouTracker

COCO_PERSON_CLASS = 0


# ============================================================================
# Letterbox + (giải) mã tọa độ — thuần numpy/cv2, không cần GPU
# ============================================================================
def letterbox(img_bgr, size, color=(114, 114, 114)):
    """
    Thu ảnh về khung vuông `size` x `size`, giữ tỉ lệ, đệm màu xám 114 hai bên (giống
    ultralytics.utils.ops.LetterBox mặc định: center=True, scaleup=True). Cả 2 engine đang
    dùng đều vuông (640x640, 192x192) nên không cần phân biệt chiều rộng/cao của size.
    Trả (ảnh đã letterbox, tỉ lệ thu r, (pad_trái, pad_trên)).
    """
    h, w = img_bgr.shape[:2]
    r = min(size / h, size / w)
    new_w, new_h = int(round(w * r)), int(round(h * r))
    if (new_w, new_h) != (w, h):
        img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    dw, dh = size - new_w, size - new_h
    left, top = dw // 2, dh // 2
    right, bottom = dw - left, dh - top
    out = cv2.copyMakeBorder(img_bgr, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return out, r, (left, top)


def preprocess_bgr(img_bgr, size):
    """BGR HxWx3 uint8 -> CHW RGB float32 [0,1] đã letterbox về size x size."""
    padded, r, pad = letterbox(img_bgr, size)
    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    chw = np.ascontiguousarray(rgb.transpose(2, 0, 1), dtype=np.float32) / 255.0
    return chw, r, pad


def _unletterbox_xy(x, y, r, pad):
    return (x - pad[0]) / r, (y - pad[1]) / r


def decode_detect(output, r, pad, orig_shape, conf_thres=0.25, cls_filter=None, max_det=300):
    """
    output: mảng (N,6) = [x1,y1,x2,y2,conf,cls] theo hệ pixel ảnh ĐÃ letterbox, đã NMS sẵn
    (end2end), sắp theo conf giảm dần. Trả (boxes Nx4 pixel ảnh GỐC, confs, classes int).
    """
    oh, ow = orig_shape[0], orig_shape[1]
    boxes, confs, classes = [], [], []
    for row in output[:max_det]:
        x1, y1, x2, y2, conf, cls = row[0], row[1], row[2], row[3], row[4], int(round(row[5]))
        if conf < conf_thres:
            continue
        if cls_filter is not None and cls not in cls_filter:
            continue
        x1, y1 = _unletterbox_xy(x1, y1, r, pad)
        x2, y2 = _unletterbox_xy(x2, y2, r, pad)
        x1 = min(max(x1, 0.0), ow - 1)
        x2 = min(max(x2, 0.0), ow - 1)
        y1 = min(max(y1, 0.0), oh - 1)
        y2 = min(max(y2, 0.0), oh - 1)
        if x2 <= x1 or y2 <= y1:
            continue
        boxes.append([x1, y1, x2, y2])
        confs.append(float(conf))
        classes.append(cls)
    return boxes, confs, classes


def decode_pose(output, r, pad, orig_shape, conf_thres=0.25, num_kpts=17, max_det=300):
    """output: (N,57) = 6 (box+conf+cls) + 17*3 (x,y,visibility). Trả thêm kpts (N,17,3)."""
    boxes, confs, classes = decode_detect(output, r, pad, orig_shape, conf_thres, None, max_det)
    oh, ow = orig_shape[0], orig_shape[1]
    kpts_all = []
    kept = 0
    for row in output[:max_det]:
        conf = row[4]
        if conf < conf_thres:
            continue
        if kept >= len(boxes):
            break
        kept += 1
        kp = row[6:6 + num_kpts * 3].reshape(num_kpts, 3).copy()
        kp[:, 0], kp[:, 1] = _unletterbox_xy(kp[:, 0], kp[:, 1], r, pad)
        kp[:, 0] = np.clip(kp[:, 0], 0, ow - 1)
        kp[:, 1] = np.clip(kp[:, 1], 0, oh - 1)
        kpts_all.append(kp)
    return boxes, confs, classes, kpts_all


# ============================================================================
# Bộ nạp + chạy engine TensorRT (dùng tensor torch làm bộ đệm GPU, không cần pycuda)
# ============================================================================
def _read_engine_file(path):
    """File .engine của Ultralytics = [4 byte độ dài][JSON metadata][engine TensorRT thô]."""
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        n = int.from_bytes(raw[:4], 'little')
        if 0 < n < 1_000_000:
            meta = json.loads(raw[4:4 + n].decode('utf-8'))
            if isinstance(meta, dict):
                return meta, raw[4 + n:]
    except Exception:
        pass
    return {}, raw


_TORCH_DTYPE = None


def _torch_dtype_map():
    global _TORCH_DTYPE
    if _TORCH_DTYPE is None:
        _TORCH_DTYPE = {
            trt.DataType.FLOAT: torch.float32,
            trt.DataType.HALF: torch.float16,
            trt.DataType.INT32: torch.int32,
            trt.DataType.INT8: torch.int8,
            trt.DataType.BOOL: torch.bool,
        }
    return _TORCH_DTYPE


class TrtEngine:
    """Nạp 1 file .engine (định dạng Ultralytics) và chạy suy luận đồng bộ, batch cố định = 1."""

    def __init__(self, engine_path, device='cuda:0'):
        if trt is None:
            raise RuntimeError(
                f'Thiếu thư viện tensorrt (chỉ chạy được trên Jetson đã cài TensorRT): {_TRT_IMPORT_ERROR}'
            )
        if not torch.cuda.is_available():
            raise RuntimeError('torch.cuda.is_available() = False: cần GPU CUDA để chạy TrtEngine')
        if not os.path.exists(engine_path):
            raise FileNotFoundError(f'Không thấy file engine: {engine_path}')

        self.path = engine_path
        self.device = torch.device(device)
        self.meta, blob = _read_engine_file(engine_path)

        logger = trt.Logger(trt.Logger.WARNING)
        runtime = trt.Runtime(logger)
        self.engine = runtime.deserialize_cuda_engine(blob)
        if self.engine is None:
            raise RuntimeError(
                f'TensorRT không nạp được {engine_path} (khác phiên bản TensorRT hoặc khác GPU '
                f'so với lúc build engine — thử build/export lại engine trên đúng máy này).'
            )
        if not hasattr(self.engine, 'num_io_tensors'):
            raise RuntimeError('TensorRT quá cũ (thiếu API tensor, cần >= 8.5). Cài TensorRT mới hơn.')

        self.context = self.engine.create_execution_context()
        self.stream = torch.cuda.Stream(device=self.device)

        self._input_name = None
        self._output_names = []
        self.bindings = {}
        self._input_pinned = None    # bộ đệm CPU "pinned" dùng chung mọi khung — copy CPU->GPU CHỈ 1 LẦN mỗi khung
        dtmap = _torch_dtype_map()

        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            shape = tuple(self.engine.get_tensor_shape(name))
            if -1 in shape:
                raise RuntimeError(
                    f"Engine '{engine_path}' có chiều động ({name}: {shape}) — TrtEngine chỉ hỗ trợ "
                    f'engine batch/kích thước cố định. Hai engine yolo26n/yolo26n-pose đã xác nhận tĩnh; '
                    f'nếu bạn đổi engine khác, cần bổ sung set_input_shape trước khi dùng lớp này.'
                )
            is_input = self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT
            dtype = dtmap[self.engine.get_tensor_dtype(name)]
            tensor = torch.zeros(shape, dtype=dtype, device=self.device)
            self.bindings[name] = {'shape': shape, 'dtype': dtype, 'tensor': tensor, 'is_input': is_input}
            self.context.set_tensor_address(name, tensor.data_ptr())
            if is_input:
                self._input_name = name
                try:
                    self._input_pinned = torch.empty(shape, dtype=dtype, pin_memory=True)
                except (RuntimeError, TypeError):
                    self._input_pinned = None   # môi trường test/không có CUDA: bỏ qua, dùng đường copy thường
            else:
                self._output_names.append(name)

        if self._input_name is None or not self._output_names:
            raise RuntimeError(f"Engine '{engine_path}' thiếu tensor vào hoặc ra.")

    @property
    def input_name(self):
        return self._input_name

    @property
    def input_shape(self):
        return self.bindings[self._input_name]['shape']

    @property
    def output_name(self):
        """Tên tensor đầu ra đầu tiên — cả 2 engine đang dùng chỉ có đúng 1 output ('output0')."""
        return self._output_names[0]

    def infer_from_cpu(self, chw_numpy):
        """
        chw_numpy: mảng numpy CHW float32 (đúng shape input, vd (3,640,640), CHƯA có chiều batch).
        Copy CPU->GPU ĐÚNG 1 LẦN (qua bộ đệm pinned dùng lại mỗi khung, không tạo tensor mới mỗi lần
        gọi — trước đây bị copy 2 lần: 1 lần ở _forward() qua .to(device), 1 lần nữa ở đây, cộng thêm
        chi phí cấp phát tensor mới mỗi khung; trên CPU ARM của Jetson mỗi lệnh gọi torch/CUDA rời rạc
        tốn đáng kể nên cộng dồn lại làm "inference" đo được cao hơn nhiều so với GPU Compute Time
        thật (đã xác nhận bằng trtexec: ~4,2 ms so với ~12-14 ms khi qua Python nhiều lớp).
        Trả dict {tên_tensor_ra: torch.Tensor trên GPU}. Đồng bộ (chờ xong mới trả về).
        """
        inp = self.bindings[self._input_name]
        expect = inp['shape'][1:]  # bỏ chiều batch
        if tuple(chw_numpy.shape) != expect:
            raise ValueError(f'Input shape {chw_numpy.shape} != engine yêu cầu {expect}')

        if self._input_pinned is not None:
            self._input_pinned[0].copy_(torch.from_numpy(chw_numpy))
            inp['tensor'].copy_(self._input_pinned, non_blocking=True)
        else:
            inp['tensor'].copy_(torch.from_numpy(chw_numpy).unsqueeze(0))

        with torch.cuda.stream(self.stream):
            ok = self.context.execute_async_v3(self.stream.cuda_stream)
        self.stream.synchronize()
        if not ok:
            raise RuntimeError(f'TensorRT execute_async_v3 thất bại cho {self.path}')
        return {n: self.bindings[n]['tensor'] for n in self._output_names}

    def infer(self, input_tensor):
        """Tương thích ngược: nhận thẳng tensor CPU/GPU đã có chiều batch (đường cũ, chậm hơn
        infer_from_cpu vì có thể copy thêm 1 lần nếu input_tensor chưa ở CPU dạng pinned)."""
        inp = self.bindings[self._input_name]
        if tuple(input_tensor.shape) != inp['shape']:
            raise ValueError(f'Input shape {tuple(input_tensor.shape)} != engine yêu cầu {inp["shape"]}')
        inp['tensor'].copy_(input_tensor, non_blocking=True)
        with torch.cuda.stream(self.stream):
            ok = self.context.execute_async_v3(self.stream.cuda_stream)
        self.stream.synchronize()
        if not ok:
            raise RuntimeError(f'TensorRT execute_async_v3 thất bại cho {self.path}')
        return {n: self.bindings[n]['tensor'] for n in self._output_names}


# ============================================================================
# Lớp giả lập đúng đối tượng kết quả của Ultralytics (chỉ phần thuộc tính code đang dùng)
# ============================================================================
class _FakeBoxes:
    def __init__(self, xyxy, conf, cls, ids):
        self.xyxy = torch.tensor(xyxy, dtype=torch.float32) if len(xyxy) else torch.zeros((0, 4))
        self.conf = torch.tensor(conf, dtype=torch.float32) if len(conf) else torch.zeros((0,))
        self.cls = torch.tensor(cls, dtype=torch.float32) if len(cls) else torch.zeros((0,))
        self.id = torch.tensor(ids, dtype=torch.int32) if ids is not None else None

    def __len__(self):
        return self.xyxy.shape[0]


class _FakeKeypoints:
    def __init__(self, kpts):
        arr = np.stack(kpts, axis=0) if len(kpts) else np.zeros((0, 17, 3), dtype=np.float32)
        self.data = torch.tensor(arr, dtype=torch.float32)
        self.xy = self.data[..., :2]
        self.conf = self.data[..., 2]

    def __len__(self):
        return self.data.shape[0]


class _FakeResult:
    def __init__(self, boxes, keypoints, orig_shape, speed, names):
        self.boxes = boxes
        self.keypoints = keypoints
        self.orig_shape = orig_shape
        self.speed = speed
        self.names = names or {}


# ============================================================================
# TrtYOLO — thay thế trực tiếp cho ultralytics.YOLO trong codebase này
# ============================================================================
class TrtYOLO:
    """
    Dùng thay ultralytics.YOLO cho các engine end2end (detect hoặc pose) của package này.
    Chỉ hỗ trợ đúng các tham số mà ai_detector_node.py / fall_detector.py đang gọi:
      .track(source, persist=True, classes=None, conf=0.4, tracker=None, verbose=False, **_)
      .predict(source, conf=0.25, classes=None, verbose=False, imgsz=None, **_)
    `source` phải là ảnh BGR numpy (H,W,3) — không hỗ trợ đường dẫn file/danh sách ảnh như
    ultralytics (code hiện tại luôn truyền frame numpy nên không cần).
    """

    def __init__(self, engine_path, device='cuda:0'):
        self.engine = TrtEngine(engine_path, device=device)
        self.task = self.engine.meta.get('task', 'detect')
        self.names = self.engine.meta.get('names', {})
        in_shape = self.engine.input_shape          # (1, 3, H, W), H == W cho 2 engine đang dùng
        if in_shape[-1] != in_shape[-2]:
            raise RuntimeError(f'TrtYOLO hiện chỉ hỗ trợ engine vuông, engine này có input {in_shape}')
        self.imgsz = int(in_shape[-1])
        self._tracker = SimpleIouTracker()
        self._warned_imgsz = False

    def _forward(self, img_bgr, conf, classes, requested_imgsz=None):
        if img_bgr is None or img_bgr.ndim != 3 or img_bgr.shape[2] != 3:
            raise ValueError('TrtYOLO chỉ nhận ảnh BGR numpy (H,W,3)')
        if requested_imgsz is not None and int(requested_imgsz) != self.imgsz and not self._warned_imgsz:
            # Engine TensorRT có kích thước vào CỐ ĐỊNH (đã build sẵn); tham số imgsz của người gọi
            # (kiểu Ultralytics) bị BỎ QUA. Chỉ cảnh báo 1 lần để không spam log.
            print(f'[TrtYOLO] CẢNH BÁO: gọi với imgsz={requested_imgsz} nhưng engine cố định '
                  f'{self.imgsz}x{self.imgsz} — dùng {self.imgsz}, bỏ qua imgsz được truyền vào.')
            self._warned_imgsz = True
        t0 = time.perf_counter()
        chw, r, pad = preprocess_bgr(img_bgr, self.imgsz)
        t1 = time.perf_counter()
        out = self.engine.infer_from_cpu(chw)
        t2 = time.perf_counter()
        out_np = out[self.engine.output_name][0].detach().to('cpu', non_blocking=False).numpy()

        if self.task == 'pose':
            boxes, confs, classes_out, kpts = decode_pose(out_np, r, pad, img_bgr.shape, conf)
        else:
            boxes, confs, classes_out, kpts = (*decode_detect(out_np, r, pad, img_bgr.shape, conf, classes), None)
        t3 = time.perf_counter()

        speed = {'preprocess': (t1 - t0) * 1000.0, 'inference': (t2 - t1) * 1000.0,
                 'postprocess': (t3 - t2) * 1000.0}
        return boxes, confs, classes_out, kpts, speed, img_bgr.shape

    def track(self, source, persist=True, classes=None, conf=0.4, tracker=None, verbose=False,
              imgsz=None, **_kwargs):
        boxes, confs, classes_out, kpts, speed, shape = self._forward(source, conf, classes, imgsz)
        if not persist:
            self._tracker.reset()
        ids = self._tracker.update(boxes)
        fb = _FakeBoxes(boxes, confs, classes_out, ids)
        kp = _FakeKeypoints(kpts) if kpts is not None else None
        return [_FakeResult(fb, kp, shape, speed, self.names)]

    def predict(self, source, conf=0.25, classes=None, verbose=False, imgsz=None, **_kwargs):
        boxes, confs, classes_out, kpts, speed, shape = self._forward(source, conf, classes, imgsz)
        fb = _FakeBoxes(boxes, confs, classes_out, None)
        kp = _FakeKeypoints(kpts) if kpts is not None else None
        return [_FakeResult(fb, kp, shape, speed, self.names)]

    # Vài project gọi model(img) thay vì model.predict(img); hỗ trợ luôn cho tiện.
    __call__ = predict
