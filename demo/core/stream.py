import cv2
import numpy as np
from typing import Optional

from demo.config.settings import CAMERA_INDEX, CAMERA_BACKEND

__all__ = ["StreamManager"]

class StreamManager:
    """단순 OpenCV VideoCapture 기반 스트림 매니저.

    * 별도 스레드 없이 호출 시점에 바로 캡처를 읽어 옵니다.
    * app.py 가 기대하는 API(start_stream/is_active/get_frame/stop)를 유지합니다.
    """

    def __init__(self, camera_index: int = CAMERA_INDEX, camera_backend: int = CAMERA_BACKEND):
        self.camera_index = camera_index
        self.camera_backend = camera_backend
        self.cap: Optional[cv2.VideoCapture] = None

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------
    def start_stream(self):
        """카메라를 열고 스트림을 시작합니다."""
        if self.cap is not None and self.cap.isOpened():
            return

        self.cap = cv2.VideoCapture(self.camera_index, self.camera_backend)
        if not self.cap.isOpened():
            print(f"[Stream] ❌ 카메라 열기 실패 (index={self.camera_index}, backend={self.camera_backend})")
            self.cap.release()
            self.cap = None
        else:
            # 지연 최소화를 위해 버퍼 크기 1 로 설정 (지원되는 백엔드 한정)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            print(f"[Stream] ✅ 카메라 열림 (index={self.camera_index})")

    def stop(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("[Stream] 📷 카메라 종료")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def is_active(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def get_frame(self):
        if not self.is_active():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    # (blank_frame 메서드 삭제 – 더 이상 사용하지 않음)
    