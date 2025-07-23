from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.text import Text
from lang.translations import translations
import subprocess
import os
import shutil
import re
import signal
import time
import threading
import queue

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

# Validações básicas
def validate_ip(ip):
    """Valida formato de IP ou DHCP"""
    if ip.lower() == "dhcp":
        return True
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)

def validate_hostname(hostname):
    """Valida formato de hostname/IP"""
    if not hostname or len(hostname.strip()) == 0:
        return False
    hostname = hostname.strip()
    if validate_ip(hostname):
        return True
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

def validate_ct_id(ct_id):
    """Valida ID do container"""
    try:
        id_num = int(ct_id)
        return 100 <= id_num <= 999999
    except ValueError:
        return False

def check_dependencies():
    """Verifica dependências básicas"""
    console.print(f"[cyan]🔍 {get_text('CHECKING_DEPS')}[/cyan]")
    
    missing_deps = []
    
    if not shutil.which("pct"):
        missing_deps.append("pct (Proxmox Container Toolkit)")
    if not shutil.which("pvesm"):
        missing_deps.append("pvesm (Proxmox VE Storage Manager)")
    if not shutil.which("brctl"):
        missing_deps.append("brctl (Bridge utilities)")
    
    if missing_deps:
        error_msg = get_text("MISSING_DEPS") + "\n" + "\n".join(f"• {dep}" for dep in missing_deps)
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        display_recommendation("DEPS_RECOMMENDATION")
        return False

    if not shutil.which("sshpass"):
        console.print(f"[cyan]{get_text('INSTALLING_SSHPASS')}[/cyan]")
        try:
            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            subprocess.run(["apt-get", "install", "-y", "sshpass"], check=True, capture_output=True)
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
            
            if "Permission denied" in result.stderr:
                display_error("SSH_PERMISSION_DENIED")
                if Confirm.ask(get_text("SSH_CONTINUE_TUTORIAL")):
                    show_ssh_tutorial()
            else:
                display_recommendation("SSH_CHECK_LIST")
            return False
            
    except subprocess.TimeoutExpired:
        display_error("SSH_TIMEOUT")
        return False
    except Exception as e:
        error_msg = get_text("SSH_TEST_ERROR").format(e)
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        return False

def show_ssh_tutorial():
    """Exibe tutorial SSH usando traduções"""
    console.print()
    
    tutorial_content = f"""[bold cyan]{get_text('SSH_TUTORIAL_INTRO')}[/bold cyan]

{get_text('SSH_TUTORIAL_STEP1')}
[dim]│[/dim] [bold green]{get_text('SSH_TUTORIAL_CMD1')}[/bold green]

{get_text('SSH_TUTORIAL_STEP2')}
[dim]│[/dim] [red]{get_text('SSH_TUTORIAL_FROM')}[/red]
[dim]│[/dim] [green]{get_text('SSH_TUTORIAL_TO')}[/green]

{get_text('SSH_TUTORIAL_STEP3')}
[dim]│[/dim] [bold green]{get_text('SSH_TUTORIAL_CMD3')}[/bold green]

{get_text('SSH_TUTORIAL_STEP4')}
[dim]│[/dim] [bold green]{get_text('SSH_TUTORIAL_CMD4')}[/bold green]

[bold yellow]{get_text('SSH_TUTORIAL_SECURITY')}[/bold yellow]
[dim]{get_text('SSH_TUTORIAL_DISABLE')}[/dim]"""

    console.print(Panel(
        tutorial_content,
        title=get_text('SSH_TUTORIAL_TITLE'),
        border_style="cyan",
        padding=(1, 2)
    ))

def select_bridge():
    """Seleciona bridge de rede com traduções"""
    try:
        result = subprocess.run(["brctl", "show"], capture_output=True, text=True, check=True)
        bridges = []
        
        for line in result.stdout.splitlines()[1:]:
            if line.strip() and not line.startswith('\t'):
                bridge_name = line.split()[0]
                if bridge_name.startswith("vmbr"):
                    bridges.append(bridge_name)

        if not bridges:
            display_error("NO_BRIDGE_FOUND")
            display_recommendation("BRIDGE_CONFIG_ERROR")
            return None

        table = Table(title=f"[bold cyan]{get_text('BRIDGE_AVAILABLE')}[/bold cyan]", show_header=True)
        table.add_column("Opção", style="cyan", width=6)
        table.add_column("Bridge", style="green", width=12)
        table.add_column("Descrição", style="dim")
        
        for i, bridge in enumerate(bridges, 1):
            desc = get_text("BRIDGE_DEFAULT") if bridge == "vmbr0" else get_text("BRIDGE_ADDITIONAL")
            table.add_row(f"[{i}]", bridge, desc)

        console.print(table)
        display_recommendation("REC_BRIDGE_DEFAULT")
        
        choice = Prompt.ask(get_text("CHOOSE_BRIDGE"), choices=[str(i) for i in range(1, len(bridges) + 1)])
        selected = bridges[int(choice) - 1]
        
        if Confirm.ask(get_text("CONFIRM_BRIDGE").format(selected)):
            return selected
        return select_bridge()

    except subprocess.CalledProcessError:
        display_error("BRIDGE_LIST_ERROR")
        return None

def select_storage():
    """Seleciona storage com traduções"""
    try:
        result = subprocess.run(["pvesm", "status"], capture_output=True, text=True, check=True)
        storages = []
        storage_info = []

        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                name, type_, status, total, used, avail = parts[0:6]
                if status == "active" and type_ in ["dir", "lvm", "lvmthin", "zfs", "btrfs"]:
                    storages.append(name)
                    storage_info.append({
                        'name': name,
                        'type': type_,
                        'total': total,
                        'used': used,
                        'avail': avail
                    })

        if not storages:
            display_error("NO_STORAGE_FOUND")
            display_recommendation("STORAGE_CHECK_ACTIVE")
            return None

        table = Table(title=f"[bold cyan]{get_text('STORAGE_AVAILABLE')}[/bold cyan]", show_header=True)
        table.add_column("Opção", style="cyan", width=6)
        table.add_column(get_text("STORAGE_NAME"), style="green", width=12)
        table.add_column(get_text("STORAGE_TYPE"), style="yellow", width=10)
        table.add_column(get_text("STORAGE_AVAILABLE_SPACE"), style="blue", width=12)
        
        for i, info in enumerate(storage_info, 1):
            table.add_row(f"[{i}]", info['name'], info['type'], info['avail'])

        console.print(table)
        display_recommendation("STORAGE_CHECK_ACTIVE")
        
        choice = Prompt.ask(get_text("CHOOSE_STORAGE"), choices=[str(i) for i in range(1, len(storages) + 1)])
        selected = storages[int(choice) - 1]
        selected_info = storage_info[int(choice) - 1]
        
        console.print(f"\n[green]{get_text('STORAGE_SELECTED')}[/green] {selected}")
        console.print(f"[blue]{get_text('STORAGE_SPACE_AVAILABLE')}:[/blue] {selected_info['avail']}")
        
        if Confirm.ask(get_text("CONFIRM_STORAGE").format(selected)):
            return selected, selected_info
        return select_storage()

    except subprocess.CalledProcessError:
        display_error("STORAGE_STATUS_ERROR")
        return None, None

def detect_disk_usage(target, port, password):
    """Detecta uso atual do disco no servidor origem"""
    console.print(f"[cyan]📊 Detectando uso do disco no servidor origem...[/cyan]")
    
    try:
        cmd = [
            "sshpass", "-p", password,
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"root@{target}",
            "df -BM / | tail -1 | awk '{print $3}'"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            used_mb = int(result.stdout.strip().replace('M', ''))
            # Adiciona margem de segurança de 20%
            recommended_mb = int(used_mb * 1.2)
            recommended_gb = recommended_mb // 1024
            
            console.print(f"[green]✅ Detecção concluída:[/green]")
            console.print(f"   📦 Uso atual: {used_mb} MB ({used_mb//1024:.1f} GB)")
            console.print(f"   💡 Recomendado: {recommended_mb} MB ({recommended_gb} GB) [dim](com margem de segurança)[/dim]")
            
            return used_mb, recommended_mb, recommended_gb
        else:
            console.print(f"[yellow]⚠️  Falha na detecção automática[/yellow]")
            return None, None, None
            
    except Exception as e:
        console.print(f"[yellow]⚠️  Erro na detecção: {e}[/yellow]")
        return None, None, None

def parse_size_input(size_input):
    """Converte entrada do usuário em MB"""
    size_input = size_input.strip().lower()
    
    # Remove 'mb:' se presente
    if size_input.startswith('mb:'):
        size_input = size_input[3:].strip()
    
    # Extrai número e unidade
    match = re.match(r'^(\d+)\s*([gmk]?)b?$', size_input)
    if not match:
        return None
    
    number = int(match.group(1))
    unit = match.group(2) or 'm'  # default MB
    
    if unit == 'g':
        return number * 1024  # GB para MB
    elif unit == 'k':
        return number // 1024  # KB para MB
    else:  # 'm' ou sem unidade
        return number

def format_size_gb(mb):
    """Formata tamanho em MB para exibição em GB"""
    return f"{mb // 1024}G"

def check_storage_space_mb(storage_info, required_mb):
    """Verifica se há espaço suficiente no storage"""
    if not storage_info:
        return False, "Storage info não disponível"
    
    # Converte espaço disponível para MB
    avail_str = storage_info['avail'].upper()
    if avail_str.endswith('G'):
        avail_mb = int(float(avail_str[:-1]) * 1024)
    elif avail_str.endswith('M'):
        avail_mb = int(float(avail_str[:-1]))
    elif avail_str.endswith('T'):
        avail_mb = int(float(avail_str[:-1]) * 1024 * 1024)
    else:
        try:
            avail_mb = int(float(avail_str)) // 1024  # assumindo bytes
        except:
            return False, "Formato de storage inválido"
    
    if required_mb > avail_mb:
        return False, f"Storage tem apenas {avail_mb//1024}G disponível, mas precisa de {required_mb//1024}G"
    
    return True, f"Storage tem {avail_mb//1024}G disponível, suficiente para {required_mb//1024}G"

def configure_disk_size(target, port, password, storage_info):
    """Configura tamanho do disco com detecção automática"""
    console.print(f"\n[cyan]{get_text('DISK_SIZE')}[/cyan]")
    
    # Detecta uso atual
    used_mb, recommended_mb, recommended_gb = detect_disk_usage(target, port, password)
    
    if recommended_mb:
        console.print(f"\n[cyan]💿 Opções de disco:[/cyan]")
        
        table = Table(show_header=True, box=None)
        table.add_column("Opção", style="cyan", width=6)
        table.add_column("Descrição", style="white", width=40)
        table.add_column("Tamanho", style="green")
        
        table.add_row("[1]", "Usar tamanho recomendado (baseado no uso atual + margem)", f"{recommended_gb}G")
        table.add_row("[2]", "Tamanho personalizado", "Definir manualmente")
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask("Escolha uma opção", choices=["1", "2"], default="1")
        
        if choice == "1":
            # Verifica se o tamanho recomendado cabe no storage
            has_space, space_msg = check_storage_space_mb(storage_info, recommended_mb)
            
            if has_space:
                console.print(f"[green]✅ {space_msg}[/green]")
                return format_size_gb(recommended_mb)
            else:
                console.print(f"[red]❌ {space_msg}[/red]")
                console.print(f"[yellow]Será necessário escolher um tamanho personalizado menor[/yellow]")
                choice = "2"  # força personalizado
    
    if not recommended_mb or choice == "2":
        # Modo personalizado
        console.print(f"\n[yellow]📝 Tamanho personalizado:[/yellow]")
        
        if storage_info:
            avail_gb = storage_info['avail'].replace('G', '').replace('M', '')
            if 'G' in storage_info['avail']:
                avail_display = storage_info['avail']
            else:
                avail_display = f"{int(float(avail_gb))//1024}G"
            console.print(f"[dim]💡 Espaço disponível no storage: {avail_display}[/dim]")
        
        console.print(f"[dim]💡 Formato: mb: 5120 (para 5GB) ou mb: 10240 (para 10GB)[/dim]")
        console.print(f"[dim]💡 Você também pode digitar apenas: 5G, 10G, 2048M[/dim]")
        
        while True:
            size_input = Prompt.ask("Digite o tamanho do disco")
            
            # Tenta parsear o input
            size_mb = parse_size_input(size_input)
            
            if size_mb is None:
                console.print(f"[red]❌ Formato inválido![/red]")
                console.print(f"[yellow]Use: mb: 5120 (5GB) ou 5G ou 5120M[/yellow]")
                continue
            
            if size_mb < 512:
                console.print(f"[red]❌ Tamanho muito pequeno! Mínimo 512MB[/red]")
                continue
            
            # Verifica se cabe no storage
            if storage_info:
                has_space, space_msg = check_storage_space_mb(storage_info, size_mb)
                
                if not has_space:
                    console.print(f"[red]❌ {space_msg}[/red]")
                    console.print(f"[yellow]💡 Escolha um tamanho menor ou outro storage[/yellow]")
                    
                    if not Confirm.ask("Tentar outro tamanho?", default=True):
                        return None
                    continue
                else:
                    console.print(f"[green]✅ {space_msg}[/green]")
            
            # Confirmação
            size_gb = size_mb // 1024
            console.print(f"\n[cyan]📋 Tamanho selecionado:[/cyan]")
            console.print(f"   💿 {size_mb} MB ({size_gb} GB)")
            
            if Confirm.ask("Confirmar este tamanho?"):
                return format_size_gb(size_mb)
    
    return None

def select_ip_config():
    """Seleciona configuração IP com traduções"""
    console.print(f"\n[cyan]{get_text('IP_CONFIG')}[/cyan]")
    
    table = Table(title=f"[bold cyan]{get_text('IP_OPTIONS')}[/bold cyan]", show_header=True)
    table.add_column("Opção", style="cyan", width=6)
    table.add_column("Tipo", style="green", width=12)
    table.add_column("Descrição", style="dim")
    
    table.add_row("[1]", get_text("IP_DHCP"), get_text("IP_DHCP_DESC"))
    table.add_row("[2]", get_text("IP_STATIC"), get_text("IP_STATIC_DESC"))
    
    console.print(table)
    console.print()

    choice = Prompt.ask(get_text("CHOOSE_IP_TYPE"), choices=["1", "2"])

    if choice == "1":
        if Confirm.ask(get_text("CONFIRM_DHCP")):
            return "dhcp", "dhcp"
    
    # IP estático
    console.print(f"\n[yellow]{get_text('STATIC_IP_CONFIG')}[/yellow]")
    display_recommendation("IP_FORMAT_REC")
    
    while True:
        ip = Prompt.ask(get_text("ENTER_CONTAINER_IP"))
        if validate_ip(ip):
            break
        else:
            display_error("INVALID_IP")
    
    display_recommendation("GATEWAY_FORMAT_REC")
    
    while True:
        gateway = Prompt.ask(get_text("ENTER_GATEWAY"))
        if validate_ip(gateway):
            break
        else:
            display_error("INVALID_GATEWAY")
    
    console.print(f"\n[green]{get_text('NETWORK_CONFIG_SUMMARY')}[/green]")
    console.print(f"[cyan]IP:[/cyan] {ip}/24")
    console.print(f"[cyan]Gateway:[/cyan] {gateway}")
    
    if Confirm.ask(get_text("CONFIRM_NETWORK_CONFIG")):
        return ip, gateway
    else:
        return select_ip_config()

def collect_user_data():
    """Coleta todos os dados necessários do usuário com interface moderna"""
    console.clear()
    console.print(f"[bold cyan]{get_text('MIGRATION_TITLE')}[/bold cyan]\n")
    
    data = {}
    
    # ID do Container
    console.print(f"[cyan]{get_text('CONTAINER_ID')}[/cyan]")
    display_recommendation("CONTAINER_ID_REC")
    
    while True:
        ct_id = Prompt.ask(get_text("CONTAINER_ID_PROMPT"), default="101")
        if validate_ct_id(ct_id):
            try:
                result = subprocess.run(["pct", "status", ct_id], capture_output=True)
                if result.returncode == 0:
                    warning_msg = get_text("CONTAINER_ID_EXISTS").format(ct_id)
                    console.print(Panel(f"⚠️  {warning_msg}", title="⚠️  ATENÇÃO", style="yellow"))
                    if not Confirm.ask(get_text("CHOOSE_ANOTHER_ID")):
                        return None
                    continue
            except:
                pass
            data["id"] = ct_id
            break
        else:
            display_error("INVALID_ID")

    # Nome do Container
    container_name_title = get_text("CONTAINER_NAME").format(data['id'])
    console.print(f"\n[cyan]{container_name_title}[/cyan]")
    display_recommendation("CONTAINER_NAME_REC")
    
    while True:
        name = Prompt.ask(get_text("CONTAINER_NAME_PROMPT"))
        if name and len(name) >= 3:
            data["name"] = name
            break
        else:
            display_error("NAME_TOO_SHORT")

    # Host de origem
    console.print(f"\n[cyan]{get_text('SOURCE_SERVER')}[/cyan]")
    display_recommendation("SOURCE_SERVER_REC")
    
    while True:
        target = Prompt.ask(get_text("SOURCE_HOST_PROMPT"))
        if target and validate_hostname(target):
            data["target"] = target
            break
        else:
            display_error("INVALID_HOSTNAME")

    # Porta SSH
    ssh_port_title = get_text("SSH_PORT").format(data['target'])
    console.print(f"\n[cyan]{ssh_port_title}[/cyan]")
    
    while True:
        port = Prompt.ask(get_text("SSH_PORT_PROMPT"), default="22")
        if validate_port(port):
            data["port"] = port
            break
        else:
            display_error("INVALID_PORT")

    # Senha SSH
    console.print(f"\n[cyan]{get_text('SSH_CREDENTIALS')}[/cyan]")
    display_warning("SSH_PASSWORD_WARNING")
    
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
            display_error("PASSWORD_CANNOT_EMPTY")

    # Bridge de rede
    console.print(f"\n[cyan]{get_text('NETWORK_CONFIG')}[/cyan]")
    bridge = select_bridge()
    if not bridge:
        return None
    data["bridge"] = bridge

    # Configuração IP
    ip, gateway = select_ip_config()
    data["ip"] = ip
    data["gateway"] = gateway

    # Storage
    console.print(f"\n[cyan]{get_text('STORAGE_CONFIG')}[/cyan]")
    storage, storage_info = select_storage()
    if not storage:
        return None
    data["storage"] = storage

    # Tamanho do disco (com detecção automática)
    rootsize = configure_disk_size(data["target"], data["port"], data["passwordSSH"], storage_info)
    if not rootsize:
        return None
    data["rootsize"] = rootsize

    # Memória
    console.print(f"\n[cyan]{get_text('MEMORY_CONFIG')}[/cyan]")
    display_recommendation("MEMORY_REC")
    
    while True:
        try:
            memory = int(Prompt.ask(get_text("MEMORY_PROMPT"), default="1024"))
            if memory >= 64:
                data["memory"] = str(memory)
                break
            else:
                display_error("MEMORY_TOO_LOW")
        except ValueError:
            display_error("NUMBERS_ONLY")

    # Senha do container
    console.print(f"\n[cyan]{get_text('CONTAINER_PASSWORD')}[/cyan]")
    display_warning("CONTAINER_PASSWORD_WARNING")
    display_recommendation("CONTAINER_PASSWORD_REC")
    
    while True:
        password = Prompt.ask(get_text("CONTAINER_PASSWORD_PROMPT"), password=True)
        if len(password) >= 5:
            confirm_pass = Prompt.ask(get_text("CONFIRM_PASSWORD"), password=True)
            if password == confirm_pass:
                data["passwordCT"] = password
                break
            else:
                display_error("PASSWORDS_DONT_MATCH")
        else:
            display_error("PASSWORD_TOO_SHORT")

    return data

def confirm_migration(data):
    """Confirma os detalhes da migração com interface melhorada"""
    console.print(f"\n[bold cyan]{get_text('MIGRATION_CONFIRMATION')}[/bold cyan]")
    
    table = Table(title=f"[bold green]{get_text('MIGRATION_DETAILS')}[/bold green]", show_header=True)
    table.add_column(get_text("DETAIL_ITEM"), style="cyan", width=20)
    table.add_column(get_text("DETAIL_VALUE"), style="white")
    
    table.add_row(get_text("DETAIL_CT_ID"), f"[bright_green]{data['id']}[/bright_green]")
    table.add_row(get_text("DETAIL_CT_NAME"), f"[bright_yellow]{data['name']}[/bright_yellow]")
    table.add_row(get_text("DETAIL_SOURCE"), f"[bright_blue]{data['target']}:{data['port']}[/bright_blue]")
    table.add_row(get_text("DETAIL_BRIDGE"), f"[bright_magenta]{data['bridge']}[/bright_magenta]")
    
    if data["ip"] == "dhcp":
        table.add_row(get_text("DETAIL_IP_DHCP"), f"[bright_cyan]{get_text('IP_AUTOMATIC')}[/bright_cyan]")
    else:
        table.add_row(get_text("DETAIL_IP_STATIC"), f"[bright_green]{data['ip']}/24[/bright_green]")
        table.add_row(get_text("DETAIL_GATEWAY"), f"[bright_green]{data['gateway']}[/bright_green]")
    
    table.add_row(get_text("DETAIL_DISK"), f"[bright_yellow]{data['rootsize']}[/bright_yellow] em [dim]{data['storage']}[/dim]")
    table.add_row(get_text("DETAIL_MEMORY"), f"[bright_yellow]{data['memory']} MB[/bright_yellow]")
    
    console.print(table)
    console.print()
    
    display_warning("MIGRATION_WARNING")
    display_recommendation("MIGRATION_CHECKLIST")
    
    return Confirm.ask(get_text("CONFIRM_MIGRATION"), default=False)

def execute_migration_with_feedback(data):
    """Executa a migração com feedback em tempo real"""
    console.print(f"\n[cyan]📦 {get_text('MIGRATION_STARTING')}[/cyan]")
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrate_container.sh")
    
    if not os.path.exists(script_path):
        console.print(f"[red]❌ Script não encontrado: {script_path}[/red]")
        return False
    
    shell_command = [
        script_path,
        "-n", data["name"],
        "-t", data["target"],
        "-P", data["port"],
        "-i", data["id"],
        "-s", data["rootsize"],
        "-a", data["ip"],
        "-b", data["bridge"],
        "-g", data["gateway"],
        "-m", data["memory"],
        "-d", data["storage"],
        "-p", data["passwordCT"],
        "-w", data["passwordSSH"]
    ]
    
    try:
        # Criar um processo que executa o script
        process = subprocess.Popen(
            shell_command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Layout para feedback em tempo real
        console.print("\n" + "="*70)
        console.print(f"[bold green]🚀 INICIANDO MIGRAÇÃO - ID {data['id']} ({data['name']})[/bold green]")
        console.print("="*70)
        
        output_lines = []
        error_lines = []
        
        # Lê a saída em tempo real
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                output_lines.append(line)
                
                # Destaca linhas importantes
                if any(symbol in line for symbol in ['🚀', '✅', '📡', '📦', '🎉', '💡']):
                    console.print(f"[bold]{line}[/bold]")
                elif '❌' in line:
                    console.print(f"[red]{line}[/red]")
                elif '⚠️' in line:
                    console.print(f"[yellow]{line}[/yellow]")
                else:
                    console.print(f"[dim]{line}[/dim]")
        
        # Captura erros se houver
        stderr_output = process.stderr.read()
        if stderr_output:
            error_lines.extend(stderr_output.split('\n'))
        
        return_code = process.poll()
        
        console.print("="*70)
        
        if return_code == 0:
            console.print(f"[bold green]🎉 {get_text('MIGRATION_COMPLETE')}[/bold green]")
            
            # Mostra informações finais do container
            console.print(f"\n[cyan]📋 {get_text('CONTAINER_INFO_ID')}[/cyan] {data['id']}")
            console.print(f"[cyan]🏷️  {get_text('CONTAINER_INFO_NAME')}[/cyan] {data['name']}")
            console.print(f"[cyan]🌐 {get_text('CONTAINER_INFO_IP')}[/cyan] {data['ip']}")
            console.print(f"[cyan]🧠 {get_text('CONTAINER_INFO_MEMORY')}[/cyan] {data['memory']}MB")
            console.print(f"[cyan]💿 {get_text('CONTAINER_INFO_DISK')}[/cyan] {data['rootsize']}")
            
            console.print(f"\n[yellow]💡 {get_text('USEFUL_COMMANDS')}[/yellow]")
            console.print(f"[white]   pct enter {data['id']}    [dim]# Entrar no container[/dim][/white]")
            console.print(f"[white]   pct stop {data['id']}     [dim]# Parar container[/dim][/white]")
            console.print(f"[white]   pct start {data['id']}    [dim]# Iniciar container[/dim][/white]")
            console.print(f"[white]   pct status {data['id']}   [dim]# Status do container[/dim][/white]")
            
            return True
        else:
            console.print(f"[red]❌ Falha na migração (código: {return_code})[/red]")
            if error_lines:
                console.print(f"[red]Erros:[/red]")
                for error in error_lines:
                    if error.strip():
                        console.print(f"[red]  {error}[/red]")
            return False
            
    except subprocess.TimeoutExpired:
        console.print(f"\n[red]❌ {get_text('SSH_TIMEOUT')}[/red]")
        return False
    except Exception as e:
        console.print(f"\n[red]❌ Erro inesperado: {e}[/red]")
        return False

def migrate_lxc():
    """Função principal de migração com interface otimizada"""
    def handle_interrupt(signum, frame):
        console.print(f"\n[yellow]⚠️  {get_text('MIGRATION_CANCELLED_USER')}[/yellow]")
        exit(1)
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    if not check_dependencies():
        return False
    
    data = collect_user_data()
    if not data:
        console.print(f"\n[yellow]❌ {get_text('MIGRATION_CANCELLED_INPUT')}[/yellow]")
        return False
    
    if not confirm_migration(data):
        console.print(f"\n[yellow]❌ {get_text('MIGRATION_CANCELLED_INPUT')}[/yellow]")
        return False
    
    return execute_migration_with_feedback(data)

if __name__ == "__main__":
    migrate_lxc() 