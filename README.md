# LINCON 🐳

Ferramenta simples para migração de containers Linux.

## Recursos

✅ **Linux → Docker**  
✅ **Linux → Proxmox/LXC**  
✅ **Interface em português**  
✅ **Recuperação automática**  

## Instalação

**Comando único:**
```bash
curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | sudo bash
```

## Uso

```bash
lincon
```

## Desinstalação

```bash
curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/uninstall.sh | sudo bash
```

## Requisitos

- Linux
- Docker (para migração Docker)
- Proxmox (para migração LXC)

## Problemas?

**Reinstalar:**
```bash
# Execute novamente e escolha reinstalar
curl -sSL https://raw.githubusercontent.com/mathewalves/lincon/main/install.sh | sudo bash
```

**Docker não encontrado:**
```bash
curl -fsSL https://get.docker.com | sudo sh
```

## Licença

MIT
