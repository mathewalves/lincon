# LINCON - Linux Containerized

Uma ferramenta para migração de containers Linux entre diferentes plataformas.

## Recursos

- Migração de Linux para Docker
- Migração de Linux para Proxmox/LXC
- Interface amigável
- Suporte a múltiplos idiomas
- Sistema de recuperação de migrações interrompidas

## Instalação Rápida

### Ubuntu/Sistemas com sudo:
```bash
curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | sudo bash
```

### Debian/Proxmox (como root):
```bash
curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | bash
```

### Ou usar su para elevar privilégios:
```bash
su -c "curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | bash"
```

## Instalação Manual

1. Clone o repositório:
```bash
git clone https://github.com/mathewalves/lincon.git
cd lincon
```

2. Instale as dependências:
```bash
# Para Ubuntu 24.04+ (ambiente gerenciado):
pip3 install rich --break-system-packages

# Para outras distribuições:
pip3 install rich
```

3. Execute diretamente:
```bash
python3 main.py
```

## Requisitos

- Python 3.8 ou superior
- Sistema operacional Linux
- Para migração para Docker:
  - Docker instalado
- Para migração para Proxmox:
  - Acesso a um servidor Proxmox
  - Ferramentas PCT instaladas

## Uso

Após a instalação automática:
```bash
lincon
```

Ou execute diretamente:
```bash
python3 main.py
```

## Troubleshooting

### Erro "sudo: command not found" (Debian/Proxmox)
Execute como root:
```bash
curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | bash
```

### Erro "externally-managed-environment" (Ubuntu 24.04+)
O script automaticamente resolve isso, mas você pode instalar manualmente:
```bash
pip3 install rich --break-system-packages
```

### Docker não encontrado
Instale o Docker:
```bash
curl -fsSL https://get.docker.com | sudo sh
```

### Problemas de setup.py
O novo script de instalação evita problemas com setuptools. Se ainda encontrar problemas, execute manualmente:
```bash
git clone https://github.com/mathewalves/lincon.git
cd lincon
pip3 install rich
python3 main.py
```

## Licença

MIT License
