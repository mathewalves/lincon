import platform
import os
import subprocess
from pathlib import Path
import shutil

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
    """Verifica se está rodando em um ambiente Proxmox (detecta comando pct)"""
    return shutil.which("pct") is not None

def get_lincon_version():
    """Retorna a versão atual do LINCON lendo o arquivo version.txt na raiz do projeto"""
    version_file = Path(__file__).parent.parent / "version.txt"
    try:
        if version_file.exists():
            with open(version_file, 'r') as f:
                version = f.read().strip()
                if version:
                    return version
        return "desconhecida"
    except Exception:
        return "desconhecida"

def get_system_status():
    """Retorna o status dos componentes do sistema"""
    return {
        "docker": check_docker(),
        "proxmox": check_proxmox(),
    }
