from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
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

def display_ssh_tutorial():
    """Exibe um tutorial moderno para habilitar SSH root"""
    console.print()
    
    # Header moderno
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

def diagnose_ssh_issue(target, port, password):
    """Diagnóstico avançado de problemas SSH"""
    console.print()
    console.print(Panel(
        get_text('SSH_DIAG_INTRO'),
        title=get_text('SSH_DIAG_TITLE'),
        border_style="yellow",
        padding=(1, 2)
    ))
    
    console.print(f"[yellow]{get_text('SSH_DIAG_TESTING')}[/yellow]")
    
    # Teste 1: SSH direto sem sshpass
    console.print(f"\n🔍 {get_text('SSH_DIAG_METHOD1')}")
    try:
        direct_cmd = [
            "ssh", "-p", str(port), 
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            "-o", "PasswordAuthentication=no",
            f"root@{target}",
            "echo 'test'"
        ]
        direct_result = subprocess.run(direct_cmd, capture_output=True, text=True, timeout=10)
        
        if direct_result.returncode == 0:
            console.print("   ✅ SSH direto funciona (chave pública configurada)")
            return "key_auth"
        else:
            console.print("   ❌ SSH direto falha (sem chave pública)")
    except:
        console.print("   ❌ SSH direto falha (timeout ou erro)")
    
    # Teste 2: Verificar se senha funciona manualmente
    console.print(f"\n🔍 {get_text('SSH_DIAG_METHOD2')}")
    manual_works = Confirm.ask(f"   {get_text('SSH_MANUAL_TEST')}", default=True)
    
    if manual_works:
        console.print("   ✅ SSH manual funciona")
        display_message("TITLE_INFO", "SSH_WORKING_MANUALLY")
        return "sshpass_issue"
    else:
        console.print("   ❌ SSH manual também falha")
        return "general_auth_issue"
    
    # Teste 3: Verificar configuração SSH
    console.print(f"\n🔍 {get_text('SSH_DIAG_METHOD3')}")
    try:
        config_cmd = [
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            f"root@{target}",
            "cat /etc/ssh/sshd_config | grep -E '(PermitRootLogin|PasswordAuthentication)'"
        ]
        config_result = subprocess.run(config_cmd, capture_output=True, text=True, timeout=10)
        console.print(f"   📋 Configuração SSH: {config_result.stdout.strip()}")
    except:
        console.print("   ❌ Não foi possível verificar configuração SSH")
    
    return "unknown"

def offer_ssh_solutions(target, port, password, issue_type):
    """Oferece soluções baseadas no diagnóstico"""
    console.print()
    
    solutions_content = f"""[bold cyan]{get_text('SSH_SOLUTION_TITLE')}[/bold cyan]

{get_text('SSH_SOLUTION_1')}
{get_text('SSH_SOLUTION_2')}
{get_text('SSH_SOLUTION_3')}"""

    console.print(Panel(
        solutions_content,
        border_style="green",
        padding=(1, 2)
    ))
    
    if issue_type == "sshpass_issue":
        console.print(f"[yellow]{get_text('SSH_SSHPASS_ISSUE')}[/yellow]")
        
        # Tentar sshpass com diferentes opções
        if Confirm.ask("🔧 Tentar sshpass com configurações alternativas?", default=True):
            return try_alternative_sshpass(target, port, password)
    
    elif issue_type == "key_auth":
        if Confirm.ask(get_text('SSH_KEY_SETUP'), default=False):
            return setup_ssh_key(target, port)
    
    # Modo interativo como último recurso
    if Confirm.ask(get_text('SSH_TRY_INTERACTIVE'), default=True):
        return try_interactive_ssh(target, port)
    
    return False

def try_alternative_sshpass(target, port, password):
    """Tenta diferentes configurações de sshpass"""
    console.print(f"[cyan]🔧 Testando configurações alternativas do sshpass...[/cyan]")
    
    # Método 1: sshpass com diferentes opções SSH
    methods = [
        {
            "name": "Método 1: Forçar autenticação por senha",
            "cmd": [
                "sshpass", "-p", password,
                "ssh", "-p", str(port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "PasswordAuthentication=yes",
                "-o", "PubkeyAuthentication=no",
                "-o", "ConnectTimeout=10",
                f"root@{target}",
                "echo 'Conexão OK'"
            ]
        },
        {
            "name": "Método 2: sshpass com TTY",
            "cmd": [
                "sshpass", "-p", password,
                "ssh", "-p", str(port),
                "-tt",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                f"root@{target}",
                "echo 'Conexão OK'"
            ]
        },
        {
            "name": "Método 3: sshpass alternativo",
            "cmd": [
                "sshpass", "-p", password,
                "ssh", "-p", str(port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "BatchMode=no",
                "-o", "ConnectTimeout=10",
                f"root@{target}",
                "echo 'Conexão OK'"
            ]
        }
    ]
    
    for i, method in enumerate(methods, 1):
        console.print(f"   🔍 {method['name']}...")
        try:
            result = subprocess.run(method['cmd'], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                console.print(f"   ✅ {method['name']} funcionou!")
                # Atualizar comando SSH globalmente (remove target e echo de teste)
                global ssh_method
                # Remove o target e o echo, mantém apenas o comando base SSH
                ssh_base = method['cmd'][:-2]  # Remove root@target e echo
                ssh_method = ssh_base
                return True
            else:
                console.print(f"   ❌ {method['name']} falhou: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            console.print(f"   ⏰ {method['name']} timeout")
        except Exception as e:
            console.print(f"   ❌ {method['name']} erro: {e}")
    
    return False

def try_interactive_ssh(target, port):
    """Modo interativo para SSH"""
    console.print(f"[cyan]🎮 Modo interativo ativado[/cyan]")
    console.print(f"[yellow]Execute o comando abaixo em outro terminal:[/yellow]")
    console.print(f"[bold green]ssh -p {port} root@{target}[/bold green]")
    console.print()
    console.print("[dim]Após conectar com sucesso, volte aqui e confirme[/dim]")
    
    if Confirm.ask("✅ SSH manual realizado com sucesso?", default=False):
        console.print("[green]🎉 Ótimo! Continuando com chave SSH...[/green]")
        return setup_ssh_key(target, port)
    
    return False

def setup_ssh_key(target, port):
    """Configura chave SSH para conexão segura"""
    console.print(f"[cyan]{get_text('SSH_KEY_GENERATION')}[/cyan]")
    
    try:
        # Verifica se já existe chave
        key_path = os.path.expanduser("~/.ssh/id_rsa")
        if not os.path.exists(key_path):
            # Gera nova chave SSH
            keygen_cmd = ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", key_path, "-N", ""]
            subprocess.run(keygen_cmd, check=True, capture_output=True)
            console.print("🔑 Chave SSH gerada")
        else:
            console.print("🔑 Usando chave SSH existente")
        
        # Copia chave para o servidor
        console.print(f"[cyan]{get_text('SSH_KEY_COPY')}[/cyan]")
        console.print(f"[yellow]Execute o comando abaixo:[/yellow]")
        console.print(f"[bold green]ssh-copy-id -p {port} root@{target}[/bold green]")
        console.print()
        
        if Confirm.ask("🔑 Chave copiada com sucesso?", default=False):
            # Testa conexão com chave
            test_cmd = ["ssh", "-p", str(port), "-o", "ConnectTimeout=10", f"root@{target}", "echo 'OK'"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                console.print("✅ Chave SSH configurada com sucesso!")
                global use_ssh_key
                use_ssh_key = True
                return True
        
    except Exception as e:
        console.print(f"❌ Erro ao configurar chave SSH: {e}")
    
    return False

# Variáveis globais para métodos SSH alternativos
ssh_method = None
use_ssh_key = False
ssh_diagnosis_attempted = False

# Modo de desenvolvimento para testes fora do Proxmox
DEV_MODE = os.getenv("LINCON_DEV_MODE", "false").lower() == "true"

def reset_ssh_config():
    """Reseta configurações SSH globais"""
    global ssh_method, use_ssh_key, ssh_diagnosis_attempted
    ssh_method = None
    use_ssh_key = False
    ssh_diagnosis_attempted = False

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
    """Testa conexão SSH com diagnóstico avançado"""
    display_message("TITLE_INFO", "TESTING_SSH")
    
    # Se já temos método SSH funcionando, usar ele
    global ssh_method, use_ssh_key
    
    if use_ssh_key:
        # Tentar com chave SSH
        try:
            cmd = ["ssh", "-p", str(port), "-o", "ConnectTimeout=10", f"root@{target}", "echo 'Conexão OK'"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                display_success("SSH_CONNECTION_OK")
                return True
        except:
            pass
    
    if ssh_method:
        # Tentar com método SSH alternativo já configurado
        try:
            # ssh_method contém comando base, adicionar target e comando
            cmd = ssh_method + [f"root@{target}", "echo 'Conexão OK'"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                display_success("SSH_CONNECTION_OK")
                return True
        except Exception as e:
            # Se falhar, resetar ssh_method para tentar outros métodos
            console.print(f"[dim]Método SSH salvo falhou: {e}[/dim]")
            ssh_method = None
    
    try:
        # Teste padrão com sshpass
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
            
            # Detecta erro de Permission denied específico
            if "Permission denied" in result.stderr and ("publickey" in result.stderr or "password" in result.stderr):
                display_error("SSH_PERMISSION_DENIED")
                
                global ssh_diagnosis_attempted
                
                # Só faz diagnóstico se ainda não tentou
                if not ssh_diagnosis_attempted:
                    ssh_diagnosis_attempted = True
                    
                    # Diagnóstico avançado
                    issue_type = diagnose_ssh_issue(target, port, password)
                    
                    # Oferece soluções específicas
                    if offer_ssh_solutions(target, port, password, issue_type):
                        # Testa novamente após aplicar solução
                        if Confirm.ask(get_text("SSH_RETEST_CONNECTION"), default=True):
                            return test_ssh_connection(target, port, password)
                        else:
                            return False
                    else:
                        # Fallback para tutorial básico
                        if Confirm.ask(get_text("SSH_CONTINUE_TUTORIAL"), default=True):
                            display_ssh_tutorial()
                            console.print()
                        return False
                else:
                    # Se já tentou diagnóstico, oferece opções de escape
                    console.print(f"[yellow]{get_text('SSH_PERSISTENT_ISSUE')}[/yellow]")
                    
                    if Confirm.ask(get_text("SSH_RESET_AND_TRY"), default=False):
                        reset_ssh_config()
                        return test_ssh_connection(target, port, password)
                    elif Confirm.ask(get_text("SSH_CONTINUE_TUTORIAL"), default=True):
                        display_ssh_tutorial()
                        console.print()
                    
                    return False
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

            # Cria uma tabela moderna para mostrar as bridges
            table = Table(title=f"[bold cyan]{get_text('BRIDGE_AVAILABLE')}[/bold cyan]", 
                         show_header=True, header_style="bold bright_white",
                         border_style="cyan", show_edge=False)
            table.add_column("Opção", style="bright_cyan", width=6)
            table.add_column("Bridge", style="bright_green", width=12)
            table.add_column("Descrição", style="dim")
            
            for i, bridge in enumerate(bridges, 1):
                desc = get_text("BRIDGE_DEFAULT") if bridge == "vmbr0" else get_text("BRIDGE_ADDITIONAL")
                table.add_row(f"[{i}]", bridge, desc)

            table.add_row("[0]", "🔙 Voltar", "[dim]Voltar ao menu anterior[/dim]")
            console.print()
            console.print(table)
            console.print()
            
            display_recommendation("REC_BRIDGE_DEFAULT")

            # Solicita escolha do usuário
            choice = Prompt.ask(
                f"[bright_cyan]{get_text('CHOOSE_BRIDGE')}[/bright_cyan]",
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
                    
                    # Aceita storages ativos que suportam containers
                    # Tipos que suportam containers: dir, lvm, lvmthin, zfs, btrfs
                    container_types = ["dir", "lvm", "lvmthin", "zfs", "btrfs", "nfs"]
                    
                    if status == "active" and type_ in container_types:
                        storages.append(name)
                        storage_info.append({
                            'name': name,
                            'type': type_,
                            'total': total,
                            'used': used,
                            'avail': avail,
                            'content': content or "containers"  # Default para containers
                        })

            if not storages:
                display_error("NO_STORAGE_FOUND")
                display_recommendation("STORAGE_CHECK_ACTIVE")
                return None

            # Cria tabela moderna para storage
            table = Table(title=f"[bold cyan]{get_text('STORAGE_AVAILABLE')}[/bold cyan]",
                         show_header=True, header_style="bold bright_white",
                         border_style="cyan", show_edge=False)
            table.add_column("Opção", style="bright_cyan", width=6)
            table.add_column(get_text("STORAGE_NAME"), style="bright_green", width=12)
            table.add_column(get_text("STORAGE_TYPE"), style="bright_yellow", width=10)
            table.add_column(get_text("STORAGE_AVAILABLE_SPACE"), style="bright_blue", width=12)
            table.add_column(get_text("STORAGE_TOTAL"), style="bright_magenta", width=12)
            
            for i, info in enumerate(storage_info, 1):
                table.add_row(
                    f"[{i}]",
                    info['name'],
                    info['type'],
                    info['avail'],
                    info['total']
                )
            
            table.add_row("[0]", "🔙 Voltar", "[dim]Menu anterior[/dim]", "", "")
            console.print()
            console.print(table)
            console.print()
            
            display_recommendation("STORAGE_CHECK_ACTIVE")

            choice = Prompt.ask(
                f"[bright_cyan]{get_text('CHOOSE_STORAGE')}[/bright_cyan]",
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
        
        table = Table(title=f"[bold cyan]{get_text('IP_OPTIONS')}[/bold cyan]",
                     show_header=True, header_style="bold bright_white",
                     border_style="cyan", show_edge=False)
        table.add_column("Opção", style="bright_cyan", width=6)
        table.add_column("Tipo", style="bright_green", width=12)
        table.add_column("Descrição", style="dim")
        
        table.add_row("[1]", get_text("IP_DHCP"), get_text("IP_DHCP_DESC"))
        table.add_row("[2]", get_text("IP_STATIC"), get_text("IP_STATIC_DESC"))
        table.add_row("[0]", "🔙 Voltar", "[dim]Voltar ao menu anterior[/dim]")
        
        console.print()
        console.print(table)
        console.print()

        choice = Prompt.ask(f"[bright_cyan]{get_text('CHOOSE_IP_TYPE')}[/bright_cyan]", choices=["0", "1", "2"])
    
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

def parse_proxmox_size(size_str):
    """Converte tamanho do Proxmox (pvesm status) para bytes"""
    size_str = str(size_str).strip()
    
    if size_str.isdigit():
        # Proxmox retorna em KB se for só número
        return int(size_str) * 1024
    
    size_str = size_str.upper().replace(',', '.')
    try:
        if size_str.endswith('G'):
            return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]) * 1024 * 1024)
        elif size_str.endswith('K'):
            return int(float(size_str[:-1]) * 1024)
        elif size_str.endswith('B'):
            return int(float(size_str[:-1]))
        else:
            return int(size_str)
    except Exception:
        return 0

def parse_size(size_str):
    """Converte string de tamanho (ex: 200412836 para bytes)"""
    size_str = str(size_str).upper().strip()
    
    # Se é apenas números, assume bytes
    if size_str.isdigit():
        return int(size_str)
    
    if size_str.endswith('G'):
        return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
    elif size_str.endswith('M'):
        return int(float(size_str[:-1]) * 1024 * 1024)
    elif size_str.endswith('K'):
        return int(float(size_str[:-1]) * 1024)
    else:
        # Tenta converter como bytes
        try:
            return int(size_str)
        except ValueError:
            return 0

def format_size(bytes_size):
    """Converte bytes para formato legível (ex: 2.3G, 500M)"""
    if bytes_size >= 1024**3:
        return f"{bytes_size / (1024**3):.1f}G"
    elif bytes_size >= 1024**2:
        return f"{bytes_size / (1024**2):.1f}M"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.1f}K"
    else:
        return f"{bytes_size}B"

def check_storage_space(storage_name, required_size):
    """Verifica se há espaço suficiente no storage"""
    try:
        result = subprocess.run(["pvesm", "status"], capture_output=True, text=True, check=True)
        available_storages = []
        for line in result.stdout.splitlines()[1:]:  # Pula o cabeçalho
            parts = line.split()
            if len(parts) >= 6:
                name, type_, status, total, used, avail = parts[0:6]
                if name == storage_name and status == "active":
                    # Usa parse_proxmox_size para total e avail
                    avail_bytes = parse_proxmox_size(avail)
                    required_bytes = parse_size(required_size)
                    total_bytes = parse_proxmox_size(total)
                    # Debug silencioso - só mostra se há problema
                    # console.print(f"[dim]🔍 Debug - Storage {name}: {format_size(avail_bytes)} disponível, {format_size(required_bytes)} necessário[/dim]")
                    avail_readable = format_size(avail_bytes)
                    required_readable = format_size(required_bytes)
                    total_readable = format_size(total_bytes)
                    if avail_bytes < required_bytes:
                        return False, f"Storage {storage_name} tem apenas {avail_readable} disponível (total: {total_readable}), mas precisa de {required_readable}"
                    return True, f"Storage {storage_name} tem {avail_readable} disponível, suficiente para {required_readable}"
                if status == "active" and type_ in ["dir", "lvm", "lvmthin", "zfs", "btrfs"]:
                    avail_bytes = parse_proxmox_size(avail)
                    avail_readable = format_size(avail_bytes)
                    available_storages.append((name, avail_readable, avail_bytes))
        if available_storages:
            console.print(f"[yellow]💡 Storages disponíveis:[/yellow]")
            for name, size, bytes_size in sorted(available_storages, key=lambda x: x[2], reverse=True):
                console.print(f"   • {name}: {size} disponível")
        return False, f"Storage {storage_name} não encontrado ou inativo"
    except subprocess.CalledProcessError as e:
        console.print(f"[dim]🔍 Debug - Erro ao executar pvesm status: {e}[/dim]")
        return False, "Erro ao verificar status do storage"
    except Exception as e:
        console.print(f"[dim]🔍 Debug - Erro inesperado: {e}[/dim]")
        return False, f"Erro inesperado: {e}"

def collect_fs(ssh_command):
    """Coleta o sistema de arquivos via SSH"""
    excluded_paths = [
        "/proc",
        "/sys", 
        "/dev",
        "/tmp",
        "/run",
        "/mnt",
        "/media",
        "/lost+found",
        "/var/cache/apt/archives",
        "/swapfile",
        "/swap.img"
    ]
    
    # Constrói comando tar como string para melhor controle
    tar_parts = [
        "tar",
        "czpf", "-",
        "--warning=no-file-changed",
        "--warning=no-file-removed", 
        "--one-file-system",
        "--ignore-failed-read",
        "--numeric-owner",
        "--exclude-caches"
    ]
    
    # Adiciona exclusões
    for path in excluded_paths:
        tar_parts.extend(["--exclude", path])
    
    # Adiciona diretório raiz
    tar_parts.append("/")
    
    # Monta comando completo com redirecionamento de stderr
    remote_cmd = " ".join(tar_parts) + " 2>/dev/null"
    ssh_command.append(remote_cmd)
    
    # Debug: mostra comando completo que será executado
    console.print(f"[dim]🔧 Comando tar remoto: {remote_cmd[:100]}...[/dim]")
    
    return subprocess.Popen(ssh_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def diagnose_ssh_connection(data):
    """Diagnóstica problemas de conexão SSH antes da migração"""
    console.print(f"\n[cyan]🔧 Executando diagnóstico SSH completo...[/cyan]")
    
    # Monta comando SSH base
    ssh_base = [
        "sshpass", "-p", data["passwordSSH"],
        "ssh", "-p", data["port"],
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"root@{data['target']}"
    ]
    
    tests = [
        ("🔌 Teste de conectividade básica", ["echo 'SSH_OK'"]),
        ("📋 Verificando usuário", ["whoami"]),
        ("💿 Testando comando tar", ["tar --version | head -1"]),
        ("📁 Verificando diretório raiz", ["ls -la / | head -5"]),
        ("💾 Verificando espaço em disco", ["df -h / | head -2"])
    ]
    
    all_passed = True
    
    for test_name, test_cmd in tests:
        console.print(f"[dim]{test_name}...[/dim]")
        try:
            result = subprocess.run(
                ssh_base + test_cmd, 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                console.print(f"[dim]   ✅ {output[:60]}{'...' if len(output) > 60 else ''}[/dim]")
            else:
                console.print(f"[yellow]   ❌ Falhou: {result.stderr.strip()[:60]}[/yellow]")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            console.print(f"[red]   ⏰ Timeout[/red]")
            all_passed = False
        except Exception as e:
            console.print(f"[red]   ❌ Erro: {str(e)[:60]}[/red]")
            all_passed = False
    
    return all_passed

def convert(data):
    """Converte e cria o container"""
    
    # Verifica espaço no storage antes de começar
    console.print(f"\n[cyan]🔍 Verificando espaço no storage...[/cyan]")
    has_space, space_msg = check_storage_space(data['storage'], data['rootsize'])
    
    if not has_space:
        console.print(Panel(f"❌ {space_msg}", title="❌ ERRO", style="red"))
        console.print(f"[yellow]💡 Soluções:[/yellow]")
        console.print(f"   • Escolha um storage com mais espaço")
        console.print(f"   • Reduza o tamanho do disco (atualmente {data['rootsize']})")
        console.print(f"   • Libere espaço no storage atual")
        return False
    
    console.print(f"[green]✅ {space_msg}[/green]")
    
    # Executa diagnóstico SSH completo
    if not diagnose_ssh_connection(data):
        console.print()
        console.print(Panel(
            "[red]❌ Diagnóstico SSH falhou[/red]\n\n[yellow]Corrija os problemas acima antes de continuar a migração.[/yellow]",
            title="[bold red]❌ ERRO DE CONECTIVIDADE[/bold red]",
            border_style="red",
            padding=(1, 2)
        ))
        return False
    
    console.print(f"\n[green]✅ Diagnóstico SSH passou - prosseguindo com migração[/green]")
    
    with tempfile.NamedTemporaryFile(prefix=f"{data['name']}_migration_", suffix=".tar.gz") as temp_file:
        console.print(f"\n[cyan]{get_text('MIGRATION_STARTING')}[/cyan]")
        
        # Estima o tempo baseado no sistema
        display_message("TITLE_INFO", "COLLECTING_FILESYSTEM")
        display_recommendation("COLLECTION_TIME_WARNING")
        
        # Usa método SSH apropriado baseado no diagnóstico
        global ssh_method, use_ssh_key
        
        if use_ssh_key:
            ssh_command = [
                "ssh", "-p", data["port"],
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=30",
                "-o", "ServerAliveInterval=30",
                f"root@{data['target']}"
            ]
        elif ssh_method:
            ssh_command = ssh_method + [f"root@{data['target']}"]  # Adiciona target ao comando base
        else:
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
            
            # Debug: mostra comando SSH que será executado
            console.print(f"[dim]🔧 Debug - Comando SSH: {' '.join(ssh_command[:-1])} '[COMANDO_TAR]'[/dim]")
            
            # Testa conectividade SSH antes da coleta
            console.print(f"[dim]🔧 Testando conectividade SSH...[/dim]")
            test_ssh = ssh_command[:-1] + ["echo 'Conexão SSH OK'"]
            test_result = subprocess.run(test_ssh, capture_output=True, text=True, timeout=10)
            
            if test_result.returncode != 0:
                console.print(f"[red]❌ Erro na conectividade SSH: {test_result.stderr}[/red]")
                return False
            else:
                console.print(f"[dim]✅ SSH conectado: {test_result.stdout.strip()}[/dim]")
            
            # Testa comando tar básico no servidor remoto
            console.print(f"[dim]🔧 Testando comando tar no servidor remoto...[/dim]")
            test_tar = ssh_command[:-1] + ["tar --version | head -1"]
            tar_test_result = subprocess.run(test_tar, capture_output=True, text=True, timeout=10)
            
            if tar_test_result.returncode == 0:
                console.print(f"[dim]✅ Tar disponível: {tar_test_result.stdout.strip()}[/dim]")
            else:
                console.print(f"[yellow]⚠️  Aviso - tar test: {tar_test_result.stderr}[/yellow]")
            
            process = collect_fs(ssh_command)
            
            # Interface moderna de progresso
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=False
            ) as progress:
                
                # Cria a task de transferência
                task = progress.add_task(
                    description="🚀 Transferindo sistema de arquivos...",
                    total=None  # Tamanho desconhecido inicialmente
                )
                
                with open(temp_file.name, 'wb') as f:
                    chunk_count = 0
                    last_update = time.time()
                    total_bytes = 0
                    update_interval = 0.5  # Atualização mais frequente
                    
                    if process.stdout:  # Verifica se stdout não é None
                        for chunk in process.stdout:
                            f.write(chunk)
                            chunk_count += 1
                            total_bytes += len(chunk)
                            
                            # Atualiza progresso mais frequentemente
                            current_time = time.time()
                            if current_time - last_update >= update_interval:
                                progress.update(
                                    task, 
                                    completed=total_bytes,
                                    description=f"🚀 Transferindo sistema ({total_bytes // (1024*1024):.0f} MB)..."
                                )
                                last_update = current_time
            
            # Aguarda o processo e captura erros
            return_code = process.wait()
            if return_code != 0:
                # Captura stderr se disponível
                stderr_output = ""
                if process.stderr:
                    try:
                        stderr_output = process.stderr.read().decode('utf-8', errors='ignore').strip()
                    except:
                        stderr_output = "Não foi possível capturar o erro"
                
                # Mostra erro detalhado
                error_content = f"""[red]❌ Falha na coleta do sistema de arquivos[/red]

[yellow]🔍 Detalhes do Erro:[/yellow]
[white]   📡 Código de retorno: {return_code}[/white]
[white]   📝 Saída de erro: {stderr_output or 'Sem detalhes específicos'}[/white]

[cyan]🔧 Possíveis Causas:[/cyan]
[white]   • Conexão SSH instável ou interrompida[/white]
[white]   • Permissões insuficientes no servidor origem[/white]
[white]   • Falta de espaço no diretório temporário[/white]
[white]   • Problema com o comando tar no servidor remoto[/white]"""
                
                console.print()
                console.print(Panel(
                    error_content,
                    title="[bold red]❌ ERRO NA COLETA[/bold red]",
                    border_style="red",
                    padding=(1, 2)
                ))
                
                return False
                
            file_size = os.path.getsize(temp_file.name)
            if file_size == 0:
                display_error("BACKUP_FILE_EMPTY")
                return False
            
            elapsed_time = time.time() - start_time
            size_mb = file_size / (1024 * 1024)
            speed_mbps = size_mb / elapsed_time if elapsed_time > 0 else 0
            
            # Mostra resultado da transferência em painel elegante
            result_content = f"""[green]✅ Transferência concluída com sucesso![/green]

[cyan]📊 Estatísticas da Transferência:[/cyan]
[white]   📦 Tamanho: {size_mb:.1f} MB[/white]
[white]   ⏱️  Tempo: {elapsed_time:.1f}s[/white]
[white]   🚀 Velocidade média: {speed_mbps:.1f} MB/s[/white]
[white]   📁 Arquivo temporário criado[/white]"""
            
            console.print()
            console.print(Panel(
                result_content,
                title="[bold green]🎉 Coleta Finalizada[/bold green]",
                border_style="green",
                padding=(1, 2)
            ))
            
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
            
            # Interface moderna de criação do container
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(description="⚙️  Criando container LXC...", total=None)
                result = subprocess.run(create_command, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print()
                console.print("[bold green]✅ Container LXC criado com sucesso![/bold green]")
                
                # Interface moderna de inicialização
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task(description="🚀 Iniciando container...", total=None)
                    start_result = subprocess.run(["pct", "start", data["id"]], capture_output=True, text=True)
                
                if start_result.returncode == 0:
                    console.print()
                    console.print("[bold green]🚀 Container iniciado com sucesso![/bold green]")
                    
                    # Painel final elegante com informações do container
                    final_content = f"""[bold green]🎉 Migração Linux → Proxmox LXC concluída![/bold green]

[cyan]📋 Informações do Container:[/cyan]
[white]   🆔 ID: {data['id']}[/white]
[white]   🏷️  Nome: {data['name']}[/white]
[white]   🌐 IP: {data['ip']}[/white]
[white]   🧠 Memória: {data['memory']} MB[/white]
[white]   💿 Disco: {data['rootsize']} em {data['storage']}[/white]
[white]   🔗 Bridge: {data['bridge']}[/white]

[yellow]💡 Comandos Úteis:[/yellow]
[bright_white]   pct enter {data['id']}    [dim]# Entrar no container[/dim][/bright_white]
[bright_white]   pct stop {data['id']}     [dim]# Parar container[/dim][/bright_white]
[bright_white]   pct start {data['id']}    [dim]# Iniciar container[/dim][/bright_white]
[bright_white]   pct status {data['id']}   [dim]# Status do container[/dim][/bright_white]"""
                    
                    console.print()
                    console.print(Panel(
                        final_content,
                        title="[bold green]🏆 MIGRAÇÃO CONCLUÍDA[/bold green]",
                        border_style="green",
                        padding=(1, 2),
                        width=80
                    ))
                    
                else:
                    # Container criado mas falha ao iniciar
                    warning_content = f"""[yellow]⚠️  Container criado mas falha ao iniciar[/yellow]

[cyan]📋 Container Criado:[/cyan]
[white]   🆔 ID: {data['id']}[/white]
[white]   🏷️  Nome: {data['name']}[/white]
[white]   📦 Status: Criado mas parado[/white]

[yellow]💡 Para iniciar manualmente:[/yellow]
[bright_white]   pct start {data['id']}[/bright_white]

[dim]Erro de inicialização: {start_result.stderr.strip() if start_result.stderr else 'Desconhecido'}[/dim]"""
                    
                    console.print()
                    console.print(Panel(
                        warning_content,
                        title="[bold yellow]⚠️  CONTAINER CRIADO[/bold yellow]",
                        border_style="yellow",
                        padding=(1, 2)
                    ))
                
                return True
            else:
                error_msg = get_text("CONTAINER_CREATE_FAILED").format(result.stderr)
                console.print(Panel(f"❌ {error_msg}", title="❌ ERRO", style="red"))
                
                # Análise específica do erro
                if "no such logical volume" in result.stderr:
                    console.print(f"[yellow]🔍 Análise do erro:[/yellow]")
                    console.print(f"   • O storage {data['storage']} não tem espaço suficiente")
                    console.print(f"   • Tamanho solicitado: {data['rootsize']}")
                    console.print(f"   • Verifique o espaço disponível com: pvesm status")
                    
                    # Verifica espaço atual
                    has_space, space_msg = check_storage_space(data['storage'], data['rootsize'])
                    if not has_space:
                        console.print(f"[red]   • {space_msg}[/red]")
                    
                    console.print(f"[yellow]💡 Soluções:[/yellow]")
                    console.print(f"   • Escolha um storage com mais espaço")
                    console.print(f"   • Reduza o tamanho do disco (atualmente {data['rootsize']})")
                    console.print(f"   • Libere espaço no storage atual")
                    console.print(f"   • Use um storage diferente (ex: local-lvm, local)")
                
                elif "already exists" in result.stderr:
                    console.print(f"[yellow]🔍 Análise do erro:[/yellow]")
                    console.print(f"   • Container ID {data['id']} já existe")
                    console.print(f"[yellow]💡 Soluções:[/yellow]")
                    console.print(f"   • Escolha outro ID de container")
                    console.print(f"   • Remova o container existente: pct destroy {data['id']}")
                
                elif "permission denied" in result.stderr:
                    console.print(f"[yellow]🔍 Análise do erro:[/yellow]")
                    console.print(f"   • Problema de permissões no Proxmox")
                    console.print(f"[yellow]💡 Soluções:[/yellow]")
                    console.print(f"   • Execute como root: sudo lincon")
                    console.print(f"   • Verifique permissões do usuário no Proxmox")
                
                display_recommendation("CONTAINER_CREATE_REC")
                return False
                
        except subprocess.TimeoutExpired:
            error_content = """[red]❌ Timeout durante migração[/red]

[yellow]🔍 Possíveis Causas:[/yellow]
[white]   • Conexão SSH muito lenta ou instável[/white]
[white]   • Sistema de arquivos muito grande[/white]
[white]   • Servidor remoto sobrecarregado[/white]

[cyan]💡 Soluções:[/cyan]
[white]   • Verifique a conectividade de rede[/white]
[white]   • Tente novamente em um horário diferente[/white]
[white]   • Considere migrar diretórios específicos[/white]"""
            
            console.print()
            console.print(Panel(
                error_content,
                title="[bold red]⏰ TIMEOUT[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))
            return False
            
        except KeyboardInterrupt:
            console.print(f"\n[yellow]⚠️  Migração interrompida pelo usuário[/yellow]")
            return False
            
        except Exception as e:
            error_content = f"""[red]❌ Erro inesperado durante conversão[/red]

[yellow]🔍 Detalhes do Erro:[/yellow]
[white]   📝 Tipo: {type(e).__name__}[/white]
[white]   📄 Mensagem: {str(e)}[/white]

[cyan]💡 Ações Recomendadas:[/cyan]
[white]   • Verifique conectividade SSH[/white]
[white]   • Confirme permissões no servidor origem[/white]
[white]   • Tente executar novamente[/white]
[white]   • Consulte logs para mais detalhes[/white]"""
            
            console.print()
            console.print(Panel(
                error_content,
                title="[bold red]❌ ERRO INESPERADO[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))
            return False

def confirm_migration(data):
    """Confirma os detalhes da migração com o usuário"""
    console.clear()
    console.print(f"[bold cyan]{get_text('MIGRATION_CONFIRMATION')}[/bold cyan]\n")
    
    # Cria tabela moderna de detalhes
    table = Table(title=f"[bold green]{get_text('MIGRATION_DETAILS')}[/bold green]",
                 show_header=True, header_style="bold bright_white",
                 border_style="green", show_edge=False, padding=(0, 1))
    table.add_column(get_text("DETAIL_ITEM"), style="bright_cyan", width=20)
    table.add_column(get_text("DETAIL_VALUE"), style="bright_white")
    
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
    
    console.print()
    console.print(table)
    console.print()
    
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
    
    # Mostra as migrações incompletas com interface moderna
    table = Table(title="[bold yellow]Migrações Pendentes[/bold yellow]",
                 show_header=True, header_style="bold bright_white",
                 border_style="yellow", show_edge=False)
    table.add_column("ID", justify="right", style="bright_cyan", width=12)
    table.add_column("Data", style="bright_magenta", width=16)
    table.add_column("Container", style="bright_green", width=15)
    table.add_column("Status", style="bright_yellow")
    
    for m in incomplete:
        date = datetime.fromisoformat(m['timestamp']).strftime('%d/%m/%Y %H:%M')
        # Verifica se data existe e não é None
        data = m.get('data', {})
        container = data.get('name', 'Unknown') if data else 'Unknown'
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
