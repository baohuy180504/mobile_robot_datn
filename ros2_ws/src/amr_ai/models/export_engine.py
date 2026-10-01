from ultralytics import YOLO
from pathlib import Path

PT_MODEL = "person.pt"

model_path = Path(PT_MODEL)

if not model_path.exists():
    raise FileNotFoundError(f"Khong tim thay model: {model_path}")

model = YOLO(str(model_path))

engine_path = model.export(
    format="engine",
    imgsz=640,
    half=True,
    device=0,
    batch=1,
    workspace=4
)

print("Export done:", engine_path)