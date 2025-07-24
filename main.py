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

import os

# Configuração inicial
console = Console()
logger = setup_logging()

current_language = os.environ.get("LINCON_LANG", "pt-br")

def get_text(key):
    return translations[current_language].get(key, key)

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
    console.print()
    
    # Interface moderna para seleção de idioma
    lang_options = Table(show_header=False, show_edge=False, pad_edge=False, box=None)
    lang_options.add_column(style="dim", width=3)
    lang_options.add_column(style="bright_cyan", width=20)
    lang_options.add_column(style="dim")
    
    lang_options.add_row("1", "Português (Brasil)", "🇧🇷")
    lang_options.add_row("2", "English", "🇺🇸")
    
    console.print(Panel(
        lang_options,
        title="🌎 Language / Idioma",
        border_style="cyan",
        padding=(1, 2)
    ))
    
    choice = Prompt.ask("[bright_cyan]" + get_text("select_language") + "[/bright_cyan]", choices=["1", "2"], default="1")
    return "pt-br" if choice == "1" else "en"

def show_menu(language):
    global current_language
    current_language = language
    while True:
        console.clear()
        # Mostra a arte ASCII do LINCON e informações
        console.print(LINCON_BANNER)
        
        # Exibe informações de sistema
        sys_info = get_system_info()
        sys_status = get_system_status()
        version = get_lincon_version()
        
        system_table = Table(show_header=False, box=None)
        system_table.add_row("[bright_cyan]ℹ " + get_text("system_info") + ":[/bright_cyan]")
        system_table.add_row(f"[bright_black]→[/bright_black] OS: {sys_info['os']} {sys_info['release']}")
        system_table.add_row(f"[bright_black]→[/bright_black] Python: {sys_info['python_version']}")
        system_table.add_row(f"[bright_black]→[/bright_black] LINCON: {version}")
        system_table.add_row("")
        
        status_table = Table(show_header=False, box=None)
        status_table.add_row("[bright_cyan]✓ " + get_text("components_status") + ":[/bright_cyan]")
        docker_status = "[green]" + get_text("available") + "[/green]" if sys_status["docker"] else "[red]" + get_text("not_available") + "[/red]"
        proxmox_status = "[green]" + get_text("available") + "[/green]" if sys_status["proxmox"] else "[red]" + get_text("not_available") + "[/red]"
        status_table.add_row(f"[bright_black]→[/bright_black] Docker: {docker_status}")
        status_table.add_row(f"[bright_black]→[/bright_black] Proxmox: {proxmox_status}")
        status_table.add_row("")
        
        console.print(system_table)
        console.print(status_table)
        
        # Menu principal moderno
        menu_table = Table(show_header=False, show_edge=False, pad_edge=False, box=None)
        menu_table.add_column(style="bright_cyan", width=3)
        menu_table.add_column(style="bright_white", width=25)
        menu_table.add_column(style="dim")
        
        menu_table.add_row("1", get_text("MENU_LINUX_DOCKER"), "🐳")
        menu_table.add_row("2", get_text("MENU_LINUX_PROXMOX"), "📦")
        menu_table.add_row("3", get_text("MENU_EXIT"), "👋")
        
        console.print(Panel(
            menu_table,
            title=f"[bold bright_green]{get_text('TITLE_WELCOME')}[/bold bright_green]",
            subtitle=f"[dim]{get_text('MSG_WELCOME')}[/dim]",
            border_style="bright_green",
            padding=(1, 2)
        ))
        
        choice = Prompt.ask("[bright_cyan]" + get_text("select_option") + "[/bright_cyan]", choices=["1", "2", "3"])
        
        if choice == "3":
            console.print(get_text("goodbye"), style="bold yellow")
            break
        elif choice == "1":
            from migrate_docker import migrate_docker
            migrate_docker()
            input("\n" + get_text("press_enter_to_continue"))
        elif choice == "2":
            from migrate_lxc import migrate_lxc
            migrate_lxc()
            input("\n" + get_text("press_enter_to_continue"))

def main():
    language = select_language()
    os.environ["LINCON_LANG"] = language  # <-- Adiciona esta linha
    show_menu(language)

if __name__ == "__main__":
    main()