#!/bin/bash

# LINCON - Desinstalador Simples
set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/lincon"
BIN_PATH="/usr/local/bin/lincon"

echo -e "${CYAN}🗑️  LINCON - Desinstalador${NC}"
echo

# Verifica root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Execute como root${NC}"
    echo -e "${YELLOW}💡 Use: sudo $0${NC}"
    exit 1
fi

# Verifica se está instalado
if [ ! -d "$INSTALL_DIR" ] && [ ! -f "$BIN_PATH" ]; then
    echo -e "${YELLOW}⚠️  LINCON não está instalado${NC}"
    exit 0
fi

# Confirma desinstalação
echo -e "${YELLOW}📍 LINCON encontrado em:${NC}"
[ -d "$INSTALL_DIR" ] && echo -e "   📁 $INSTALL_DIR"
[ -f "$BIN_PATH" ] && echo -e "   🔗 $BIN_PATH"
echo

read -p "❓ Confirma desinstalação? (s/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${CYAN}✅ Desinstalação cancelada${NC}"
    exit 0
fi

# Remove arquivos
echo -e "${CYAN}🗑️  Removendo LINCON...${NC}"
rm -rf "$INSTALL_DIR" 2>/dev/null
rm -f "$BIN_PATH" 2>/dev/null

# Pergunta sobre Rich
read -p "📦 Remover Python Rich também? (s/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${CYAN}🐍 Removendo Python Rich...${NC}"
    pip3 uninstall rich -y > /dev/null 2>&1 || true
fi

echo
echo -e "${GREEN}✅ LINCON removido com sucesso!${NC}" 