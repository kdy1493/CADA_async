import autorootcwd
import json
from pathlib import Path

import cv2
import gradio as gr
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastrtc import Stream, get_twilio_turn_credentials
from gradio.utils import get_space
from huggingface_hub import hf_hub_download
from pydantic import BaseModel, Field
import socketio

from demo.services.cada import CADAService
from src.utils import YOLOv10


cur_dir = Path(__file__).parent    

model_file = hf_hub_download(
    repo_id="onnx-community/yolov10n", filename="onnx/model.onnx"
)
model = YOLOv10(model_file)

def detection(image, conf_threshold=0.3):
    image = cv2.resize(image, (model.input_width, model.input_height))
    new_image = model.detect_objects(image, conf_threshold)
    return cv2.resize(new_image, (500, 500))

stream = Stream(
    handler=detection,
    modality="video",
    mode="send-receive",
    additional_inputs=[gr.Slider(minimum=0, maximum=1, step=0.01, value=0.3)],
    rtc_configuration=get_twilio_turn_credentials() if get_space() else None,
    concurrency_limit=2 if get_space() else None,
)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
fastapi_app = FastAPI()

cada_service = CADAService(sio)
cada_service.start()

stream.mount(fastapi_app)

# Socket.IO 이벤트 핸들러 -----------------------------------------

@sio.event(namespace="/csi")
async def connect(sid, environ):
    print("[SocketIO] client connected", sid)
    await sio.emit("cada_result", {
        "topic": "debug",
        "timestamp_ms": 0,
        "activity": 0,
        "flag": 0,
        "threshold": 0,
    }, to=sid, namespace="/csi")
    if cada_service.mqtt_manager and cada_service.mqtt_manager.loop is None:
        import asyncio
        cada_service.mqtt_manager.loop = asyncio.get_running_loop()
        print("[SocketIO] event loop bound to MQTTManager")


@sio.event(namespace="/csi")
def disconnect(sid):
    print("[SocketIO] client disconnected", sid)

@fastapi_app.get("/")
async def index():
    rtc_config = get_twilio_turn_credentials() if get_space() else None
    html_content = open(cur_dir / "templates" / "index3.html", encoding="utf-8").read()
    html_content = html_content.replace("__RTC_CONFIGURATION__", json.dumps(rtc_config))
    return HTMLResponse(content=html_content)

class InputData(BaseModel):
    webrtc_id: str
    conf_threshold: float = Field(ge=0, le=1)

@fastapi_app.post("/input_hook")
async def update_threshold(data: InputData):
    stream.set_input(data.webrtc_id, data.conf_threshold)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
