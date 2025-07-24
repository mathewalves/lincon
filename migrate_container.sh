#!/bin/bash

# Verifica se o comando 'pct' está disponível na máquina host (Proxmox)
if ! command -v pct &> /dev/null
then
    echo "❌ Erro: Comando 'pct' não encontrado. Este script deve ser executado na máquina host Proxmox."
    exit 1
fi

# Função para exibir o uso do script
usage()
{
    cat <<EOF
Uso: $(basename "$0") [opções]

Opções Obrigatórias:
 -n, --name [nome]             Nome para o novo container LXC.
 -t, --target [host]           IP ou hostname do servidor de origem a ser migrado.
 -P, --port [porta]            Porta SSH do servidor de origem.
 -i, --id [id]                 ID numérico para o novo container no Proxmox.
 -s, --root-size [tamanho]     Tamanho do disco para o rootfs (ex: 4G, 10G).
 -a, --ip [ip|dhcp]            Endereço IP para o container (ex: 192.168.1.100 ou dhcp).
 -b, --bridge [bridge]         Interface de bridge do Proxmox (ex: vmbr0).
 -g, --gateway [gateway]       Gateway da rede (necessário se o IP não for dhcp).
 -m, --memory [memoria]        Memória RAM em MB para o container (ex: 1024).
 -d, --disk-storage [storage]  Pool de armazenamento do Proxmox para o disco.
 -p, --password [senha]        Senha 'root' para o novo container (mín. 5 caracteres).
 -w, --ssh-password [senha]    Senha 'root' do servidor de origem para conexão SSH.

Ajuda:
 -h, --help                    Exibe esta mensagem de ajuda.
EOF
    return 0
}

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
    --exclude="*.log*" \
    --exclude="*.gz" \
    --exclude="*.sql" \
    --exclude="./swap.img" \
    --exclude="./tmp" \
    --exclude="./var/tmp" \
    --exclude="./var/lib/docker" \
    --exclude="./var/lib/containers" \
    --exclude="./var/cache" \
    --exclude="./var/log" \
    --exclude="./var/backups" \
    --exclude="./mnt" \
    --exclude="./media" \
    .
}

echo "🚀 Iniciando o processo de migração..."
echo "📡 Coletando sistema de arquivos de $target... Isso pode levar vários minutos."

# Conecta via SSH na máquina de origem, executa a função de coleta e salva em um arquivo temporário
if ! sshpass -p "$ssh_password" ssh -p "$port" -o "StrictHostKeyChecking=no" "root@$target" "$(typeset -f collectFS); collectFS" > "/tmp/$name.tar.gz"; then
    echo "❌ Falha ao coletar o sistema de arquivos da máquina de origem."
    exit 1
fi

echo "✅ Sistema de arquivos coletado com sucesso."
echo "📦 Preparando para criar o container $id ($name)..."

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

# Cria um script temporário para o comando 'pct create' para ser executado pelo 'at'
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
    echo "❌ Falha ao agendar a tarefa de criação do contêiner com 'at'. Verifique se o serviço 'atd' está instalado e em execução."
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
        echo "❌ Timeout: O contêiner $id não foi criado em $TIMEOUT segundos. Verifique os logs de tarefas na interface web do Proxmox para detalhes."
        rm -f "$CREATE_SCRIPT"
        rm -f "/tmp/$name.tar.gz"
        exit 1
    fi
    echo -n "."
done
echo ""

# Verifica se o contêiner realmente existe após o loop
if pct status "$id" &> /dev/null; then
    echo "✅ Contêiner criado com sucesso!"
    echo "🚀 Iniciando o contêiner $id..."

    # --- INÍCIO DA CORREÇÃO ---
    # Cria um script temporário para o comando 'pct start'
    START_SCRIPT="/tmp/start_ct_${id}.sh"
    echo "#!/bin/bash" > "$START_SCRIPT"
    echo "pct start $id" >> "$START_SCRIPT"
    chmod +x "$START_SCRIPT"

    # Executa o start usando 'at' para evitar erros de TTY
    if ! at -f "$START_SCRIPT" now; then
        echo "⚠️  Falha ao agendar a tarefa de inicialização. Tente manualmente: pct start $id"
    fi
    
    # Aguarda um pouco para o comando start ser executado
    sleep 5 
    
    # Verifica se o contêiner está rodando
    if pct status "$id" | grep -q "running"; then
        echo "🎉 Migração concluída com sucesso!"
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
        echo "⚠️  O contêiner foi criado mas falhou ao iniciar."
        echo "💡 Tente manualmente: pct start $id"
    fi
    # --- FIM DA CORREÇÃO ---
else
    echo "❌ Falha ao criar o contêiner após a execução separada. Verifique os logs de tarefas na interface web do Proxmox."
    exit 1
fi

# Remove os arquivos temporários
echo "🧹 Limpando arquivos temporários..."
rm -f "$CREATE_SCRIPT"
rm -f "$START_SCRIPT" # Limpa o novo script de start
rm -f "/tmp/$name.tar.gz"

echo "✨ Processo de migração finalizado!"