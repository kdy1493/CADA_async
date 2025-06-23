import autorootcwd
import os
import threading
import cv2

from flask import Flask, render_template, Response
from flask_socketio import SocketIO

from demo.services.cada import CADAService
from demo.config.settings import HOST, PORT, DEBUG, CAMERA_INDEX, CAMERA_BACKEND

# FastRTC + FastAPI + Uvicorn
from fastrtc import Stream
from fastapi import FastAPI
import uvicorn

# 환경 변수 설정 -----------------------------------------------------------
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
FFMPEG_OPTS = (
    "fflags nobuffer;"
    "flags low_delay;"
    "probesize 32;"
    "analyzeduration 0"
)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = FFMPEG_OPTS


class CADAApp:
    def __init__(self):
        # Flask / SocketIO 초기화
        self.app = Flask(
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        )
        self.socketio = SocketIO(async_mode="threading")
        self.socketio.init_app(self.app)

        # CADA 서비스 시작
        self.cada_service = CADAService(self.socketio)
        self.cada_service.start()

        # FastRTC ASGI 서버(포트 8000) 띄우기
        threading.Thread(target=self._start_fastrtc_asgi, daemon=True).start()

        # Flask 라우트 & SocketIO 핸들러
        self._setup_routes()
        self._register_socketio_handlers()

    def _start_fastrtc_asgi(self):
        """
        FastAPI + Uvicorn으로 FastRTC 스트리밍 서버를 띄웁니다.
        클라이언트는 http://<host>:8000/ui 를 iframe 으로 불러오세요.
        """
        def passthrough(frame):
            return frame

        # 1) ASGI 앱 생성
        rtc_app = FastAPI()

        cap = cv2.VideoCapture(CAMERA_INDEX, CAMERA_BACKEND)
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        def camera_handler(_) :
            ret , frame = cap.read()
            return frame if ret else None

        stream = Stream( handler = camera_handler,
                         modality = "video",
                         mode = "send") 
        stream.mount(rtc_app, path="/ui")
        uvicorn.run(rtc_app, host="0.0.0.0", port=8002, log_level="warning")

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template("index2.html")

        @self.app.route("/alerts")
        def alerts():
            # 빈 SSE 스트림 (JS 에러 방지)
            def event_stream():
                while True:
                    yield "data: \n\n"
            return Response(event_stream(), mimetype="text/event-stream")

    def _register_socketio_handlers(self):
        @self.socketio.on("connect", namespace="/csi")
        def on_connect():
            if self.cada_service.mqtt_manager:
                self.cada_service.mqtt_manager.start()
            print("[SocketIO] Client connected")

        @self.socketio.on("disconnect", namespace="/csi")
        def on_disconnect():
            print("[SocketIO] Client disconnected")

    def run(self):
        self.app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)


if __name__ == "__main__":
    app = CADAApp()
    app.run()
