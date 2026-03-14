#!/bin/bash
# setup.sh — Predictfy × Locaweb
# Cria o ambiente conda e registra o kernel no Jupyter
# Uso: bash setup.sh

set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Predictfy × Locaweb — Setup do ambiente"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Criar ambiente a partir do environment.yml
echo "▶ Criando ambiente conda 'predictfy-locaweb'..."
conda env create -f environment.yml

# 2. Ativar e registrar kernel no Jupyter
echo ""
echo "▶ Registrando kernel no Jupyter..."
conda run -n predictfy-locaweb python -m ipykernel install \
  --user \
  --name predictfy-locaweb \
  --display-name "Python 3.12 (predictfy-locaweb)"

# 3. Copiar .env.example se .env não existir
if [ ! -f .env ]; then
  echo ""
  echo "▶ Criando .env a partir do .env.example..."
  cp .env.example .env
  echo "  ⚠ Edite o .env com suas chaves antes de rodar o chatbot."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Setup concluído!"
echo ""
echo "  Para ativar o ambiente:"
echo "    conda activate predictfy-locaweb"
echo ""
echo "  Para abrir o JupyterLab:"
echo "    jupyter lab"
echo ""
echo "  Para rodar o pipeline de ML:"
echo "    python src/pipeline.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
