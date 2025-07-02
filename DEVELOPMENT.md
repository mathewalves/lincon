# LINCON - Guia de Desenvolvimento

## 🚀 Branch Strategy

- **`main`** - Versão estável de produção
- **`dev`** - Branch de desenvolvimento ativo

## 🔧 Setup de Desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/mathewalves/lincon.git
cd lincon

# Mude para branch dev
git checkout dev

# Instale dependências
pip3 install rich --break-system-packages

# Execute localmente
python3 main.py
```

## 📁 Estrutura do Projeto

```
lincon/
├── main.py              # Interface principal
├── migrate_docker.py    # Migração Linux → Docker
├── migrate_lxc.py       # Migração Linux → LXC/Proxmox
├── install.sh           # Instalador simplificado
├── uninstall.sh         # Desinstalador
├── utils/               # Utilitários
│   ├── logger.py        # Sistema de logs
│   ├── system_info.py   # Info do sistema
│   ├── migration_state.py # Estado de migração
│   └── exceptions.py    # Exceções customizadas
├── lang/                # Traduções PT-BR/EN
│   └── translations.py
├── logs/                # Logs da aplicação
└── state/               # Estados de migração
```

## 🎯 Workflow de Desenvolvimento

1. **Crie feature branch a partir de dev:**
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/nova-funcionalidade
   ```

2. **Faça suas alterações e teste:**
   ```bash
   python3 main.py  # Teste local
   ```

3. **Commit com mensagens claras:**
   ```bash
   git add .
   git commit -m "✨ Adiciona nova funcionalidade X"
   ```

4. **Push e crie PR para dev:**
   ```bash
   git push origin feature/nova-funcionalidade
   # Criar PR no GitHub: feature/nova-funcionalidade → dev
   ```

5. **Deploy para main:**
   ```bash
   # Após aprovação, merge dev → main
   git checkout main
   git merge dev
   git push origin main
   ```

## 🧪 Testes

```bash
# Teste de sintaxe dos scripts
bash -n install.sh
bash -n uninstall.sh

# Teste de importação Python
python3 -c "import main; print('✅ OK')"

# Teste de dependências
python3 -c "import rich; from lang.translations import translations; print('✅ Deps OK')"
```

## 📋 Checklist de Release

- [ ] Funcionalidades testadas em dev
- [ ] Scripts de instalação validados
- [ ] README atualizado
- [ ] Versão incrementada
- [ ] Merge dev → main
- [ ] Tag da versão criada

## 🐛 Debug

```bash
# Logs em tempo real
tail -f logs/lincon_*.log

# Verificar estado de migração
ls -la state/

# Teste de conectividade
python3 -c "from utils.system_info import check_docker; print('Docker:', check_docker())"
``` 