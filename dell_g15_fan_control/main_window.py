#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dell G15 Fan Control - Main Window
Modern professional PyQt6 GUI for controlling thermal profiles and monitoring system telemetry.
100% Vector Icons, Zero Emojis, Robust ACPI State Persistence.
"""

import sys
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QGridLayout, QCheckBox, QComboBox,
    QGroupBox, QTabWidget, QProgressBar, QMessageBox, QSpacerItem,
    QSizePolicy, QScrollArea, QButtonGroup, QSystemTrayIcon
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

# Local imports
from .acpi_controller import ACPIController, ThermalMode
from .system_monitor import SystemMonitor
from .config_manager import ConfigManager
from .system_tray import SystemTrayIcon
from .icon_manager import IconManager


class StatCard(QFrame):
    """Card widget for displaying a telemetry metric with a vector icon."""
    
    def __init__(self, title: str, icon_name: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statsCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(120, 80)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Header layout (Icon + Title)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if icon_name:
            self.icon_label = QLabel()
            self.icon_label.setPixmap(IconManager.get_pixmap(icon_name, 16))
            self.icon_label.setFixedSize(16, 16)
            header_layout.addWidget(self.icon_label)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label)
        
        layout.addLayout(header_layout)
        
        # Value
        self.value_label = QLabel("--")
        self.value_label.setObjectName("statValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str, style_class: str = "statValue") -> None:
        """Set the displayed value with optional style."""
        self.value_label.setText(value)
        if self.value_label.objectName() != style_class:
            self.value_label.setObjectName(style_class)
            self.value_label.style().unpolish(self.value_label)
            self.value_label.style().polish(self.value_label)


class FanSpeedWidget(QFrame):
    """Widget for displaying fan speed and visual RPM progress."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statsCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(160, 95)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        icon_label.setPixmap(IconManager.get_pixmap("fan", 18))
        icon_label.setFixedSize(18, 18)
        header_layout.addWidget(icon_label)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")
        header_layout.addWidget(self.title_label)
        layout.addLayout(header_layout)
        
        # RPM Value
        self.rpm_label = QLabel("-- RPM")
        self.rpm_label.setObjectName("statValue")
        self.rpm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rpm_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 5500)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)
    
    def set_rpm(self, rpm: int, is_gmode: bool = False) -> None:
        """Set displayed RPM value and progress bar styling."""
        self.rpm_label.setText(f"{rpm} RPM")
        self.progress.setValue(min(rpm, 5500))
        target_obj = "fanGMode" if is_gmode else ""
        if self.progress.objectName() != target_obj:
            self.progress.setObjectName(target_obj)
            self.progress.style().unpolish(self.progress)
            self.progress.style().polish(self.progress)


class MainWindow(QMainWindow):
    """Main window for Dell G15 Fan Control application."""
    
    def __init__(self, start_minimized: bool = False):
        super().__init__()
        
        self.config_manager = ConfigManager()
        self.system_monitor = SystemMonitor()
        self.acpi_controller = ACPIController(
            force_intel=self.config_manager.get("use_intel_path", True)
        )
        
        self._current_mode: str = self.config_manager.get("default_mode", "balanced")
        is_root, _ = self.acpi_controller.check_root_privileges()
        self._is_root: bool = is_root
        
        self._setup_ui()
        self._load_stylesheet()
        self._setup_tray()
        self._setup_timers()
        self._check_requirements()
        self._load_config()
        
        # Apply and verify hardware thermal profile on startup
        self._apply_startup_mode()
        
        if start_minimized and self.config_manager.get("minimize_to_tray", True):
            self.hide()
            self.tray_icon.show()
        else:
            self.show()
    
    def _setup_ui(self) -> None:
        """Setup the main user interface."""
        self.setWindowTitle("Dell G15 Fan Control")
        self.setMinimumSize(640, 720)
        self.setWindowIcon(IconManager.get_icon("app_icon"))
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_monitor_tab(), IconManager.get_icon("tab_monitor"), "Monitor")
        self.tabs.addTab(self._create_control_tab(), IconManager.get_icon("tab_control"), "Perfiles Térmicos")
        self.tabs.addTab(self._create_settings_tab(), IconManager.get_icon("tab_settings"), "Configuración")
        self.tabs.setCurrentIndex(1)  # Default to Control tab for quick profile switching
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.statusBar().showMessage("Sistema inicializado")
    
    def _create_header(self) -> QWidget:
        """Create the professional brand header section."""
        header = QFrame()
        header.setObjectName("headerCard")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(16)
        
        # App Icon
        icon_label = QLabel()
        icon_label.setPixmap(IconManager.get_pixmap("app_icon", 36))
        icon_label.setFixedSize(36, 36)
        layout.addWidget(icon_label)
        
        # Brand text
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)
        
        title = QLabel("Dell G15 Fan Control")
        title.setObjectName("brandTitle")
        brand_layout.addWidget(title)
        
        subtitle = QLabel("Gestión Térmica & Rendimiento • G15 5511")
        subtitle.setObjectName("brandSubtitle")
        brand_layout.addWidget(subtitle)
        
        layout.addLayout(brand_layout)
        layout.addStretch()
        
        # Current active mode badge
        self.mode_badge = QLabel("EQUILIBRADO")
        self.mode_badge.setObjectName("modeBadge")
        layout.addWidget(self.mode_badge)
        
        return header
    
    def _create_monitor_tab(self) -> QWidget:
        """Create the telemetry monitoring tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # CPU Section
        cpu_group = QGroupBox("Procesador (CPU)")
        cpu_layout = QGridLayout(cpu_group)
        cpu_layout.setSpacing(10)
        
        self.cpu_temp_card = StatCard("Temperatura", "temp")
        self.cpu_usage_card = StatCard("Uso CPU", "usage")
        self.cpu_freq_card = StatCard("Frecuencia", "clock")
        
        cpu_layout.addWidget(self.cpu_temp_card, 0, 0)
        cpu_layout.addWidget(self.cpu_usage_card, 0, 1)
        cpu_layout.addWidget(self.cpu_freq_card, 0, 2)
        layout.addWidget(cpu_group)
        
        # Fans Section
        fans_group = QGroupBox("Refrigeración (Ventiladores)")
        fans_layout = QHBoxLayout(fans_group)
        fans_layout.setSpacing(10)
        
        self.fan1_widget = FanSpeedWidget("CPU Fan")
        self.fan2_widget = FanSpeedWidget("GPU Fan")
        
        fans_layout.addWidget(self.fan1_widget)
        fans_layout.addWidget(self.fan2_widget)
        layout.addWidget(fans_group)
        
        # GPU Section
        gpu_group = QGroupBox("Gráficos (GPU NVIDIA)")
        gpu_layout = QGridLayout(gpu_group)
        gpu_layout.setSpacing(10)
        
        self.gpu_temp_card = StatCard("Temp GPU", "gpu")
        self.gpu_usage_card = StatCard("Uso GPU", "usage")
        self.gpu_vram_card = StatCard("VRAM", "ram")
        
        gpu_layout.addWidget(self.gpu_temp_card, 0, 0)
        gpu_layout.addWidget(self.gpu_usage_card, 0, 1)
        gpu_layout.addWidget(self.gpu_vram_card, 0, 2)
        layout.addWidget(gpu_group)
        
        # System & Battery Section
        sys_group = QGroupBox("Memoria & Energía")
        sys_layout = QGridLayout(sys_group)
        sys_layout.setSpacing(10)
        
        self.ram_card = StatCard("Memoria RAM", "ram")
        self.battery_card = StatCard("Batería", "battery")
        self.battery_health_card = StatCard("Salud Batería", "battery_health")
        
        sys_layout.addWidget(self.ram_card, 0, 0)
        sys_layout.addWidget(self.battery_card, 0, 1)
        sys_layout.addWidget(self.battery_health_card, 0, 2)
        layout.addWidget(sys_group)
        
        layout.addStretch()
        scroll.setWidget(content)
        return scroll
    
    def _create_control_tab(self) -> QWidget:
        """Create the thermal profile control tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Thermal Profiles Group
        modes_group = QGroupBox("Perfiles Térmicos")
        modes_layout = QVBoxLayout(modes_group)
        modes_layout.setSpacing(12)
        
        # Mutually exclusive button group
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.setExclusive(True)
        
        # G-Mode Hero Button
        self.btn_gmode = QPushButton("G-MODE (Game Shift)")
        self.btn_gmode.setObjectName("btnGMode")
        self.btn_gmode.setIcon(IconManager.get_icon("mode_gmode"))
        self.btn_gmode.setIconSize(QSize(24, 24))
        self.btn_gmode.setCheckable(True)
        self.btn_gmode.setMinimumHeight(64)
        self.btn_gmode.setToolTip("Ventiladores al 100% permanente. Máxima disipación térmica para gaming o renders.")
        self.btn_gmode.clicked.connect(lambda: self._set_mode("gmode"))
        self.mode_button_group.addButton(self.btn_gmode)
        modes_layout.addWidget(self.btn_gmode)
        
        # Other modes
        other_modes_layout = QHBoxLayout()
        other_modes_layout.setSpacing(10)
        
        self.btn_performance = QPushButton("Rendimiento")
        self.btn_performance.setObjectName("btnPerformance")
        self.btn_performance.setIcon(IconManager.get_icon("mode_performance"))
        self.btn_performance.setIconSize(QSize(20, 20))
        self.btn_performance.setCheckable(True)
        self.btn_performance.setMinimumHeight(52)
        self.btn_performance.setToolTip("Curva de ventilación agresiva con respuesta rápida ante picos de temperatura.")
        self.btn_performance.clicked.connect(lambda: self._set_mode("performance"))
        self.mode_button_group.addButton(self.btn_performance)
        other_modes_layout.addWidget(self.btn_performance)
        
        self.btn_balanced = QPushButton("Equilibrado")
        self.btn_balanced.setObjectName("btnBalanced")
        self.btn_balanced.setIcon(IconManager.get_icon("mode_balanced"))
        self.btn_balanced.setIconSize(QSize(20, 20))
        self.btn_balanced.setCheckable(True)
        self.btn_balanced.setChecked(True)
        self.btn_balanced.setMinimumHeight(52)
        self.btn_balanced.setToolTip("Curva predeterminada de fábrica con balance óptimo entre acústica y refrigeración.")
        self.btn_balanced.clicked.connect(lambda: self._set_mode("balanced"))
        self.mode_button_group.addButton(self.btn_balanced)
        other_modes_layout.addWidget(self.btn_balanced)
        
        self.btn_quiet = QPushButton("Silencioso")
        self.btn_quiet.setObjectName("btnQuiet")
        self.btn_quiet.setIcon(IconManager.get_icon("mode_quiet"))
        self.btn_quiet.setIconSize(QSize(20, 20))
        self.btn_quiet.setCheckable(True)
        self.btn_quiet.setMinimumHeight(52)
        self.btn_quiet.setToolTip("Límite acústico estricto en ventiladores para navegación, multimedia o trabajo de oficina.")
        self.btn_quiet.clicked.connect(lambda: self._set_mode("quiet"))
        self.mode_button_group.addButton(self.btn_quiet)
        other_modes_layout.addWidget(self.btn_quiet)
        
        modes_layout.addLayout(other_modes_layout)
        layout.addWidget(modes_group)
        
        # Diagnostic & Hardware Info Card
        diag_group = QGroupBox("Estado del Controlador ACPI")
        diag_layout = QVBoxLayout(diag_group)
        diag_layout.setSpacing(8)
        
        self.status_icon_label = QLabel()
        self.status_label = QLabel("Verificando controlador...")
        self.status_label.setWordWrap(True)
        
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self.diag_status_icon = QLabel()
        self.diag_status_icon.setPixmap(IconManager.get_pixmap("check", 18))
        self.diag_status_icon.setFixedSize(18, 18)
        status_row.addWidget(self.diag_status_icon)
        status_row.addWidget(self.status_label, 1)
        diag_layout.addLayout(status_row)
        
        self.hw_state_label = QLabel("Registro ACPI: Consultando...")
        self.hw_state_label.setStyleSheet("color: #64748b; font-family: monospace; font-size: 9pt;")
        diag_layout.addWidget(self.hw_state_label)
        
        layout.addWidget(diag_group)
        layout.addStretch()
        
        scroll.setWidget(content)
        return scroll
    
    def _create_settings_tab(self) -> QWidget:
        """Create the settings configuration tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Startup & Persistence
        startup_group = QGroupBox("Inicio y Persistencia")
        startup_layout = QVBoxLayout(startup_group)
        startup_layout.setSpacing(8)
        
        self.chk_autostart = QCheckBox("Iniciar automáticamente con el sistema")
        self.chk_autostart.setToolTip("Ejecutar la aplicación al iniciar la sesión gráfica.")
        self.chk_autostart.stateChanged.connect(self._on_autostart_changed)
        startup_layout.addWidget(self.chk_autostart)
        
        self.chk_minimized = QCheckBox("Iniciar minimizado en la bandeja del sistema")
        self.chk_minimized.stateChanged.connect(self._on_setting_changed)
        startup_layout.addWidget(self.chk_minimized)
        
        self.chk_restore_startup = QCheckBox("Restaurar perfil térmico guardado al arrancar")
        self.chk_restore_startup.setToolTip("Aplica directamente el modo guardado al hardware mediante llamadas ACPI al iniciar.")
        self.chk_restore_startup.setChecked(True)
        self.chk_restore_startup.stateChanged.connect(self._on_setting_changed)
        startup_layout.addWidget(self.chk_restore_startup)
        
        self.chk_preserve_exit = QCheckBox("Preservar perfil térmico al salir o reiniciar")
        self.chk_preserve_exit.setToolTip("Evita que la aplicación restablezca el perfil a equilibrado al cerrarse o apagarse el equipo.")
        self.chk_preserve_exit.setChecked(True)
        self.chk_preserve_exit.stateChanged.connect(self._on_setting_changed)
        startup_layout.addWidget(self.chk_preserve_exit)
        
        layout.addWidget(startup_group)
        
        # Behavior
        behavior_group = QGroupBox("Comportamiento")
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setSpacing(8)
        
        self.chk_tray = QCheckBox("Minimizar a la bandeja del sistema al cerrar ventana")
        self.chk_tray.setChecked(True)
        self.chk_tray.stateChanged.connect(self._on_setting_changed)
        behavior_layout.addWidget(self.chk_tray)
        
        self.chk_notifications = QCheckBox("Mostrar notificaciones al cambiar de perfil")
        self.chk_notifications.setChecked(True)
        self.chk_notifications.stateChanged.connect(self._on_setting_changed)
        behavior_layout.addWidget(self.chk_notifications)
        
        resume_layout = QHBoxLayout()
        resume_label = QLabel("Modo al despertar de suspensión:")
        resume_layout.addWidget(resume_label)
        
        self.combo_resume_mode = QComboBox()
        self.combo_resume_mode.addItems(["Preservar último modo", "G-Mode", "Rendimiento", "Equilibrado", "Silencioso"])
        self.combo_resume_mode.currentIndexChanged.connect(self._on_setting_changed)
        resume_layout.addWidget(self.combo_resume_mode)
        resume_layout.addStretch()
        behavior_layout.addLayout(resume_layout)
        
        layout.addWidget(behavior_group)
        
        # CPU Governor
        governor_group = QGroupBox("Gobernador de CPU")
        governor_layout = QVBoxLayout(governor_group)
        
        self.chk_governor = QCheckBox("Sincronizar gobernador de frecuencia (performance / powersave)")
        self.chk_governor.setChecked(True)
        self.chk_governor.stateChanged.connect(self._on_setting_changed)
        governor_layout.addWidget(self.chk_governor)
        layout.addWidget(governor_group)
        
        # Systemd Services
        services_group = QGroupBox("Servicios del Sistema")
        services_layout = QVBoxLayout(services_group)
        services_layout.setSpacing(8)
        
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Intervalo de telemetría:")
        interval_layout.addWidget(interval_label)
        
        self.combo_interval = QComboBox()
        self.combo_interval.addItems(["1 segundo", "2 segundos", "5 segundos"])
        self.combo_interval.setCurrentIndex(1)
        self.combo_interval.currentIndexChanged.connect(self._on_interval_changed)
        interval_layout.addWidget(self.combo_interval)
        interval_layout.addStretch()
        services_layout.addLayout(interval_layout)
        
        self.btn_install_service = QPushButton("Sincronizar servicios systemd (Boot & Resume)")
        self.btn_install_service.setIcon(IconManager.get_icon("refresh"))
        self.btn_install_service.setToolTip("Instala y habilita servicios para asegurar que el perfil térmico se restaure al arrancar y al reanudar.")
        self.btn_install_service.clicked.connect(self._install_services)
        services_layout.addWidget(self.btn_install_service)
        
        layout.addWidget(services_group)
        layout.addStretch()
        
        scroll.setWidget(content)
        return scroll
    
    def _load_stylesheet(self) -> None:
        """Load the QSS stylesheet."""
        style_path = Path(__file__).parent / "styles.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
    
    def _setup_tray(self) -> None:
        """Setup the system tray icon."""
        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.mode_requested.connect(self._set_mode)
        self.tray_icon.show_window_requested.connect(self._toggle_window)
        self.tray_icon.quit_requested.connect(self._quit_app)
        self.tray_icon.show()
    
    def _setup_timers(self) -> None:
        """Setup background update timers."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_stats)
        interval = self.config_manager.get("update_interval_ms", 2000)
        self.update_timer.start(interval)
        self._update_stats()
    
    def _check_requirements(self) -> None:
        """Verify root permissions and ACPI interface."""
        all_passed, checks = self.acpi_controller.run_checks()
        failed = [f"{name}: {msg}" for name, passed, msg in checks if not passed]
        
        if failed:
            self.diag_status_icon.setPixmap(IconManager.get_pixmap("alert", 18))
            self.status_label.setText("Atención: " + "; ".join(failed))
            self.status_label.setStyleSheet("color: #f59e0b;")
        else:
            self.diag_status_icon.setPixmap(IconManager.get_pixmap("check", 18))
            self.status_label.setText("Sistema listo • Interfaz ACPI y permisos operativos")
            self.status_label.setStyleSheet("color: #10b981;")
    
    def _load_config(self) -> None:
        """Load persisted configuration into UI elements."""
        config = self.config_manager.config
        
        self.chk_autostart.setChecked(self.config_manager.is_autostart_enabled())
        self.chk_minimized.setChecked(config.start_minimized)
        self.chk_restore_startup.setChecked(getattr(config, "restore_mode_on_startup", True))
        self.chk_preserve_exit.setChecked(getattr(config, "preserve_mode_on_exit", True))
        self.chk_tray.setChecked(config.minimize_to_tray)
        self.chk_notifications.setChecked(config.show_notifications)
        self.chk_governor.setChecked(config.set_cpu_governor)
        
        # Resume mode mapping: 0: last, 1: gmode, 2: performance, 3: balanced, 4: quiet
        resume_map = {"last": 0, "gmode": 1, "performance": 2, "balanced": 3, "quiet": 4}
        self.combo_resume_mode.setCurrentIndex(resume_map.get(config.mode_on_resume, 0))
        
        # Interval
        interval_map = {1000: 0, 2000: 1, 5000: 2}
        self.combo_interval.setCurrentIndex(interval_map.get(config.update_interval_ms, 1))
    
    def _save_config(self) -> None:
        """Save UI settings to config file."""
        config = self.config_manager.config
        
        config.start_minimized = self.chk_minimized.isChecked()
        config.minimize_to_tray = self.chk_tray.isChecked()
        config.show_notifications = self.chk_notifications.isChecked()
        config.set_cpu_governor = self.chk_governor.isChecked()
        setattr(config, "restore_mode_on_startup", self.chk_restore_startup.isChecked())
        setattr(config, "preserve_mode_on_exit", self.chk_preserve_exit.isChecked())
        
        mode_map = {0: "last", 1: "gmode", 2: "performance", 3: "balanced", 4: "quiet"}
        config.mode_on_resume = mode_map.get(self.combo_resume_mode.currentIndex(), "last")
        
        interval_map = {0: 1000, 1: 2000, 2: 5000}
        config.update_interval_ms = interval_map.get(self.combo_interval.currentIndex(), 2000)
        
        self.config_manager.save()
    
    def _apply_startup_mode(self) -> None:
        """Apply saved thermal mode to ACPI hardware at startup."""
        saved_mode = self.config_manager.get("default_mode", "balanced")
        should_restore = self.config_manager.get("restore_mode_on_startup", True)
        
        # Query current hardware state
        success, hw_mode = self.acpi_controller.query_current_mode()
        if success and hw_mode:
            self.hw_state_label.setText(f"Hardware ACPI: Modo detectado '{hw_mode}'")
        
        if should_restore and self._is_root:
            # Enforce saved profile in ACPI registers
            self._set_mode(saved_mode, force=True, show_notification=False)
        elif success and hw_mode in ["gmode", "performance", "balanced", "quiet"]:
            self._update_ui_mode(hw_mode)
            self.tray_icon.set_mode(hw_mode)
            self._current_mode = hw_mode
        else:
            self._update_ui_mode(saved_mode)
            self.tray_icon.set_mode(saved_mode)
    
    def _update_ui_mode(self, mode: str) -> None:
        """Update buttons and header badge without calling ACPI."""
        self.btn_gmode.setChecked(mode == "gmode")
        self.btn_performance.setChecked(mode == "performance")
        self.btn_balanced.setChecked(mode == "balanced")
        self.btn_quiet.setChecked(mode == "quiet")
        
        labels = {
            "gmode": "G-MODE (GAME SHIFT)",
            "performance": "RENDIMIENTO",
            "balanced": "EQUILIBRADO",
            "quiet": "SILENCIOSO"
        }
        self.mode_badge.setText(labels.get(mode, mode.upper()))
        self.mode_badge.setObjectName(f"modeBadge_{mode}")
        self.mode_badge.style().unpolish(self.mode_badge)
        self.mode_badge.style().polish(self.mode_badge)
    
    def _set_mode(self, mode: str, force: bool = False, show_notification: bool = True) -> None:
        """Set thermal profile in hardware and persist preference."""
        mode_map = {
            "gmode": ThermalMode.GMODE,
            "performance": ThermalMode.PERFORMANCE,
            "balanced": ThermalMode.BALANCED,
            "quiet": ThermalMode.QUIET
        }
        
        if mode not in mode_map:
            return
        
        if self._is_root:
            if mode == "gmode":
                success, msg = self.acpi_controller.activate_gmode()
            else:
                success, msg = self.acpi_controller.set_thermal_mode(mode_map[mode])
            
            if success:
                self._current_mode = mode
                self.config_manager.set("default_mode", mode)
                self.config_manager.save()
                
                # CPU Governor
                if self.chk_governor.isChecked():
                    gov = "performance" if mode in ["gmode", "performance"] else "powersave"
                    self.acpi_controller.set_cpu_governor(gov)
                
                # Notifications
                if show_notification and self.config_manager.get("show_notifications", True):
                    self.tray_icon.show_message("Perfil Térmico", msg)
                
                self.statusBar().showMessage(msg)
                self.hw_state_label.setText(f"Hardware ACPI: {msg} (OK)")
            else:
                self.statusBar().showMessage(f"Error cambiando perfil: {msg}")
                self.hw_state_label.setText(f"Hardware ACPI Error: {msg}")
        else:
            self.statusBar().showMessage("Se requieren privilegios root para modificar registros ACPI")
        
        self._update_ui_mode(mode)
        self.tray_icon.set_mode(mode)
    
    def _update_stats(self) -> None:
        """Update system statistics display."""
        cpu = self.system_monitor.get_cpu_stats()
        if cpu:
            temp_style = "tempCool"
            if cpu.average_temp > 82:
                temp_style = "tempHot"
            elif cpu.average_temp > 68:
                temp_style = "tempWarm"
            
            self.cpu_temp_card.set_value(f"{cpu.average_temp:.0f}°C", temp_style)
            self.cpu_usage_card.set_value(f"{cpu.usage_percent:.0f}%")
            self.cpu_freq_card.set_value(f"{int(cpu.frequency_mhz)} MHz")
            self.tray_icon.set_temperature(cpu.average_temp)
        
        fans = self.system_monitor.get_fan_stats()
        if fans:
            is_gmode = (self._current_mode == "gmode")
            self.fan1_widget.set_rpm(fans.fan1_rpm, is_gmode)
            self.fan2_widget.set_rpm(fans.fan2_rpm, is_gmode)
        
        ram = self.system_monitor.get_ram_stats()
        if ram:
            self.ram_card.set_value(f"{ram.used_gb:.1f} / {ram.total_gb:.1f} GB")
        
        battery = self.system_monitor.get_battery_stats()
        if battery:
            state = "Cargando" if battery.is_charging else "Conectado" if battery.power_plugged else "Batería"
            self.battery_card.set_value(f"{battery.percent:.0f}% ({state})")
            self.battery_health_card.set_value(f"{battery.health_percent:.0f}%")
        
        gpu = self.system_monitor.get_gpu_stats()
        if gpu:
            self.gpu_temp_card.set_value(f"{gpu.temp:.0f}°C")
            self.gpu_usage_card.set_value(f"{gpu.usage_percent:.0f}%")
            self.gpu_vram_card.set_value(f"{gpu.memory_used_mb} / {gpu.memory_total_mb} MB")
        else:
            self.gpu_temp_card.set_value("Suspendida")
            self.gpu_usage_card.set_value("0%")
            self.gpu_vram_card.set_value("N/A")
    
    def _on_autostart_changed(self, state: int) -> None:
        """Handle autostart toggle."""
        enabled = (state == 2 or state is True)
        launcher_path = "/usr/local/bin/dell-g15-fan-control-gui"
        if not Path(launcher_path).exists():
            launcher_path = "/opt/DellG15FanControl/g15_fan_control.py"
        self.config_manager.setup_autostart(enabled, launcher_path)
    
    def _on_setting_changed(self) -> None:
        """Handle general settings changes."""
        self._save_config()
    
    def _on_interval_changed(self, index: int) -> None:
        """Handle telemetry interval change."""
        self._save_config()
        interval = self.config_manager.get("update_interval_ms", 2000)
        self.update_timer.setInterval(interval)
    
    def _install_services(self) -> None:
        """Install and enable both resume and boot systemd services."""
        script_path = "/opt/DellG15FanControl/g15_fan_control.py"
        _, resume_info = self.config_manager.create_systemd_resume_service(script_path)
        _, boot_info = self.config_manager.create_systemd_boot_service(script_path)
        
        all_cmds = resume_info['install_commands'] + boot_info['install_commands']
        full_command = " && ".join(all_cmds)
        
        import subprocess
        try:
            res = subprocess.run(full_command, shell=True, capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                QMessageBox.information(
                    self, "Servicios Instalados",
                    "Los servicios systemd de arranque (boot) y reanudación (resume) fueron instalados y habilitados exitosamente."
                )
            else:
                QMessageBox.warning(self, "Error", f"Fallo al instalar servicios: {res.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Excepción", f"Error ejecutando configuración: {str(e)}")
    
    def _toggle_window(self) -> None:
        """Toggle main window visibility."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def _quit_app(self) -> None:
        """Quit the application while honoring profile persistence."""
        preserve = self.config_manager.get("preserve_mode_on_exit", True)
        if not preserve and self._is_root and self._current_mode != "balanced":
            self.acpi_controller.set_thermal_mode(ThermalMode.BALANCED)
        
        self.tray_icon.hide()
        QApplication.quit()
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        if self.config_manager.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            self.tray_icon.show_message(
                "Dell G15 Fan Control",
                "La aplicación continúa ejecutándose en la bandeja del sistema."
            )
        else:
            self._quit_app()


def main():
    """Start GUI."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    start_minimized = "--minimized" in sys.argv
    window = MainWindow(start_minimized=start_minimized)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
