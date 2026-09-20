#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dell G15 Fan Control - Icon Manager
Provides vector SVG icons for UI and system tray without emojis.
"""

from pathlib import Path
from typing import Dict, Optional
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import QSize, Qt


class IconManager:
    """Centralized manager for loading and caching vector SVG icons."""
    
    ICONS_DIR = Path(__file__).parent / "icons"
    _cache: Dict[str, QIcon] = {}
    
    @classmethod
    def get_icon_path(cls, icon_name: str) -> Path:
        """Get absolute path to an icon SVG file."""
        if not icon_name.endswith(".svg"):
            icon_name = f"{icon_name}.svg"
        return cls.ICONS_DIR / icon_name

    @classmethod
    def get_icon(cls, icon_name: str, size: Optional[int] = None) -> QIcon:
        """Get a QIcon from the icons directory with caching."""
        cache_key = f"{icon_name}_{size}" if size else icon_name
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        path = cls.get_icon_path(icon_name)
        if path.exists():
            icon = QIcon(str(path))
            if size:
                pix = icon.pixmap(size, size)
                icon = QIcon(pix)
            cls._cache[cache_key] = icon
            return icon
        
        # Fallback empty icon
        return QIcon()

    @classmethod
    def get_pixmap(cls, icon_name: str, size: int = 24) -> QPixmap:
        """Get a QPixmap scaled to specific size."""
        icon = cls.get_icon(icon_name)
        return icon.pixmap(QSize(size, size))

    @classmethod
    def get_colored_fan_icon(cls, color_hex: str = "#0ea5e9", size: int = 64) -> QIcon:
        """Create dynamic colored fan icon for tray."""
        svg_template = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}">
  <circle cx="32" cy="32" r="29" fill="#0f172a" stroke="{color_hex}" stroke-width="2.5"/>
  <g transform="translate(32,32)">
    <path d="M0,-5 C10,-24 22,-14 20,-3 C18,3 8,4 0,0 Z" fill="{color_hex}"/>
    <path d="M5,0 C24,10 14,22 3,20 C-3,18 -4,8 0,0 Z" fill="{color_hex}"/>
    <path d="M0,5 C-10,24 -22,14 -20,3 C-18,-3 -8,-4 0,0 Z" fill="{color_hex}"/>
    <path d="M-5,0 C-24,-10 -14,-22 -3,-20 C3,-18 4,-8 0,0 Z" fill="{color_hex}"/>
    <circle cx="0" cy="0" r="5.5" fill="#ffffff" stroke="{color_hex}" stroke-width="1.5"/>
    <circle cx="0" cy="0" r="2.5" fill="{color_hex}"/>
  </g>
</svg>"""
        from PyQt6.QtCore import QByteArray
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(svg_template.encode('utf-8')))
        return QIcon(pixmap)
