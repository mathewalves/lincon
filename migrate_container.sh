#!/bin/bash

# ... (toda a parte inicial de verificação e obtenção de parâmetros permanece a mesma) ...
# Apenas a parte final, após "Creating container", será modificada.

# Copie e cole todo o seu script até esta linha:
echo "📦 Creating container $id ($name)..."

# ---> INÍCIO DA SEÇÃO MODIFICADA <---

# Detecta tipo do storage
storage_type=$(pvesm status | awk -v s="$storage" '$1==s {print $2}')

# Remove G/M se for dir
if [ "$storage_type" = "dir" ]; then
    rootsize_num=$(echo "$rootsize" | sed 's/[GM]//I')
    rootfs_param="$storage:$rootsize_num"
else
    rootfs_param="$storage:$rootsize"
fi

# Set network configuration based on IP type
if [ "$ip" = "dhcp" ]; then
    net_config="name=eth0,bridge=$bridge,ip=dhcp"
else
    net_config="name=eth0,bridge=$bridge,ip=$ip/24,gw=$gateway"
fi

# Criar um script temporário para o comando 'pct create'
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
  --description "Migrated from $target" \\
  --nameserver 8.8.8.8 \\
  --features nesting=1 \\
  --unprivileged
EOF

chmod +x "$CREATE_SCRIPT"

echo "🚀 Executing container creation in a detached session to avoid TTY errors..."

# Executa o script de criação usando 'at' para garantir um ambiente limpo
if ! at -f "$CREATE_SCRIPT" now; then
    echo "❌ Failed to schedule container creation task using 'at'. Make sure 'atd' service is running."
    rm -f "$CREATE_SCRIPT"
    rm -f "/tmp/$name.tar.gz"
    exit 1
fi

# Aguarda a criação do contêiner verificando seu status
echo "⏳ Waiting for container $id to be created... (this may take a few minutes)"
TIMEOUT=600 # 10 minutos de timeout
COUNT=0
while ! pct status "$id" &> /dev/null; do
    sleep 5
    COUNT=$((COUNT + 5))
    if [ "$COUNT" -ge "$TIMEOUT" ]; then
        echo "❌ Timeout: Container $id was not created within $TIMEOUT seconds."
        rm -f "$CREATE_SCRIPT"
        rm -f "/tmp/$name.tar.gz"
        exit 1
    fi
    echo -n "."
done
echo ""

# Verifica se o contêiner realmente existe após o loop
if pct status "$id" &> /dev/null; then
    echo "✅ Container created successfully!"
    echo "🚀 Starting container $id..."

    if pct start "$id"; then
        echo "🎉 Migration completed successfully!"
        echo "📋 Container details:"
        echo "   ID: $id"
        echo "   Name: $name"
        echo "   IP: $ip (may take a moment to acquire if DHCP)"
        echo "   Memory: ${memory}MB"
        echo "   Storage: $storage"
        echo ""
        echo "💡 Useful commands:"
        echo "   pct enter $id    # Enter container"
        echo "   pct stop $id     # Stop container"
        echo "   pct status $id   # Check status"
    else
        echo "⚠️  Container created but failed to start"
        echo "💡 Try manually: pct start $id"
    fi
else
    echo "❌ Failed to create container after detached execution."
    exit 1
fi

# Remove os arquivos temporários
echo "🧹 Cleaning up temporary files..."
rm -f "$CREATE_SCRIPT"
rm -f "/tmp/$name.tar.gz"

echo "✨ Migration process completed!"