#!/bin/bash

# LINCON - Script de Correção Pós-Migração
# Corrige problemas comuns após migração de containers

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔧 LINCON - Correção Pós-Migração${NC}"
echo

# Verifica se está sendo executado dentro de um container
if [ ! -f /.dockerenv ] && [ ! -f /proc/1/cgroup ] || grep -q "lxc" /proc/1/cgroup 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Este script deve ser executado dentro do container migrado${NC}"
    echo -e "${CYAN}💡 Use: pct enter <container_id>${NC}"
    exit 1
fi

echo -e "${CYAN}🔍 Verificando problemas comuns...${NC}"

# 1. Corrige diretórios de log ausentes
echo -e "${CYAN}📁 Criando diretórios de log necessários...${NC}"

# Lista de diretórios de log comuns
log_dirs=(
    "/var/log/apache2"
    "/var/log/nginx"
    "/var/log/mysql"
    "/var/log/postgresql"
    "/var/log/php"
    "/var/log/php-fpm"
    "/var/log/lighttpd"
    "/var/log/haproxy"
    "/var/log/squid"
    "/var/log/bind"
    "/var/log/dhcp"
    "/var/log/dnsmasq"
    "/var/log/rsyslog"
    "/var/log/systemd"
    "/var/log/journal"
    "/var/log/audit"
    "/var/log/secure"
    "/var/log/messages"
    "/var/log/kern.log"
    "/var/log/auth.log"
    "/var/log/syslog"
    "/var/log/user.log"
    "/var/log/debug"
    "/var/log/daemon.log"
    "/var/log/mail.log"
    "/var/log/cron"
    "/var/log/faillog"
    "/var/log/btmp"
    "/var/log/lastlog"
    "/var/log/wtmp"
    "/var/log/utmp"
)

# Cria diretórios de log
for dir in "${log_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        chmod 755 "$dir"
        echo -e "${GREEN}✅ Criado: $dir${NC}"
    fi
done

# 2. Corrige permissões de arquivos importantes
echo -e "${CYAN}🔐 Corrigindo permissões...${NC}"

# Corrige permissões de diretórios importantes
chmod 755 /var/log 2>/dev/null || true
chmod 755 /var/run 2>/dev/null || true
chmod 755 /var/spool 2>/dev/null || true
chmod 755 /var/cache 2>/dev/null || true

# Corrige permissões de arquivos de log
find /var/log -type f -name "*.log" -exec chmod 644 {} \; 2>/dev/null || true
find /var/log -type d -exec chmod 755 {} \; 2>/dev/null || true

# 3. Recria arquivos de sistema importantes
echo -e "${CYAN}📄 Recriando arquivos de sistema...${NC}"

# /etc/hosts se não existir
if [ ! -f /etc/hosts ]; then
    cat > /etc/hosts << EOF
127.0.0.1 localhost
::1 localhost ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF
    echo -e "${GREEN}✅ Recriado: /etc/hosts${NC}"
fi

# /etc/resolv.conf se não existir
if [ ! -f /etc/resolv.conf ]; then
    cat > /etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
    echo -e "${GREEN}✅ Recriado: /etc/resolv.conf${NC}"
fi

# 4. Corrige configurações de Apache
echo -e "${CYAN}🌐 Corrigindo configurações do Apache...${NC}"

if command -v apache2 >/dev/null 2>&1; then
    # Cria diretório de logs do Apache se não existir
    mkdir -p /var/log/apache2 2>/dev/null || true
    chmod 755 /var/log/apache2 2>/dev/null || true
    
    # Corrige configuração do Apache
    if [ -f /etc/apache2/apache2.conf ]; then
        # Adiciona configuração de logs se não existir
        if ! grep -q "ErrorLog" /etc/apache2/apache2.conf; then
            echo "ErrorLog \${APACHE_LOG_DIR}/error.log" >> /etc/apache2/apache2.conf
            echo "CustomLog \${APACHE_LOG_DIR}/access.log combined" >> /etc/apache2/apache2.conf
        fi
    fi
    
    # Cria arquivo de log do Apache se não existir
    touch /var/log/apache2/error.log 2>/dev/null || true
    touch /var/log/apache2/access.log 2>/dev/null || true
    chmod 644 /var/log/apache2/*.log 2>/dev/null || true
    
    echo -e "${GREEN}✅ Configurações do Apache corrigidas${NC}"
fi

# 5. Corrige configurações de MySQL/MariaDB
echo -e "${CYAN}🗄️  Corrigindo configurações do MySQL/MariaDB...${NC}"

if command -v mysql >/dev/null 2>&1 || command -v mariadb >/dev/null 2>&1; then
    # Cria diretório de logs do MySQL se não existir
    mkdir -p /var/log/mysql 2>/dev/null || true
    chmod 755 /var/log/mysql 2>/dev/null || true
    
    # Cria arquivo de log do MySQL se não existir
    touch /var/log/mysql/error.log 2>/dev/null || true
    chmod 644 /var/log/mysql/*.log 2>/dev/null || true
    
    echo -e "${GREEN}✅ Configurações do MySQL/MariaDB corrigidas${NC}"
fi

# 6. Corrige configurações de Nginx
echo -e "${CYAN}🌐 Corrigindo configurações do Nginx...${NC}"

if command -v nginx >/dev/null 2>&1; then
    # Cria diretório de logs do Nginx se não existir
    mkdir -p /var/log/nginx 2>/dev/null || true
    chmod 755 /var/log/nginx 2>/dev/null || true
    
    # Cria arquivo de log do Nginx se não existir
    touch /var/log/nginx/error.log 2>/dev/null || true
    touch /var/log/nginx/access.log 2>/dev/null || true
    chmod 644 /var/log/nginx/*.log 2>/dev/null || true
    
    echo -e "${GREEN}✅ Configurações do Nginx corrigidas${NC}"
fi

# 7. Corrige configurações de SSH
echo -e "${CYAN}🔐 Corrigindo configurações do SSH...${NC}"

if command -v sshd >/dev/null 2>&1; then
    # Cria diretório de logs do SSH se não existir
    mkdir -p /var/log/ssh 2>/dev/null || true
    chmod 755 /var/log/ssh 2>/dev/null || true
    
    # Cria arquivo de log do SSH se não existir
    touch /var/log/ssh/auth.log 2>/dev/null || true
    chmod 644 /var/log/ssh/*.log 2>/dev/null || true
    
    echo -e "${GREEN}✅ Configurações do SSH corrigidas${NC}"
fi

# 8. Recria diretórios temporários
echo -e "${CYAN}📁 Recriando diretórios temporários...${NC}"

temp_dirs=(
    "/tmp"
    "/var/tmp"
    "/var/run"
    "/var/spool"
    "/var/cache"
)

for dir in "${temp_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        chmod 1777 "$dir"
        echo -e "${GREEN}✅ Criado: $dir${NC}"
    fi
done

# 9. Corrige configurações de timezone
echo -e "${CYAN}🕐 Corrigindo configurações de timezone...${NC}"

if [ ! -f /etc/timezone ]; then
    echo "UTC" > /etc/timezone
    echo -e "${GREEN}✅ Configurado timezone: UTC${NC}"
fi

# 10. Corrige configurações de locale
echo -e "${CYAN}🌍 Corrigindo configurações de locale...${NC}"

if [ ! -f /etc/default/locale ]; then
    cat > /etc/default/locale << EOF
LANG=en_US.UTF-8
LC_ALL=en_US.UTF-8
EOF
    echo -e "${GREEN}✅ Configurado locale: en_US.UTF-8${NC}"
fi

# 11. Reinicia serviços críticos
echo -e "${CYAN}🔄 Reiniciando serviços críticos...${NC}"

# Reinicia systemd se disponível
if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload 2>/dev/null || true
    echo -e "${GREEN}✅ systemd daemon reloaded${NC}"
fi

# Reinicia rsyslog se disponível
if command -v rsyslogd >/dev/null 2>&1; then
    systemctl restart rsyslog 2>/dev/null || true
    echo -e "${GREEN}✅ rsyslog reiniciado${NC}"
fi

echo
echo -e "${GREEN}✅ Correção pós-migração concluída!${NC}"
echo -e "${CYAN}💡 Agora você pode tentar iniciar seus serviços novamente${NC}"
echo -e "${YELLOW}⚠️  Se ainda houver problemas, verifique os logs específicos do serviço${NC}" 