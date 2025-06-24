# app.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastrtc import Stream
import numpy as np
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="demo/templates")

# 브라우저에서 받은 프레임을 그대로 되돌려줌
def camera_handler(frame: np.ndarray) -> np.ndarray:
    return frame

# FastRTC 설정
stream = Stream(handler=camera_handler, 
                modality="video", 
                mode="send-receive")
stream.mount(app)

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index3.html", {"request": request})

# 실행
if __name__ == "__main__":
    uvicorn.run(app)
