# Real-Time Intrusion Detection Pipeline

This repository implements a four-stage end-to-end system for detecting and responding to unauthorized entry:

1. **CSI-Based Presence Detection**  
   Continuously monitor WiFi CSI (Channel State Information) to detect door openings or human entry.

2. **Intruder Localization**  
   Analyze phase and amplitude shifts to approximate the intruder's position in the room.

3. **Real-Time Human Detection & Tracking**  
   - **YOLOv10 (ONNX)** for lightweight, real-time person bounding-box detection  
   - **WebRTC + fastrtc** pipeline to stream processed frames back to the browser  

4. **Activity Visualization & Alerting**  
   - Real-time Plotly graphs driven by CSI-based activity metrics  
   - Optional MQTT trigger (`ptz/trigger`) for external PTZ or alarm systems  

5. **Logging & Anomaly Alerts**  
   Record intrusion events and push activity logs/alerts to the dashboard or mobile.

By combining wireless sensing, computer vision, and intelligent logging, this pipeline delivers robust, automated intrusion monitoring in real time.

## 프로젝트 전체 실행 흐름·구조 요약

### 진입점 - `demo/app.py`
1) HF Hub에서 YOLOv10 모델을 내려받아 `YOLOv10` 클래스로 로드합니다.  
2) `detection(frame, conf)` – 영상 한 프레임을 받아 객체를 검출하고 결과 이미지를 반환하는 핸들러를 정의합니다.  
3) WebRTC용 `Stream`(`fastrtc`)을 생성해  
   - 모드: `send-receive` (사용자 → 서버 → 사용자)  
   - 핸들러: 위 `detection`  
   - 추가 입력: Gradio 슬라이더(신뢰도 임계값)  
4) `FastAPI()` 인스턴스를 만들고 `stream.mount(fastapi_app)`로 WebRTC 관련 URL(`/webrtc/*`)을 자동 등록합니다.  
5) `socketio.AsyncServer` 를 같은 FastAPI 앱에 래핑해(ASGIApp) Socket.IO 네임스페이스 `/csi` 를 제공합니다.  
6) `CADAService` 를 초기화·시작하여 이후 CSI(무선 채널 정보) 기반 활동 탐지 파이프라인을 구동합니다.

### CADAService 계층 (`demo/services/cada.py`)
1) `RealtimeCSIBufferManager`: 센서별 CSI 버퍼 및 특징 버퍼 유지.  
2) `SlidingCadaProcessor`: 320-프레임 슬라이딩 윈도를 40프레임 간격으로 추출해 CADA 모델에 투입, 활동 점수·임계값·플래그 산출.  
3) `MQTTManager`: 브로커(`BROKER_ADDR`, `BROKER_PORT`)에 접속, 지정 토픽으로부터 CSI 문자열을 수신 → 파싱·정규화 후 버퍼에 넣고 Processor 호출.  
4) Processor 결과가 나오면 Socket.IO로 `cada_result` 이벤트 전송(네임스페이스 `/csi`).

### 프런트엔드 - `demo/templates/index.html`
- 페이지 로딩 시 `navigator.mediaDevices.getUserMedia()` 로 카메라 스트림 확보 → `RTCPeerConnection` 생성.  
- `/webrtc/offer` 엔드포인트로 SDP 오퍼를 보내 WebRTC 세션을 수립하여  
  원본 영상 트랙과 서버가 돌려주는 검출 영상 트랙(핸들러 결과)을 하나의 연결로 전달받습니다.  
- 슬라이더를 움직이면 `/input_hook`(FastAPI) 로 임계값을 POST → 서버의 `stream.set_input()`으로 실시간 반영.  
- Socket.IO 클라이언트로 `/csi` 네임스페이스에 접속, `cada_result` 메시지를 수신하면 Plotly 그래프로 실시간 시각화합니다.

### YOLOv10 구현 - `src/utils.py`
- ONNX Runtime 세션을 생성하고 입력–출력 텐서를 관리합니다.  
- `detect_objects()` : 전처리 → 추론 → NMS → 바운딩박스 그리기.

### 기타 보조 모듈
- `demo/core/stream.py` : 로컬 Webcam 캡처용 `StreamManager`(현재 사용 안 함).  
- `demo/config/settings.py` : 모델 디바이스, 카메라·MQTT·CSI 파라미터 등 전역 설정.

### 전체 실행 순서
1) `python demo/app.py` (또는 `uvicorn`) → FastAPI + Socket.IO ASGI 서버 기동.  
2) 브라우저가 `/` 접속 → `index.html` 반환.  
3) JS 가 WebRTC 세션을 열고 영상 프레임을 전송.  
4) 서버 `Stream` 객체가 프레임마다 `detection()` 실행 후 결과 영상을 WebRTC 반환.  
5) 동시에 MQTT → CADA 파이프라인이 CSI 신호를 처리, 활동 지표를 Socket.IO 로 Push.  
6) 프런트엔드는 Plotly 그래프와 Bounding Box가 입혀진 영상을 실시간으로 표시합니다.

이처럼 영상·무선 두 스트림이 비동기적으로 처리되며, 서버는 FastAPI 한 프로세스 안에서 WebRTC (`fastrtc`), Socket.IO (`python-socketio`), MQTT (`paho`), YOLO 추론, CADA 활동 탐지를 동시에 수행합니다.

## Setup Instructions
I recommend using uv venv to create isolated environments, simplifying dependency management and ensuring reproducible setups.

### 1. Clone the repository
```bash
git clone https://github.com/kdy1493/CADA_async.git
cd CADA_async
```

### 2. Create & activate virtualenv
```bash
# Install the 'uv' CLI and create a new venv
pip install uv
uv venv

# On macOS / Linux
source .venv/bin/activate
# On Windows (PowerShell)
source .venv/Scripts/activate
```

### 3. Install packages
```bash
# Install project and dependencies in editable mode
uv pip install -e .

# (Optional) If you want GPU acceleration, install the appropriate PyTorch build BEFORE this step, e.g.
# uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Download SAM2 Checkpoints
```bash
cd checkpoints
./download_ckpts.sh
cd ..
```

---

## Usage
### Web Application
Run the web application for real-time human detection and tracking:

```bash
python .\demo\app.py
```

After running, access the web interface at `http://localhost:5000`.


### MQTT Configuration
To use the CSI-based presence detection feature, you need to configure your MQTT broker settings in `demo/config/settings.py`:

```python
BROKER_ADDR = "your_broker_address"
BROKER_PORT = your_broker_port
```

The repository includes default topic configurations for ESP32 devices, but you can modify these settings according to your specific MQTT setup.

### Customization
You can customize various settings in `demo/config/settings.py`:

- **Camera Settings**: change `CAMERA_INDEX` to select the default webcam (or RTSP stream)
- **CSI / MQTT Settings**: update `BROKER_ADDR`, `BROKER_PORT`, `CSI_TOPIC` to match your broker & devices
- **Model Settings**: to switch to a different YOLOv10 variant, change the HF repo or local ONNX file path in `demo/app.py`
- **Detection Thresholds**: tweak the default `conf_threshold` or remove the Gradio slider if you prefer a fixed value

### PTZ / Trigger Integration
If you have a PTZ camera or external alarm system listening on the `ptz/trigger` topic, the server will publish `1` (ON) when activity is detected and `0` (OFF) after inactivity. Modify `demo/utils/mqtt_manager.py` for custom logic.

### Acknowledgment
This project leverages:  
- **YOLOv10** (ONNX) by the ONNX Community for efficient real-time object detection  
- **fastrtc** for minimal-boilerplate WebRTC in Python  
- **python-socketio** for low-latency event delivery  
- **Plotly** for interactive, in-browser visualization

## Citation
```
@misc{yolov10_2024,
  title={YOLOv10: A Lightweight, Fast and Accurate Object Detector},
  author={ONNX Community},
  year={2024},
  url={https://github.com/onnx/models}
}
```

---
