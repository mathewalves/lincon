from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from lang.translations import translations
from utils.migration_state import MigrationState
from utils.system_info import check_docker
from utils.logger import setup_logging
import subprocess
import os
import shutil
import re
import signal
import time
import select
from datetime import datetime
import logging
from pathlib import Path
import tempfile

console = Console()
logger = setup_logging()

def get_text(key):
    """Obtém texto traduzido com fallback seguro e logging"""
    lang = os.environ.get("LINCON_LANG", "pt-br")
    try:
        lang_map = translations.get(lang)
        if not lang_map:
            logger.warning(f"Idioma não encontrado: {lang}. Usando 'pt-br'.")
            lang_map = translations.get("pt-br", {})
        if key not in lang_map:
            logger.warning(f"Tradução ausente para chave '{key}' no idioma '{lang}'.")
        return lang_map.get(key, key)
    except Exception as e:
        logger.warning(f"Falha ao obter tradução para '{key}': {e}")
        return key

def display_error(message_key):
    """Exibe um erro usando tradução e registra log"""
    message = get_text(message_key)
    logger.error(message)
    console.print(Panel(f"❌ {message}", title="❌ ERRO", style="red"))

def display_success(message_key):
    """Exibe sucesso usando tradução e registra log"""
    message = get_text(message_key)
    logger.info(message)
    console.print(Panel(f"✅ {message}", title="✅ SUCESSO", style="green"))

def display_warning(message_key):
    """Exibe aviso usando tradução e registra log"""
    message = get_text(message_key)
    logger.warning(message)
    console.print(Panel(f"⚠️  {message}", title="⚠️  ATENÇÃO", style="yellow"))

def display_recommendation(message_key):
    """Exibe recomendação usando tradução"""
    message = get_text(message_key)
    logger.info(f"Recomendação: {message}")
    console.print(Panel(f"💡 {message}", title="💡 RECOMENDAÇÃO", style="cyan"))

# Validações básicas
def validate_hostname(hostname):
    """Valida formato de hostname/IP"""
    if not hostname or len(hostname.strip()) == 0:
        return False
    hostname = hostname.strip()
    if len(hostname) > 253:
        return False
    if hostname.endswith('.'):
        hostname = hostname[:-1]
    parts = hostname.split('.')
    for part in parts:
        if not part or len(part) > 63:
            return False
        if part.startswith('-') or part.endswith('-'):
            return False
        if not re.match(r'^[a-zA-Z0-9-]+$', part):
            return False
    return True

def validate_port(port):
    """Valida porta SSH"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except ValueError:
        return False

def validate_container_name(name):
    """Valida nome do container Docker"""
    if not name or len(name.strip()) < 3:
        return False
    return re.match(r'^[a-zA-Z0-9_.-]+$', name.strip()) is not None

def check_dependencies():
    """Verifica dependências básicas"""
    logger.info("Verificando dependências do sistema...")
    console.print(f"[cyan]🔍 {get_text('CHECKING_DEPS')}[/cyan]")
    
    missing_deps = []
    
    if not check_docker():
        missing_deps.append(get_text("DOCKER_DEP"))
    
    if missing_deps:
        error_msg = get_text("MISSING_DEPS") + "\n" + "\n".join(f"• {dep}" for dep in missing_deps)
        logger.error(f"Dependências faltando: {missing_deps}")
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        display_recommendation(get_text("DEPS_RECOMMENDATION"))
        return False

    if not shutil.which("sshpass"):
        logger.info("Instalando sshpass...")
        try:
            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            subprocess.run(["apt-get", "install", "-y", "sshpass"], check=True, capture_output=True)
            display_success(get_text("SSHPASS_INSTALLED"))
        except subprocess.CalledProcessError:
            logger.error("Falha ao instalar sshpass")
            display_error(get_text("SSH_INSTALL_FAILED"))
            return False
    
    display_success(get_text("ALL_DEPS_AVAILABLE"))
    return True

def test_ssh_connection(target, port, password):
    """Testa conexão SSH"""
    console.print(f"[cyan]🔍 {get_text('TESTING_SSH')}[/cyan]")
    
    try:
        cmd = [
            "sshpass", "-p", password,
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"root@{target}",
            "echo 'SSH_OK'"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            display_success(get_text("SSH_CONNECTION_OK"))
            return True
        else:
            error_msg = get_text("SSH_CONNECTION_FAILED").format(result.stderr.strip())
            console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
            display_recommendation(get_text("SSH_CHECK_LIST"))
            return False
            
    except subprocess.TimeoutExpired:
        display_error(get_text("SSH_TIMEOUT"))
        return False
    except Exception as e:
        error_msg = get_text("SSH_TEST_ERROR").format(e)
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        return False

def collect_user_data():
    """Coleta dados do usuário"""
    console.clear()
    console.print(f"[bold cyan]{get_text('DOCKER_MIGRATION_TITLE')}[/bold cyan]\n")
    
    data = {}
    
    # nome do container
    console.print(f"[cyan]{get_text('DOCKER_CONTAINER_NAME')}[/cyan]")
    display_recommendation(get_text("DOCKER_CONTAINER_NAME_DESC"))
    
    while True:
        container_name = Prompt.ask(get_text("DOCKER_CONTAINER_NAME"))
        if validate_container_name(container_name):
            # Verifica se container já existe
            try:
                result = subprocess.run(["docker", "ps", "-a", "--filter", f"name={container_name}"], 
                                      capture_output=True, text=True)
                if container_name in result.stdout:
                    warning_msg = get_text("DOCKER_CONTAINER_EXISTS").format(container_name)
                    console.print(Panel(f"⚠️  {warning_msg}", title="⚠️  ATENÇÃO", style="yellow"))
                    if not Confirm.ask(get_text("CHOOSE_ANOTHER_NAME")):
                        return None
                    continue
            except:
                pass
            data["container_name"] = container_name
            break
        else:
            display_error(get_text("DOCKER_CONTAINER_NAME_ERROR"))

    # host de origem
    console.print(f"\n[cyan]{get_text('SOURCE_SERVER')}[/cyan]")
    display_recommendation(get_text("SOURCE_SERVER_DESC"))
    
    while True:
        target = Prompt.ask(get_text("SOURCE_HOST_PROMPT"))
        if target and validate_hostname(target):
            data["target"] = target
            break
        else:
            display_error(get_text("INVALID_HOSTNAME"))

    # porta SSH
    ssh_port_title = get_text("SSH_PORT").format(data['target'])
    console.print(f"\n[cyan]{ssh_port_title}[/cyan]")
    
    while True:
        port = Prompt.ask(get_text("SSH_PORT_PROMPT"), default="22")
        if validate_port(port):
            data["port"] = port
            break
        else:
            display_error(get_text("INVALID_PORT"))

    # senha SSH
    console.print(f"\n[cyan]{get_text('SSH_CREDENTIALS')}[/cyan]")
    display_warning(get_text("SSH_PASSWORD_WARNING"))
    
    while True:
        password = Prompt.ask(get_text("SSH_PASSWORD_PROMPT"), password=True)
        if password:
            if test_ssh_connection(data["target"], data["port"], password):
                data["passwordSSH"] = password
                break
            else:
                if not Confirm.ask(get_text("TRY_ANOTHER_PASSWORD")):
                    return None
        else:
            display_error(get_text("PASSWORD_CANNOT_EMPTY"))
    
    # Configuração de rede
    console.print(f"\n[cyan]{get_text('NETWORK_CONFIG')}[/cyan]")
    
    table = Table(title=f"[bold cyan]{get_text('NETWORK_OPTIONS')}[/bold cyan]", show_header=True)
    table.add_column(get_text("NETWORK_OPTION"), style="cyan", width=6)
    table.add_column(get_text("NETWORK_TYPE"), style="green", width=15)
    table.add_column(get_text("NETWORK_DESCRIPTION"), style="dim")
    
    table.add_row("1", "bridge", "Rede bridge padrão")
    table.add_row("2", "host", "Rede do host")
    table.add_row("3", "none", "Sem rede")

    console.print(table)
    console.print()

    network_choice = Prompt.ask(get_text("CHOOSE_NETWORK_TYPE"), choices=["1", "2", "3"], default="1")
    
    if network_choice == "1":
        data["network"] = "bridge"
    elif network_choice == "2":
        data["network"] = "host"
    else:
        data["network"] = "none"
    
    # Configuração de portas
    if data["network"] != "host" and data["network"] != "none":
        console.print(f"\n[cyan]{get_text('PORT_MAPPING')}[/cyan]")
        console.print(f"[dim]💡 {get_text('PORT_MAPPING_FORMAT')}[/dim]")
        data["ports"] = Prompt.ask(get_text("PORT_MAPPING_PROMPT"), default="")
    else:
        data["ports"] = ""
    
    return data

def confirm_migration(data):
    """Confirma os detalhes da migração"""
    console.print(f"\n[bold cyan]{get_text('DOCKER_MIGRATION_CONFIRMATION_TITLE')}[/bold cyan]")
    
    table = Table(title=f"[bold green]{get_text('DOCKER_MIGRATION_DETAILS_TITLE')}[/bold green]", show_header=True)
    table.add_column(get_text("DOCKER_MIGRATION_ITEM"), style="cyan", width=20)
    table.add_column(get_text("DOCKER_MIGRATION_VALUE"), style="white")
    
    table.add_row(get_text("DOCKER_MIGRATION_CONTAINER_NAME"), f"[bright_green]{data['container_name']}[/bright_green]")
    table.add_row(get_text("DOCKER_MIGRATION_SOURCE_SERVER"), f"[bright_blue]{data['target']}:{data['port']}[/bright_blue]")
    table.add_row(get_text("DOCKER_MIGRATION_NETWORK"), f"[bright_yellow]{data['network']}[/bright_yellow]")
    
    if data.get("ports"):
        table.add_row(get_text("DOCKER_MIGRATION_PORTS"), f"[bright_magenta]{data['ports']}[/bright_magenta]")
    
    console.print(table)
    console.print()
    
    display_warning(get_text("DOCKER_MIGRATION_OPERATION_WARNING"))
    
    return Confirm.ask(get_text("CONFIRM_DOCKER_MIGRATION"), default=False)

def collect_filesystem_simple(target, port, password):
    """Coleta sistema de arquivos de forma simples e robusta"""
    console.print(f"[cyan]📡 {get_text('COLLECTING_FILESYSTEM')}[/cyan]")
    
    # Comando tar simplificado com exclusões essenciais
    tar_command = [
        "tar", "czf", "-",
        "--numeric-owner",
        "--exclude=./proc",
        "--exclude=./sys",
        "--exclude=./dev",
        "--exclude=./tmp",
        "--exclude=./run",
        "--exclude=./mnt",
        "--exclude=./media",
        "--exclude=./lost+found",
        "--exclude=./var/cache/apt/archives",
        "--exclude=./boot",
        "--exclude=./lib/modules",
        "--exclude=./var/log/*.log",
        "--exclude=./var/log/*.log.*",
        "--exclude=./var/log/apt",
        "--exclude=./var/log/btmp",
        "--exclude=./var/log/faillog",
        "--exclude=./var/log/lastlog",
        "--exclude=./var/log/wtmp",
        "--exclude=./var/log/alternatives.log",
        "--exclude=./var/log/bootstrap.log",
        "--exclude=./var/log/dpkg.log",
        "--exclude=./var/log/fontconfig.log",
        "--exclude=./var/log/fsck",
        "--exclude=./var/log/installer",
        "--exclude=./var/log/landscape",
        "--exclude=./var/log/lightdm",
        "--exclude=./var/log/upstart",
        "--exclude=./var/log/unattended-upgrades",
        "--exclude=./var/cache",
        "--exclude=./var/tmp",
        "--exclude=./var/spool",
        "--exclude=./var/run",
        "--exclude=./swapfile",
        "--exclude=./swap.img",
        "--exclude=./.snapshots",
        "--exclude=./.zfs",
        "--exclude=./.btrfs",
        "--exclude=./var/lib/docker",
        "--exclude=./var/lib/containers",
        "--exclude=./var/lib/dpkg/info",
        "--exclude=./var/lib/apt",
        "--exclude=./var/lib/dpkg",
        "--exclude=./var/cache/apt",
        "--exclude=./var/cache/debconf",
        "--exclude=./var/lib/systemd",
        "--exclude=./var/lib/NetworkManager",
        "--exclude=./var/lib/upower",
        "--exclude=./var/lib/udisks2",
        "--exclude=./var/lib/polkit-1",
        "--exclude=./var/lib/colord",
        "--exclude=./var/lib/AccountsService",
        "--exclude=./var/lib/gdm3",
        "--exclude=./var/lib/lightdm",
        "--exclude=./var/lib/sddm",
        "--exclude=./var/lib/plymouth",
        "--exclude=./var/lib/update-notifier",
        "--exclude=./var/lib/ubuntu-release-upgrader",
        "--exclude=./var/lib/ubuntu-drivers-common",
        "--exclude=./var/lib/snapd",
        "--exclude=./var/lib/flatpak",
        "--exclude=./var/lib/app-info",
        "--exclude=./var/lib/dbus",
        "--exclude=./var/lib/aspell",
        "--exclude=./var/lib/dictionaries-common",
        "--exclude=./var/lib/wordlists",
        "--exclude=./var/lib/mlocate",
        "--exclude=./var/lib/alternatives",
        "--exclude=./var/lib/menu",
        "--exclude=./var/lib/update-rc.d",
        "--exclude=./var/lib/dpkg/alternatives",
        "--exclude=./var/lib/dpkg/triggers",
        "--exclude=./var/lib/dpkg/updates",
        "--exclude=./var/lib/dpkg/parts",
        "--exclude=./var/lib/dpkg/status-old",
        "--exclude=./var/lib/dpkg/status",
        "--exclude=./var/lib/dpkg/available",
        "--exclude=./var/lib/dpkg/available-old",
        "--exclude=./var/lib/dpkg/lock",
        "--exclude=./var/lib/dpkg/lock-frontend",
        "."
    ]
    
    ssh_command = [
        "sshpass", "-p", password,
        "ssh", "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"root@{target}",
        "cd / && " + " ".join(tar_command)
    ]
    
    return subprocess.Popen(ssh_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def detect_os_simple(target, port, password):
    """Detecta o sistema operacional da máquina de origem"""
    console.print(f"[cyan]🔍 Detectando sistema operacional...[/cyan]")
    
    try:
        # Tenta detectar via /etc/os-release
        cmd = [
            "sshpass", "-p", password,
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"root@{target}",
            "cat /etc/os-release 2>/dev/null || echo 'ID=unknown'"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            os_info = result.stdout.strip()
            
            # Parse do arquivo os-release
            os_data = {}
            for line in os_info.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os_data[key] = value.strip('"')
            
            # Identifica o sistema
            os_id = os_data.get('ID', '').lower()
            os_name = os_data.get('NAME', '').lower()
            os_version = os_data.get('VERSION_ID', '')
            
            if 'debian' in os_id or 'debian' in os_name:
                return {
                    'os': 'debian',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'Debian'),
                    'recommended_image': f'debian:{os_version}' if os_version else 'debian:11'
                }
            elif 'ubuntu' in os_id or 'ubuntu' in os_name:
                return {
                    'os': 'ubuntu',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'Ubuntu'),
                    'recommended_image': f'ubuntu:{os_version}' if os_version else 'ubuntu:20.04'
                }
            elif 'centos' in os_id or 'centos' in os_name:
                return {
                    'os': 'centos',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'CentOS'),
                    'recommended_image': f'centos:{os_version}' if os_version else 'centos:7'
                }
            elif 'rocky' in os_id or 'rocky' in os_name:
                return {
                    'os': 'rocky',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'Rocky Linux'),
                    'recommended_image': f'rocky:{os_version}' if os_version else 'rocky:8'
                }
            elif 'alma' in os_id or 'alma' in os_name:
                return {
                    'os': 'alma',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'AlmaLinux'),
                    'recommended_image': f'alma:{os_version}' if os_version else 'alma:8'
                }
            elif 'fedora' in os_id or 'fedora' in os_name:
                return {
                    'os': 'fedora',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'Fedora'),
                    'recommended_image': f'fedora:{os_version}' if os_version else 'fedora:36'
                }
            elif 'opensuse' in os_id or 'suse' in os_name:
                return {
                    'os': 'opensuse',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'openSUSE'),
                    'recommended_image': f'opensuse/leap:{os_version}' if os_version else 'opensuse/leap:15.4'
                }
            elif 'alpine' in os_id or 'alpine' in os_name:
                return {
                    'os': 'alpine',
                    'version': os_version,
                    'name': os_data.get('PRETTY_NAME', 'Alpine Linux'),
                    'recommended_image': f'alpine:{os_version}' if os_version else 'alpine:3.17'
                }
            else:
                # Fallback: tenta detectar via outros métodos
                return detect_os_fallback(target, port, password)
        
    except Exception as e:
        console.print(f"[yellow]⚠️  Erro na detecção automática: {e}[/yellow]")
        return detect_os_fallback(target, port, password)
    
    return detect_os_fallback(target, port, password)

def detect_os_fallback(target, port, password):
    """Detecção alternativa do sistema operacional"""
    try:
        # Tenta detectar via lsb_release
        cmd = [
            "sshpass", "-p", password,
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"root@{target}",
            "lsb_release -a 2>/dev/null || echo 'Distributor ID: unknown'"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            output = result.stdout.lower()
            
            if 'debian' in output:
                return {
                    'os': 'debian',
                    'version': '11',
                    'name': 'Debian GNU/Linux',
                    'recommended_image': 'debian:11'
                }
            elif 'ubuntu' in output:
                return {
                    'os': 'ubuntu',
                    'version': '20.04',
                    'name': 'Ubuntu',
                    'recommended_image': 'ubuntu:20.04'
                }
            elif 'centos' in output:
                return {
                    'os': 'centos',
                    'version': '7',
                    'name': 'CentOS',
                    'recommended_image': 'centos:7'
                }
            elif 'rocky' in output:
                return {
                    'os': 'rocky',
                    'version': '8',
                    'name': 'Rocky Linux',
                    'recommended_image': 'rocky:8'
                }
            elif 'fedora' in output:
                return {
                    'os': 'fedora',
                    'version': '36',
                    'name': 'Fedora',
                    'recommended_image': 'fedora:36'
                }
            elif 'opensuse' in output or 'suse' in output:
                return {
                    'os': 'opensuse',
                    'version': '15.4',
                    'name': 'openSUSE',
                    'recommended_image': 'opensuse/leap:15.4'
                }
            elif 'alpine' in output:
                return {
                    'os': 'alpine',
                    'version': '3.17',
                    'name': 'Alpine Linux',
                    'recommended_image': 'alpine:3.17'
                }
    except:
        pass
    
    # Fallback padrão
    return {
        'os': 'unknown',
        'version': 'unknown',
        'name': 'Sistema Operacional Desconhecido',
        'recommended_image': 'ubuntu:20.04'
    }

def select_base_image(os_info):
    """Permite ao usuário selecionar a imagem base"""
    console.print(f"\n[cyan]🐳 {get_text('BASE_IMAGE_SELECTION')}[/cyan]")
    
    # Mostra informações detectadas
    if os_info['os'] != 'unknown':
        console.print(f"[green]✅ Sistema detectado:[/green] {os_info['name']}")
        console.print(f"[green]✅ Imagem recomendada:[/green] {os_info['recommended_image']}")
    else:
        console.print(f"[yellow]⚠️  Sistema não detectado automaticamente[/yellow]")
        console.print(f"[yellow]⚠️  Imagem padrão:[/yellow] {os_info['recommended_image']}")
    
    # Opções de imagens base
    base_images = [
        ("debian:11", "Debian 11 (Bullseye)"),
        ("debian:12", "Debian 12 (Bookworm)"),
        ("ubuntu:20.04", "Ubuntu 20.04 LTS"),
        ("ubuntu:22.04", "Ubuntu 22.04 LTS"),
        ("centos:7", "CentOS 7"),
        ("rocky:8", "Rocky Linux 8"),
        ("rocky:9", "Rocky Linux 9"),
        ("alma:8", "AlmaLinux 8"),
        ("alma:9", "AlmaLinux 9"),
        ("fedora:36", "Fedora 36"),
        ("fedora:37", "Fedora 37"),
        ("opensuse/leap:15.4", "openSUSE Leap 15.4"),
        ("alpine:3.17", "Alpine Linux 3.17"),
        ("alpine:3.18", "Alpine Linux 3.18"),
        ("custom", "Imagem personalizada")
    ]
    
    # Encontra a imagem recomendada na lista
    recommended_index = None
    for i, (image, desc) in enumerate(base_images):
        if image == os_info['recommended_image']:
            recommended_index = i
            break
    
    # Exibe tabela de opções
    table = Table(title=f"[bold cyan]{get_text('AVAILABLE_BASE_IMAGES')}[/bold cyan]", show_header=True)
    table.add_column("Opção", style="cyan", width=6)
    table.add_column("Imagem", style="green", width=25)
    table.add_column("Descrição", style="white", width=30)
    table.add_column("Recomendada", style="yellow", width=12)
    
    for i, (image, desc) in enumerate(base_images):
        is_recommended = "✅ Sim" if i == recommended_index else ""
        table.add_row(f"[{i+1}]", image, desc, is_recommended)
    
    console.print(table)
    console.print()
    
    if recommended_index is not None:
        display_recommendation(get_text("RECOMMENDED_IMAGE_MESSAGE").format(os_info['recommended_image']))
    
    # Seleção do usuário
    while True:
        try:
            choice = Prompt.ask(
                get_text("SELECT_BASE_IMAGE_PROMPT"),
                choices=[str(i) for i in range(1, len(base_images) + 1)] + ["r"],
                default=str(recommended_index + 1) if recommended_index is not None else "1"
            )
            
            if choice == "r" and recommended_index is not None:
                selected_image = base_images[recommended_index][0]
                console.print(f"[green]✅ Imagem selecionada: {selected_image}[/green]")
                return selected_image
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(base_images):
                selected_image = base_images[choice_idx][0]
                
                if selected_image == "custom":
                    custom_image = Prompt.ask(get_text("ENTER_CUSTOM_IMAGE"))
                    if custom_image and ":" in custom_image:
                        console.print(f"[green]✅ Imagem personalizada: {custom_image}[/green]")
                        return custom_image
                    else:
                        display_error(get_text("INVALID_CUSTOM_IMAGE"))
                        continue
                else:
                    console.print(f"[green]✅ Imagem selecionada: {selected_image}[/green]")
                    return selected_image
            else:
                display_error(get_text("INVALID_IMAGE_CHOICE"))
                
        except ValueError:
            display_error(get_text("INVALID_IMAGE_CHOICE"))

def create_dockerfile_with_base_image(base_image):
    """Cria Dockerfile com a imagem base selecionada"""
    return f"""FROM {base_image}

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

def execute_docker_migration_simple(data):
    """Executa migração Docker de forma simples e direta"""
    logger.info(f"Iniciando migração Docker para container {data['container_name']}")
    console.print(f"\n[cyan]{get_text('DOCKER_MIGRATION_STARTING')}[/cyan]")
    
    with tempfile.TemporaryDirectory(prefix=f"{data['container_name']}_migration_") as temp_dir:
        temp_path = Path(temp_dir)
        filesystem_tar = temp_path / "filesystem.tar.gz"
        
        try:
            # Coleta sistema de arquivos
            console.print(f"[cyan]📡 {get_text('COLLECTING_FILESYSTEM')}[/cyan]")
            
            process = collect_filesystem_simple(data["target"], data["port"], data["passwordSSH"])
            
            with Progress(
                SpinnerColumn(style="cyan"),
                TextColumn("[bold blue]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("📡 Coletando sistema de arquivos...", total=None)
                
                with open(filesystem_tar, 'wb') as f:
                    while True:
                        if process.poll() is not None:
                            break
                        
                        ready, _, _ = select.select([process.stdout], [], [], 1.0)
                        if ready:
                            chunk = process.stdout.read(8192)
                            if chunk:
                                f.write(chunk)
                                # Atualiza progresso baseado no tamanho do arquivo
                                current_size = filesystem_tar.stat().st_size if filesystem_tar.exists() else 0
                                if current_size > 0:
                                    size_mb = current_size / (1024 * 1024)
                                    progress.update(task, description=f"📡 Coletando sistema... ({size_mb:.1f} MB)")
            
            # verifica se a coleta foi bem-sucedida
            return_code = process.wait(timeout=30)
            if return_code != 0:
                stderr_output = ""
                try:
                    stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                except:
                    pass
                
                console.print(f"[red]❌ {get_text('FILESYSTEM_COLLECTION_FAILED')}[/red]")
                if stderr_output:
                    console.print(f"[red]Erro: {stderr_output.strip()}[/red]")
                return False
            
            if filesystem_tar.stat().st_size == 0:
                console.print(f"[red]❌ {get_text('FILESYSTEM_COLLECTION_FAILED')}[/red]")
                return False
            
            size_mb = filesystem_tar.stat().st_size / (1024 * 1024)
            console.print(f"[green]✅ {get_text('SYSTEM_COLLECTED')}: {size_mb:.1f} {get_text('MB')}[/green]")
            
            # detecta o sistema operacional da máquina de origem
            os_info = detect_os_simple(data["target"], data["port"], data["passwordSSH"])
            
            # permite ao usuário selecionar a imagem base
            base_image_choice = select_base_image(os_info)
            
            # criar Dockerfile
            console.print(f"[cyan]🐳 {get_text('BUILDING_DOCKER_IMAGE')}[/cyan]")
            dockerfile_path = temp_path / "Dockerfile"
            with open(dockerfile_path, 'w') as f:
                f.write(create_dockerfile_with_base_image(base_image_choice))
            
            # constrói imagem Docker
            build_command = [
                "docker", "build", "-t", f"lincon-migrated:{data['container_name']}", 
                str(temp_path)
            ]
            
            with Progress(
                SpinnerColumn(style="cyan"),
                TextColumn("[bold blue]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("🔨 Construindo imagem Docker...", total=None)
                
                build_process = subprocess.Popen(
                    build_command, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                while True:
                    if build_process.poll() is not None:
                        break
                    
                    ready, _, _ = select.select([build_process.stdout], [], [], 1.0)
                    if ready:
                        line = build_process.stdout.readline()
                        if line:
                            line = line.strip()
                            if line:
                                console.print(f"[dim]{line}[/dim]")
            
            if build_process.returncode != 0:
                console.print(f"[red]❌ {get_text('DOCKER_IMAGE_BUILD_FAILED')}[/red]")
                return False
            
            display_success("MSG_DOCKER_IMAGE_CREATED")
            
            # executa container
            console.print(f"[cyan]🚀 {get_text('STARTING_DOCKER_CONTAINER')}[/cyan]")
            
            run_command = ["docker", "run", "-d", "--name", data['container_name']]
            
            # adiciona configuração de rede
            if data["network"] == "host":
                run_command.extend(["--network", "host"])
            elif data["network"] == "none":
                run_command.extend(["--network", "none"])
            
            # adiciona mapeamento de portas
            if data.get("ports") and data["network"] not in ["host", "none"]:
                for port_map in data["ports"].split(","):
                    if ":" in port_map.strip():
                        run_command.extend(["-p", port_map.strip()])
            
            run_command.append(f"lincon-migrated:{data['container_name']}")
            
            result = subprocess.run(run_command, capture_output=True, text=True)
            
            if result.returncode == 0:
                display_success("MSG_DOCKER_CONTAINER_STARTED")
                
                # mostra informações finais
                console.print("="*70)
                console.print(f"[bold green]{get_text('DOCKER_MIGRATION_COMPLETED')}[/bold green]")
                console.print("="*70)
                
                console.print(f"[cyan]{get_text('DOCKER_CONTAINER_NAME')}:[/cyan] {data['container_name']}")
                console.print(f"[cyan]{get_text('DOCKER_IMAGE')}:[/cyan] lincon-migrated:{data['container_name']}")
                console.print(f"[cyan]{get_text('DOCKER_NETWORK')}:[/cyan] {data['network']}")
                
                if data["network"] not in ["host", "none"] and data.get("ports"):
                    console.print(f"[cyan]{get_text('DOCKER_PORTS')}:[/cyan] {data['ports']}")
                
                console.print(f"\n[yellow]{get_text('DOCKER_USEFUL_COMMANDS')}[/yellow]")
                console.print(f"[white]   docker exec -it {data['container_name']} bash    [dim]{get_text('DOCKER_EXEC_DESC')}[/dim][/white]")
                console.print(f"[white]   docker stop {data['container_name']}     [dim]{get_text('DOCKER_STOP_DESC')}[/dim][/white]")
                console.print(f"[white]   docker start {data['container_name']}    [dim]{get_text('DOCKER_START_DESC')}[/dim][/white]")
                console.print(f"[white]   docker logs {data['container_name']}    [dim]{get_text('DOCKER_LOGS_DESC')}[/dim][/white]")
                
                return True
            else:
                console.print(f"[red]❌ {get_text('DOCKER_CONTAINER_START_FAILED')}:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante migração Docker: {e}")
            console.print(f"[red]❌ {get_text('UNEXPECTED_ERROR')}: {e}[/red]")
            return False

def check_incomplete_migrations():
    """Verifica migrações incompletas"""
    state_manager = MigrationState()
    incomplete = state_manager.get_incomplete_migrations()
    
    if not incomplete:
        return MigrationState(), None
        
    console.print(f"\n[bold yellow]{get_text('INCOMPLETE_MIGRATIONS')}[/bold yellow]")
    
    table = Table(title=f"[bold yellow]{get_text('PENDING_MIGRATIONS')}[/bold yellow]",
                 show_header=True, header_style="bold bright_white",
                 border_style="yellow", show_edge=False)
    table.add_column(get_text("MIGRATION_ID"), justify="right", style="bright_cyan", width=12)
    table.add_column(get_text("MIGRATION_DATE"), style="bright_magenta", width=16)
    table.add_column(get_text("MIGRATION_CONTAINER"), style="bright_green", width=15)
    table.add_column(get_text("MIGRATION_STATUS"), style="bright_yellow")
    
    for m in incomplete:
        date = datetime.fromisoformat(m['timestamp']).strftime('%d/%m/%Y %H:%M')
        data = m.get('data', {})
        container = data.get('container_name', get_text('UNKNOWN_CONTAINER')) if data else get_text('UNKNOWN_CONTAINER')
        table.add_row(
            m['migration_id'],
            date,
            container,
            m['step']
        )
    
    console.print()
    console.print(table)
    console.print()
    
    if Confirm.ask(get_text("CONTINUE_PREVIOUS")):
        choices = [m['migration_id'] for m in incomplete] + ["0"]
        choice = Prompt.ask(
            get_text("MIGRATION_ID_PROMPT"),
            choices=choices
        )
        
        if choice != "0":
            selected = next(m for m in incomplete if m['migration_id'] == choice)
            return MigrationState(choice), selected
    
    return MigrationState(), None

def migrate_docker():
    """Função principal de migração Docker"""
    def handle_interrupt(signum, frame):
        if 'state_manager' in locals() and state_manager is not None and 'data' in locals():
            state_manager.save_state(data, "interrupted")
        console.print(f"\n[red]{get_text('DOCKER_MIGRATION_CANCELLED_BY_USER')}[/red]")
        exit(1)
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    # 1. verificar migrações incompletas
    state_manager, previous_state = check_incomplete_migrations()
    
    if not check_dependencies():
        return False
    
    # 2. Se existe estado anterior, retoma
    if previous_state:
        data = previous_state['data']
        continue_msg = get_text("CONTINUING_MIGRATION").format(previous_state['migration_id'], previous_state['step'])
        console.print(f"[yellow]{continue_msg}[/yellow]")
    else:
        data = collect_user_data()
        if not data:
            console.print(f"\n[yellow]{get_text('MIGRATION_CANCELLED_INPUT')}[/yellow]")
            return False
        state_manager.save_state(data, "input_collected")
    
    # 3. validação dos dados
    state_manager.save_state(data, "validated")
    
    # 4. confirmação
    if not previous_state or previous_state['step'] not in ['converting', 'validated']:
        if not confirm_migration(data):
            console.print(f"\n[yellow]{get_text('MIGRATION_CANCELLED_INPUT')}[/yellow]")
            state_manager.save_state(data, "cancelled")
            return False
    
    state_manager.save_state(data, "converting")

    # 5. executar migração
    if execute_docker_migration_simple(data):
        state_manager.save_state(data, "completed")
        state_manager.clear_state()
        return True
    else:
        state_manager.save_state(data, "failed")
        return False

if __name__ == "__main__":
    migrate_docker()
