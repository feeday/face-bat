# 人脸相似度对比：GPT 与 Kimi 两版本

两套独立实现，作者归属由用户确认。两者使用 OpenCV YuNet 检测与 SFace 特征匹配，不是两种不同的人脸识别模型。

| 目录 | 来源 | Windows 入口 |
| --- | --- | --- |
| [gpt-6.1-sol](gpt-6.1-sol/) | 仓库原有版本 | `gpt-6.1-sol/start.bat` |
| [kimi-3.1-pro](kimi-3.1-pro/) | 用户本次附件 | `kimi-3.1-pro/start.bat` |

[代码与 UI 对比](COMPARISON.md)

根目录 app.py、requirements.txt、start.bat 保留原有 GPT 版本，兼容已有使用方式。推荐进入对应目录启动，虚拟环境与模型缓存各自独立。

GPT 版启动后自动分配空闲端口，以终端实际输出为准；其目录内原始 README 曾写固定 7860，已经过时。Kimi 默认 5000。

Kimi 同时保留原始 BAT 与后续代理修复 BAT，详见其 README。此次整理未合并两套推理代码，也未把修复后的启动脚本算作原模型能力。

首次运行需要联网安装依赖、下载模型；之后照片在本机处理。识别分数不是同一人概率。验证范围与已知缺陷见对比文档。
