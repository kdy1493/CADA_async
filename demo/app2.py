# app.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastrtc import Stream

from ultralytics import YOLO
import numpy as np
import cv2, uvicorn, torch

app = FastAPI()
templates = Jinja2Templates(directory="demo/templates")

# ───────── 모델 준비 ─────────
DEVICE = 0 if torch.cuda.is_available() else "cpu"
if DEVICE == "cpu":
    print("[WARN] CUDA 미사용, CPU 모드", flush=True)

model = YOLO("yolov8n.pt")
if DEVICE != "cpu":
    model.model.to(f"cuda:{DEVICE}")
    _ = model.predict(np.zeros((640, 640, 3), dtype=np.uint8), device=DEVICE)

# ───────── 핸들러 ─────────
def camera_handler(frame: np.ndarray) -> np.ndarray:
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    results = model.predict(
        bgr,
        conf=0.10,              # ← 0.05~0.10 로 낮춤
        imgsz=640,
        device=DEVICE,
        classes=[0],            # ← person 클래스만
        verbose=False,
    )[0]

    if len(results.boxes):
        # 박스·라벨 주석(BGR)
        bgr = results.plot(line_width=2, font_size=0.5)

    # 브라우저용 RGB
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

# ───────── FastRTC ─────────
stream = Stream(handler=camera_handler,
                modality="video",
                mode="send-receive")
stream.mount(app)

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index3.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
