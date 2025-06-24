#!/bin/bash

# Script de instalação local para teste
echo "=== LINCON - Instalação Local de Teste ==="

# Instala dependências se necessário
echo "Verificando dependências..."
pip3 install rich --break-system-packages 2>/dev/null || pip3 install rich

# Remove links antigos
sudo rm -f /usr/local/bin/lincon 2>/dev/null

# Cria o script executável
echo "Criando comando lincon..."
sudo bash -c 'cat > /usr/local/bin/lincon << '"'"'EOF'"'"'
#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")/../../Área de trabalho/containerized-linux"
python3 main.py "$@"
EOF'

# Torna executável
sudo chmod +x /usr/local/bin/lincon

# Verifica se foi criado
if [ -x /usr/local/bin/lincon ]; then
    echo "✅ Comando 'lincon' criado com sucesso!"
    echo "Para testar, execute: lincon"
else
    echo "❌ Erro ao criar comando 'lincon'"
fi

echo "Localização atual: $(pwd)"
echo "Para executar diretamente: python3 main.py" 