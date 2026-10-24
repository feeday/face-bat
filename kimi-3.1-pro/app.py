from __future__ import annotations

import hashlib
import os
import threading
import time
import webbrowser
from pathlib import Path

import cv2
import numpy as np
import requests
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / ".models"
MAX_IMAGE_BYTES = 6 * 1024 * 1024
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
COSINE_THRESHOLD = 0.363
MODEL_SPECS = {
    "face_detection_yunet_2023mar.onnx": {
        "sha256": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        "urls": [
            "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
            "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
            "https://hf-mirror.com/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
        ],
    },
    "face_recognition_sface_2021dec.onnx": {
        "sha256": "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
        "urls": [
            "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
            "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
            "https://hf-mirror.com/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
        ],
    },
}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 13 * 1024 * 1024


class FaceEngine:
    def __init__(self) -> None:
        self._detector = None
        self._recognizer = None
        self._lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @staticmethod
    def _download(name: str) -> Path:
        MODEL_DIR.mkdir(exist_ok=True)
        target = MODEL_DIR / name
        spec = MODEL_SPECS[name]

        def valid(path: Path) -> bool:
            if not path.exists():
                return False
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest() == spec["sha256"]

        if valid(target):
            return target
        target.unlink(missing_ok=True)
        partial = target.with_suffix(".download")
        errors = []
        for url in spec["urls"]:
            print(f"[模型] 正在下载 {name}，仅首次运行需要……", flush=True)
            try:
                digest = hashlib.sha256()
                with requests.get(url, stream=True, timeout=(15, 180)) as response:
                    response.raise_for_status()
                    with partial.open("wb") as output:
                        for chunk in response.iter_content(1024 * 256):
                            if chunk:
                                output.write(chunk)
                                digest.update(chunk)
                if digest.hexdigest() != spec["sha256"]:
                    raise RuntimeError("模型校验失败")
                partial.replace(target)
                return target
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                partial.unlink(missing_ok=True)
        raise RuntimeError("所有模型下载源均不可用；" + " | ".join(errors))

    def load(self) -> None:
        if self._detector is not None:
            return
        with self._lock:
            if self._detector is not None:
                return
            try:
                detector_path = self._download("face_detection_yunet_2023mar.onnx")
                recognizer_path = self._download("face_recognition_sface_2021dec.onnx")
                detector = cv2.FaceDetectorYN_create(
                    str(detector_path), "", (320, 320), 0.7, 0.3, 5000
                )
                recognizer = cv2.FaceRecognizerSF_create(str(recognizer_path), "")
                self._detector = detector
                self._recognizer = recognizer
                print("[模型] 人脸检测与特征提取模型已就绪。", flush=True)
            except Exception as exc:
                raise RuntimeError(
                    f"模型初始化失败：{exc}。请检查网络能否访问 GitHub，然后重试。"
                ) from exc

    def extract(self, image: np.ndarray) -> tuple[np.ndarray, dict]:
        self.load()
        assert self._detector is not None and self._recognizer is not None
        height, width = image.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(image)
        if faces is None or len(faces) == 0:
            raise ValueError("未检测到人脸，请使用五官清晰、无遮挡的正面照片。")
        face = max(faces, key=lambda item: float(item[2] * item[3]))
        aligned = self._recognizer.alignCrop(image, face)
        feature = self._recognizer.feature(aligned)
        x, y, w, h = (float(value) for value in face[:4])
        info = {
            "face_count": int(len(faces)),
            "box": {
                "x": max(0, round(x, 1)),
                "y": max(0, round(y, 1)),
                "width": round(w, 1),
                "height": round(h, 1),
            },
        }
        return feature, info

    def compare(self, image_a: np.ndarray, image_b: np.ndarray) -> dict:
        with self._inference_lock:
            try:
                feature_a, info_a = self.extract(image_a)
            except ValueError as exc:
                raise ValueError(f"图片 A：{exc}") from exc
            try:
                feature_b, info_b = self.extract(image_b)
            except ValueError as exc:
                raise ValueError(f"图片 B：{exc}") from exc
            assert self._recognizer is not None
            cosine = float(
                self._recognizer.match(
                    feature_a, feature_b, cv2.FaceRecognizerSF_FR_COSINE
                )
            )
        similarity = round(max(0.0, min(1.0, cosine)) * 100, 1)
        return {
            "similarity": similarity,
            "cosine": round(cosine, 4),
            "threshold": COSINE_THRESHOLD,
            "same_person": cosine >= COSINE_THRESHOLD,
            "image_a": info_a,
            "image_b": info_b,
            "note": "结果仅用于辅助比对，不代表身份鉴定结论。",
        }


engine = FaceEngine()


def decode_image(upload) -> np.ndarray:
    if upload is None or not upload.filename:
        raise ValueError("请选择两张图片后再开始对比。")
    if upload.mimetype not in ALLOWED_MIMES:
        raise ValueError("仅支持 JPG、PNG、WEBP 或 BMP 图片。")
    data = upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("单张图片不能超过 6 MB。")
    if not data:
        raise ValueError("图片内容为空，请重新选择。")
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("图片无法读取，请更换有效的图片文件。")
    if image.shape[0] * image.shape[1] > 30_000_000:
        raise ValueError("图片像素过大，请压缩到 3000 万像素以内。")
    return image


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "model_loaded": engine._detector is not None})


@app.post("/api/compare")
def compare():
    try:
        image_a = decode_image(request.files.get("image_a"))
        image_b = decode_image(request.files.get("image_b"))
        result = engine.compare(image_a, image_b)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        app.logger.exception("Face comparison failed")
        return jsonify({"error": f"对比失败：{exc}"}), 500


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(_):
    return jsonify({"error": "图片总大小超过限制，请压缩后重试。"}), 413


def open_browser_later(url: str) -> None:
    time.sleep(1.2)
    webbrowser.open(url)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    public_docker = os.environ.get("DOCKER", "") == "1"
    host = "0.0.0.0" if public_docker else "127.0.0.1"
    try:
        engine.load()
    except RuntimeError as exc:
        print(str(exc), flush=True)
        raise SystemExit(1) from exc
    url = f"http://127.0.0.1:{port}"
    print(f"\n人脸相似度对比已启动：{url}\n按 Ctrl+C 可停止服务。\n", flush=True)
    if not public_docker and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=open_browser_later, args=(url,), daemon=True).start()
    app.run(host=host, port=port, debug=False, threaded=True)
