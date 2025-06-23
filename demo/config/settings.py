import os
import torch
import cv2

# Device selection for model inference
# Options: "cuda:0" for GPU, "cpu" for CPU
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

# Web server settings
HOST = '0.0.0.0'
PORT = 5001
DEBUG = True

# Camera settings
CAMERA_INDEX = 0
CAMERA_BACKEND = cv2.CAP_DSHOW

# Camera streaming settingsAdd commentMore actions
STREAM_URL = "rtsp://61.252.57.136:4991/stream"
BROKER_ADDR = "61.252.57.136"
BROKER_PORT = 4991


CSI_TOPIC = ["L0382/ESP/8"]
# CSI MQTT settings
CSI_TOPICS = [
    "L0382/ESP/1",
    "L0382/ESP/2",
    "L0382/ESP/3",
    "L0382/ESP/4",
    "L0382/ESP/5",
    "L0382/ESP/6",
    "L0382/ESP/7",
    "L0382/ESP/8",
]
CSI_INDICES_TO_REMOVE = list(range(21, 32))
CSI_SUBCARRIERS = 52
CSI_WINDOW_SIZE = 320
CSI_STRIDE = 40
CSI_SMALL_WIN_SIZE = 64
CSI_FPS_LIMIT = 10