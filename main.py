from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import track
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner

from lang.translations import translations
from utils.system_info import get_system_info, get_system_status, get_lincon_version
from utils.logger import setup_logging
from utils.exceptions import *

# Configuração inicial
console = Console()
logger = setup_logging()

LINCON_BANNER = """
 [bold bright_cyan]██╗     ██╗███╗   ██╗ ██████╗ ██████╗ ███╗   ██╗
 ██║     ██║████╗  ██║██╔════╝██╔═══██╗████╗  ██║
 ██║     ██║██╔██╗ ██║██║     ██║   ██║██╔██╗ ██║
 ██║     ██║██║╚██╗██║██║     ██║   ██║██║╚██╗██║
 ███████╗██║██║ ╚████║╚██████╗╚██████╔╝██║ ╚████║
 ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝[/bold bright_cyan]
                          [bold bright_green]</> [/bold bright_green][bold bright_magenta]Linux Containerized[/bold bright_magenta] 

    [orange]Github: https://github.com/mathewalves[/orange]
"""

def select_language():
    console.print(Panel("🌎 Language / Idioma", style="bold blue"))
    table = Table(show_header=False, box=None)
    table.add_row("[1] Português (Brasil)")
    table.add_row("[2] English")
    console.print(table)
    
    choice = Prompt.ask("", choices=["1", "2"], default="1")
    return "pt-br" if choice == "1" else "en"

def show_menu(language):
    while True:
        console.clear()
        # Mostra a arte ASCII do LINCON e informações
        console.print(LINCON_BANNER)
        
        # Exibe informações de sistema
        sys_info = get_system_info()
        sys_status = get_system_status()
        version = get_lincon_version()
        
        system_table = Table(show_header=False, box=None)
        system_table.add_row("[bright_cyan]ℹ System Information:[/bright_cyan]")
        system_table.add_row(f"[bright_black]→[/bright_black] OS: {sys_info['os']} {sys_info['release']}")
        system_table.add_row(f"[bright_black]→[/bright_black] Python: {sys_info['python_version']}")
        system_table.add_row(f"[bright_black]→[/bright_black] LINCON: {version}")
        system_table.add_row("")
        
        status_table = Table(show_header=False, box=None)
        status_table.add_row("[bright_cyan]✓ Components Status:[/bright_cyan]")
        docker_status = "[green]Available[/green]" if sys_status["docker"] else "[red]Not Available[/red]"
        proxmox_status = "[green]Available[/green]" if sys_status["proxmox"] else "[red]Not Available[/red]"
        status_table.add_row(f"[bright_black]→[/bright_black] Docker: {docker_status}")
        status_table.add_row(f"[bright_black]→[/bright_black] Proxmox: {proxmox_status}")
        status_table.add_row("")
        
        console.print(system_table)
        console.print(status_table)
        
        # Mostra o menu principal
        table = Table(show_header=False, box=None)
        table.add_row("[1] " + translations[language]["MENU_LINUX_DOCKER"])
        table.add_row("[2] " + translations[language]["MENU_LINUX_PROXMOX"])
        table.add_row("[3] " + translations[language]["MENU_EXIT"])
        
        console.print(Panel(
            table,
            title=translations[language]["TITLE_WELCOME"],
            subtitle=translations[language]["MSG_WELCOME"],
            style="bold green"
        ))
        
        choice = Prompt.ask("", choices=["1", "2", "3"])
        
        if choice == "3":
            console.print(translations[language]["goodbye"], style="bold yellow")
            break
        elif choice == "1":
            from migrate_docker import migrate_docker
            migrate_docker()
            input("\nPressione Enter para continuar...")
        elif choice == "2":
            from migrate_lxc import migrate_lxc
            migrate_lxc()
            input("\nPressione Enter para continuar...")

def main():
    language = select_language()
    show_menu(language)

if __name__ == "__main__":
    main()