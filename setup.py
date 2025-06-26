# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
import os

from setuptools import find_packages, setup

# Package metadata
NAME = "DEMO"
VERSION = "1.0"
DESCRIPTION = "SAM 2 Human Detection Demo"
URL = "https://github.com/NVA-Lab/intrusion-detector.git"
AUTHOR = "KIST-NVA Lab"
AUTHOR_EMAIL = "yeonjae.jeong@kist.re.kr"
LICENSE = "Apache 2.0"

# Read the contents of README file
with open("README.md", "r", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

BUILD_CUDA = os.getenv("SAM2_BUILD_CUDA", "1") == "1"
BUILD_ALLOW_ERRORS = os.getenv("SAM2_BUILD_ALLOW_ERRORS", "1") == "1"

CUDA_ERROR_MSG = (
    "{}\n\n"
    "Failed to build the SAM 2 CUDA extension due to the error above. "
    "You can still use SAM 2 and it's OK to ignore the error above, although some "
    "post-processing functionality may be limited (which doesn't affect the results in most cases; "
    "(see https://github.com/facebookresearch/sam2/blob/main/INSTALL.md).\n"
)


def get_extensions():
    if not BUILD_CUDA:
        return []

    try:
        from torch.utils.cpp_extension import CUDAExtension

        srcs = ["sam2/csrc/connected_components.cu"]
        compile_args = {
            "cxx": [],
            "nvcc": [
                "-DCUDA_HAS_FP16=1",
                "-D__CUDA_NO_HALF_OPERATORS__",
                "-D__CUDA_NO_HALF_CONVERSIONS__",
                "-D__CUDA_NO_HALF2_OPERATORS__",
            ],
        }
        ext_modules = [CUDAExtension("sam2._C", srcs, extra_compile_args=compile_args)]
    except Exception as e:
        if BUILD_ALLOW_ERRORS:
            print(CUDA_ERROR_MSG.format(e))
            ext_modules = []
        else:
            raise e

    return ext_modules


try:
    from torch.utils.cpp_extension import BuildExtension

    class BuildExtensionIgnoreErrors(BuildExtension):

        def finalize_options(self):
            try:
                super().finalize_options()
            except Exception as e:
                print(CUDA_ERROR_MSG.format(e))
                self.extensions = []

        def build_extensions(self):
            try:
                super().build_extensions()
            except Exception as e:
                print(CUDA_ERROR_MSG.format(e))
                self.extensions = []

        def get_ext_filename(self, ext_name):
            try:
                return super().get_ext_filename(ext_name)
            except Exception as e:
                print(CUDA_ERROR_MSG.format(e))
                self.extensions = []
                return "_C.so"

    cmdclass = {
        "build_ext": (
            BuildExtensionIgnoreErrors.with_options(no_python_abi_suffix=True)
            if BUILD_ALLOW_ERRORS
            else BuildExtension.with_options(no_python_abi_suffix=True)
        )
    }
except Exception as e:
    cmdclass = {}
    if BUILD_ALLOW_ERRORS:
        print(CUDA_ERROR_MSG.format(e))
    else:
        raise e


setup(
    name="human_detection",
    version="0.1.0",
    description="Human detection + SAM2 demo",
    author="Yeonjae37",
    python_requires=">=3.10",

    package_dir={"": "src"},
    packages=find_packages(where="src"),

    install_requires=[
        # --- 필수 라이브러리 (프로젝트 코드에서 실제 사용) -------------------
        "torch>=2.3.1",
        "numpy==1.26.4",
        "opencv-python>=4.9.0.80",
        "torchvision>=0.18.1",

        # 서버 & 실시간 통신
        "flask>=3.0.3",
        "flask-socketio>=5.5.1",
        "python-socketio>=5.11.1",
        "fastapi>=0.111.0",
        "uvicorn>=0.29.0",

        # 실시간 스트리밍 / WebRTC
        "fastrtc>=0.2.5",

        # 모델 추론
        "ultralytics>=8.3.131",
        "onnxruntime>=1.18.0",

        # 데이터 처리 / 과학 연산
        "scipy>=1.15.3",
        "paho-mqtt>=2.1.0",
        "autorootcwd>=1.0.1",

        # 인터랙티브 데모 & UI
        "gradio>=4.38.0",

        # 기타 유틸
        "huggingface_hub>=0.19.0",
        "pydantic>=2.7.1",
        "fastapi>=0.115.13",
        "fastrtc>=0.0.28",
        "gradio>=5.34.2",
        "onnxruntime>=1.22.0",
    ],

    extras_require={
        "dev": [
            "black",
            "ruff",
        ],
        "tensorrt": [
            "tensorrt>=8.6.0",
            "pycuda>=2024.1",
            "onnx>=1.15.0",
            "onnxruntime-gpu>=1.16.0",
        ]
    },
)