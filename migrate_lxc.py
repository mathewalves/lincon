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
    # Verifica pct
    if not shutil.which("pct"):
        display_message("TITLE_ERROR", "MSG_NO_PCT")
        return False
    
    # Verifica pvesm
    if not shutil.which("pvesm"):
        display_message("TITLE_ERROR", "MSG_NO_PVESM")
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

def select_bridge():
    """Seleciona uma bridge de rede"""
    try:
        # Executa brctl show e obtém a saída
        result = subprocess.run(["brctl", "show"], capture_output=True, text=True, check=True)
        bridges = []
        
        # Processa a saída para extrair as bridges
        for line in result.stdout.splitlines()[1:]:  # Pula o cabeçalho
            if line.startswith("vmbr"):
                bridges.append(line.split()[0])

        if not bridges:
            display_message("TITLE_ERROR", "MSG_NO_BRIDGE")
            return None

        # Cria uma tabela para mostrar as bridges
        table = Table(show_header=False)
        for i, bridge in enumerate(bridges, 1):
            table.add_row(f"[{i}] {bridge}")

        console.print(Panel(translations[current_language]["MSG_BRIDGE_PROMPT"]))
        console.print(table)

        # Solicita escolha do usuário
        choice = Prompt.ask("", choices=[str(i) for i in range(1, len(bridges) + 1)])
        return bridges[int(choice) - 1]

    except subprocess.CalledProcessError:
        display_message("TITLE_ERROR", "MSG_NO_BRIDGE")
        return None

def select_storage():
    """Seleciona um storage"""
    try:
        result = subprocess.run(["pvesm", "status"], capture_output=True, text=True, check=True)
        storages = []
        descriptions = []

        for line in result.stdout.splitlines()[1:]:  # Pula o cabeçalho
            parts = line.split()
            if len(parts) >= 4:
                name, type_, status = parts[0:3]
                content = parts[3] if len(parts) > 3 else ""
                
                if status == "active" and ("rootdir" in content or "images" in content):
                    storages.append(name)
                    descriptions.append(f"({type_})")

        if not storages:
            display_message("TITLE_ERROR", "MSG_NO_SUITABLE_STORAGE")
            return None

        table = Table(show_header=False)
        for i, (storage, desc) in enumerate(zip(storages, descriptions), 1):
            table.add_row(f"[{i}] {storage} {desc}")

        console.print(Panel(translations[current_language]["MSG_STORAGE_PROMPT"]))
        console.print(table)

        choice = Prompt.ask("", choices=[str(i) for i in range(1, len(storages) + 1)])
        return storages[int(choice) - 1]

    except subprocess.CalledProcessError:
        display_message("TITLE_ERROR", "MSG_PVESM_STATUS_FAILED")
        return None

def select_ip_config():
    """Seleciona a configuração de IP"""
    table = Table(show_header=False)
    table.add_row("[1] " + translations[current_language]["OPTION_DHCP"])
    table.add_row("[2] " + translations[current_language]["OPTION_MANUAL"])

    console.print(Panel(translations[current_language]["MSG_IP_PROMPT"]))
    console.print(table)

    choice = Prompt.ask("", choices=["1", "2"])
    
    if choice == "1":
        return "dhcp", "dhcp"
    else:
        ip = Prompt.ask(translations[current_language]["MSG_CT_IP"])
        gateway = Prompt.ask(translations[current_language]["MSG_GATEWAY"])
        return ip, gateway

def user_input():
    """Coleta todos os dados necessários do usuário"""
    data = {}
    
    data["id"] = Prompt.ask(translations[current_language]["TITLE_CT_ID"])
    data["name"] = Prompt.ask(translations[current_language]["TITLE_CT_NAME"])
    data["target"] = Prompt.ask(translations[current_language]["TITLE_TARGET"])
    data["port"] = Prompt.ask(translations[current_language]["TITLE_SSH_PORT"])
    data["passwordSSH"] = Prompt.ask(translations[current_language]["TITLE_SSH_PASS"], password=True)
    
    data["bridge"] = select_bridge()
    if not data["bridge"]:
        return None
        
    data["ip"], data["gateway"] = select_ip_config()
    
    data["rootsize"] = Prompt.ask(translations[current_language]["TITLE_ROOTSIZE"])
    data["memory"] = Prompt.ask(translations[current_language]["TITLE_MEMORY"])
    
    data["storage"] = select_storage()
    if not data["storage"]:
        return None
        
    data["passwordCT"] = Prompt.ask(translations[current_language]["TITLE_CT_PASS"], password=True)
    
    return data

def validate_parameters(data):
    """Valida os parâmetros fornecidos"""
    required_fields = ["name", "target", "port", "id", "rootsize", "ip", 
                      "bridge", "memory", "storage", "passwordCT", "passwordSSH"]
                      
    for field in required_fields:
        if not data.get(field):
            display_message("TITLE_ERROR", "MSG_MISSING_PARAMS")
            return False
            
    if len(data["passwordCT"]) < 5:
        display_message("TITLE_ERROR", "MSG_PASS_TOO_SHORT")
        return False
        
    return True

def collect_fs(ssh_command):
    """Coleta o sistema de arquivos via SSH"""
    excluded_paths = [
        "/proc/*", "/sys/*", "/dev/*", "/tmp/*", "/run/*",
        "/mnt/*", "/media/*", "/lost+found", "/var/cache/apt/archives/*"
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
        display_message("TITLE_INFO", "MSG_COLLECTING_FS")
        
        ssh_command = [
            "sshpass", "-p", data["passwordSSH"],
            "ssh", "-p", data["port"],
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"root@{data['target']}"
        ]
        
        try:
            process = collect_fs(ssh_command)
            with open(temp_file.name, 'wb') as f:
                for chunk in process.stdout:
                    f.write(chunk)
            
            if process.wait() != 0:
                display_message("TITLE_ERROR", "MSG_SSH_CONNECTION_FAILED")
                return False
                
            if os.path.getsize(temp_file.name) == 0:
                display_message("TITLE_ERROR", "MSG_FS_COLLECTION_EMPTY")
                return False
            
            display_message("TITLE_INFO", "MSG_CREATING_CT")
            
            # Prepara parâmetros do pct create
            if data["ip"] == "dhcp":
                net_param = f"name=eth0,bridge={data['bridge']},ip=dhcp"
            else:
                net_param = f"name=eth0,bridge={data['bridge']},ip={data['ip']}/24,gw={data['gateway']}"
            
            create_command = [
                "pct", "create", data["id"], temp_file.name,
                "--description", f"LXC Migrated: {data['name']} (from {data['target']})",
                "--hostname", data["name"],
                "--features", "nesting=1",
                "--unprivileged", "0",
                "--memory", data["memory"],
                "--nameserver", "8.8.8.8",
                "--net0", net_param,
                "--rootfs", f"{data['storage']}:{data['rootsize']}",
                "--password", data["passwordCT"],
                "--onboot", "1",
                "--cmode", "shell"
            ]
            
            if subprocess.run(create_command).returncode == 0:
                display_message("TITLE_SUCCESS", "MSG_CT_CREATED")
                
                display_message("TITLE_INFO", "MSG_STARTING_CT")
                if subprocess.run(["pct", "start", data["id"]]).returncode == 0:
                    display_message("TITLE_SUCCESS", "MSG_CT_STARTED")
                else:
                    display_message("TITLE_WARNING", "MSG_CT_START_FAILED")
                return True
            else:
                display_message("TITLE_ERROR", "MSG_CT_FAILED")
                return False
                
        except Exception as e:
            display_message("TITLE_ERROR", str(e))
            return False

def confirm_migration(data):
    """Confirma os detalhes da migração com o usuário"""
    details = translations[current_language]["MSG_CONFIRM_DETAILS_PREAMBLE"] + "\n"
    details += f"  {translations[current_language]['LBL_CT_ID']}: {data['id']}\n"
    details += f"  {translations[current_language]['LBL_CT_NAME']}: {data['name']}\n"
    details += f"  {translations[current_language]['LBL_TARGET_HOST']}: {data['target']}:{data['port']}\n"
    details += f"  {translations[current_language]['LBL_BRIDGE']}: {data['bridge']}\n"
    details += f"  {translations[current_language]['LBL_IP_CONFIG']}: {data['ip']}"
    
    if data["ip"] != "dhcp":
        details += f"/24 (GW: {data['gateway']})"
    
    details += f"\n  {translations[current_language]['LBL_ROOT_SIZE']}: {data['rootsize']} on {data['storage']}\n"
    details += f"  {translations[current_language]['LBL_MEMORY']}: {data['memory']} MB"
    
    console.print(Panel(details, title=translations[current_language]["TITLE_CONFIRM_MIGRATION"]))
    return Confirm.ask("")

def check_incomplete_migrations():
    """Verifica se existem migrações incompletas e permite continuar"""
    state_manager = MigrationState()
    incomplete = state_manager.get_incomplete_migrations()
    
    if not incomplete:
        return None, None
        
    # Mostra as migrações incompletas
    table = Table(show_header=True)
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
    
    console.print("\n[bold cyan]Migrações Incompletas Encontradas:[/bold cyan]")
    console.print(table)
    
    if Confirm.ask("\nDeseja continuar uma migração anterior?"):
        choice = Prompt.ask(
            "Digite o ID da migração",
            choices=[m['migration_id'] for m in incomplete]
        )
        selected = next(m for m in incomplete if m['migration_id'] == choice)
        return MigrationState(choice), selected
    
    return MigrationState(), None

def migrate_lxc():
    """Função principal de migração"""
    def handle_interrupt(signum, frame):
        if 'state_manager' in locals():
            state_manager.save_state(data, "interrupted")
        display_message("TITLE_INFO", "MSG_MIGRATION_CANCELLED_INT")
        exit(1)
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    # Verifica migrações incompletas
    state_manager, previous_state = check_incomplete_migrations()
    
    if not check_dependencies():
        return False
    
    # Se temos um estado anterior, podemos pular algumas etapas
    if previous_state:
        data = previous_state['data']
        logger.info(f"Continuando migração {previous_state['migration_id']} do passo {previous_state['step']}")
    else:
        data = user_input()
        if not data:
            display_message("TITLE_ERROR", "MSG_USER_INPUT_CANCELLED")
            return False
        state_manager.save_state(data, "input_collected")
    
    if not validate_parameters(data):
        return False
    state_manager.save_state(data, "validated")
    
    # Se estamos continuando uma migração e já passamos da confirmação, podemos pular
    if previous_state and previous_state['step'] in ['converting', 'validated']:
        logger.info("Pulando confirmação - já validado anteriormente")
    else:
        if not confirm_migration(data):
            display_message("TITLE_INFO", "MSG_MIGRATION_CANCELLED_BY_USER")
            state_manager.save_state(data, "cancelled")
            return False
    
    state_manager.save_state(data, "converting")
    if convert(data):
        state_manager.save_state(data, "completed")
        state_manager.clear_state()  # Remove o arquivo de estado após sucesso
        return True
    else:
        state_manager.save_state(data, "failed")
        return False

if __name__ == "__main__":
    migrate_lxc()
