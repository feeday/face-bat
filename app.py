import base64
import os
from pathlib import Path
import threading
import urllib.request
import webbrowser

import cv2
import numpy as np
from flask import Flask, request, render_template_string
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / 'models'
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 24 * 1024 * 1024
lock = threading.Lock()
PAGE = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>人脸相似度对比</title><style>body{font-family:system-ui;background:#edf2f7;color:#19283d;max-width:900px;margin:45px auto;padding:20px}main{background:white;padding:30px;border-radius:20px}section{display:flex;gap:24px;flex-wrap:wrap}.card{flex:1;min-width:240px;padding:18px;background:#f4f7fc;border-radius:12px}img.preview{width:100%;height:250px;object-fit:contain}button{background:#2665db;color:white;border:0;border-radius:9px;padding:14px 26px;margin-top:20px;cursor:pointer}.error{color:#b42318}.score{font-size:34px;font-weight:bold}input{max-width:100%}small{color:#52637a}</style><main><h1>两张照片 · 人脸相似度</h1><p>本机处理，选择两张清晰的单人人脸照片。</p><form method="post" enctype="multipart/form-data"><section>{% for i in [1,2] %}<div class="card"><h3>照片 {{i}}</h3><input required type="file" name="image{{i}}" accept="image/*" onchange="preview(this,'p{{i}}')"><p><img class="preview" id="p{{i}}" {% if originals %}src="{{ originals[i-1] }}"{% endif %}></p></div>{% endfor %}</section><p>参考阈值：<input name="threshold" type="number" min="-1" max="1" step="0.001" value="{{ threshold }}"></p><button id="run" type="submit">开始对比</button></form>{% if error %}<p class="error">{{ error }}</p>{% endif %}{% if score is not none %}<hr><div class="score">余弦相似度 {{ '%.4f'|format(score) }}</div><p>{{ verdict }}（阈值 {{ threshold }}）</p><section>{% for face in faces %}<div class="card"><img width="160" src="{{ face }}"><p>实际参与对比的人脸 {{ loop.index }}</p></div>{% endfor %}</section>{% endif %}<p><small>相似度不是“同一人的概率”，不可直接解释成准确率。光照、侧脸、遮挡和生成图片都会影响结果。默认 0.363 来自 OpenCV SFace 的 LFW 参考阈值，可按你的数据调整。</small></p><small>关闭启动窗口即可停止服务。模型首次下载后可离线使用。</small></main><script>function preview(input,id){if(input.files[0]){const r=new FileReader();r.onload=()=>document.getElementById(id).src=r.result;r.readAsDataURL(input.files[0]);}}document.querySelector('form').onsubmit=()=>{document.getElementById('run').textContent='正在对比…';};</script></html>'''

def download_models():
    MODELS.mkdir(exist_ok=True)
    for name, minimum in [('face_detection_yunet_2023mar.onnx', 200000), ('face_recognition_sface_2021dec.onnx', 30000000)]:
        target = MODELS / name
        if target.exists() and target.stat().st_size >= minimum:
            continue
        folder = 'face_detection_yunet' if 'yunet' in name else 'face_recognition_sface'
        url = f'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/{folder}/{name}'
        print(f'Downloading {name} ...', flush=True)
        temp = target.with_suffix('.part')
        try:
            with urllib.request.urlopen(url, timeout=120) as src, temp.open('wb') as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            if temp.stat().st_size < minimum:
                raise RuntimeError('下载内容不完整，请检查网络，或按 README 手动下载模型。')
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)

def data_url(bgr):
    ok, buf = cv2.imencode('.jpg', bgr)
    if not ok:
        raise ValueError('图像编码失败')
    return 'data:image/jpeg;base64,' + base64.b64encode(buf).decode('ascii')

def load_image(upload):
    if not upload or not upload.filename:
        raise ValueError('请选择两张照片。')
    with Image.open(upload.stream) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
        im.thumbnail((1600, 1600))
        return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)

def extract(image, label):
    detector.setInputSize((image.shape[1], image.shape[0]))
    _, detected = detector.detect(image)
    if detected is None or len(detected) == 0:
        raise ValueError(f'{label}未检测到人脸，请使用清晰、正面或轻微侧脸的照片。')
    if len(detected) != 1:
        raise ValueError(f'{label}检测到 {len(detected)} 张人脸，请先裁剪为单人照。')
    aligned = recognizer.alignCrop(image, detected[0])
    return recognizer.feature(aligned), aligned

@app.route('/', methods=['GET', 'POST'])
def index():
    score, error, faces, originals = None, None, [], []
    threshold = 0.363
    if request.method == 'POST':
        try:
            threshold = float(request.form.get('threshold', '0.363'))
            if not np.isfinite(threshold) or not -1 <= threshold <= 1:
                raise ValueError('阈值必须在 -1 到 1 之间。')
            images = [load_image(request.files.get(f'image{i}')) for i in (1, 2)]
            originals = [data_url(im) for im in images]
            with lock:
                a, ac = extract(images[0], '照片 1')
                b, bc = extract(images[1], '照片 2')
                score = float(recognizer.match(a, b, cv2.FaceRecognizerSF_FR_COSINE))
            faces = [data_url(ac), data_url(bc)]
        except Exception as exc:
            error = str(exc)
    verdict = '达到同一人参考阈值' if score is not None and score >= threshold else '未达到同一人参考阈值'
    return render_template_string(PAGE, score=score, error=error, faces=faces, originals=originals, threshold=threshold, verdict=verdict)

@app.errorhandler(413)
def too_large(_):
    return render_template_string(PAGE, score=None, error='两张图片合计请小于 24 MB。', originals=[], faces=[], threshold=0.363), 413

if __name__ == '__main__':
    download_models()
    detector = cv2.FaceDetectorYN.create(str(MODELS / 'face_detection_yunet_2023mar.onnx'), '', (320, 320), 0.8, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(MODELS / 'face_recognition_sface_2021dec.onnx'), '')
    from waitress.server import create_server
    # Port 0 asks Windows to allocate an available ephemeral port.
    server = create_server(app, host='127.0.0.1', port=0, threads=2)
    port = server.socket.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    print(f'Open {url}   Close this window to stop.', flush=True)
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    server.run()
