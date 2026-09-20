#!/bin/bash

# Dell G15 Fan Control Ultimate - Installation Script
# For EndeavourOS (Arch Linux based) with Intel i7-11800H

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║       Dell G15 Fan Control Ultimate - Instalador              ║"
echo "║       Para EndeavourOS con Intel i7-11800H                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Este script debe ejecutarse como root o con sudo.${NC}"
    echo "Uso: sudo ./install.sh"
    exit 1
fi

# Get the actual user (if running with sudo)
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER=$SUDO_USER
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    ACTUAL_USER=$(whoami)
    USER_HOME=$HOME
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}Usuario detectado:${NC} $ACTUAL_USER"
echo -e "${GREEN}Directorio home:${NC} $USER_HOME"
echo -e "${GREEN}Directorio de instalación:${NC} $SCRIPT_DIR"
echo ""

# Step 1: Install Dependencies
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 1: Instalando dependencias del sistema...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Detect kernel type
KERNEL_RELEASE=$(uname -r)
HEADERS_PKG="linux-headers"

if [[ "$KERNEL_RELEASE" == *"lts"* ]]; then
    echo -e "${GREEN}Kernel LTS detectado:${NC} $KERNEL_RELEASE"
    HEADERS_PKG="linux-lts-headers"
elif [[ "$KERNEL_RELEASE" == *"zen"* ]]; then
    echo -e "${GREEN}Kernel Zen detectado:${NC} $KERNEL_RELEASE"
    HEADERS_PKG="linux-zen-headers"
else
    echo -e "${GREEN}Kernel estándar detectado:${NC} $KERNEL_RELEASE"
fi

# Update and install packages
pacman -Syu --noconfirm

PACKAGES="base-devel git $HEADERS_PKG acpi_call-dkms python-psutil python-pyqt6"

echo -e "${YELLOW}Instalando paquetes:${NC} $PACKAGES"
pacman -S --needed --noconfirm $PACKAGES

# Step 2: Configure acpi_call module
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 2: Configurando módulo acpi_call...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Load module
if modprobe acpi_call 2>/dev/null; then
    echo -e "${GREEN}✓ Módulo acpi_call cargado correctamente${NC}"
else
    echo -e "${RED}✗ Error al cargar acpi_call. Puede que Secure Boot esté habilitado.${NC}"
    echo -e "${YELLOW}  Desactiva Secure Boot en la BIOS o firma el módulo manualmente.${NC}"
fi

# Configure auto-load on boot
echo "acpi_call" > /etc/modules-load.d/acpi_call.conf
echo -e "${GREEN}✓ Módulo configurado para carga automática en boot${NC}"

# Step 3: Set permissions
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 3: Configurando permisos...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

chmod +x "$SCRIPT_DIR/g15_fan_control.py"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR"

echo -e "${GREEN}✓ Permisos configurados${NC}"

# Step 4: Create desktop entry
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 4: Creando acceso directo en el menú de aplicaciones...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Create system-wide launcher script (no spaces in path)
LAUNCHER_SCRIPT="/usr/local/bin/dell-g15-fan-control-gui"
cat > "$LAUNCHER_SCRIPT" <<LAUNCHEREOF
#!/bin/bash
# Dell G15 Fan Control GUI Launcher
# Runs as normal user - ACPI calls use sudo internally

SCRIPT_DIR="$SCRIPT_DIR"
exec /usr/bin/python3 "\$SCRIPT_DIR/g15_fan_control.py" "\$@"
LAUNCHEREOF
chmod +x "$LAUNCHER_SCRIPT"

# Install application icon
mkdir -p /usr/share/icons/hicolor/scalable/apps
cp "$SCRIPT_DIR/dell_g15_fan_control/icons/app_icon.svg" /usr/share/icons/hicolor/scalable/apps/dell-g15-fan-control.svg

DESKTOP_FILE="$USER_HOME/.local/share/applications/dell-g15-fan-control.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Dell G15 Fan Control
GenericName=Fan Control
Comment=Control de perfiles térmicos para Dell G15 5511
Exec=$LAUNCHER_SCRIPT
Icon=dell-g15-fan-control
Terminal=false
Categories=System;Settings;HardwareSettings;
Keywords=fan;ventilador;dell;g15;thermal;termal;cooling;
StartupNotify=true
EOF

chown "$ACTUAL_USER:$ACTUAL_USER" "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

echo -e "${GREEN}✓ Launcher creado: $LAUNCHER_SCRIPT${NC}"
echo -e "${GREEN}✓ Acceso directo creado: $DESKTOP_FILE${NC}"

# Step 5: Create polkit rule for running without password (optional)
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 5: Configurando polkit (ejecución con contraseña gráfica)...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

POLKIT_FILE="/usr/share/polkit-1/actions/org.dell.g15.fancontrol.policy"

cat > "$POLKIT_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="org.dell.g15.fancontrol">
    <description>Dell G15 Fan Control</description>
    <message>Se requiere autenticación para controlar los ventiladores</message>
    <icon_name>utilities-system-monitor</icon_name>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/bin/python3</annotate>
    <annotate key="org.freedesktop.policykit.exec.argv1">$SCRIPT_DIR/g15_fan_control.py</annotate>
  </action>
</policyconfig>
EOF

echo -e "${GREEN}✓ Regla polkit creada${NC}"

# Step 6: Create sudoers rule for passwordless execution
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 6: Configurando ejecución sin contraseña (sudoers)...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

SUDOERS_FILE="/etc/sudoers.d/dell-g15-fan-control"

cat > "$SUDOERS_FILE" <<EOF
# Dell G15 Fan Control - Allow passwordless ACPI and CPU governor access
# For bash commands used by the Python app
$ACTUAL_USER ALL=(root) NOPASSWD: /usr/bin/bash -c *
$ACTUAL_USER ALL=(root) NOPASSWD: /usr/bin/cat /proc/acpi/call
$ACTUAL_USER ALL=(root) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
EOF

chmod 440 "$SUDOERS_FILE"

# Verify sudoers file syntax
if visudo -c -f "$SUDOERS_FILE" 2>/dev/null; then
    echo -e "${GREEN}✓ Regla sudoers creada - Ejecución sin contraseña habilitada${NC}"
else
    echo -e "${RED}✗ Error en la regla sudoers, eliminando...${NC}"
    rm -f "$SUDOERS_FILE"
fi

# Step 7: Create systemd resume service
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 7: Creando servicio systemd para resume...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

SERVICE_FILE="/etc/systemd/system/dell-g15-fan-resume.service"
BOOT_SERVICE_FILE="/etc/systemd/system/dell-g15-fan-boot.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Dell G15 Fan Control - Restore thermal profile on resume
After=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $SCRIPT_DIR/g15_fan_control.py --apply-saved-mode

[Install]
WantedBy=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
EOF

cat > "$BOOT_SERVICE_FILE" <<EOF
[Unit]
Description=Dell G15 Fan Control - Restore thermal profile at boot
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $SCRIPT_DIR/g15_fan_control.py --apply-saved-mode
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dell-g15-fan-resume.service
systemctl enable dell-g15-fan-boot.service

echo -e "${GREEN}✓ Servicios systemd de arranque y reanudación creados y habilitados${NC}"

# Step 7: Create CLI symlink
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Paso 7: Creando enlace simbólico para CLI...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

ln -sf "$SCRIPT_DIR/g15_fan_control.py" /usr/local/bin/g15-fan-control
chmod +x /usr/local/bin/g15-fan-control

echo -e "${GREEN}✓ Enlace creado: /usr/local/bin/g15-fan-control${NC}"

# Finished
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}¡Instalación completada!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Cómo usar:${NC}"
echo ""
echo -e "  ${GREEN}GUI:${NC}"
echo "    • Busca 'Dell G15 Fan Control' en el menú de aplicaciones"
echo "    • O ejecuta: sudo python3 $SCRIPT_DIR/g15_fan_control.py"
echo ""
echo -e "  ${GREEN}CLI:${NC}"
echo "    • sudo g15-fan-control --cli b   (modo equilibrado)"
echo "    • sudo g15-fan-control --cli p   (modo rendimiento)"
echo "    • sudo g15-fan-control --cli q   (modo silencioso)"
echo "    • sudo g15-fan-control --cli g   (G-Mode toggle)"
echo ""
echo -e "  ${GREEN}Monitor:${NC}"
echo "    • sudo g15-fan-control --monitor"
echo ""
echo -e "${YELLOW}NOTA:${NC} Si tienes Secure Boot habilitado, el módulo acpi_call"
echo "      podría fallar. Desactívalo en la BIOS si ves errores."
echo ""
