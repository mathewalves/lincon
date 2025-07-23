#!/bin/bash

# Check if the 'pct' command is available on the host machine (Proxmox)
if ! command -v pct &> /dev/null
then
    echo "pct could not be found. This script must be run on the host machine Proxmox"
    exit 1
fi

# Function to display script usage
usage()
{
    cat <<EOF
$1 -h|--help
 -n|--name [LXC container name]
 -t|--target [target machine SSH URI]
 -P|--port [target SSH port]
 -i|--id [Proxmox container ID]
 -s|--root-size [rootfs size in GB]
 -a|--ip [target container IP]
 -b|--bridge [bridge interface]
 -g|--gateway [gateway IP]
 -m|--memory [memory in MB]
 -d|--disk-storage [target Proxmox storage pool]
 -p|--password [root password for container (min. 5 chars)]
 -w|--ssh-password [SSH password for target machine]
EOF
    return 0
}

# Parse command-line options
options=$(getopt -o n:t:P:i:s:a:b:g:m:d:p:w:h -l help,name:,target:,port:,id:,root-size:,ip:,bridge:,gateway:,memory:,disk-storage:,password:,ssh-password: -- "$@")
if [ $? -ne 0 ]; then
    usage "$(basename "$0")"
    exit 1
fi
eval set -- "$options"

# Process command-line options
while true
do
    case "$1" in
        -h|--help)          usage "$0" && exit 0;;
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

# Validate required parameters
if [ -z "$name" ] || [ -z "$target" ] || [ -z "$port" ] || [ -z "$id" ] || [ -z "$rootsize" ] || [ -z "$ip" ] || [ -z "$bridge" ] || [ -z "$gateway" ] || [ -z "$memory" ] || [ -z "$storage" ] || [ -z "$password" ] || [ -z "$ssh_password" ]; then
    echo "Error: Missing required parameters"
    usage "$(basename "$0")"
    exit 1
fi

# Function to collect file system data, excluding unnecessary directories and files
collectFS() {
    tar -czvf - -C / \
    --exclude="sys" \
    --exclude="dev" \
    --exclude="run" \
    --exclude="proc" \
    --exclude="*.log" \
    --exclude="*.log*" \
    --exclude="*.gz" \
    --exclude="*.sql" \
    --exclude="swap.img" \
    --exclude="tmp" \
    --exclude="var/tmp" \
    --exclude="var/lib/docker" \
    --exclude="var/lib/containers" \
    --exclude="var/cache" \
    --exclude="var/log" \
    --exclude="var/backups" \
    --exclude="mnt" \
    --exclude="media" \
    .
}

echo "🚀 Starting container migration..."
echo "📡 Collecting filesystem from $target..."

# SSH into the target machine, execute the file system collection function, and save to a temporary file
if ! sshpass -p "$ssh_password" ssh -p "$port" -o "StrictHostKeyChecking=no" "root@$target" "$(typeset -f collectFS); collectFS" > "/tmp/$name.tar.gz"; then
    echo "❌ Failed to collect filesystem from target machine"
    exit 1
fi

echo "✅ Filesystem collected successfully"
echo "📦 Creating container $id ($name)..."

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

echo "id: $id"
echo "name: $name"
echo "storage: $storage"
echo "rootsize: $rootsize"
echo "memory: $memory"
echo "bridge: $bridge"
echo "ip: $ip"
echo "gateway: $gateway"
echo "rootfs_param: $rootfs_param"

if [ -z "$id" ] || [ -z "$rootfs_param" ] || [ -z "$storage" ] || [ -z "$name" ] || [ -z "$memory" ] || [ -z "$net_config" ] || [ -z "$password" ]; then
  echo "❌ Erro: Um ou mais parâmetros obrigatórios estão vazios!"
  echo "id: $id"
  echo "rootfs_param: $rootfs_param"
  echo "storage: $storage"
  echo "name: $name"
  echo "memory: $memory"
  echo "net_config: $net_config"
  echo "password: $password"
  exit 1
fi

echo "Comando real a ser executado:"
echo pct create "$id" "/tmp/$name.tar.gz" --rootfs "$rootfs_param" --storage "$storage" --hostname "$name" --memory "$memory" --net0 "$net_config" -password "$password"

if pct create "$id" "/tmp/$name.tar.gz" \
  -description "LXC" \
  -hostname "$name" \
  --features nesting=1 \
  -memory "$memory" -nameserver 8.8.8.8 \
  -net0 "$net_config" \
  --rootfs "$rootfs_param" \
  -password "$password"
then
    
    echo "✅ Container created successfully!"
    echo "🚀 Starting container $id..."
    
    # Start the container
    if pct start "$id"; then
        echo "🎉 Migration completed successfully!"
        echo "📋 Container details:"
        echo "   ID: $id"
        echo "   Name: $name"
        echo "   IP: $ip"
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
    echo "❌ Failed to create container"
    exit 1
fi

# Remove the temporary file
echo "🧹 Cleaning up temporary files..."
rm -rf "/tmp/$name.tar.gz"

echo "✨ Migration process completed!" 