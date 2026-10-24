# Kimi-3.1-pro 版本

作者归属由用户确认。app.py、index.html、requirements.txt 保留附件内容。

- Windows：双击 start.bat。它是后续修复版，仅在依赖安装阶段绕过失效代理，并在清华源失败时尝试官方源。
- start-original.bat：原始附件启动脚本，用于比较；存在失效代理导致安装失败的问题。
- 两个 BAT 都内嵌程序，启动时会覆盖同目录 app.py、index.html、requirements.txt。修改源码后请直接运行 `.venv\Scripts\python.exe app.py`，或同步重建 BAT，避免改动被覆盖。
- 默认端口 5000；被占用时可先在 CMD 设置 `set PORT=5001`，再运行。
- 单张图片最多 6 MB；多人照片自动选最大人脸。

对比和验证范围见仓库根目录 COMPARISON.md。
