#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dell G15 ACPI Controller Module
Controls thermal profiles via ACPI calls for Dell G15 5511 (Intel i7-11800H)
"""

import os
import subprocess
from enum import Enum
from typing import Optional, Tuple
from pathlib import Path


class ThermalMode(Enum):
    """Available thermal modes for Dell G15"""
    BALANCED = ("balanced", 0xa0, "Modo equilibrado - Curva conservadora")
    PERFORMANCE = ("performance", 0xa1, "Modo rendimiento - Curva agresiva")
    QUIET = ("quiet", 0xa3, "Modo silencioso - RPM limitadas")
    GMODE = ("gmode", 0xab, "Game Shift - Ventiladores al 100%")
    
    def __init__(self, mode_id: str, acpi_code: int, description: str):
        self.mode_id = mode_id
        self.acpi_code = acpi_code
        self.description = description


class ACPIController:
    """
    Controller for Dell G15 thermal management via ACPI calls.
    
    Uses the acpi_call kernel module to communicate with the BIOS
    and change thermal profiles.
    """
    
    # ACPI paths - Intel uses AMWW, AMD uses AMW3
    ACPI_PATH_INTEL = r"\_SB.AMWW.WMAX"
    ACPI_PATH_AMD = r"\_SB.AMW3.WMAX"
    
    # ACPI call interface
    ACPI_CALL_PATH = "/proc/acpi/call"
    
    def __init__(self, force_intel: bool = True):
        """
        Initialize the ACPI controller.
        
        Args:
            force_intel: If True, use Intel ACPI path (AMWW). 
                        If False, use AMD path (AMW3).
        """
        self.acpi_path = self.ACPI_PATH_INTEL if force_intel else self.ACPI_PATH_AMD
        self._current_mode: Optional[ThermalMode] = None
        self._gmode_active: bool = False
        
    def check_acpi_call_loaded(self) -> Tuple[bool, str]:
        """
        Check if the acpi_call kernel module is loaded.
        
        Returns:
            Tuple of (is_loaded, message)
        """
        try:
            result = subprocess.run(
                ["lsmod"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "acpi_call" in result.stdout:
                return True, "Módulo acpi_call cargado correctamente"
            else:
                return False, "El módulo acpi_call no está cargado. Ejecuta: sudo modprobe acpi_call"
        except subprocess.TimeoutExpired:
            return False, "Timeout al verificar módulo"
        except Exception as e:
            return False, f"Error verificando módulo: {str(e)}"
    
    def check_acpi_interface(self) -> Tuple[bool, str]:
        """
        Check if the ACPI call interface exists.
        
        Returns:
            Tuple of (exists, message)
        """
        if Path(self.ACPI_CALL_PATH).exists():
            return True, "Interfaz ACPI disponible"
        else:
            return False, f"No se encontró {self.ACPI_CALL_PATH}. ¿Está cargado acpi_call?"
    
    def check_root_privileges(self) -> Tuple[bool, str]:
        """
        Check if running with root privileges or passwordless sudo access.
        
        Returns:
            Tuple of (is_root, message)
        """
        if os.geteuid() == 0:
            return True, "Ejecutando como root"
        
        # Check for passwordless sudo access
        try:
            # Check using bash because that's what we whitelisted in sudoers
            result = subprocess.run(
                ['sudo', '-n', 'bash', '-c', 'true'],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return True, "Acceso root disponible vía sudo"
            else:
                return False, "Se requieren privilegios de root (o sudo sin password)"
        except Exception:
            return False, "Error verificando privilegios sudo"
    
    def run_checks(self) -> Tuple[bool, list]:
        """
        Run all preliminary checks.
        
        Returns:
            Tuple of (all_passed, list of (check_name, passed, message))
        """
        checks = []
        
        # Check root
        passed, msg = self.check_root_privileges()
        checks.append(("Privilegios root", passed, msg))
        
        # Check module
        passed, msg = self.check_acpi_call_loaded()
        checks.append(("Módulo acpi_call", passed, msg))
        
        # Check interface
        passed, msg = self.check_acpi_interface()
        checks.append(("Interfaz ACPI", passed, msg))
        
        all_passed = all(c[1] for c in checks)
        return all_passed, checks
    
    def _execute_acpi_call(self, command: str) -> Tuple[bool, str]:
        """
        Execute an ACPI call by writing to /proc/acpi/call.
        Uses sudo if not running as root.
        
        Args:
            command: The ACPI command to execute
            
        Returns:
            Tuple of (success, result/error message)
        """
        try:
            if os.geteuid() == 0:
                # Running as root - direct write
                with open(self.ACPI_CALL_PATH, 'w') as f:
                    f.write(command)
                
                with open(self.ACPI_CALL_PATH, 'r') as f:
                    result = f.read().strip()
            else:
                # Running as user - use sudo
                # Write command
                write_result = subprocess.run(
                    ['sudo', 'bash', '-c', f'echo "{command}" > {self.ACPI_CALL_PATH}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if write_result.returncode != 0:
                    return False, f"Error writing ACPI command: {write_result.stderr}"
                
                # Read result
                read_result = subprocess.run(
                    ['sudo', 'cat', self.ACPI_CALL_PATH],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                result = read_result.stdout.strip()
            
            # Check for errors
            if result.startswith("Error") or "not found" in result.lower():
                return False, f"Error ACPI: {result}"
            
            return True, result
            
        except subprocess.TimeoutExpired:
            return False, "Timeout ejecutando comando ACPI"
        except PermissionError:
            return False, "Error de permisos. Configura sudoers o ejecuta como root."
        except FileNotFoundError:
            return False, f"No se encontró {self.ACPI_CALL_PATH}"
        except Exception as e:
            return False, f"Error ejecutando llamada ACPI: {str(e)}"
    
    def set_thermal_mode(self, mode: ThermalMode) -> Tuple[bool, str]:
        """
        Set the thermal mode.
        
        Args:
            mode: The ThermalMode to set
            
        Returns:
            Tuple of (success, message)
        """
        # Build ACPI command for thermal mode
        # Format: \_SB.AMWW.WMAX 0 0x15 {1, MODE_CODE, 0x00, 0x00}
        command = f"{self.acpi_path} 0 0x15 {{1, {hex(mode.acpi_code)}, 0x00, 0x00}}"
        
        success, result = self._execute_acpi_call(command)
        
        if success:
            self._current_mode = mode
            # If setting a mode other than GMODE, ensure G-Mode is disabled
            if mode != ThermalMode.GMODE:
                self._disable_gmode()
            return True, f"Modo {mode.mode_id} activado"
        else:
            return False, result
    
    def _enable_gmode(self) -> Tuple[bool, str]:
        """Enable G-Mode (fans at 100%)."""
        # G-Mode ON: \_SB.AMWW.WMAX 0 0x25 {1, 0x01, 0x00, 0x00}
        command = f"{self.acpi_path} 0 0x25 {{1, 0x01, 0x00, 0x00}}"
        success, result = self._execute_acpi_call(command)
        if success:
            self._gmode_active = True
        return success, result
    
    def _disable_gmode(self) -> Tuple[bool, str]:
        """Disable G-Mode."""
        # G-Mode OFF: \_SB.AMWW.WMAX 0 0x25 {1, 0x00, 0x00, 0x00}
        command = f"{self.acpi_path} 0 0x25 {{1, 0x00, 0x00, 0x00}}"
        success, result = self._execute_acpi_call(command)
        if success:
            self._gmode_active = False
        return success, result
    
    def activate_gmode(self) -> Tuple[bool, str]:
        """
        Activate G-Mode (Game Shift) - fans at maximum speed.
        
        Returns:
            Tuple of (success, message)
        """
        # First set thermal profile to G-Mode
        success1, msg1 = self.set_thermal_mode(ThermalMode.GMODE)
        if not success1:
            return False, msg1
        
        # Then enable G-Mode flag
        success2, msg2 = self._enable_gmode()
        if not success2:
            return False, msg2
        
        self._gmode_active = True
        return True, "G-Mode activado - Ventiladores al máximo"
    
    def deactivate_gmode(self) -> Tuple[bool, str]:
        """
        Deactivate G-Mode and return to balanced mode.
        
        Returns:
            Tuple of (success, message)
        """
        # Disable G-Mode flag
        success1, msg1 = self._disable_gmode()
        
        # Set to balanced mode
        success2, msg2 = self.set_thermal_mode(ThermalMode.BALANCED)
        
        self._gmode_active = False
        
        if success1 and success2:
            return True, "G-Mode desactivado - Volviendo a modo equilibrado"
        else:
            return False, f"Error: {msg1 if not success1 else msg2}"
    
    def toggle_gmode(self) -> Tuple[bool, str]:
        """
        Toggle G-Mode on/off.
        
        Returns:
            Tuple of (success, message)
        """
        if self._gmode_active:
            return self.deactivate_gmode()
        else:
            return self.activate_gmode()
    
    def query_gmode_status(self) -> Tuple[bool, bool]:
        """
        Query the current G-Mode status from the hardware.
        
        Returns:
            Tuple of (success, is_gmode_active)
        """
        # Query: \_SB.AMWW.WMAX 0 0x14 {0x0b, 0x00, 0x00, 0x00}
        # Returns 0xab if G-Mode is on
        command = f"{self.acpi_path} 0 0x14 {{0x0b, 0x00, 0x00, 0x00}}"
        
        success, result = self._execute_acpi_call(command)
        
        if success:
            is_active = "0xab" in result.lower()
            self._gmode_active = is_active
            return True, is_active
        else:
            return False, False
    
    def query_current_mode(self) -> Tuple[bool, Optional[str]]:
        """
        Query hardware for the current active thermal profile.
        Returns:
            Tuple of (success, mode_string: 'gmode' | 'performance' | 'quiet' | 'balanced')
        """
        command = f"{self.acpi_path} 0 0x14 {{0x0b, 0x00, 0x00, 0x00}}"
        success, result = self._execute_acpi_call(command)
        if not success:
            return False, None
        
        result_clean = result.lower().strip()
        if "0xab" in result_clean:
            self._gmode_active = True
            self._current_mode = ThermalMode.GMODE
            return True, "gmode"
        elif "0xa1" in result_clean:
            self._gmode_active = False
            self._current_mode = ThermalMode.PERFORMANCE
            return True, "performance"
        elif "0xa3" in result_clean:
            self._gmode_active = False
            self._current_mode = ThermalMode.QUIET
            return True, "quiet"
        elif "0xa0" in result_clean:
            self._gmode_active = False
            self._current_mode = ThermalMode.BALANCED
            return True, "balanced"
        
        return True, result_clean
    
    def set_cpu_governor(self, governor: str) -> Tuple[bool, str]:
        """
        Set the CPU frequency governor.
        Uses sudo if not running as root.
        
        Args:
            governor: One of 'performance', 'powersave', 'schedutil', etc.
            
        Returns:
            Tuple of (success, message)
        """
        valid_governors = ['performance', 'powersave', 'schedutil', 'ondemand', 'conservative']
        
        if governor not in valid_governors:
            return False, f"Gobernador inválido. Opciones: {', '.join(valid_governors)}"
        
        try:
            if os.geteuid() == 0:
                # Running as root - direct write
                cpu_dirs = Path("/sys/devices/system/cpu").glob("cpu[0-9]*")
                for cpu_dir in cpu_dirs:
                    governor_path = cpu_dir / "cpufreq" / "scaling_governor"
                    if governor_path.exists():
                        with open(governor_path, 'w') as f:
                            f.write(governor)
            else:
                # Running as user - use sudo
                result = subprocess.run(
                    ['sudo', 'bash', '-c', 
                     f'echo {governor} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return False, f"Error: {result.stderr}"
            
            return True, f"Gobernador CPU establecido a: {governor}"
            
        except subprocess.TimeoutExpired:
            return False, "Timeout cambiando gobernador CPU"
        except PermissionError:
            return False, "Error de permisos al cambiar el gobernador CPU"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @property
    def current_mode(self) -> Optional[ThermalMode]:
        """Get the currently set thermal mode."""
        return self._current_mode
    
    @property
    def is_gmode_active(self) -> bool:
        """Check if G-Mode is currently active."""
        return self._gmode_active


def main():
    """Test the ACPI controller from command line."""
    import sys
    
    controller = ACPIController(force_intel=True)
    
    # Run checks
    all_passed, checks = controller.run_checks()
    
    print("=== Dell G15 ACPI Controller ===\n")
    print("Verificaciones del sistema:")
    for name, passed, msg in checks:
        status = "✓" if passed else "✗"
        print(f"  [{status}] {name}: {msg}")
    
    if not all_passed:
        print("\n¡Algunas verificaciones fallaron! Corrige los problemas antes de continuar.")
        sys.exit(1)
    
    print("\n¡Todas las verificaciones pasaron!\n")
    
    # Parse command line
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg.startswith('b'):
            success, msg = controller.set_thermal_mode(ThermalMode.BALANCED)
        elif arg.startswith('p'):
            success, msg = controller.set_thermal_mode(ThermalMode.PERFORMANCE)
        elif arg.startswith('q'):
            success, msg = controller.set_thermal_mode(ThermalMode.QUIET)
        elif arg.startswith('g'):
            success, msg = controller.toggle_gmode()
        elif arg.startswith('h'):
            print("Uso: python acpi_controller.py [modo]")
            print("  b - Balanced (equilibrado)")
            print("  p - Performance (rendimiento)")
            print("  q - Quiet (silencioso)")
            print("  g - G-Mode toggle (ventiladores al máximo)")
            sys.exit(0)
        else:
            print(f"Modo desconocido: {arg}")
            sys.exit(1)
        
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ {msg}")
            sys.exit(1)
    else:
        print("Usa -h para ver la ayuda")


if __name__ == "__main__":
    main()
