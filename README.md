Windows 人脸相似度对比

1. 安装 Python 3.11 64位（推荐），勾选 Add Python to PATH。
2. 解压整个文件夹，双击 start.bat；不要在压缩包内直接运行。
3. 首次自动在本文件夹创建 .venv，安装依赖并下载约 39 MB 模型。
4. 浏览器自动打开 http://127.0.0.1:7860，选择两张照片，点击开始对比。
5. 之后双击 start.bat 即可；关闭命令行窗口停止。

不需要显卡、CUDA、API Key。支持 Python 3.10—3.12 64位。
照片只在本机内存处理，程序不保存上传照片，不启用公网分享。
端口被占用时，关闭之前的程序后重试。
如果 pip 下载失败，可配置你信任的 pip 镜像后重试。
若模型下载失败，可手动把以下文件保存到 models 子文件夹，再运行：
https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx
请下载实际 ONNX 二进制文件，不要保存 Git LFS 指针文本或网页。

检测：YuNet；特征匹配：SFace；相似度为原始余弦值，越高越相似。
默认 0.363 是 OpenCV 在 LFW 上的参考阈值，并非适用于所有数据。
相似度不是同一人概率，也不代表生成图片的整体质量。
多人照片必须先裁剪，界面展示实际参与匹配的对齐人脸。

官方说明与模型许可：
https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html
https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
如用于商业交付，请查看以上模型目录的许可证与使用说明。

验证范围：交付前完成 Python 语法和网页模板检查；当前环境无法运行 Windows BAT、下载模型实测。
