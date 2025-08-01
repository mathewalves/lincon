#!/bin/bash

# Verifica se o comando 'pct' está disponível na máquina host (Proxmox)
if ! command -v pct &> /dev/null
then
    echo "❌ Erro: Comando 'pct' não encontrado. Este script deve ser executado na máquina host Proxmox."
    exit 1
fi

# Analisa as opções da linha de comando
options=$(getopt -o n:t:P:i:s:a:b:g:m:d:p:w:h -l help,name:,target:,port:,id:,root-size:,ip:,bridge:,gateway:,memory:,disk-storage:,password:,ssh-password: -- "$@")
if [ $? -ne 0 ]; then
    usage
    exit 1
fi
eval set -- "$options"

# Processa as opções da linha de comando
while true
do
    case "$1" in
        -h|--help)          usage && exit 0;;
        -n|--name)          name=$2; shift 2;;
        -t|--target)        target=$2; shift 2;;
        -P|--port)          port=$2; shift 2;;
        -i|--id)            id=$2; shift 2;;
        -s|--root-size)     rootsize=$2; shift 2;;
        -a|--ip)            ip=$2; shift 2;;
        -b|--bridge)        bridge=$2; shift 2;;
        -g|--gateway)       gateway=$2; shift 2;;
        -m|--memory)        memory=$2; shift 2;;
        -p|--password)      password=$2; shift 2;;
        -d|--disk-storage)  storage=$2; shift 2;;
        -w|--ssh-password)  ssh_password=$2; shift 2;;
        --)                 shift; break ;;
        *)                  break ;;
    esac
done

# Valida se todos os parâmetros obrigatórios foram fornecidos
if [ -z "$name" ] || [ -z "$target" ] || [ -z "$port" ] || [ -z "$id" ] || [ -z "$rootsize" ] || [ -z "$ip" ] || [ -z "$memory" ] || [ -z "$storage" ] || [ -z "$password" ] || [ -z "$ssh_password" ]; then
    echo "❌ Erro: Faltando parâmetros obrigatórios."
    usage
    exit 1
fi

# Define a função para coletar o sistema de arquivos, com todas as correções
collectFS() {
    tar -czvf - -C / \
    --mtime='1970-01-01' \
    --exclude="./boot" \
    --exclude="./lib/modules" \
    --exclude="./sys" \
    --exclude="./dev" \
    --exclude="./run" \
    --exclude="./proc" \
    --exclude="*.log" \
    --exclude="*.log.*" \
    --exclude="*.gz" \
    --exclude="*.sql" \
    --exclude="./swap.img" \
    --exclude="./tmp" \
    --exclude="./var/tmp" \
    --exclude="./var/lib/docker" \
    --exclude="./var/lib/containers" \
    --exclude="./var/cache" \
    --exclude="./var/log/*.log" \
    --exclude="./var/log/*.log.*" \
    --exclude="./var/log/apt" \
    --exclude="./var/log/btmp" \
    --exclude="./var/log/faillog" \
    --exclude="./var/log/lastlog" \
    --exclude="./var/log/wtmp" \
    --exclude="./var/log/alternatives.log" \
    --exclude="./var/log/bootstrap.log" \
    --exclude="./var/log/dpkg.log" \
    --exclude="./var/log/fontconfig.log" \
    --exclude="./var/log/fsck" \
    --exclude="./var/log/installer" \
    --exclude="./var/log/landscape" \
    --exclude="./var/log/lightdm" \
    --exclude="./var/log/upstart" \
    --exclude="./var/log/unattended-upgrades" \
    --exclude="./var/log/upstart" \
    --exclude="./var/log/upstart" \
    --exclude="./var/backups" \
    --exclude="./mnt" \
    --exclude="./media" \
    --exclude="./var/lib/dpkg/info" \
    --exclude="./var/lib/apt" \
    --exclude="./var/lib/dpkg" \
    --exclude="./var/cache/apt" \
    --exclude="./var/cache/debconf" \
    --exclude="./var/lib/systemd" \
    --exclude="./var/lib/NetworkManager" \
    --exclude="./var/lib/upower" \
    --exclude="./var/lib/udisks2" \
    --exclude="./var/lib/polkit-1" \
    --exclude="./var/lib/colord" \
    --exclude="./var/lib/AccountsService" \
    --exclude="./var/lib/gdm3" \
    --exclude="./var/lib/lightdm" \
    --exclude="./var/lib/sddm" \
    --exclude="./var/lib/plymouth" \
    --exclude="./var/lib/update-notifier" \
    --exclude="./var/lib/ubuntu-release-upgrader" \
    --exclude="./var/lib/ubuntu-drivers-common" \
    --exclude="./var/lib/snapd" \
    --exclude="./var/lib/flatpak" \
    --exclude="./var/lib/app-info" \
    --exclude="./var/lib/dbus" \
    --exclude="./var/lib/aspell" \
    --exclude="./var/lib/dictionaries-common" \
    --exclude="./var/lib/wordlists" \
    --exclude="./var/lib/mlocate" \
    --exclude="./var/lib/alternatives" \
    --exclude="./var/lib/menu" \
    --exclude="./var/lib/update-rc.d" \
    --exclude="./var/lib/dpkg/alternatives" \
    --exclude="./var/lib/dpkg/info" \
    --exclude="./var/lib/dpkg/triggers" \
    --exclude="./var/lib/dpkg/updates" \
    --exclude="./var/lib/dpkg/parts" \
    --exclude="./var/lib/dpkg/status-old" \
    --exclude="./var/lib/dpkg/status" \
    --exclude="./var/lib/dpkg/available" \
    --exclude="./var/lib/dpkg/available-old" \
    --exclude="./var/lib/dpkg/lock" \
    --exclude="./var/lib/dpkg/lock-frontend" \
    --exclude="./var/lib/dpkg/lock-frontend" \
    --exclude="./var/lib/dpkg/triggers" \
    --exclude="./var/lib/dpkg/triggers/Unincorp" \
    --exclude="./var/lib/dpkg/triggers/File" \
    --exclude="./var/lib/dpkg/triggers/NoPath" \
    --exclude="./var/lib/dpkg/triggers/Path" \
    --exclude="./var/lib/dpkg/triggers/Interest" \
    --exclude="./var/lib/dpkg/triggers/Interest-NoWait" \
    --exclude="./var/lib/dpkg/triggers/Interest-Await" \
    --exclude="./var/lib/dpkg/triggers/Processed" \
    --exclude="./var/lib/dpkg/triggers/Unincorp" \
    --exclude="./var/lib/dpkg/triggers/File" \
    --exclude="./var/lib/dpkg/triggers/NoPath" \
    --exclude="./var/lib/dpkg/triggers/Path" \
    --exclude="./var/lib/dpkg/triggers/Interest" \
    --exclude="./var/lib/dpkg/triggers/Interest-NoWait" \
    --exclude="./var/lib/dpkg/triggers/Interest-Await" \
    --exclude="./var/lib/dpkg/triggers/Processed" \
    .
}

# Função para calcular o tamanho necessário do disco
calculate_disk_size() {
    local tar_file="$1"
    local current_size="$2"
    
    # Obtém o tamanho do arquivo tar.gz em bytes
    local tar_size=$(stat -c%s "$tar_file" 2>/dev/null || echo "0")
    
    # Estimativa: arquivo tar.gz descompactado geralmente é 3-5x maior
    # Usamos um fator conservador de 4x para garantir espaço suficiente
    local estimated_uncompressed=$((tar_size * 4))
    
    # Converte para GB (1GB = 1073741824 bytes)
    local estimated_gb=$((estimated_uncompressed / 1073741824))
    
    # Adiciona 20% de margem de segurança
    local recommended_gb=$((estimated_gb + (estimated_gb / 5)))
    
    # Mínimo de 2GB
    if [ "$recommended_gb" -lt 2 ]; then
        recommended_gb=2
    fi
    
    # Máximo de 100GB (limite de segurança)
    if [ "$recommended_gb" -gt 100 ]; then
        recommended_gb=100
    fi
    
    echo "$recommended_gb"
}

# Função para converter tamanho para formato adequado
format_size() {
    local size="$1"
    if [ "$size" -ge 1024 ]; then
        echo "${size}G"
    else
        echo "${size}M"
    fi
}

# adicionar bloco de traduções no início do script
# detectar idioma
LANG_CODE="${LINCON_LANG:-${LANG:0:2}}"
if [ "$LANG_CODE" = "en" ]; then
  MSG_START_MIGRATION="Starting container migration..."
  MSG_COLLECT_FS="Collecting filesystem from"
  MSG_FS_COLLECTED="Filesystem collected successfully."
  MSG_CREATING_CT="Creating container"
  MSG_CONTAINER_CREATED="Container created successfully!"
  MSG_STARTING_CT="Starting container"
  MSG_MIGRATION_COMPLETED="Migration process completed!"
  MSG_CLEANING_UP="Cleaning up temporary files..."
  MSG_ERROR_MISSING_PARAMS="Error: Missing required parameters."
  MSG_ERROR_COLLECT_FS="❌ Failed to collect filesystem from target machine."
  MSG_ERROR_CREATE_CT="❌ Failed to create container."
  MSG_ERROR_TIMEOUT_CT="❌ Timeout: The container was not created in time. Check Proxmox task logs for details."
  MSG_ERROR_AT="❌ Failed to schedule the container creation task with 'at'. Check if the 'atd' service is installed and running."
  MSG_CONTAINER_STARTED="Container started successfully!"
  MSG_CONTAINER_START_FAILED="⚠️  The container was created but failed to start. Try manually: pct start"
  MSG_ANALYZING_SIZE="Analyzing filesystem size..."
  MSG_COLLECTED_SIZE="Collected file size:"
  MSG_ORIGINAL_SIZE="Original configured size:"
  MSG_RECOMMENDED_SIZE="Recommended size:"
  MSG_SIZE_WARNING="Warning: The configured size may be insufficient."
  MSG_SIZE_ADJUSTING="Automatically adjusting to avoid space errors..."
  MSG_SIZE_OK="Configured size is adequate."
else
  MSG_START_MIGRATION="Iniciando o processo de migração..."
  MSG_COLLECT_FS="Coletando sistema de arquivos de"
  MSG_FS_COLLECTED="Sistema de arquivos coletado com sucesso."
  MSG_CREATING_CT="Preparando para criar o container"
  MSG_CONTAINER_CREATED="Contêiner criado com sucesso!"
  MSG_STARTING_CT="Iniciando o contêiner"
  MSG_MIGRATION_COMPLETED="Processo de migração finalizado!"
  MSG_CLEANING_UP="Limpando arquivos temporários..."
  MSG_ERROR_MISSING_PARAMS="❌ Erro: Faltando parâmetros obrigatórios."
  MSG_ERROR_COLLECT_FS="❌ Falha ao coletar o sistema de arquivos da máquina de origem."
  MSG_ERROR_CREATE_CT="❌ Falha ao criar o contêiner."
  MSG_ERROR_TIMEOUT_CT="❌ Timeout: O contêiner não foi criado a tempo. Verifique os logs de tarefas no Proxmox para detalhes."
  MSG_ERROR_AT="❌ Falha ao agendar a tarefa de criação do contêiner com 'at'. Verifique se o serviço 'atd' está instalado e em execução."
  MSG_CONTAINER_STARTED="Contêiner iniciado com sucesso!"
  MSG_CONTAINER_START_FAILED="⚠️  O contêiner foi criado mas falhou ao iniciar. Tente manualmente: pct start"
  MSG_ANALYZING_SIZE="Analisando tamanho do sistema de arquivos..."
  MSG_COLLECTED_SIZE="Tamanho do arquivo coletado:"
  MSG_ORIGINAL_SIZE="Tamanho original configurado:"
  MSG_RECOMMENDED_SIZE="Tamanho recomendado:"
  MSG_SIZE_WARNING="Aviso: O tamanho configurado pode ser insuficiente."
  MSG_SIZE_ADJUSTING="Ajustando automaticamente para evitar erros de espaço..."
  MSG_SIZE_OK="Tamanho configurado é adequado."
fi

# Função de log
LOG_FILE="${LINCON_LOG:-/tmp/lincon_migrate_container.log}"
log_msg() {
  local msg="$1"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" >> "$LOG_FILE"
}

log_msg "$MSG_START_MIGRATION"
echo "$MSG_START_MIGRATION"
log_msg "$MSG_COLLECT_FS $target..."
echo "$MSG_COLLECT_FS $target... Isso pode levar vários minutos."

# Conecta via SSH na máquina de origem, executa a função de coleta e salva em um arquivo temporário
if ! sshpass -p "$ssh_password" ssh -p "$port" -o "StrictHostKeyChecking=no" "root@$target" "$(typeset -f collectFS); collectFS" > "/tmp/$name.tar.gz"; then
    log_msg "$MSG_ERROR_COLLECT_FS"
    echo "$MSG_ERROR_COLLECT_FS"
    exit 1
fi

log_msg "$MSG_FS_COLLECTED"
echo "$MSG_FS_COLLECTED"

# Calcula o tamanho necessário do disco baseado no arquivo coletado
echo "📊 $MSG_ANALYZING_SIZE"
tar_file="/tmp/$name.tar.gz"
original_size="$rootsize"

# Remove sufixos G/M para obter apenas o número
original_size_num=$(echo "$original_size" | sed 's/[GM]//I')

# Calcula o tamanho recomendado
recommended_size=$(calculate_disk_size "$tar_file" "$original_size_num")

echo "📦 $MSG_COLLECTED_SIZE $(du -h "$tar_file" | cut -f1)"
echo "💾 $MSG_ORIGINAL_SIZE ${original_size_num}GB"
echo "🔍 $MSG_RECOMMENDED_SIZE ${recommended_size}GB"

# Se o tamanho recomendado for maior que o original, ajusta automaticamente
if [ "$recommended_size" -gt "$original_size_num" ]; then
    echo "⚠️  $MSG_SIZE_WARNING"
    echo "🔄 $MSG_SIZE_ADJUSTING"
    rootsize="${recommended_size}G"
else
    echo "✅ $MSG_SIZE_OK"
    rootsize="$original_size"
fi

log_msg "$MSG_CREATING_CT $id ($name)..."
echo "$MSG_CREATING_CT $id ($name)..."

# Detecta o tipo do storage para formatar o parâmetro rootfs corretamente
storage_type=$(pvesm status | awk -v s="$storage" '$1==s {print $2}')
if [ "$storage_type" = "dir" ]; then
    rootsize_num=$(echo "$rootsize" | sed 's/[GM]//I')
    rootfs_param="$storage:$rootsize_num"
else
    rootfs_param="$storage:$rootsize"
fi

# Define a configuração de rede com base no tipo de IP
if [ "$ip" = "dhcp" ]; then
    net_config="name=eth0,bridge=$bridge,ip=dhcp"
else
    net_config="name=eth0,bridge=$bridge,ip=$ip/24,gw=$gateway"
fi

# cria um script temporário para o comando 'pct create'
CREATE_SCRIPT="/tmp/create_ct_${id}.sh"
cat > "$CREATE_SCRIPT" << EOF
#!/bin/bash
pct create $id "/tmp/$name.tar.gz" \\
  --rootfs "$rootfs_param" \\
  --storage "$storage" \\
  --hostname "$name" \\
  --memory "$memory" \\
  --net0 "$net_config" \\
  --password "$password" \\
  --description "Migrado de $target" \\
  --nameserver 8.8.8.8 \\
  --features nesting=1 \\
  --unprivileged
EOF

chmod +x "$CREATE_SCRIPT"

echo "🚀 Executando a criação do contêiner em uma sessão separada para evitar erros de TTY..."

# Executa o script de criação usando 'at' para garantir um ambiente de execução limpo
if ! at -f "$CREATE_SCRIPT" now; then
    log_msg "$MSG_ERROR_AT"
    echo "$MSG_ERROR_AT"
    rm -f "$CREATE_SCRIPT"
    rm -f "/tmp/$name.tar.gz"
    exit 1
fi

# Aguarda a criação do contêiner verificando seu status periodicamente
echo "⏳ Aguardando a criação do contêiner $id... (Isso pode levar vários minutos)"
TIMEOUT=1800 # 30 minutos
COUNT=0
while ! pct status "$id" &> /dev/null; do
    sleep 5
    COUNT=$((COUNT + 5))
    if [ "$COUNT" -ge "$TIMEOUT" ]; then
        log_msg "$MSG_ERROR_TIMEOUT_CT"
        echo "$MSG_ERROR_TIMEOUT_CT"
        rm -f "$CREATE_SCRIPT"
        rm -f "/tmp/$name.tar.gz"
        exit 1
    fi
    echo -n "."
done
echo ""

# Verifica se o contêiner realmente existe após o loop
if pct status "$id" &> /dev/null; then
    log_msg "$MSG_CONTAINER_CREATED"
    echo "$MSG_CONTAINER_CREATED"
    echo "$MSG_STARTING_CT $id..."

    # --- INÍCIO DA CORREÇÃO ---
    # Cria um script temporário para o comando 'pct start'
    START_SCRIPT="/tmp/start_ct_${id}.sh"
    echo "#!/bin/bash" > "$START_SCRIPT"
    echo "pct start $id" >> "$START_SCRIPT"
    chmod +x "$START_SCRIPT"

    # Executa o start usando 'at' para evitar erros de TTY
    if ! at -f "$START_SCRIPT" now; then
        log_msg "$MSG_CONTAINER_START_FAILED"
        echo "$MSG_CONTAINER_START_FAILED"
    fi
    
    # Aguarda um pouco para o comando start ser executado
    sleep 5 
    
    # Verifica se o contêiner está rodando
    if pct status "$id" | grep -q "running"; then
        log_msg "$MSG_CONTAINER_STARTED"
        echo "$MSG_CONTAINER_STARTED"
        echo "📋 Detalhes do Contêiner:"
        echo "   ID: $id"
        echo "   Nome: $name"
        echo "   IP: $ip (pode levar um momento para obter se for DHCP)"
        echo "   Memória: ${memory}MB"
        echo "   Storage: $storage"
        echo ""
        echo "💡 Comandos úteis:"
        echo "   pct enter $id    # Entrar no contêiner"
        echo "   pct stop $id     # Parar o contêiner"
        echo "   pct status $id   # Verificar o status"
    else
        log_msg "$MSG_CONTAINER_START_FAILED"
        echo "$MSG_CONTAINER_START_FAILED"
        echo "💡 Tente manualmente: pct start $id"
    fi
    # --- FIM DA CORREÇÃO ---
else
    log_msg "$MSG_ERROR_CREATE_CT"
    echo "$MSG_ERROR_CREATE_CT"
    exit 1
fi

# Remove os arquivos temporários
echo "$MSG_CLEANING_UP"
log_msg "$MSG_CLEANING_UP"
rm -f "$CREATE_SCRIPT"
rm -f "$START_SCRIPT" # Limpa o novo script de start
rm -f "/tmp/$name.tar.gz"

log_msg "$MSG_MIGRATION_COMPLETED"
echo "$MSG_MIGRATION_COMPLETED"