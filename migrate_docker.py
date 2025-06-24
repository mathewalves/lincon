from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import track
from lang.translations import translations
from utils.migration_state import MigrationState
from utils.system_info import check_docker
from datetime import datetime
import subprocess
import os
import shutil
from pathlib import Path
import tempfile
import signal
import logging

logger = logging.getLogger('lincon')

console = Console()
current_language = "pt-br"

def display_message(title, message):
    """Exibe uma mensagem em um painel"""
    title_text = translations[current_language].get(title, title)
    message_text = translations[current_language].get(message, message)
    console.print(Panel(message_text, title=title_text))

def check_dependencies():
    """Verifica se as dependências necessárias estão instaladas"""
    # Verifica Docker
    if not check_docker():
        display_message("TITLE_ERROR", "MSG_NO_DOCKER")
        console.print("\n[yellow]Para instalar o Docker, execute:[/yellow]")
        console.print("[cyan]curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh[/cyan]")
        return False

    # Verifica/instala sshpass
    if not shutil.which("sshpass"):
        display_message("TITLE_INFO", "MSG_INSTALLING_SSHPASS")
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "sshpass"], check=True)
            display_message("TITLE_SUCCESS", "MSG_SSHPASS_INSTALLED")
        except subprocess.CalledProcessError:
            display_message("TITLE_ERROR", "MSG_SSH_INSTALL_FAILED")
            return False
    return True

def user_input():
    """Coleta todos os dados necessários do usuário"""
    data = {}
    
    data["container_name"] = Prompt.ask("Nome do Container Docker")
    data["target"] = Prompt.ask("Host de Origem")
    data["port"] = Prompt.ask("Porta SSH", default="22")
    data["passwordSSH"] = Prompt.ask("Senha SSH", password=True)
    
    # Configuração de rede
    table = Table(show_header=False)
    table.add_row("[1] Bridge padrão (docker0)")
    table.add_row("[2] Host network")
    table.add_row("[3] Personalizada")

    console.print(Panel("Selecione o tipo de rede:", title="Configuração de Rede"))
    console.print(table)

    network_choice = Prompt.ask("", choices=["1", "2", "3"])
    
    if network_choice == "1":
        data["network"] = "bridge"
    elif network_choice == "2":
        data["network"] = "host"
    else:
        data["network"] = Prompt.ask("Nome da rede personalizada")
    
    # Configuração de portas
    if data["network"] != "host":
        data["ports"] = Prompt.ask("Mapeamento de portas (ex: 80:80,443:443)", default="")
    else:
        data["ports"] = ""
    
    # Configuração de volumes
    data["volumes"] = Prompt.ask("Volumes extras (ex: /host/path:/container/path)", default="")
    
    return data

def validate_parameters(data):
    """Valida os parâmetros fornecidos"""
    required_fields = ["container_name", "target", "port", "passwordSSH", "network"]
                      
    for field in required_fields:
        if not data.get(field):
            display_message("TITLE_ERROR", "MSG_MISSING_PARAMS")
            return False
            
    return True

def collect_fs(ssh_command):
    """Coleta o sistema de arquivos via SSH"""
    excluded_paths = [
        "/proc/*", "/sys/*", "/dev/*", "/tmp/*", "/run/*",
        "/mnt/*", "/media/*", "/lost+found", "/var/cache/apt/archives/*",
        "/boot/*", "/lib/modules/*"
    ]
    
    tar_command = ["tar", "czpf", "-", "--numeric-owner", "--anchored"]
    for path in excluded_paths:
        tar_command.extend(["--exclude", path])
    tar_command.append(".")
    
    ssh_command.extend(["cd / &&"] + tar_command)
    return subprocess.Popen(ssh_command, stdout=subprocess.PIPE)

def create_dockerfile(base_os="ubuntu:20.04"):
    """Cria um Dockerfile básico"""
    dockerfile_content = f"""FROM {base_os}

# Copia o sistema de arquivos
ADD filesystem.tar.gz /

# Instala dependências básicas
RUN apt-get update && apt-get install -y \\
    openssh-server \\
    sudo \\
    && rm -rf /var/lib/apt/lists/*

# Configura SSH
RUN mkdir /var/run/sshd
RUN echo 'root:lincon123' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Expõe porta SSH
EXPOSE 22

# Comando padrão
CMD ["/usr/sbin/sshd", "-D"]
"""
    return dockerfile_content

def convert(data):
    """Converte e cria o container Docker"""
    with tempfile.TemporaryDirectory(prefix=f"{data['container_name']}_migration_") as temp_dir:
        temp_path = Path(temp_dir)
        
        display_message("TITLE_INFO", "MSG_COLLECTING_FS")
        
        ssh_command = [
            "sshpass", "-p", data["passwordSSH"],
            "ssh", "-p", data["port"],
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"root@{data['target']}"
        ]
        
        try:
            # Coleta sistema de arquivos
            process = collect_fs(ssh_command)
            filesystem_tar = temp_path / "filesystem.tar.gz"
            
            with open(filesystem_tar, 'wb') as f:
                for chunk in process.stdout:
                    f.write(chunk)
            
            if process.wait() != 0:
                display_message("TITLE_ERROR", "MSG_SSH_CONNECTION_FAILED")
                return False
                
            if filesystem_tar.stat().st_size == 0:
                display_message("TITLE_ERROR", "MSG_FS_COLLECTION_EMPTY")
                return False
            
            display_message("TITLE_INFO", "MSG_CREATING_DOCKER_IMAGE")
            
            # Cria Dockerfile
            dockerfile_path = temp_path / "Dockerfile"
            with open(dockerfile_path, 'w') as f:
                f.write(create_dockerfile())
            
            # Constrói imagem Docker
            build_command = [
                "docker", "build", "-t", f"lincon-migrated:{data['container_name']}", 
                str(temp_path)
            ]
            
            if subprocess.run(build_command).returncode != 0:
                display_message("TITLE_ERROR", "MSG_DOCKER_BUILD_FAILED")
                return False
            
            display_message("TITLE_SUCCESS", "MSG_DOCKER_IMAGE_CREATED")
            
            # Executa container
            display_message("TITLE_INFO", "MSG_STARTING_DOCKER_CONTAINER")
            
            run_command = ["docker", "run", "-d", "--name", data['container_name']]
            
            # Adiciona configuração de rede
            if data["network"] == "host":
                run_command.extend(["--network", "host"])
            elif data["network"] != "bridge":
                run_command.extend(["--network", data["network"]])
            
            # Adiciona mapeamento de portas
            if data.get("ports") and data["network"] != "host":
                for port_map in data["ports"].split(","):
                    if ":" in port_map.strip():
                        run_command.extend(["-p", port_map.strip()])
            
            # Adiciona volumes
            if data.get("volumes"):
                for volume in data["volumes"].split(","):
                    if ":" in volume.strip():
                        run_command.extend(["-v", volume.strip()])
            
            run_command.append(f"lincon-migrated:{data['container_name']}")
            
            if subprocess.run(run_command).returncode == 0:
                display_message("TITLE_SUCCESS", "MSG_DOCKER_CONTAINER_STARTED")
                
                # Mostra informações do container
                console.print(f"\n[green]Container criado com sucesso![/green]")
                console.print(f"[cyan]Nome:[/cyan] {data['container_name']}")
                console.print(f"[cyan]Imagem:[/cyan] lincon-migrated:{data['container_name']}")
                console.print(f"[cyan]Rede:[/cyan] {data['network']}")
                
                if data["network"] != "host" and data.get("ports"):
                    console.print(f"[cyan]Portas:[/cyan] {data['ports']}")
                
                console.print("\n[yellow]Para acessar o container:[/yellow]")
                console.print(f"[white]docker exec -it {data['container_name']} /bin/bash[/white]")
                
                return True
            else:
                display_message("TITLE_ERROR", "MSG_DOCKER_CONTAINER_FAILED")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante conversão: {e}")
            display_message("TITLE_ERROR", str(e))
            return False

def confirm_migration(data):
    """Confirma os detalhes da migração com o usuário"""
    details = "Detalhes da Migração Docker:\n"
    details += f"  Nome do Container: {data['container_name']}\n"
    details += f"  Host de Origem: {data['target']}:{data['port']}\n"
    details += f"  Rede: {data['network']}\n"
    
    if data.get("ports"):
        details += f"  Portas: {data['ports']}\n"
    
    if data.get("volumes"):
        details += f"  Volumes: {data['volumes']}\n"
    
    console.print(Panel(details, title="Confirmar Migração Docker"))
    return Confirm.ask("Confirmar migração?")

def migrate_docker():
    """Função principal de migração para Docker"""
    def handle_interrupt(signum, frame):
        if 'state_manager' in locals():
            state_manager.save_state(data, "interrupted")
        display_message("TITLE_INFO", "MSG_MIGRATION_CANCELLED_INT")
        exit(1)
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    state_manager = MigrationState()
    
    if not check_dependencies():
        return False
    
    data = user_input()
    if not data:
        display_message("TITLE_ERROR", "MSG_USER_INPUT_CANCELLED")
        return False
    
    state_manager.save_state(data, "input_collected")
    
    if not validate_parameters(data):
        return False
    
    state_manager.save_state(data, "validated")
    
    if not confirm_migration(data):
        display_message("TITLE_INFO", "MSG_MIGRATION_CANCELLED_BY_USER")
        state_manager.save_state(data, "cancelled")
        return False
    
    state_manager.save_state(data, "converting")
    if convert(data):
        state_manager.save_state(data, "completed")
        state_manager.clear_state()
        return True
    else:
        state_manager.save_state(data, "failed")
        return False

if __name__ == "__main__":
    migrate_docker()
