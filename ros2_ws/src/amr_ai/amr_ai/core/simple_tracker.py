#!/usr/bin/env python3
"""
simple_tracker.py — gán ID theo IoU giữa khung liên tiếp, thay cho BoT-SORT của Ultralytics.

Vì sao đổi: BoT-SORT (tracker mặc định của Ultralytics khi gọi .track(), kể cả không truyền
tham số tracker) chạy bù chuyển động camera bằng optical flow (gmc_method: sparseOptFlow) trên
CPU mỗi khung, tốn thời gian ngay cả khi with_reid=False (cấu hình mặc định, không dùng model
ReID). Bỏ optical flow giúp giảm CPU. Đánh đổi: khi robot quay nhanh, box có thể lệch giữa 2
khung liên tiếp làm IoU giảm và ID dễ đổi hơn BoT-SORT (BoT-SORT bù chuyển động camera nên ổn
định hơn lúc quay). Với ai_detector (chỉ dùng ID để đếm số khung liên tiếp xác nhận/hết té ngã,
không dùng ID để phân biệt nhiều người theo thời gian dài), ảnh hưởng thực tế nhỏ: ID đổi giữa
chừng chỉ làm bộ đếm xác nhận/hết té ngã reset, làm chậm phát hiện thêm vài khung chứ không báo
sai. Nếu sau này thấy ảnh hưởng rõ, tăng iou_threshold/max_age hoặc quay lại BoT-SORT.

Thuật toán: ghép tham lam theo IoU giảm dần (không phải Hungarian tối ưu toàn cục, nhưng đủ tốt
với số người thường gặp trong 1 khung, và nhanh hơn nhiều so với optical flow).
"""
from typing import List, Optional, Sequence


class SimpleIouTracker:
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 10):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.tracks = {}          # id -> {'box': [x1,y1,x2,y2], 'age': số khung liên tiếp không khớp}
        self.next_id = 1

    def reset(self):
        self.tracks.clear()
        self.next_id = 1

    @staticmethod
    def _iou(a: Sequence[float], b: Sequence[float]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
        inter = iw * ih
        if inter <= 0.0:
            return 0.0
        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    def update(self, boxes: List[Sequence[float]]) -> List[int]:
        """boxes: danh sách [x1,y1,x2,y2]. Trả về ID tương ứng theo đúng thứ tự `boxes`."""
        n = len(boxes)
        assigned: List[Optional[int]] = [None] * n

        # Xếp mọi cặp (detection, track) đủ IoU theo thứ tự giảm dần, ghép tham lam.
        pairs = []
        for di in range(n):
            for tid, tr in self.tracks.items():
                iou = self._iou(boxes[di], tr['box'])
                if iou >= self.iou_threshold:
                    pairs.append((iou, di, tid))
        pairs.sort(key=lambda p: p[0], reverse=True)

        used_dets, used_tracks = set(), set()
        for _iou_val, di, tid in pairs:
            if di in used_dets or tid in used_tracks:
                continue
            assigned[di] = tid
            used_dets.add(di)
            used_tracks.add(tid)
            self.tracks[tid]['box'] = boxes[di]
            self.tracks[tid]['age'] = 0

        for di in range(n):
            if assigned[di] is None:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {'box': boxes[di], 'age': 0}
                assigned[di] = tid
                used_tracks.add(tid)

        # Track không khớp khung này: tăng tuổi, xóa nếu vắng mặt quá lâu.
        for tid in list(self.tracks.keys()):
            if tid not in used_tracks:
                self.tracks[tid]['age'] += 1
                if self.tracks[tid]['age'] > self.max_age:
                    del self.tracks[tid]

        return assigned  # type: ignore[return-value]
