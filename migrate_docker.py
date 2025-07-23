from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
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

def get_text(key):
    """Obtém texto traduzido"""
    return translations[current_language].get(key, key)

def display_error(message_key):
    """Exibe um erro usando tradução"""
    message = get_text(message_key)
    console.print(Panel(f"❌ {message}", title="❌ ERRO", style="red"))

def display_success(message_key):
    """Exibe sucesso usando tradução"""
    message = get_text(message_key)
    console.print(Panel(f"✅ {message}", title="✅ SUCESSO", style="green"))

def display_warning(message_key):
    """Exibe aviso usando tradução"""
    message = get_text(message_key)
    console.print(Panel(f"⚠️  {message}", title="⚠️  ATENÇÃO", style="yellow"))

def display_recommendation(message_key):
    """Exibe recomendação usando tradução"""
    message = get_text(message_key)
    console.print(Panel(f"💡 {message}", title="💡 RECOMENDAÇÃO", style="cyan"))

def check_dependencies():
    """Verifica se as dependências necessárias estão instaladas"""
    console.print(f"[cyan]🔍 {get_text('CHECKING_DEPS')}[/cyan]")
    
    # Verifica Docker
    if not check_docker():
        display_error("MSG_NO_DOCKER")
        console.print(f"\n[yellow]Para instalar o Docker, execute:[/yellow]")
        console.print(f"[cyan]curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh[/cyan]")
        return False

    # Verifica/instala sshpass
    if not shutil.which("sshpass"):
        console.print(f"[cyan]{get_text('INSTALLING_SSHPASS')}[/cyan]")
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=True, capture_output=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "sshpass"], check=True, capture_output=True)
            display_success("SSHPASS_INSTALLED")
        except subprocess.CalledProcessError:
            display_error("SSH_INSTALL_FAILED")
            return False
    
    display_success("ALL_DEPS_AVAILABLE")
    return True

def test_ssh_connection(target, port, password):
    """Testa conexão SSH com feedback visual"""
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
            display_success("SSH_CONNECTION_OK")
            return True
        else:
            error_msg = get_text("SSH_CONNECTION_FAILED").format(result.stderr.strip())
            console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
            return False
            
    except subprocess.TimeoutExpired:
        display_error("SSH_TIMEOUT")
        return False
    except Exception as e:
        error_msg = get_text("SSH_TEST_ERROR").format(e)
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        return False

def user_input():
    """Coleta todos os dados necessários do usuário com interface moderna"""
    console.clear()
    console.print(f"[bold cyan]🐳 LINCON - Migração Linux → Docker[/bold cyan]\n")
    
    data = {}
    
    # Nome do Container
    console.print(f"[cyan]📦 Nome do Container Docker[/cyan]")
    console.print(f"[dim]💡 Use nomes descritivos sem espaços (ex: web-app, api-server)[/dim]")
    
    while True:
        container_name = Prompt.ask("Nome do Container Docker")
        if container_name and len(container_name) >= 3:
            data["container_name"] = container_name
            break
        else:
            console.print(f"[red]❌ Nome deve ter pelo menos 3 caracteres![/red]")
    
    # Host de origem
    console.print(f"\n[cyan]🖥️  Servidor de Origem[/cyan]")
    console.print(f"[dim]💡 Use IP ou hostname do servidor Linux a ser migrado[/dim]")
    
    while True:
        target = Prompt.ask("Host/IP de origem")
        if target and len(target) >= 3:
            data["target"] = target
            break
        else:
            console.print(f"[red]❌ Host inválido![/red]")
    
    # Porta SSH
    console.print(f"\n[cyan]🔌 Porta SSH (Host: {data['target']})[/cyan]")
    
    while True:
        port = Prompt.ask("Porta SSH", default="22")
        try:
            port_num = int(port)
            if 1 <= port_num <= 65535:
                data["port"] = port
                break
            else:
                console.print(f"[red]❌ Porta deve estar entre 1-65535![/red]")
        except ValueError:
            console.print(f"[red]❌ Digite apenas números![/red]")
    
    # Senha SSH
    console.print(f"\n[cyan]🔐 Credenciais SSH[/cyan]")
    console.print(f"[yellow]⚠️  A senha será usada para conectar como root no servidor de origem[/yellow]")
    
    while True:
        password = Prompt.ask("Senha SSH do root", password=True)
        if password:
            if test_ssh_connection(data["target"], data["port"], password):
                data["passwordSSH"] = password
                break
            else:
                if not Confirm.ask("Tentar outra senha?"):
                    return None
        else:
            console.print(f"[red]❌ Senha não pode estar vazia![/red]")
    
    # Configuração de rede
    console.print(f"\n[cyan]🌐 Configuração de Rede[/cyan]")
    
    table = Table(show_header=True, box=None)
    table.add_column("Opção", style="cyan", width=6)
    table.add_column("Tipo", style="green", width=15)
    table.add_column("Descrição", style="dim")
    
    table.add_row("[1]", "Bridge padrão", "docker0 (padrão)")
    table.add_row("[2]", "Host network", "Usa rede do host")
    table.add_row("[3]", "Personalizada", "Rede customizada")

    console.print(table)
    
    network_choice = Prompt.ask("Escolha o tipo de rede", choices=["1", "2", "3"], default="1")
    
    if network_choice == "1":
        data["network"] = "bridge"
    elif network_choice == "2":
        data["network"] = "host"
    else:
        data["network"] = Prompt.ask("Nome da rede personalizada")
    
    # Configuração de portas
    if data["network"] != "host":
        console.print(f"\n[cyan]🔗 Mapeamento de Portas[/cyan]")
        console.print(f"[dim]💡 Formato: 80:80,443:443 (porta_host:porta_container)[/dim]")
        data["ports"] = Prompt.ask("Mapeamento de portas (opcional)", default="")
    else:
        data["ports"] = ""
    
    # Configuração de volumes
    console.print(f"\n[cyan]💾 Volumes Extras[/cyan]")
    console.print(f"[dim]💡 Formato: /host/path:/container/path[/dim]")
    data["volumes"] = Prompt.ask("Volumes extras (opcional)", default="")
    
    return data

def validate_parameters(data):
    """Valida os parâmetros fornecidos"""
    required_fields = ["container_name", "target", "port", "passwordSSH", "network"]
                      
    for field in required_fields:
        if not data.get(field):
            display_error("MSG_MISSING_PARAMS")
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

def convert_with_feedback(data):
    """Converte e cria o container Docker com feedback em tempo real"""
    console.print(f"\n[cyan]📦 {get_text('MSG_CREATING_DOCKER_IMAGE')}[/cyan]")
    
    with tempfile.TemporaryDirectory(prefix=f"{data['container_name']}_migration_") as temp_dir:
        temp_path = Path(temp_dir)
        
        console.print(f"[cyan]📡 Coletando sistema de arquivos...[/cyan]")
        
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
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("🔄 Coletando dados...", total=None)
                    
                    for chunk in process.stdout:
                        f.write(chunk)
                        progress.update(task, advance=1)
            
            if process.wait() != 0:
                display_error("SSH_CONNECTION_FAILED")
                return False
                
            if filesystem_tar.stat().st_size == 0:
                console.print(f"[red]❌ Coleta do sistema de arquivos falhou[/red]")
                return False
            
            size_mb = filesystem_tar.stat().st_size / (1024 * 1024)
            console.print(f"[green]✅ Sistema coletado: {size_mb:.1f} MB[/green]")
            
            console.print(f"[cyan]🐳 Construindo imagem Docker...[/cyan]")
            
            # Cria Dockerfile
            dockerfile_path = temp_path / "Dockerfile"
            with open(dockerfile_path, 'w') as f:
                f.write(create_dockerfile())
            
            # Constrói imagem Docker
            build_command = [
                "docker", "build", "-t", f"lincon-migrated:{data['container_name']}", 
                str(temp_path)
            ]
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("🔨 Construindo imagem...", total=None)
                result = subprocess.run(build_command, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Falha na construção da imagem:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                return False
            
            display_success("MSG_DOCKER_IMAGE_CREATED")
            
            # Executa container
            console.print(f"[cyan]🚀 Iniciando container Docker...[/cyan]")
            
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
            
            result = subprocess.run(run_command, capture_output=True, text=True)
            
            if result.returncode == 0:
                display_success("MSG_DOCKER_CONTAINER_STARTED")
                
                # Mostra informações do container
                console.print(f"\n" + "="*70)
                console.print(f"[bold green]🎉 MIGRAÇÃO DOCKER CONCLUÍDA![/bold green]")
                console.print("="*70)
                
                console.print(f"[cyan]📦 Nome:[/cyan] {data['container_name']}")
                console.print(f"[cyan]🐳 Imagem:[/cyan] lincon-migrated:{data['container_name']}")
                console.print(f"[cyan]🌐 Rede:[/cyan] {data['network']}")
                
                if data["network"] != "host" and data.get("ports"):
                    console.print(f"[cyan]🔗 Portas:[/cyan] {data['ports']}")
                
                if data.get("volumes"):
                    console.print(f"[cyan]💾 Volumes:[/cyan] {data['volumes']}")
                
                console.print(f"\n[yellow]💡 Comandos úteis:[/yellow]")
                console.print(f"[white]   docker exec -it {data['container_name']} /bin/bash[/white]  [dim]# Entrar no container[/dim]")
                console.print(f"[white]   docker stop {data['container_name']}[/white]                [dim]# Parar container[/dim]")
                console.print(f"[white]   docker start {data['container_name']}[/white]               [dim]# Iniciar container[/dim]")
                console.print(f"[white]   docker logs {data['container_name']}[/white]                [dim]# Ver logs[/dim]")
                
                return True
            else:
                console.print(f"[red]❌ Falha ao iniciar container:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante conversão: {e}")
            console.print(f"[red]❌ Erro inesperado: {e}[/red]")
            return False

def confirm_migration(data):
    """Confirma os detalhes da migração com o usuário"""
    console.print(f"\n[bold cyan]📋 Confirmação da Migração Docker[/bold cyan]")
    
    table = Table(title="[bold green]Detalhes da Migração Docker[/bold green]", show_header=True)
    table.add_column("Item", style="cyan", width=20)
    table.add_column("Valor", style="white")
    
    table.add_row("🐳 Nome do Container", f"[bright_green]{data['container_name']}[/bright_green]")
    table.add_row("🖥️  Servidor Origem", f"[bright_blue]{data['target']}:{data['port']}[/bright_blue]")
    table.add_row("🌐 Rede", f"[bright_yellow]{data['network']}[/bright_yellow]")
    
    if data.get("ports"):
        table.add_row("🔗 Portas", f"[bright_magenta]{data['ports']}[/bright_magenta]")
    
    if data.get("volumes"):
        table.add_row("💾 Volumes", f"[bright_cyan]{data['volumes']}[/bright_cyan]")
    
    console.print(table)
    console.print()
    
    console.print(f"[yellow]⚠️  Esta operação irá:[/yellow]")
    console.print(f"• Conectar ao servidor origem via SSH")
    console.print(f"• Coletar todo o sistema de arquivos")
    console.print(f"• Criar uma imagem Docker")
    console.print(f"• Iniciar o container automaticamente")
    
    console.print(f"\n[cyan]💡 Certifique-se de que:[/cyan]")
    console.print(f"• O Docker está instalado e rodando")
    console.print(f"• O servidor origem está acessível")
    console.print(f"• Há espaço suficiente em disco")
    
    return Confirm.ask(f"\n✅ Confirmar migração Docker?", default=False)

def migrate_docker():
    """Função principal de migração para Docker com interface otimizada"""
    def handle_interrupt(signum, frame):
        console.print(f"\n[yellow]⚠️  Migração Docker cancelada pelo usuário[/yellow]")
        exit(1)
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    state_manager = MigrationState()
    
    if not check_dependencies():
        return False
    
    data = user_input()
    if not data:
        console.print(f"\n[yellow]❌ Migração cancelada pelo usuário[/yellow]")
        return False
    
    state_manager.save_state(data, "input_collected")
    
    if not validate_parameters(data):
        return False
    
    state_manager.save_state(data, "validated")
    
    if not confirm_migration(data):
        console.print(f"\n[yellow]❌ Migração cancelada pelo usuário[/yellow]")
        state_manager.save_state(data, "cancelled")
        return False
    
    state_manager.save_state(data, "converting")
    if convert_with_feedback(data):
        state_manager.save_state(data, "completed")
        state_manager.clear_state()
        return True
    else:
        state_manager.save_state(data, "failed")
        return False

if __name__ == "__main__":
    migrate_docker()
