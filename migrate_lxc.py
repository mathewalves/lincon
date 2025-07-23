from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
import subprocess
import os
import shutil
import re
import signal

console = Console()

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

def validate_size_format(size):
    """Valida formato de tamanho (ex: 20G, 500M)"""
    pattern = r'^\d+[GM]$'
    return re.match(pattern, size.upper()) is not None

def check_dependencies():
    """Verifica dependências básicas"""
    missing_deps = []
    
    if not shutil.which("pct"):
        missing_deps.append("pct (Proxmox Container Toolkit)")
    if not shutil.which("pvesm"):
        missing_deps.append("pvesm (Proxmox VE Storage Manager)")
    if not shutil.which("brctl"):
        missing_deps.append("brctl (Bridge utilities)")
    
    if missing_deps:
        error_msg = "Dependências faltando:\n" + "\n".join(f"• {dep}" for dep in missing_deps)
        console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
        return False

    if not shutil.which("sshpass"):
        console.print("[cyan]Instalando sshpass...[/cyan]")
        try:
            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            subprocess.run(["apt-get", "install", "-y", "sshpass"], check=True, capture_output=True)
            console.print("[green]✅ sshpass instalado[/green]")
        except subprocess.CalledProcessError:
            console.print("[red]❌ Falha ao instalar sshpass[/red]")
            return False
    
    return True

def test_ssh_connection(target, port, password):
    """Testa conexão SSH básica"""
    console.print("[cyan]🔍 Testando conexão SSH...[/cyan]")
    
    try:
        cmd = [
            "sshpass", "-p", password,
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"root@{target}",
            "echo 'SSH OK'"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            console.print("[green]✅ Conexão SSH estabelecida[/green]")
            return True
        else:
            console.print(f"[red]❌ Falha SSH: {result.stderr.strip()}[/red]")
            if "Permission denied" in result.stderr:
                console.print("[yellow]💡 Verifique se o root SSH está habilitado no servidor de origem[/yellow]")
            return False
            
    except subprocess.TimeoutExpired:
        console.print("[red]❌ Timeout na conexão SSH[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Erro SSH: {e}[/red]")
        return False

def select_bridge():
    """Seleciona bridge de rede"""
    try:
        result = subprocess.run(["brctl", "show"], capture_output=True, text=True, check=True)
        bridges = []
        
        for line in result.stdout.splitlines()[1:]:
            if line.strip() and not line.startswith('\t'):
                bridge_name = line.split()[0]
                if bridge_name.startswith("vmbr"):
                    bridges.append(bridge_name)

        if not bridges:
            console.print("[red]❌ Nenhuma bridge encontrada[/red]")
            return None

        table = Table(title="[bold cyan]Bridges Disponíveis[/bold cyan]", show_header=True)
        table.add_column("Opção", style="cyan", width=6)
        table.add_column("Bridge", style="green", width=12)
        
        for i, bridge in enumerate(bridges, 1):
            table.add_row(f"[{i}]", bridge)

        console.print(table)
        
        choice = Prompt.ask("Escolha uma bridge", choices=[str(i) for i in range(1, len(bridges) + 1)])
        return bridges[int(choice) - 1]

    except subprocess.CalledProcessError:
        console.print("[red]❌ Erro ao listar bridges[/red]")
        return None

def select_storage():
    """Seleciona storage"""
    try:
        result = subprocess.run(["pvesm", "status"], capture_output=True, text=True, check=True)
        storages = []

        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                name, type_, status = parts[0:3]
                if status == "active" and type_ in ["dir", "lvm", "lvmthin", "zfs", "btrfs"]:
                    storages.append(name)

        if not storages:
            console.print("[red]❌ Nenhum storage adequado encontrado[/red]")
            return None

        table = Table(title="[bold cyan]Storages Disponíveis[/bold cyan]", show_header=True)
        table.add_column("Opção", style="cyan", width=6)
        table.add_column("Storage", style="green", width=15)
        
        for i, storage in enumerate(storages, 1):
            table.add_row(f"[{i}]", storage)

        console.print(table)
        
        choice = Prompt.ask("Escolha um storage", choices=[str(i) for i in range(1, len(storages) + 1)])
        return storages[int(choice) - 1]

    except subprocess.CalledProcessError:
        console.print("[red]❌ Erro ao listar storages[/red]")
        return None

def collect_user_data():
    """Coleta todos os dados necessários do usuário"""
    console.clear()
    console.print("[bold cyan]🚀 LINCON - Migração Linux → Proxmox LXC[/bold cyan]\n")
    
    data = {}
    
    # ID do Container
    while True:
        ct_id = Prompt.ask("ID do Container (100-999999)", default="101")
        if validate_ct_id(ct_id):
            try:
                result = subprocess.run(["pct", "status", ct_id], capture_output=True)
                if result.returncode == 0:
                    console.print(f"[yellow]⚠️  Container {ct_id} já existe[/yellow]")
                    if not Confirm.ask("Escolher outro ID?"):
                        return None
                    continue
            except:
                pass
            data["id"] = ct_id
            break
        else:
            console.print("[red]❌ ID inválido[/red]")

    # Nome do Container
    while True:
        name = Prompt.ask(f"Nome do Container {data['id']}")
        if name and len(name) >= 3:
            data["name"] = name
            break
        else:
            console.print("[red]❌ Nome muito curto (mínimo 3 caracteres)[/red]")

    # Host de origem
    while True:
        target = Prompt.ask("Host de origem (IP ou hostname)")
        if target and validate_hostname(target):
            data["target"] = target
            break
        else:
            console.print("[red]❌ Hostname/IP inválido[/red]")

    # Porta SSH
    while True:
        port = Prompt.ask("Porta SSH", default="22")
        if validate_port(port):
            data["port"] = port
            break
        else:
            console.print("[red]❌ Porta inválida[/red]")

    # Senha SSH
    while True:
        password = Prompt.ask("Senha SSH do servidor origem", password=True)
        if password:
            if test_ssh_connection(data["target"], data["port"], password):
                data["passwordSSH"] = password
                break
            else:
                if not Confirm.ask("Tentar outra senha?"):
                    return None
        else:
            console.print("[red]❌ Senha não pode estar vazia[/red]")

    # Bridge de rede
    bridge = select_bridge()
    if not bridge:
        return None
    data["bridge"] = bridge

    # Configuração IP
    console.print("\n[cyan]Configuração de IP:[/cyan]")
    table = Table(show_header=True)
    table.add_column("Opção", style="cyan")
    table.add_column("Tipo", style="green")
    table.add_row("[1]", "DHCP (automático)")
    table.add_row("[2]", "IP estático")
    console.print(table)
    
    ip_choice = Prompt.ask("Escolha", choices=["1", "2"])
    
    if ip_choice == "1":
        data["ip"] = "dhcp"
        data["gateway"] = "dhcp"
    else:
        while True:
            ip = Prompt.ask("IP do container")
            if validate_ip(ip):
                data["ip"] = ip
                break
            else:
                console.print("[red]❌ IP inválido[/red]")
        
        while True:
            gateway = Prompt.ask("Gateway")
            if validate_ip(gateway):
                data["gateway"] = gateway
                break
            else:
                console.print("[red]❌ Gateway inválido[/red]")

    # Tamanho do disco
    while True:
        rootsize = Prompt.ask("Tamanho do disco (ex: 20G, 500M)", default="20G")
        if validate_size_format(rootsize):
            data["rootsize"] = rootsize.upper()
            break
        else:
            console.print("[red]❌ Formato inválido (use: 20G, 500M, etc.)[/red]")

    # Memória
    while True:
        try:
            memory = int(Prompt.ask("Memória em MB", default="1024"))
            if memory >= 64:
                data["memory"] = str(memory)
                break
            else:
                console.print("[red]❌ Memória muito baixa (mínimo 64MB)[/red]")
        except ValueError:
            console.print("[red]❌ Digite apenas números[/red]")

    # Storage
    storage = select_storage()
    if not storage:
        return None
    data["storage"] = storage

    # Senha do container
    while True:
        password = Prompt.ask("Senha do container (mínimo 5 caracteres)", password=True)
        if len(password) >= 5:
            confirm_pass = Prompt.ask("Confirme a senha", password=True)
            if password == confirm_pass:
                data["passwordCT"] = password
                break
            else:
                console.print("[red]❌ Senhas não coincidem[/red]")
        else:
            console.print("[red]❌ Senha muito curta[/red]")

    return data

def confirm_migration(data):
    """Confirma os detalhes da migração"""
    console.print("\n[bold cyan]📋 Confirmação da Migração[/bold cyan]")
    
    table = Table(title="[bold green]Detalhes da Migração[/bold green]", show_header=True)
    table.add_column("Item", style="cyan", width=20)
    table.add_column("Valor", style="white")
    
    table.add_row("🆔 Container ID", data["id"])
    table.add_row("🏷️  Nome", data["name"])
    table.add_row("🖥️  Servidor Origem", f"{data['target']}:{data['port']}")
    table.add_row("🌐 Bridge", data["bridge"])
    table.add_row("📡 IP", data["ip"])
    if data["ip"] != "dhcp":
        table.add_row("🚪 Gateway", data["gateway"])
    table.add_row("💿 Disco", data["rootsize"])
    table.add_row("🧠 Memória", f"{data['memory']} MB")
    table.add_row("💾 Storage", data["storage"])
    
    console.print(table)
    
    console.print("\n[yellow]⚠️  IMPORTANTE:[/yellow]")
    console.print("• Este processo pode demorar dependendo do tamanho do sistema")
    console.print("• Certifique-se de que o servidor de origem está acessível")
    console.print("• O container será criado e iniciado automaticamente")
    
    return Confirm.ask("\n🚀 Confirmar migração?", default=False)

def execute_migration(data):
    """Executa a migração usando o script shell"""
    console.print("\n[cyan]📦 Executando migração...[/cyan]")
    
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(description="🚀 Executando migração...", total=None)
            result = subprocess.run(shell_command, capture_output=True, text=True, timeout=1800)
        
        if result.returncode == 0:
            console.print("\n[bold green]🎉 Migração concluída com sucesso![/bold green]")
            # Exibe apenas as linhas importantes do output
            for line in result.stdout.split('\n'):
                if any(symbol in line for symbol in ['✅', '🎉', '📋', '💡']):
                    console.print(line)
            return True
        else:
            console.print(f"\n[red]❌ Erro na migração:[/red]")
            console.print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        console.print("\n[red]❌ Timeout: Migração demorou muito tempo[/red]")
        return False
    except Exception as e:
        console.print(f"\n[red]❌ Erro inesperado: {e}[/red]")
        return False

def migrate_lxc():
    """Função principal de migração"""
    def handle_interrupt(signum, frame):
        console.print("\n[yellow]⚠️  Migração cancelada pelo usuário[/yellow]")
        exit(1)
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    if not check_dependencies():
        return False
    
    data = collect_user_data()
    if not data:
        console.print("\n[yellow]❌ Migração cancelada[/yellow]")
        return False
    
    if not confirm_migration(data):
        console.print("\n[yellow]❌ Migração cancelada[/yellow]")
        return False
    
    return execute_migration(data)

if __name__ == "__main__":
    migrate_lxc() 