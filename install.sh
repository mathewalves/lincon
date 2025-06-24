#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${GREEN}=== LINCON - Linux Containerized Installer ===${NC}\n"

# Verifica se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Este script precisa ser executado como root${NC}"
    echo -e "${YELLOW}Use um dos comandos abaixo:${NC}"
    echo -e "${WHITE}  # Com sudo (Ubuntu/sistemas com sudo):${NC}"
    echo -e "${CYAN}  curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | sudo bash${NC}"
    echo -e "${WHITE}  # Como root (Debian/Proxmox):${NC}"
    echo -e "${CYAN}  su -c \"curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | bash\"${NC}"
    exit 1
fi

# Função para verificar se um comando existe
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${YELLOW}Instalando $1...${NC}"
        return 1
    fi
    return 0
}

# Função para instalar pacotes (detecta se sudo está disponível)
install_package() {
    if command -v sudo &> /dev/null && [ "$EUID" -ne 0 ]; then
        sudo apt-get install -y "$@"
    else
        apt-get install -y "$@"
    fi
}

# Função para atualizar repositórios
update_repos() {
    if command -v sudo &> /dev/null && [ "$EUID" -ne 0 ]; then
        sudo apt-get update
    else
        apt-get update
    fi
}

# Verifica se curl está instalado
if ! check_command curl; then
    update_repos
    install_package curl
fi

# Verifica e instala o Python e ferramentas necessárias
if ! check_command python3; then
    update_repos
    install_package python3 python3-pip python3-venv
else
    # Garante que python3-venv e python3-pip estão instalados
    update_repos
    install_package python3-pip python3-venv
fi

# Verifica e instala o git se necessário
if ! check_command git; then
    update_repos
    install_package git
fi

# Verifica e instala o sshpass se necessário
if ! check_command sshpass; then
    update_repos
    install_package sshpass
fi

# Cria diretório de instalação
INSTALL_DIR="/opt/lincon"
echo -e "${GREEN}Criando diretório de instalação...${NC}"
mkdir -p "$INSTALL_DIR"

# Clona o repositório diretamente no diretório de instalação
echo -e "${GREEN}Clonando repositório LINCON...${NC}"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}Atualizando repositório existente...${NC}"
    cd "$INSTALL_DIR" && git pull
else
    git clone https://github.com/mathewalves/lincon.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR" || exit 1

# Instala apenas as dependências Python (sem o pacote em modo desenvolvimento)
echo -e "${GREEN}Instalando dependências Python...${NC}"

# Instala apenas o rich diretamente
if pip3 install rich &>/dev/null; then
    echo -e "${GREEN}Dependências instaladas com sucesso${NC}"
else
    echo -e "${YELLOW}Ambiente Python gerenciado externamente detectado. Usando método alternativo...${NC}"
    if pip3 install rich --break-system-packages; then
        echo -e "${GREEN}Dependências instaladas com sucesso${NC}"
    else
        echo -e "${RED}Falha ao instalar dependências Python${NC}"
        exit 1
    fi
fi

# Cria script executável
echo -e "${GREEN}Configurando comando 'lincon'...${NC}"
cat > /usr/local/bin/lincon << 'EOF'
#!/bin/bash
cd /opt/lincon
python3 main.py "$@"
EOF

chmod +x /usr/local/bin/lincon

# Torna o main.py executável
chmod +x "$INSTALL_DIR/main.py"

echo -e "\n${GREEN}Instalação concluída!${NC}"
echo -e "${YELLOW}Localização: ${NC}$INSTALL_DIR"
echo -e "${YELLOW}Para usar o LINCON, simplesmente digite: ${NC}${CYAN}lincon${NC}"

# Pergunta se quer executar agora
read -p "Deseja executar o LINCON agora? (s/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${GREEN}Iniciando LINCON...${NC}"
    lincon
fi
