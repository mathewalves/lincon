#!/bin/bash

# LINCON - Instalador Simplificado
set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/lincon"
BIN_PATH="/usr/local/bin/lincon"

echo -e "${CYAN}🐳 LINCON - Linux Containerized Installer${NC}"
echo

# Verifica root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Execute como root${NC}"
    echo -e "${YELLOW}💡 Use: sudo $0${NC}"
    exit 1
fi

# Verifica instalação existente
if [ -d "$INSTALL_DIR" ] || [ -f "$BIN_PATH" ]; then
    echo -e "${YELLOW}⚠️  LINCON já está instalado${NC}"
    read -p "🔄 Reinstalar? (s/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${CYAN}✅ Mantendo instalação atual${NC}"
        echo -e "${GREEN}💻 Para usar: lincon${NC}"
        exit 0
    fi
    echo -e "${YELLOW}🗑️  Removendo instalação anterior...${NC}"
    rm -rf "$INSTALL_DIR" "$BIN_PATH"
fi

# Instala dependências
echo -e "${CYAN}📦 Instalando dependências...${NC}"
apt-get update > /dev/null 2>&1
apt-get install -y python3-pip git sshpass curl > /dev/null 2>&1

# Instala Python Rich
echo -e "${CYAN}🐍 Instalando Python Rich...${NC}"
pip3 install rich --break-system-packages > /dev/null 2>&1 || pip3 install rich > /dev/null 2>&1

# Clona repositório
echo -e "${CYAN}📥 Baixando LINCON...${NC}"
git clone https://github.com/mathewalves/lincon.git "$INSTALL_DIR" > /dev/null 2>&1

# Cria comando
echo -e "${CYAN}⚙️  Configurando comando...${NC}"
cat > "$BIN_PATH" << 'EOF'
#!/bin/bash
cd /opt/lincon && python3 main.py "$@"
EOF
chmod +x "$BIN_PATH"
chmod +x "$INSTALL_DIR/main.py"

# Verifica instalação
if [ -x "$BIN_PATH" ] && [ -f "$INSTALL_DIR/main.py" ]; then
    echo
    echo -e "${GREEN}✅ Instalação concluída!${NC}"
    echo -e "${CYAN}💻 Para usar: ${YELLOW}lincon${NC}"
    echo
    
    read -p "🚀 Executar agora? (s/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        "$BIN_PATH"
    fi
else
    echo -e "${RED}❌ Erro na instalação${NC}"
    exit 1
fi
