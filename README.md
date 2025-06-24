# LINCON - Linux Containerized

Uma ferramenta para migração de containers Linux entre diferentes plataformas.

## Recursos

- Migração de Linux para Docker
- Migração de Linux para Proxmox/LXC
- Interface amigável
- Suporte a múltiplos idiomas
- Sistema de recuperação de migrações interrompidas

## Instalação Rápida

Para instalar o LINCON com um único comando, execute:

```bash
curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | sudo bash
```

## Instalação Manual

1. Clone o repositório:
```bash
git clone https://github.com/mathewalves/lincon.git
```

2. Entre no diretório:
```bash
cd lincon
```

3. Instale as dependências:
```bash
pip install -e .
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

Após a instalação, simplesmente execute:

```bash
lincon
```

## Licença

MIT License
