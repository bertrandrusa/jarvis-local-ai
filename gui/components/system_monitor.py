"""
System Monitor Component - Displays CPU, RAM, GPU usage and running Ollama models.
Router-related status has been removed.
"""

import psutil
import requests
from PySide6.QtWidgets import QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import QTimer, QObject, Signal, QThread

from config import OLLAMA_URL

# Try to import pynvml for GPU monitoring
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except Exception:
    GPU_AVAILABLE = False


class MonitorWorker(QObject):
    """Worker to collect system stats in the background."""
    stats_updated = Signal(dict)

    def __init__(self):
        super().__init__()

    def collect(self):
        """Collect and emit stats."""
        try:
            stats = {}

            stats["cpu"] = psutil.cpu_percent(interval=None)

            ram = psutil.virtual_memory()
            stats["ram"] = {
                "percent": ram.percent,
                "used": ram.used / (1024 ** 3),
                "total": ram.total / (1024 ** 3),
            }

            if GPU_AVAILABLE:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

                    stats["gpu"] = {
                        "percent": util.gpu,
                        "vram_used": mem_info.used / (1024 ** 3),
                        "vram_total": mem_info.total / (1024 ** 3),
                        "vram_percent": (mem_info.used / mem_info.total) * 100,
                    }
                except Exception:
                    stats["gpu"] = None
            else:
                stats["gpu"] = None

            try:
                response = requests.get(f"{OLLAMA_URL}/ps", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    if models:
                        stats["models"] = [
                            m.get("name", "?").split(":")[0] for m in models
                        ]
                    else:
                        stats["models"] = []
                else:
                    stats["models"] = "Offline"
            except Exception:
                stats["models"] = "Offline"

            self.stats_updated.emit(stats)

        except Exception as e:
            print(f"MonitorWorker Error: {e}")


class SystemMonitor(QFrame):
    """
    A status bar showing system resource usage and running Ollama models.
    Updates every 3 seconds via background thread.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("systemMonitor")
        self._setup_ui()
        self._init_worker()
        self._init_voice_indicator()

    def _setup_ui(self):
        """Build the monitor UI."""
        self.setFixedHeight(32)
        self.setStyleSheet("""
            QFrame#systemMonitor {
                background: rgba(20, 20, 30, 0.9);
                border-bottom: 1px solid rgba(187, 134, 252, 0.3);
            }
            QLabel {
                color: #b0b0b0;
                font-size: 11px;
                padding: 0 8px;
            }
            QLabel#valueLabel {
                color: #e0e0e0;
                font-weight: bold;
            }
            QLabel#modelsLabel {
                color: #81c784;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(24)

        cpu_container = QHBoxLayout()
        cpu_container.setSpacing(4)
        cpu_icon = QLabel("🖥️")
        cpu_icon.setFixedWidth(20)
        cpu_container.addWidget(cpu_icon)
        cpu_label = QLabel("CPU:")
        cpu_container.addWidget(cpu_label)
        self.cpu_value = QLabel("0%")
        self.cpu_value.setObjectName("valueLabel")
        cpu_container.addWidget(self.cpu_value)
        layout.addLayout(cpu_container)

        ram_container = QHBoxLayout()
        ram_container.setSpacing(4)
        ram_icon = QLabel("💾")
        ram_icon.setFixedWidth(20)
        ram_container.addWidget(ram_icon)
        ram_label = QLabel("RAM:")
        ram_container.addWidget(ram_label)
        self.ram_value = QLabel("0%")
        self.ram_value.setObjectName("valueLabel")
        ram_container.addWidget(self.ram_value)
        layout.addLayout(ram_container)

        gpu_container = QHBoxLayout()
        gpu_container.setSpacing(4)
        gpu_icon = QLabel("🎮")
        gpu_icon.setFixedWidth(20)
        gpu_container.addWidget(gpu_icon)
        gpu_label = QLabel("GPU:")
        gpu_container.addWidget(gpu_label)
        self.gpu_value = QLabel("N/A" if not GPU_AVAILABLE else "0%")
        self.gpu_value.setObjectName("valueLabel")
        self.gpu_value.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        gpu_container.addWidget(self.gpu_value)
        layout.addLayout(gpu_container)

        vram_container = QHBoxLayout()
        vram_container.setSpacing(4)
        vram_label = QLabel("VRAM:")
        vram_container.addWidget(vram_label)
        self.vram_value = QLabel("N/A" if not GPU_AVAILABLE else "0 GB")
        self.vram_value.setObjectName("valueLabel")
        self.vram_value.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        vram_container.addWidget(self.vram_value)
        layout.addLayout(vram_container)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("background: rgba(255,255,255,0.2);")
        separator.setFixedWidth(1)
        layout.addWidget(separator)

        models_container = QHBoxLayout()
        models_container.setSpacing(4)
        models_icon = QLabel("🤖")
        models_icon.setFixedWidth(20)
        models_container.addWidget(models_icon)
        models_label = QLabel("Models:")
        models_container.addWidget(models_label)
        self.models_value = QLabel("Loading...")
        self.models_value.setObjectName("modelsLabel")
        self.models_value.setStyleSheet("color: #81c784; font-weight: bold;")
        models_container.addWidget(self.models_value)
        layout.addLayout(models_container)

        self.voice_indicator = QFrame()
        self.voice_indicator.setFixedSize(4, 20)
        self.voice_indicator.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 2px;
            }
        """)
        self.voice_indicator.hide()
        layout.addWidget(self.voice_indicator)

        layout.addStretch()

    def _init_voice_indicator(self):
        """Initialize voice listening indicator animation."""
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve

        self.voice_animation = QPropertyAnimation(self.voice_indicator, b"styleSheet")
        self.voice_animation.setDuration(1000)
        self.voice_animation.setLoopCount(-1)
        self.voice_animation.setEasingCurve(QEasingCurve.InOutSine)

        self.voice_animation.setStartValue("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(51, 181, 229, 150),
                    stop:0.5 rgba(51, 181, 229, 255),
                    stop:1 rgba(51, 181, 229, 150));
                border-radius: 2px;
            }
        """)
        self.voice_animation.setEndValue("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(51, 181, 229, 255),
                    stop:0.5 rgba(51, 181, 229, 150),
                    stop:1 rgba(51, 181, 229, 255));
                border-radius: 2px;
            }
        """)

    def show_listening(self):
        if not self.voice_indicator.isVisible():
            self.voice_indicator.show()
            self.voice_animation.start()

    def hide_listening(self):
        self.voice_animation.stop()
        self.voice_indicator.hide()

    def _init_worker(self):
        """Initialize the background worker and thread."""
        self.monitor_thread = QThread()
        self.worker = MonitorWorker()
        self.worker.moveToThread(self.monitor_thread)

        self.worker.stats_updated.connect(self._on_stats_updated)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.worker.collect)
        self.timer.start(3000)

        self.monitor_thread.start()
        QTimer.singleShot(100, self.worker.collect)

    def _on_stats_updated(self, stats):
        cpu_val = stats.get("cpu", 0)
        self.cpu_value.setText(f"{cpu_val:.1f}%")
        self._color_by_usage(self.cpu_value, cpu_val)

        ram_data = stats.get("ram", {})
        ram_percent = ram_data.get("percent", 0)
        self.ram_value.setText(
            f"{ram_percent:.1f}% ({ram_data.get('used', 0):.1f}/{ram_data.get('total', 0):.1f} GB)"
        )
        self._color_by_usage(self.ram_value, ram_percent)

        gpu_data = stats.get("gpu")
        if gpu_data:
            gpu_percent = gpu_data.get("percent", 0)
            self.gpu_value.setText(f"{gpu_percent}%")
            self._color_by_usage(self.gpu_value, gpu_percent)

            vram_text = f"{gpu_data.get('vram_used', 0):.1f}/{gpu_data.get('vram_total', 0):.1f} GB"
            self.vram_value.setText(vram_text)
            self._color_by_usage(self.vram_value, gpu_data.get("vram_percent", 0))
        elif not GPU_AVAILABLE:
            self.gpu_value.setText("N/A")
            self.vram_value.setText("N/A")
        else:
            self.gpu_value.setText("Error")
            self.vram_value.setText("Error")

        models = stats.get("models", [])
        if isinstance(models, list):
            if models:
                if len(models) <= 2:
                    self.models_value.setText(", ".join(models))
                else:
                    self.models_value.setText(f"{models[0]} +{len(models)-1}")
            else:
                self.models_value.setText("None")
        elif models == "Offline":
            self.models_value.setText("Ollama Offline")
        else:
            self.models_value.setText("None")

    def _color_by_usage(self, label: QLabel, percent: float):
        if percent >= 90:
            color = "#ef5350"
        elif percent >= 70:
            color = "#ffb74d"
        elif percent >= 50:
            color = "#fff176"
        else:
            color = "#81c784"
        label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def __del__(self):
        if hasattr(self, "monitor_thread"):
            self.monitor_thread.quit()
            self.monitor_thread.wait()