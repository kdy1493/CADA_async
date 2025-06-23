import autorootcwd
import cv2
import time
import os
from flask import Flask, Response, render_template
from flask_socketio import SocketIO

from demo.core.stream import StreamManager
from demo.services.cada import CADAService
from demo.config.settings import HOST, PORT, DEBUG, CAMERA_INDEX

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
    """Flask + Socket.IO 애플리케이션 (영상 스트림 & CADA 시각화 전용)"""

    def __init__(self):
        # --- Flask / SocketIO 초기화 -------------------------------------
        self.app = Flask(
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        )
        self.socketio = SocketIO(async_mode="threading")
        self.socketio.init_app(self.app)

        # --- 서비스 초기화 -----------------------------------------------
        self.stream_manager = StreamManager()
        self.cada_service = CADAService(self.socketio)


        self._start_services()
        # 스트림 즉시 시작 (MQTT 트리거 없이 영상 출력)
        self.stream_manager.start_stream()
        self._setup_routes()
        self._register_socketio_handlers()

    # ---------------------------------------------------------------------
    # 서비스 시작
    # ---------------------------------------------------------------------
    def _start_services(self):
        """MQTT / CADA 백그라운드 서비스 가동"""
        self.cada_service.start()
    # ---------------------------------------------------------------------
    # Flask 라우트 정의
    # ---------------------------------------------------------------------
    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/video_feed")
        def video_feed():
            return Response(
                self._gen_frames(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )
    # ---------------------------------------------------------------------
    # 프레임 생성기 (영상 스트림)
    # ---------------------------------------------------------------------
    def _gen_frames(self):
        while True:
            # 스트림이 아직 시작되지 않았으면 잠시 대기
            if not self.stream_manager.is_active():
                time.sleep(0.05)
                continue

            # 활성화된 경우: 최신 프레임 전송 -------------------------------
            frame = self.stream_manager.get_frame()
            if frame is None:
                time.sleep(0.02)
                continue

            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if ok:
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
                )

    # ---------------------------------------------------------------------
    # Socket.IO 이벤트 핸들러
    # ---------------------------------------------------------------------
    def _register_socketio_handlers(self):
        @self.socketio.on("connect", namespace="/csi")
        def on_connect():
            if self.cada_service.mqtt_manager:
                self.cada_service.mqtt_manager.start()
            print("[SocketIO] Client connected")

        @self.socketio.on("disconnect", namespace="/csi")
        def on_disconnect():
            print("[SocketIO] Client disconnected")

    # ---------------------------------------------------------------------
    # 실행
    # ---------------------------------------------------------------------
    def run(self):
        self.app.run(host=HOST, port=PORT, debug=DEBUG)


if __name__ == "__main__":
    app = CADAApp()
    app.run()

for idx in range(5):
    cap = cv2.VideoCapture(idx)      # 백엔드 지정 없이 기본값
    print(idx, cap.isOpened())
    cap.release()