#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dell G15 Configuration Manager Module
Handles persistent configuration storage for the fan control application.
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """Application configuration container."""
    # Thermal settings
    default_mode: str = "balanced"
    mode_on_resume: str = "last"
    set_cpu_governor: bool = True
    preserve_mode_on_exit: bool = True
    restore_mode_on_startup: bool = True
    
    # UI settings
    start_minimized: bool = False
    minimize_to_tray: bool = True
    show_notifications: bool = True
    
    # Autostart
    autostart_enabled: bool = False
    
    # Monitoring
    update_interval_ms: int = 2000
    show_gpu_stats: bool = True
    
    # Window
    window_x: int = -1
    window_y: int = -1
    
    # Advanced
    use_intel_path: bool = True  # True for Intel (AMWW), False for AMD (AMW3)


class ConfigManager:
    """
    Manager for application configuration persistence.
    
    Stores configuration in ~/.config/dell-g15-fan-control/config.json
    """
    
    CONFIG_DIR = Path.home() / ".config" / "dell-g15-fan-control"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    
    AUTOSTART_DIR = Path.home() / ".config" / "autostart"
    AUTOSTART_FILE = AUTOSTART_DIR / "dell-g15-fan-control.desktop"
    
    def __init__(self):
        """Initialize the config manager."""
        self._config: AppConfig = AppConfig()
        self._ensure_config_dir()
        self.load()
    
    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> None:
        """Load configuration from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                
                # Update config with loaded values
                for key, value in data.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)
                        
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                # Keep default config
    
    def save(self) -> bool:
        """
        Save configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_config_dir()
            
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(asdict(self._config), f, indent=2)
            
            return True
            
        except IOError as e:
            print(f"Error saving config: {e}")
            return False
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config
    
    def get(self, key: str, default=None):
        """Get a configuration value by key."""
        return getattr(self._config, key, default)
    
    def set(self, key: str, value) -> bool:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Returns:
            True if successful, False if key doesn't exist
        """
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            return True
        return False
    
    def setup_autostart(self, enable: bool, script_path: str) -> bool:
        """
        Configure application autostart.
        
        Args:
            enable: Whether to enable autostart
            script_path: Path to the main application script
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if enable:
                # Create autostart directory if needed
                self.AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                
                exec_cmd = f"/usr/bin/python3 {script_path} --minimized" if str(script_path).endswith(".py") else f"{script_path} --minimized"
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=Dell G15 Fan Control
Comment=Control de ventiladores Dell G15
Exec={exec_cmd}
Icon=utilities-system-monitor
Terminal=false
Categories=System;Settings;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
                
                with open(self.AUTOSTART_FILE, 'w') as f:
                    f.write(desktop_content)
                
                self._config.autostart_enabled = True
                
            else:
                # Remove autostart file
                if self.AUTOSTART_FILE.exists():
                    self.AUTOSTART_FILE.unlink()
                
                self._config.autostart_enabled = False
            
            self.save()
            return True
            
        except IOError as e:
            print(f"Error configuring autostart: {e}")
            return False
    
    def is_autostart_enabled(self) -> bool:
        """Check if autostart is currently enabled."""
        return self.AUTOSTART_FILE.exists()
    
    def create_systemd_resume_service(self, script_path: str) -> tuple:
        """
        Create a systemd service file for resume from suspend.
        
        Note: This requires root privileges to install.
        
        Args:
            script_path: Path to the main application script
            
        Returns:
            Tuple of (success, service_content or error_message)
        """
        service_content = f"""[Unit]
Description=Dell G15 Fan Control - Restore thermal profile on resume
After=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {script_path} --apply-saved-mode

[Install]
WantedBy=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
"""
        
        service_path = "/etc/systemd/system/dell-g15-fan-resume.service"
        
        return True, {
            'content': service_content,
            'path': service_path,
            'install_commands': [
                f"sudo tee {service_path} << 'EOF'\n{service_content}EOF",
                "sudo systemctl daemon-reload",
                "sudo systemctl enable dell-g15-fan-resume.service"
            ]
        }
    
    def create_systemd_boot_service(self, script_path: str) -> tuple:
        """Create a systemd service file for early boot profile restoration."""
        service_content = f"""[Unit]
Description=Dell G15 Fan Control - Restore thermal profile at boot
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {script_path} --apply-saved-mode
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
        service_path = "/etc/systemd/system/dell-g15-fan-boot.service"
        return True, {
            'content': service_content,
            'path': service_path,
            'install_commands': [
                f"sudo tee {service_path} << 'EOF'\n{service_content}EOF",
                "sudo systemctl daemon-reload",
                "sudo systemctl enable dell-g15-fan-boot.service"
            ]
        }
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = AppConfig()
        self.save()


def main():
    """Test the config manager."""
    manager = ConfigManager()
    
    print("=== Dell G15 Config Manager ===\n")
    
    print("Configuración actual:")
    for key, value in asdict(manager.config).items():
        print(f"  {key}: {value}")
    
    print(f"\nArchivo de configuración: {manager.CONFIG_FILE}")
    print(f"Autostart habilitado: {manager.is_autostart_enabled()}")


if __name__ == "__main__":
    main()
