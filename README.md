# Uvicorn GUI Launcher

轻量级 PyQt6 桌面工具，用于启动/停止 Uvicorn（单入口 FastAPI/ASGI 项目）。支持 `--reload` 与可靠的进程清理，适合本地开发快速启动。

A lightweight PyQt6 desktop tool to start/stop Uvicorn for a single FastAPI (or ASGI) entry file. Built for quick local development with optional `--reload` and clean shutdown.

## Features / 功能

- 选择 Python 解释器（`python.exe`）和入口文件（`main.py`）
- 自动解析入口文件中的 app 对象名
- 一键启动/停止 Uvicorn，支持热重载
- 进程树清理，避免残留 `python` 进程
- 简洁的控制台输出查看

- Pick Python interpreter (`python.exe`) and entry file (`main.py`)
- Auto-detect app object names from the selected file
- Start/stop Uvicorn with optional hot reload
- Process tree cleanup to avoid orphaned `python` processes
- Simple console output viewer

## Requirements / 环境要求

- Python 3.9+
- PyQt6
- Uvicorn（以及你的 ASGI 应用）

Install:

```
pip install PyQt6 uvicorn
```

## Usage / 使用方法

### Run the GUI / 启动 GUI

```
python uvicorn_gui.py
```

### Steps / 步骤

1. Select your Python interpreter. / 选择 Python 解释器
2. Choose your entry file (e.g., `main.py`). / 选择入口文件
3. Pick the app object (e.g., `app`). / 选择 app 对象
4. Set host/port and click **Start**. / 设置 Host/Port 后点击 **Start**

## Notes / 注意事项

- **Host** 仅填写主机名或 IP（如 `127.0.0.1`、`0.0.0.0`），不要包含协议或端口。
- GUI 通过子进程运行 Uvicorn，停止时会清理进程树。
- Windows 体验最佳，停止逻辑也兼容类 Unix 系统。

- **Host** should be a hostname or IP only (e.g., `127.0.0.1`, `0.0.0.0`). Do not include protocol or port.
- The GUI runs Uvicorn in a child process and performs process-tree cleanup on stop.
- Works best on Windows, but the stop logic also supports Unix-like systems.
