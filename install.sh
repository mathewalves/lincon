#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== LINCON - Linux Containerized Installer ===${NC}\n"

# Verifica se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Este script precisa ser executado como root (sudo)${NC}"
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

# Verifica e instala o Python se necessário
if ! check_command python3; then
    apt-get update
    apt-get install -y python3 python3-pip
fi

# Verifica e instala o git se necessário
if ! check_command git; then
    apt-get update
    apt-get install -y git
fi

# Verifica e instala o sshpass se necessário
if ! check_command sshpass; then
    apt-get update
    apt-get install -y sshpass
fi

# Cria diretório temporário
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR" || exit 1

echo -e "${GREEN}Clonando repositório LINCON...${NC}"
git clone https://github.com/mathewalves/lincon.git
cd lincon || exit 1

# Instala as dependências Python
echo -e "${GREEN}Instalando dependências Python...${NC}"
pip3 install -e .

# Cria link simbólico para o comando lincon
echo -e "${GREEN}Configurando comando 'lincon'...${NC}"
ln -sf "$(pwd)/main.py" /usr/local/bin/lincon
chmod +x /usr/local/bin/lincon

# Limpa arquivos temporários
cd / && rm -rf "$TEMP_DIR"

echo -e "\n${GREEN}Instalação concluída!${NC}"
echo -e "${YELLOW}Para usar o LINCON, simplesmente digite: ${NC}lincon"

# Pergunta se quer executar agora
read -p "Deseja executar o LINCON agora? (s/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${GREEN}Iniciando LINCON...${NC}"
    lincon
fi
