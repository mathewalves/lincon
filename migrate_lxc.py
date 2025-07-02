from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import track
from lang.translations import translations
from utils.migration_state import MigrationState
from datetime import datetime
import subprocess
import os
import shutil
from pathlib import Path
import tempfile
import signal
import logging
import re
import time

logger = logging.getLogger('lincon')

console = Console()
current_language = "pt-br"

def get_text(key):
    """Obtém texto traduzido, com fallback para a chave se não encontrar"""
    text = translations[current_language].get(key)
    return text if text is not None else key

def display_message(title_key, message_key, style=""):
    """Exibe uma mensagem em um painel usando chaves de tradução"""
    title_text = get_text(title_key)
    message_text = get_text(message_key)
    console.print(Panel(message_text, title=title_text, style=style))

def display_warning(message_key):
    """Exibe um aviso usando chave de tradução"""
    message = get_text(message_key)
    console.print(Panel(f"⚠️  {message}", title="⚠️  ATENÇÃO", style="yellow"))

def display_recommendation(message_key):
    """Exibe uma recomendação usando chave de tradução"""
    message = get_text(message_key)
    console.print(Panel(f"💡 {message}", title="💡 RECOMENDAÇÃO", style="cyan"))

def display_error(message_key):
    """Exibe um erro usando chave de tradução"""
    message = get_text(message_key)
    console.print(Panel(f"❌ {message}", title="❌ ERRO", style="red"))

def display_success(message_key):
    """Exibe sucesso usando chave de tradução"""
    message = get_text(message_key)
    console.print(Panel(f"✅ {message}", title="✅ SUCESSO", style="green"))

def back_to_menu_option():
    """Pergunta se quer voltar ao menu"""
    return Confirm.ask(get_text("BACK_TO_MENU"), default=True)

def validate_ip(ip):
    """Valida formato de IP"""
    if ip.lower() == "dhcp":
        return True
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)

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

def validate_size_format(size):
    """Valida formato de tamanho (ex: 20G, 500M)"""
    pattern = r'^\d+[GM]$'
    return re.match(pattern, size.upper()) is not None

def check_dependencies():
    """Verifica se as dependências necessárias estão instaladas"""
    display_message("TITLE_INFO", "CHECKING_DEPS")
    
    missing_deps = []
    
    # Verifica pct
    if not shutil.which("pct"):
        missing_deps.append("pct (Proxmox Container Toolkit)")
    
    # Verifica pvesm
    if not shutil.which("pvesm"):
        missing_deps.append("pvesm (Proxmox VE Storage Manager)")
    
    # Verifica brctl
    if not shutil.which("brctl"):
        missing_deps.append("brctl (Bridge utilities)")
    
    if missing_deps:
        error_msg = get_text("MISSING_DEPS") + "\n" + "\n".join(f"• {dep}" for dep in missing_deps)
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        display_recommendation("DEPS_RECOMMENDATION")
        return False

    # Verifica/instala sshpass
    if not shutil.which("sshpass"):
        display_message("TITLE_INFO", "INSTALLING_SSHPASS")
        try:
            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            subprocess.run(["apt-get", "install", "-y", "sshpass"], check=True, capture_output=True)
            display_success("SSHPASS_INSTALLED")
        except subprocess.CalledProcessError as e:
            error_msg = get_text("SSH_INSTALL_FAILED").format(e)
            console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
            return False
    
    display_success("ALL_DEPS_AVAILABLE")
    return True

def test_ssh_connection(target, port, password):
    """Testa conexão SSH"""
    display_message("TITLE_INFO", "TESTING_SSH")
    
    try:
        cmd = [
            "sshpass", "-p", password,
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes",
            f"root@{target}",
            "echo 'Conexão OK'"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            display_success("SSH_CONNECTION_OK")
            return True
        else:
            error_msg = get_text("SSH_CONNECTION_FAILED").format(result.stderr)
            console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
            display_recommendation("SSH_CHECK_LIST")
            return False
            
    except subprocess.TimeoutExpired:
        display_error("SSH_TIMEOUT")
        return False
    except Exception as e:
        error_msg = get_text("SSH_TEST_ERROR").format(e)
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        return False

def select_bridge():
    """Seleciona uma bridge de rede com validação"""
    while True:
        try:
            console.print(f"\n[cyan]{get_text('NETWORK_CONFIG')}[/cyan]")
            
            # Executa brctl show e obtém a saída
            result = subprocess.run(["brctl", "show"], capture_output=True, text=True, check=True)
            bridges = []
            
            # Processa a saída para extrair as bridges
            for line in result.stdout.splitlines()[1:]:  # Pula o cabeçalho
                if line.strip() and not line.startswith('\t'):
                    bridge_name = line.split()[0]
                    if bridge_name.startswith("vmbr"):
                        bridges.append(bridge_name)

            if not bridges:
                display_error("NO_BRIDGE_FOUND")
                display_recommendation("BRIDGE_CONFIG_ERROR")
                return None

            # Cria uma tabela para mostrar as bridges
            table = Table(title=get_text("BRIDGE_AVAILABLE"))
            table.add_column("Opção", style="cyan")
            table.add_column("Bridge", style="green")
            table.add_column("Descrição", style="yellow")
            
            for i, bridge in enumerate(bridges, 1):
                desc = get_text("BRIDGE_DEFAULT") if bridge == "vmbr0" else get_text("BRIDGE_ADDITIONAL")
                table.add_row(f"[{i}]", bridge, desc)
            
            table.add_row(f"[0]", "🔙 Voltar", "Voltar ao menu anterior")
            console.print(table)
            
            display_recommendation("REC_BRIDGE_DEFAULT")

            # Solicita escolha do usuário
            choice = Prompt.ask(
                get_text("CHOOSE_BRIDGE"),
                choices=[str(i) for i in range(len(bridges) + 1)]
            )
            
            if choice == "0":
                return "BACK"
            
            selected_bridge = bridges[int(choice) - 1]
            
            # Confirma a escolha
            confirm_msg = get_text("CONFIRM_BRIDGE").format(selected_bridge)
            if Confirm.ask(confirm_msg):
                return selected_bridge
            
        except subprocess.CalledProcessError:
            display_error("BRIDGE_LIST_ERROR")
            if back_to_menu_option():
                return "BACK"
            return None
        except (ValueError, IndexError):
            display_warning("INVALID_OPTION")
            continue

def select_storage():
    """Seleciona um storage com informações detalhadas"""
    while True:
        try:
            console.print(f"\n[cyan]{get_text('STORAGE_CONFIG')}[/cyan]")
            
            result = subprocess.run(["pvesm", "status"], capture_output=True, text=True, check=True)
            storages = []
            storage_info = []

            for line in result.stdout.splitlines()[1:]:  # Pula o cabeçalho
                parts = line.split()
                if len(parts) >= 6:
                    name, type_, status, total, used, avail = parts[0:6]
                    content = parts[6] if len(parts) > 6 else ""
                    
                    if status == "active" and ("rootdir" in content or "images" in content):
                        storages.append(name)
                        storage_info.append({
                            'name': name,
                            'type': type_,
                            'total': total,
                            'used': used,
                            'avail': avail,
                            'content': content
                        })

            if not storages:
                display_error("NO_STORAGE_FOUND")
                display_recommendation("STORAGE_CHECK_ACTIVE")
                return None

            # Cria tabela detalhada
            table = Table(title=get_text("STORAGE_AVAILABLE"))
            table.add_column("Opção", style="cyan")
            table.add_column(get_text("STORAGE_NAME"), style="green")
            table.add_column(get_text("STORAGE_TYPE"), style="yellow")
            table.add_column(get_text("STORAGE_AVAILABLE_SPACE"), style="blue")
            table.add_column(get_text("STORAGE_TOTAL"), style="magenta")
            
            for i, info in enumerate(storage_info, 1):
                table.add_row(
                    f"[{i}]",
                    info['name'],
                    info['type'],
                    info['avail'],
                    info['total']
                )
            
            table.add_row(f"[0]", "🔙 Voltar", "", "", "")
            console.print(table)
            
            display_recommendation("STORAGE_CHECK_ACTIVE")

            choice = Prompt.ask(
                get_text("CHOOSE_STORAGE"),
                choices=[str(i) for i in range(len(storages) + 1)]
            )
            
            if choice == "0":
                return "BACK"
            
            selected_storage = storages[int(choice) - 1]
            selected_info = storage_info[int(choice) - 1]
            
            # Mostra detalhes e confirma
            console.print(f"\n[green]{get_text('STORAGE_SELECTED')}[/green] {selected_storage}")
            console.print(f"[yellow]{get_text('STORAGE_TYPE')}:[/yellow] {selected_info['type']}")
            console.print(f"[blue]{get_text('STORAGE_SPACE_AVAILABLE')}:[/blue] {selected_info['avail']}")
            
            confirm_msg = get_text("CONFIRM_STORAGE").format(selected_storage)
            if Confirm.ask(confirm_msg):
                return selected_storage

        except subprocess.CalledProcessError:
            display_error("STORAGE_STATUS_ERROR")
            if back_to_menu_option():
                return "BACK"
            return None
        except (ValueError, IndexError):
            display_warning("INVALID_OPTION")
            continue

def select_ip_config():
    """Seleciona configuração de IP com validação"""
    while True:
        console.print(f"\n[cyan]{get_text('IP_CONFIG')}[/cyan]")
        
        table = Table(title=get_text("IP_OPTIONS"))
        table.add_column("Opção", style="cyan")
        table.add_column("Tipo", style="green")
        table.add_column("Descrição", style="yellow")
        
        table.add_row("[1]", get_text("IP_DHCP"), get_text("IP_DHCP_DESC"))
        table.add_row("[2]", get_text("IP_STATIC"), get_text("IP_STATIC_DESC"))
        table.add_row("[0]", "🔙 Voltar", "Voltar ao menu anterior")
        
        console.print(table)
        
        choice = Prompt.ask(get_text("CHOOSE_IP_TYPE"), choices=["0", "1", "2"])
        
        if choice == "0":
            return "BACK", "BACK"
        elif choice == "1":
            if Confirm.ask(get_text("CONFIRM_DHCP")):
                return "dhcp", "dhcp"
        else:
            return configure_static_ip()

def configure_static_ip():
    """Configura IP estático com validação"""
    while True:
        console.print(f"\n[yellow]{get_text('STATIC_IP_CONFIG')}[/yellow]")
        
        display_recommendation("IP_FORMAT_REC")
        
        while True:
            ip = Prompt.ask(get_text("ENTER_CONTAINER_IP"))
            
            if validate_ip(ip):
                break
            else:
                display_warning("INVALID_IP")
                if not Confirm.ask(get_text("TRY_AGAIN")):
                    return "BACK", "BACK"
        
        display_recommendation("GATEWAY_FORMAT_REC")
        
        while True:
            gateway = Prompt.ask(get_text("ENTER_GATEWAY"))
            
            if validate_ip(gateway):
                break
            else:
                display_warning("INVALID_GATEWAY")
                if not Confirm.ask(get_text("TRY_AGAIN")):
                    return "BACK", "BACK"
        
        # Confirma configuração
        console.print(f"\n[green]{get_text('NETWORK_CONFIG_SUMMARY')}[/green]")
        console.print(f"[cyan]IP:[/cyan] {ip}/24")
        console.print(f"[cyan]Gateway:[/cyan] {gateway}")
        
        if Confirm.ask(get_text("CONFIRM_NETWORK_CONFIG")):
            return ip, gateway
        elif not Confirm.ask(get_text("RECONFIGURE_OPTION")):
            return "BACK", "BACK"

def user_input():
    """Coleta todos os dados necessários do usuário com validação"""
    data = {}
    
    console.clear()
    console.print(f"[bold cyan]{get_text('MIGRATION_TITLE')}[/bold cyan]\n")
    
    # ID do Container
    while True:
        console.print(f"[cyan]{get_text('CONTAINER_ID')}[/cyan]")
        display_recommendation("CONTAINER_ID_REC")
        
        ct_id = Prompt.ask(get_text("CONTAINER_ID_PROMPT"))
        
        if validate_ct_id(ct_id):
            # Verifica se ID já existe
            try:
                result = subprocess.run(["pct", "status", ct_id], capture_output=True)
                if result.returncode == 0:
                    warning_msg = get_text("CONTAINER_ID_EXISTS").format(ct_id)
                    console.print(Panel(f"⚠️  {warning_msg}", title="⚠️  ATENÇÃO", style="yellow"))
                    if not Confirm.ask(get_text("CHOOSE_ANOTHER_ID")):
                        return None
                    continue
                else:
                    data["id"] = ct_id
                    break
            except:
                data["id"] = ct_id
                break
        else:
            display_warning("INVALID_ID")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Nome do Container
    while True:
        container_name_title = get_text("CONTAINER_NAME").format(data['id'])
        console.print(f"\n[cyan]{container_name_title}[/cyan]")
        display_recommendation("CONTAINER_NAME_REC")
        
        name = Prompt.ask(get_text("CONTAINER_NAME_PROMPT"))
        
        if name and len(name) >= 3:
            data["name"] = name
            break
        else:
            display_warning("NAME_TOO_SHORT")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Host de origem
    while True:
        console.print(f"\n[cyan]{get_text('SOURCE_SERVER')}[/cyan]")
        display_recommendation("SOURCE_SERVER_REC")
        
        target = Prompt.ask(get_text("SOURCE_HOST_PROMPT"))
        
        if target:
            data["target"] = target
            break
        else:
            display_warning("HOST_CANNOT_EMPTY")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Porta SSH
    while True:
        ssh_port_title = get_text("SSH_PORT").format(data['target'])
        console.print(f"\n[cyan]{ssh_port_title}[/cyan]")
        
        port = Prompt.ask(get_text("SSH_PORT_PROMPT"), default="22")
        
        if validate_port(port):
            data["port"] = port
            break
        else:
            display_warning("INVALID_PORT")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Senha SSH
    while True:
        console.print(f"\n[cyan]{get_text('SSH_CREDENTIALS')}[/cyan]")
        display_warning("SSH_PASSWORD_WARNING")
        
        password = Prompt.ask(get_text("SSH_PASSWORD_PROMPT"), password=True)
        
        if password:
            # Testa conexão SSH
            if test_ssh_connection(data["target"], data["port"], password):
                data["passwordSSH"] = password
                break
            else:
                if not Confirm.ask(get_text("TRY_ANOTHER_PASSWORD")):
                    return None
        else:
            display_warning("PASSWORD_CANNOT_EMPTY")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Bridge de rede
    while True:
        bridge = select_bridge()
        if bridge == "BACK":
            if not Confirm.ask(get_text("CANCEL_MIGRATION")):
                continue
            return None
        elif bridge:
            data["bridge"] = bridge
            break
        else:
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Configuração IP
    while True:
        ip, gateway = select_ip_config()
        if ip == "BACK":
            continue
        else:
            data["ip"] = ip
            data["gateway"] = gateway
            break
    
    # Tamanho do disco
    while True:
        console.print(f"\n[cyan]{get_text('DISK_SIZE')}[/cyan]")
        display_recommendation("DISK_SIZE_REC")
        display_warning("DISK_SIZE_WARNING")
        
        rootsize = Prompt.ask(get_text("DISK_SIZE_PROMPT"), default="20G")
        
        if validate_size_format(rootsize):
            data["rootsize"] = rootsize.upper()
            break
        else:
            display_warning("INVALID_SIZE_FORMAT")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Memória
    while True:
        console.print(f"\n[cyan]{get_text('MEMORY_CONFIG')}[/cyan]")
        display_recommendation("MEMORY_REC")
        
        try:
            memory = int(Prompt.ask(get_text("MEMORY_PROMPT"), default="1024"))
            if memory >= 64:
                data["memory"] = str(memory)
                break
            else:
                display_warning("MEMORY_TOO_LOW")
                if not Confirm.ask(get_text("TRY_AGAIN")):
                    return None
        except ValueError:
            display_warning("NUMBERS_ONLY")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Storage
    while True:
        storage = select_storage()
        if storage == "BACK":
            continue
        elif storage:
            data["storage"] = storage
            break
        else:
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    # Senha do container
    while True:
        console.print(f"\n[cyan]{get_text('CONTAINER_PASSWORD')}[/cyan]")
        display_warning("CONTAINER_PASSWORD_WARNING")
        display_recommendation("CONTAINER_PASSWORD_REC")
        
        password = Prompt.ask(get_text("CONTAINER_PASSWORD_PROMPT"), password=True)
        
        if len(password) >= 5:
            confirm_pass = Prompt.ask(get_text("CONFIRM_PASSWORD"), password=True)
            if password == confirm_pass:
                data["passwordCT"] = password
                break
            else:
                display_warning("PASSWORDS_DONT_MATCH")
                if not Confirm.ask(get_text("TRY_AGAIN")):
                    return None
        else:
            display_warning("PASSWORD_TOO_SHORT")
            if not Confirm.ask(get_text("TRY_AGAIN")):
                return None
    
    return data

def validate_parameters(data):
    """Valida os parâmetros fornecidos"""
    required_fields = ["name", "target", "port", "id", "rootsize", "ip", 
                      "bridge", "memory", "storage", "passwordCT", "passwordSSH"]
                      
    for field in required_fields:
        if not data.get(field):
            display_error("MSG_MISSING_PARAMS")
            return False
    
    # Validações específicas
    if not validate_ct_id(data["id"]):
        display_error("INVALID_ID")
        return False
        
    if not validate_port(data["port"]):
        display_error("INVALID_PORT")
        return False
        
    if data["ip"] != "dhcp" and not validate_ip(data["ip"]):
        display_error("INVALID_IP")
        return False
        
    if data["gateway"] != "dhcp" and not validate_ip(data["gateway"]):
        display_error("INVALID_GATEWAY")
        return False
        
    if not validate_size_format(data["rootsize"]):
        display_error("INVALID_SIZE_FORMAT")
        return False
        
    if len(data["passwordCT"]) < 5:
        display_error("PASSWORD_TOO_SHORT")
        return False
        
    return True

def collect_fs(ssh_command):
    """Coleta o sistema de arquivos via SSH"""
    excluded_paths = [
        "/proc/*", "/sys/*", "/dev/*", "/tmp/*", "/run/*",
        "/mnt/*", "/media/*", "/lost+found", "/var/cache/apt/archives/*",
        "/swapfile", "/swap.img"
    ]
    
    tar_command = ["tar", "czpf", "-", "--numeric-owner", "--anchored"]
    for path in excluded_paths:
        tar_command.extend(["--exclude", path])
    tar_command.append(".")
    
    ssh_command.extend(["cd / &&"] + tar_command)
    return subprocess.Popen(ssh_command, stdout=subprocess.PIPE)

def convert(data):
    """Converte e cria o container"""
    with tempfile.NamedTemporaryFile(prefix=f"{data['name']}_migration_", suffix=".tar.gz") as temp_file:
        console.print(f"\n[cyan]{get_text('MIGRATION_STARTING')}[/cyan]")
        
        # Estima o tempo baseado no sistema
        display_message("TITLE_INFO", "COLLECTING_FILESYSTEM")
        display_recommendation("COLLECTION_TIME_WARNING")
        
        ssh_command = [
            "sshpass", "-p", data["passwordSSH"],
            "ssh", "-p", data["port"],
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=30",
            "-o", "ServerAliveInterval=30",
            f"root@{data['target']}"
        ]
        
        try:
            start_time = time.time()
            process = collect_fs(ssh_command)
            
            # Mostra progresso
            console.print(f"[yellow]{get_text('TRANSFERRING_DATA')}[/yellow]")
            
            with open(temp_file.name, 'wb') as f:
                chunk_count = 0
                if process.stdout:  # Verifica se stdout não é None
                    for chunk in process.stdout:
                        f.write(chunk)
                        chunk_count += 1
                        if chunk_count % 1000 == 0:
                            console.print(".", end="", style="yellow")
            
            console.print()  # Nova linha
            
            if process.wait() != 0:
                display_error("FILESYSTEM_COLLECTION_FAILED")
                display_recommendation("FILESYSTEM_COLLECTION_REC")
                return False
                
            file_size = os.path.getsize(temp_file.name)
            if file_size == 0:
                display_error("BACKUP_FILE_EMPTY")
                return False
            
            elapsed_time = time.time() - start_time
            size_mb = file_size / (1024 * 1024)
            
            console.print(f"[green]{get_text('COLLECTION_COMPLETE')}[/green]")
            size_text = get_text("FILE_SIZE").format(size_mb)
            time_text = get_text("TRANSFER_TIME").format(elapsed_time)
            console.print(f"   {size_text}")
            console.print(f"   {time_text}")
            
            display_message("TITLE_INFO", "CREATING_CONTAINER")
            
            # Prepara parâmetros do pct create
            if data["ip"] == "dhcp":
                net_param = f"name=eth0,bridge={data['bridge']},ip=dhcp"
            else:
                net_param = f"name=eth0,bridge={data['bridge']},ip={data['ip']}/24,gw={data['gateway']}"
            
            create_command = [
                "pct", "create", data["id"], temp_file.name,
                "--description", f"🐳 LINCON Migration: {data['name']} (from {data['target']}) - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "--hostname", data["name"],
                "--features", "nesting=1",
                "--unprivileged", "0",
                "--memory", data["memory"],
                "--nameserver", "8.8.8.8,1.1.1.1",
                "--net0", net_param,
                "--rootfs", f"{data['storage']}:{data['rootsize']}",
                "--password", data["passwordCT"],
                "--onboot", "1",
                "--cmode", "shell",
                "--arch", "amd64"
            ]
            
            console.print(f"[yellow]{get_text('CREATING_CONTAINER_PROGRESS')}[/yellow]")
            
            result = subprocess.run(create_command, capture_output=True, text=True)
            
            if result.returncode == 0:
                display_success("MSG_CT_CREATED")
                
                display_message("TITLE_INFO", "STARTING_CONTAINER")
                start_result = subprocess.run(["pct", "start", data["id"]], capture_output=True, text=True)
                
                if start_result.returncode == 0:
                    display_success("MSG_CT_STARTED")
                    
                    # Mostra informações finais
                    console.print(f"\n[bold green]{get_text('MIGRATION_COMPLETE')}[/bold green]")
                    console.print(f"[cyan]{get_text('CONTAINER_INFO_ID')}[/cyan] {data['id']}")
                    console.print(f"[cyan]{get_text('CONTAINER_INFO_NAME')}[/cyan] {data['name']}")
                    console.print(f"[cyan]{get_text('CONTAINER_INFO_IP')}[/cyan] {data['ip']}")
                    console.print(f"[cyan]{get_text('CONTAINER_INFO_MEMORY')}[/cyan] {data['memory']} MB")
                    console.print(f"[cyan]{get_text('CONTAINER_INFO_DISK')}[/cyan] {data['rootsize']}")
                    console.print(f"\n[yellow]{get_text('USEFUL_COMMANDS')}[/yellow]")
                    enter_cmd = get_text("CMD_ENTER_CONTAINER").format(data['id'])
                    stop_cmd = get_text("CMD_STOP_CONTAINER").format(data['id'])
                    start_cmd = get_text("CMD_START_CONTAINER").format(data['id'])
                    console.print(f"[white]  {enter_cmd}[/white]")
                    console.print(f"[white]  {stop_cmd}[/white]")
                    console.print(f"[white]  {start_cmd}[/white]")
                    
                else:
                    display_warning("CONTAINER_CREATED_START_FAILED")
                    manual_start = get_text("MANUAL_START").format(data['id'])
                    console.print(f"[yellow]{manual_start}[/yellow]")
                
                return True
            else:
                error_msg = get_text("CONTAINER_CREATE_FAILED").format(result.stderr)
                console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
                display_recommendation("CONTAINER_CREATE_REC")
                return False
                
        except Exception as e:
            error_msg = get_text("CONVERSION_ERROR").format(e)
            console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
            return False

def confirm_migration(data):
    """Confirma os detalhes da migração com o usuário"""
    console.clear()
    console.print(f"[bold cyan]{get_text('MIGRATION_CONFIRMATION')}[/bold cyan]\n")
    
    # Cria tabela de detalhes
    table = Table(title=get_text("MIGRATION_DETAILS"))
    table.add_column(get_text("DETAIL_ITEM"), style="cyan")
    table.add_column(get_text("DETAIL_VALUE"), style="green")
    
    table.add_row(get_text("DETAIL_CT_ID"), data['id'])
    table.add_row(get_text("DETAIL_CT_NAME"), data['name'])
    table.add_row(get_text("DETAIL_SOURCE"), f"{data['target']}:{data['port']}")
    table.add_row(get_text("DETAIL_BRIDGE"), data['bridge'])
    
    if data["ip"] == "dhcp":
        table.add_row(get_text("DETAIL_IP_DHCP"), get_text("IP_AUTOMATIC"))
    else:
        table.add_row(get_text("DETAIL_IP_STATIC"), f"{data['ip']}/24")
        table.add_row(get_text("DETAIL_GATEWAY"), data['gateway'])
    
    table.add_row(get_text("DETAIL_DISK"), f"{data['rootsize']} em {data['storage']}")
    table.add_row(get_text("DETAIL_MEMORY"), f"{data['memory']} MB")
    
    console.print(table)
    
    display_warning("MIGRATION_WARNING")
    display_recommendation("MIGRATION_CHECKLIST")
    
    return Confirm.ask(get_text("CONFIRM_MIGRATION"), default=False)

def check_incomplete_migrations():
    """Verifica se existem migrações incompletas e permite continuar"""
    state_manager = MigrationState()
    incomplete = state_manager.get_incomplete_migrations()
    
    if not incomplete:
        return MigrationState(), None
        
    console.print(f"\n[bold yellow]{get_text('INCOMPLETE_MIGRATIONS')}[/bold yellow]")
    
    # Mostra as migrações incompletas
    table = Table()
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Data", style="magenta")
    table.add_column("Container", style="green")
    table.add_column("Status", style="yellow")
    
    for m in incomplete:
        date = datetime.fromisoformat(m['timestamp']).strftime('%d/%m/%Y %H:%M')
        container = m['data'].get('name', 'Unknown')
        table.add_row(
            m['migration_id'],
            date,
            container,
            m['step']
        )
    
    console.print(table)
    
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

def migrate_lxc():
    """Função principal de migração"""
    def handle_interrupt(signum, frame):
        if 'state_manager' in locals() and state_manager is not None:
            state_manager.save_state(data, "interrupted")
        console.print(f"\n[red]{get_text('MIGRATION_CANCELLED_USER')}[/red]")
        exit(1)
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    # Verifica migrações incompletas
    state_manager, previous_state = check_incomplete_migrations()
    
    if not check_dependencies():
        console.print(f"\n[red]❌ Falha na verificação de dependências[/red]")
        return False
    
    # Se temos um estado anterior, podemos pular algumas etapas
    if previous_state:
        data = previous_state['data']
        continue_msg = get_text("CONTINUING_MIGRATION").format(previous_state['migration_id'], previous_state['step'])
        console.print(f"[yellow]{continue_msg}[/yellow]")
        logger.info(f"Continuando migração {previous_state['migration_id']} do passo {previous_state['step']}")
    else:
        data = user_input()
        if not data:
            console.print(f"\n[yellow]{get_text('MIGRATION_CANCELLED_INPUT')}[/yellow]")
            return False
        if state_manager:
            state_manager.save_state(data, "input_collected")
    
    if not validate_parameters(data):
        console.print(f"\n[red]{get_text('INVALID_PARAMETERS')}[/red]")
        return False
    
    if state_manager:
        state_manager.save_state(data, "validated")
    
    # Se estamos continuando uma migração e já passamos da confirmação, podemos pular
    if previous_state and previous_state['step'] in ['converting', 'validated']:
        console.print(f"[yellow]{get_text('SKIPPING_CONFIRMATION')}[/yellow]")
    else:
        if not confirm_migration(data):
            console.print(f"\n[yellow]{get_text('MIGRATION_CANCELLED_INPUT')}[/yellow]")
            if state_manager:
                state_manager.save_state(data, "cancelled")
            return False
    
    if state_manager:
        state_manager.save_state(data, "converting")
    if convert(data):
        if state_manager:
            state_manager.save_state(data, "completed")
            state_manager.clear_state()  # Remove o arquivo de estado após sucesso
        return True
    else:
        if state_manager:
            state_manager.save_state(data, "failed")
        return False

if __name__ == "__main__":
    migrate_lxc()
