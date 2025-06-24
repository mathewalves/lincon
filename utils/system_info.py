import platform
import os
import subprocess
from pathlib import Path

def get_system_info():
    """Retorna informações do sistema"""
    info = {
        "os": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    return info

def check_docker():
    """Verifica se o Docker está instalado e rodando"""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_proxmox():
    """Verifica se está rodando em um ambiente Proxmox"""
    return os.path.exists("/usr/bin/pct") and os.path.exists("/usr/bin/pvesm")

def get_lincon_version():
    """Retorna a versão atual do LINCON"""
    return "0.1.0-dev"

def get_system_status():
    """Retorna o status dos componentes do sistema"""
    return {
        "docker": check_docker(),
        "proxmox": check_proxmox(),
    }
