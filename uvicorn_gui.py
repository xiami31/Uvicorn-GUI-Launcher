import ast
import ipaddress
import os
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QProcess, QTimer, Qt
from PyQt6.QtGui import QMouseEvent, QColor, QFont, QIcon, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
    QGridLayout,
)

# ==========================================
#   样式表 (StyleSheet)
# ==========================================
PRO_STYLESHEET = """
/* 1. 主容器 */
#MainContainer {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
}

/* 2. 标题栏 */
#TitleBar {
    background-color: transparent;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    border-bottom: 1px solid #F3F4F6;
}
QLabel#app_title {
    color: #374151;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
    font-weight: 700;
    padding-left: 8px;
}
QLabel#status_badge {
    color: #9CA3AF;
    font-size: 9pt;
    font-weight: 600;
    padding-right: 8px;
}

/* 3. 窗口控制按钮 */
QPushButton#win_btn {
    background-color: transparent;
    border: none;
    color: #6B7280;
    border-radius: 4px;
    font-size: 12px;
    margin: 4px;
}
QPushButton#win_btn:hover { background-color: #F3F4F6; color: #111827; }
QPushButton#close_btn:hover { background-color: #EF4444; color: white; }

/* 4. 通用标签 */
QLabel.field_label {
    color: #6B7280;
    font-size: 9pt;
    font-weight: 600;
}

/* 5. 输入控件 */
QLineEdit, QSpinBox, QComboBox {
    background-color: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1F2937;
    font-family: 'Consolas', monospace;
    font-size: 10pt;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    background-color: #FFFFFF;
    border-color: #3B82F6;
}
QLineEdit:read-only {
    color: #6B7280;
    background-color: #F3F4F6;
}

/* 6. 按钮 */
QPushButton {
    border-radius: 6px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}
/* 浏览按钮 */
QPushButton#browse_btn {
    background-color: white;
    border: 1px solid #D1D5DB;
    color: #4B5563;
}
QPushButton#browse_btn:hover {
    background-color: #F9FAFB;
    border-color: #9CA3AF;
    color: #111827;
}
/* 启动按钮 */
QPushButton#action_btn_start {
    background-color: #2563EB; 
    color: white;
    border: none;
    padding: 8px 30px;
    font-size: 10pt;
}
QPushButton#action_btn_start:hover { background-color: #1D4ED8; }

/* 停止按钮 */
QPushButton#action_btn_stop {
    background-color: #DC2626;
    color: white;
    border: none;
    padding: 8px 30px;
    font-size: 10pt;
}
QPushButton#action_btn_stop:hover { background-color: #B91C1C; }

/* 7. 日志区域 */
/* 日志工具栏 */
QFrame#LogToolbar {
    background-color: #F9FAFB;
    border-top: 1px solid #E5E7EB;
    border-left: 1px solid #E5E7EB;
    border-right: 1px solid #E5E7EB;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QLabel#log_title {
    color: #6B7280;
    font-weight: bold;
    font-size: 9pt;
    padding-left: 5px;
}
/* 清空按钮 (工具栏内) */
QPushButton#toolbar_clear_btn {
    background-color: transparent;
    color: #6B7280;
    border: none;
    font-size: 9pt;
    padding: 4px 10px;
}
QPushButton#toolbar_clear_btn:hover {
    background-color: #E5E7EB;
    color: #374151;
    border-radius: 4px;
}

/* 日志内容 */
QPlainTextEdit {
    background-color: #111827;
    border: 1px solid #E5E7EB;
    border-top: none; /* 顶部与工具栏融合 */
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
    font-family: 'Consolas', monospace;
    color: #E5E7EB;
    padding: 12px;
    font-size: 9.5pt;
}

QCheckBox { color: #4B5563; font-weight: 500; }
"""


class AppParser:
    @staticmethod
    def parse_file(file_path: str) -> list[str]:
        variables = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=file_path)
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append(target.id)
        except Exception:
            pass
        priority = ['app', 'server', 'api', 'main', 'application']
        variables.sort(key=lambda x: (x not in priority, x))
        return variables


class UvicornController(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Uvicorn Launcher")
        self.resize(720, 550)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.old_pos = None
        self.work_dir = ""
        self.module_stem = ""
        self.last_pid = 0

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.started.connect(self.on_started)
        self.process.finished.connect(self.on_finished)
        self.process.readyReadStandardOutput.connect(self.on_output)

        self._init_ui()
        self._init_tray()
        self._init_defaults()

    def _init_defaults(self):
        if not getattr(sys, "frozen", False):
            self.set_python_path(sys.executable)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout_base = QVBoxLayout(central)
        layout_base.setContentsMargins(10, 10, 10, 10)

        # 1. 主容器
        self.container = QFrame()
        self.container.setObjectName("MainContainer")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.container.setGraphicsEffect(shadow)

        layout_container = QVBoxLayout(self.container)
        layout_container.setContentsMargins(0, 0, 0, 0)
        layout_container.setSpacing(0)

        # === A. 标题栏 ===
        header = QFrame()
        header.setObjectName("TitleBar")
        header.setFixedHeight(38)
        header.mouseMoveEvent = self.mouseMoveEvent
        header.mousePressEvent = self.mousePressEvent

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 6, 0)

        self.title_label = QLabel("Uvicorn Launcher")
        self.title_label.setObjectName("app_title")

        self.status_label = QLabel("● 就绪")
        self.status_label.setObjectName("status_badge")

        btn_min = QPushButton("－")
        btn_min.setObjectName("win_btn")
        btn_min.setFixedSize(28, 28)
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("win_btn")
        btn_close.setObjectName("close_btn")
        btn_close.setFixedSize(28, 28)
        btn_close.clicked.connect(self.close)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        header_layout.addWidget(btn_min)
        header_layout.addWidget(btn_close)

        # === B. 控制面板区 ===
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(20, 20, 20, 10)
        control_layout.setSpacing(15)

        # Row 0: Python
        py_layout = QHBoxLayout()
        py_layout.setSpacing(10)

        self.python_input = QLineEdit()
        self.python_input.setPlaceholderText("选择 Python 解释器 (python.exe)")
        self.python_input.setFixedHeight(32)

        self.python_browse_btn = QPushButton("浏览...")
        self.python_browse_btn.setObjectName("browse_btn")
        self.python_browse_btn.setFixedSize(80, 32)
        self.python_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.python_browse_btn.clicked.connect(self.browse_python)

        py_layout.addWidget(self.python_input)
        py_layout.addWidget(self.python_browse_btn)

        # Row 1: File
        file_layout = QHBoxLayout()
        file_layout.setSpacing(10)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择 Python 入口文件...")
        self.path_input.setReadOnly(True)
        self.path_input.setFixedHeight(32)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setObjectName("browse_btn")
        self.browse_btn.setFixedSize(80, 32)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self.browse_file)

        file_layout.addWidget(self.path_input)
        file_layout.addWidget(self.browse_btn)

        # Row 2: Grid
        grid = QGridLayout()
        grid.setVerticalSpacing(5)
        grid.setHorizontalSpacing(15)

        l1 = QLabel("App 对象")
        l1.setProperty("class", "field_label")
        l2 = QLabel("Host")
        l2.setProperty("class", "field_label")
        l3 = QLabel("Port")
        l3.setProperty("class", "field_label")

        self.app_combo = QComboBox()
        self.app_combo.setEditable(True)
        self.app_combo.setPlaceholderText("e.g. app")
        self.app_combo.setFixedHeight(32)

        self.host_input = QLineEdit("127.0.0.1")
        self.host_input.setFixedHeight(32)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8000)
        self.port_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.port_input.setFixedHeight(32)

        grid.addWidget(l1, 0, 0)
        grid.addWidget(l2, 0, 1)
        grid.addWidget(l3, 0, 2)
        grid.addWidget(self.app_combo, 1, 0)
        grid.addWidget(self.host_input, 1, 1)
        grid.addWidget(self.port_input, 1, 2)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # Row 3: Actions
        action_layout = QHBoxLayout()

        self.reload_check = QCheckBox("开启热重载 (Auto Reload)")
        self.reload_check.setChecked(True)

        self.main_btn = QPushButton("启动服务")
        self.main_btn.setObjectName("action_btn_start")
        self.main_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_btn.clicked.connect(self.toggle_service)

        action_layout.addWidget(self.reload_check)
        action_layout.addStretch()
        action_layout.addWidget(self.main_btn)

        control_layout.addLayout(py_layout)
        control_layout.addLayout(file_layout)
        control_layout.addLayout(grid)
        control_layout.addLayout(action_layout)

        # === C. 日志区域 (带独立工具栏) ===
        log_wrapper = QWidget()
        log_layout = QVBoxLayout(log_wrapper)
        log_layout.setContentsMargins(20, 0, 20, 20)
        log_layout.setSpacing(0)

        # C1. 日志工具栏 (Header)
        toolbar = QFrame()
        toolbar.setObjectName("LogToolbar")
        toolbar.setFixedHeight(32)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 0, 10, 0)

        lbl_log = QLabel("运行日志 (Console Output)")
        lbl_log.setObjectName("log_title")

        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.setObjectName("toolbar_clear_btn")
        self.clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(lambda: self.log_view.clear())

        toolbar_layout.addWidget(lbl_log)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.clear_btn)

        # C2. 日志内容
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("系统就绪...")
        self.log_view.setFrameShape(QFrame.Shape.NoFrame)

        log_layout.addWidget(toolbar)
        log_layout.addWidget(self.log_view)

        # 组装
        layout_container.addWidget(header)
        layout_container.addWidget(control_panel)
        layout_container.addWidget(log_wrapper, 1)

        layout_base.addWidget(self.container)
        self.setStyleSheet(PRO_STYLESHEET)

    def _init_tray(self):
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        menu = QMenu()
        menu.addAction("显示主界面", self.showNormal)
        menu.addAction("退出程序", self.exit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.showNormal() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    # --- Mouse Events (Drag) ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.old_pos = None

    # --- Logic ---
    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择入口文件", "", "Python (*.py)")
        if f: self.load_file(f)

    def browse_python(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Python 解释器",
            "",
            "Python (python.exe);;All Files (*)",
        )
        if f:
            self.set_python_path(f)

    def set_python_path(self, path: str):
        if not path:
            return
        self.python_input.setText(path)
        self.python_input.setToolTip(path)

    def guess_python_from_project(self, file_path: str) -> str:
        p = Path(file_path).resolve()
        search_roots = [p.parent, *p.parents]
        venv_names = [".venv", "venv", "env"]
        for root in search_roots:
            for name in venv_names:
                win_py = root / name / "Scripts" / "python.exe"
                if win_py.exists():
                    return str(win_py)
                nix_py = root / name / "bin" / "python"
                if nix_py.exists():
                    return str(nix_py)
        return ""

    def load_file(self, path):
        p = Path(path)
        self.work_dir = str(p.parent)
        self.module_stem = p.stem
        self.path_input.setText(p.name)
        self.path_input.setToolTip(path)

        self.app_combo.clear()
        vars = AppParser.parse_file(path)
        if vars:
            self.app_combo.addItems(vars)
            if "app" in vars: self.app_combo.setCurrentText("app")

        if not self.python_input.text().strip():
            guessed = self.guess_python_from_project(path)
            if guessed:
                self.set_python_path(guessed)

    def is_running(self) -> bool:
        return self.process.state() == QProcess.ProcessState.Running

    def toggle_service(self):
        if self.is_running():
            self.stop_service()
        else:
            self.start_service()

    def start_service(self):
        if self.is_running():
            return

        python_path = self.python_input.text().strip()
        if not python_path:
            self.log_view.appendPlainText(">> 请先选择 Python 解释器。")
            return

        if not Path(python_path).exists():
            self.log_view.appendPlainText(">> Python 路径不存在。")
            return

        app = self.app_combo.currentText().strip()
        if not self.work_dir or not app:
            self.log_view.appendPlainText(">> 请先选择入口文件与 App 对象。")
            return

        target = f"{self.module_stem}:{app}"
        host = self.host_input.text().strip() or "127.0.0.1"
        if not self._validate_host(host):
            return
        port = self.port_input.value()

        cmd = [
            python_path,
            "-m",
            "uvicorn",
            target,
            "--host",
            host,
            "--port",
            str(port),
        ]
        if self.reload_check.isChecked():
            cmd.append("--reload")

        self.process.setWorkingDirectory(self.work_dir)
        self.process.start(cmd[0], cmd[1:])
        self.log_view.appendPlainText(f">> 正在启动服务: {target}")

    def _validate_host(self, host: str) -> bool:
        if not host:
            self.log_view.appendPlainText(">> Host 不能为空。")
            return False
        if "://" in host:
            self.log_view.appendPlainText(">> Host 只需填写主机名或IP，不要包含协议。")
            return False
        if ":" in host:
            self.log_view.appendPlainText(">> Host 不要包含端口，端口请填写在 Port。")
            return False
        if any(c.isspace() for c in host):
            self.log_view.appendPlainText(">> Host 含有空白字符，请检查。")
            return False
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            try:
                socket.getaddrinfo(host, None)
                return True
            except OSError:
                self.log_view.appendPlainText(f">> Host 无法解析: {host}")
                return False

    def stop_service(self):
        if not self.is_running():
            return
        pid = self.process.processId() or self.last_pid
        if pid:
            self.last_pid = pid
        self.process.terminate()
        if pid:
            self._kill_process_tree(pid, force=False)
            QTimer.singleShot(1500, lambda p=pid: self._kill_process_tree(p, force=True))
        QTimer.singleShot(2000, self.process.kill)
        self.log_view.appendPlainText(">> 正在停止服务...")

    def _kill_process_tree(self, pid: int, force: bool):
        # Ensure uvicorn's reload child processes are also terminated.
        if not pid:
            return
        try:
            if sys.platform.startswith("win"):
                cmd = ["taskkill", "/PID", str(pid), "/T"]
                if force:
                    cmd.append("/F")
                self._run_kill_command_async(cmd)
            else:
                sig = signal.SIGKILL if force else signal.SIGTERM
                self._run_kill_command_async(["pkill", f"-{sig.name}", "-P", str(pid)])
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    return
        finally:
            pass

    def _run_kill_command_async(self, cmd: list[str]):
        def _worker():
            try:
                kwargs = {
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                }
                if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                result = subprocess.run(cmd, **kwargs)
                if result.returncode != 0:
                    QTimer.singleShot(
                        0, lambda: self.log_view.appendPlainText(f">> 结束进程失败: {' '.join(cmd)}")
                    )
            except FileNotFoundError:
                QTimer.singleShot(
                    0, lambda: self.log_view.appendPlainText(f">> 未找到命令: {cmd[0]}")
                )

        threading.Thread(target=_worker, daemon=True).start()

    def on_started(self):
        pid = self.process.processId()
        if pid:
            self.last_pid = pid
        self.status_label.setText("● 运行中")
        self.status_label.setStyleSheet("color: #10B981; font-weight: bold; padding-right: 8px;")
        self.main_btn.setText("停止服务")
        self.main_btn.setObjectName("action_btn_stop")
        self.main_btn.setStyle(self.main_btn.style())
        self.path_input.setEnabled(False)
        self.app_combo.setEnabled(False)
        self.python_input.setEnabled(False)
        self.python_browse_btn.setEnabled(False)

    def on_finished(self):
        self.status_label.setText("● 已停止")
        self.status_label.setStyleSheet("color: #9CA3AF; font-weight: bold; padding-right: 8px;")
        self.main_btn.setText("启动服务")
        self.main_btn.setObjectName("action_btn_start")
        self.main_btn.setStyle(self.main_btn.style())
        self.path_input.setEnabled(True)
        self.app_combo.setEnabled(True)
        self.python_input.setEnabled(True)
        self.python_browse_btn.setEnabled(True)
        self.log_view.appendPlainText(">> 服务已退出。")

    def on_output(self):
        d = self.process.readAllStandardOutput().data().decode("utf-8", "ignore")
        if d:
            self.log_view.appendPlainText(d.strip())
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("Uvicorn Launcher", "已最小化到托盘", QSystemTrayIcon.MessageIcon.Information, 1000)

    def exit_app(self):
        if self.is_running():
            pid = self.process.processId() or self.last_pid
            if pid:
                self.last_pid = pid
                self._kill_process_tree(pid, force=True)
            self.process.terminate()
            self.process.waitForFinished(2000)
            if self.is_running():
                self.process.kill()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = UvicornController()
    win.show()
    sys.exit(app.exec())
