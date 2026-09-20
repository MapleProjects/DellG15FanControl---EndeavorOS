#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dell G15 System Tray Module
Provides system tray icon with quick access to thermal profiles using vector icons.
"""

from typing import Optional, Dict
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject

from .icon_manager import IconManager


class SystemTrayIcon(QObject):
    """
    System tray icon for Dell G15 Fan Control.
    Provides quick access to thermal profiles and displays current telemetry in tooltip.
    """
    
    # Signals
    mode_requested = pyqtSignal(str)
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    MODE_COLORS = {
        "gmode": "#ef4444",       # Crimson Red
        "performance": "#f97316", # Flame Orange
        "balanced": "#0ea5e9",    # Electric Blue
        "quiet": "#10b981"        # Emerald Green
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None
        self._mode_actions: Dict[str, QAction] = {}
        self._current_mode: str = "balanced"
        self._current_temp: float = 0.0
        
        self._setup_tray()
    
    def _setup_tray(self) -> None:
        """Setup the system tray icon and context menu."""
        initial_icon = IconManager.get_colored_fan_icon(self.MODE_COLORS.get(self._current_mode, "#0ea5e9"))
        self._tray_icon = QSystemTrayIcon(initial_icon, self.parent())
        
        # Context menu
        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', 'Ubuntu', 'Roboto', sans-serif;
                font-size: 10pt;
            }
            QMenu::item {
                padding: 7px 24px 7px 12px;
                border-radius: 6px;
                margin: 1px 0px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #38bdf8;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 6px 8px;
            }
        """)
        
        # Show/Hide action
        show_action = QAction(IconManager.get_icon("window"), "Abrir Panel de Control", self._menu)
        show_action.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(show_action)
        
        self._menu.addSeparator()
        
        # Thermal mode actions
        modes = [
            ("gmode", "G-Mode (Game Shift)", "Ventiladores al 100% - Máximo rendimiento", "mode_gmode"),
            ("performance", "Rendimiento", "Curva agresiva de ventilación", "mode_performance"),
            ("balanced", "Equilibrado", "Balance óptimo entre ruido y temperatura", "mode_balanced"),
            ("quiet", "Silencioso", "RPM limitadas para trabajo silencioso", "mode_quiet"),
        ]
        
        for mode_id, label, tooltip, icon_name in modes:
            action = QAction(IconManager.get_icon(icon_name), label, self._menu)
            action.setToolTip(tooltip)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, m=mode_id: self._on_mode_clicked(m))
            self._menu.addAction(action)
            self._mode_actions[mode_id] = action
        
        self._menu.addSeparator()
        
        # Quit action
        quit_action = QAction(IconManager.get_icon("quit"), "Salir", self._menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.activated.connect(self._on_activated)
        self._update_tooltip()
    
    def _on_mode_clicked(self, mode: str) -> None:
        """Handle mode selection from menu."""
        self.mode_requested.emit(mode)
    
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click activation."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window_requested.emit()
    
    def _update_tooltip(self) -> None:
        """Update tray tooltip with clean technical info."""
        mode_names = {
            "balanced": "Equilibrado",
            "performance": "Rendimiento",
            "quiet": "Silencioso",
            "gmode": "G-Mode (Game Shift)"
        }
        name = mode_names.get(self._current_mode, self._current_mode)
        tooltip = f"Dell G15 Fan Control\nPerfil: {name}"
        if self._current_temp > 0:
            tooltip += f"\nCPU: {self._current_temp:.1f}°C"
        
        if self._tray_icon:
            self._tray_icon.setToolTip(tooltip)
    
    def set_mode(self, mode: str) -> None:
        """Update displayed current mode and tray icon color."""
        self._current_mode = mode
        
        for mode_id, action in self._mode_actions.items():
            action.setChecked(mode_id == mode)
        
        color = self.MODE_COLORS.get(mode, "#0ea5e9")
        if self._tray_icon:
            self._tray_icon.setIcon(IconManager.get_colored_fan_icon(color))
        
        self._update_tooltip()
    
    def set_temperature(self, temp: float) -> None:
        """Update displayed temperature in tooltip."""
        self._current_temp = temp
        self._update_tooltip()
    
    def show(self) -> None:
        """Show tray icon."""
        if self._tray_icon:
            self._tray_icon.show()
    
    def hide(self) -> None:
        """Hide tray icon."""
        if self._tray_icon:
            self._tray_icon.hide()
    
    def show_message(self, title: str, message: str, 
                     icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
                     ms_timeout: int = 3000) -> None:
        """Show desktop notification."""
        if self._tray_icon and self._tray_icon.isVisible():
            self._tray_icon.showMessage(title, message, icon, ms_timeout)
    
    def is_visible(self) -> bool:
        """Check if tray icon is visible."""
        return self._tray_icon.isVisible() if self._tray_icon else False
