# 🔄 Script de Sincronização - Google Sheets → JSON

## Como Usar

### Execução Manual

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar sincronização
python scripts/sincronizar_sheets_para_json.py
```

### Requisitos

- Variável `GOOGLE_SHEETS_ID` configurada no `.env`
- Planilha Google Sheets pública (ou com acesso configurado)
- Conexão com internet para baixar dados

### O Que Faz

1. 📥 Baixa dados do Google Sheets via CSV público
2. 🔄 Converte para formato JSON estilo Nina
3. 💾 Salva em `knowledge/integracoes.json`

### Saída Esperada

```
============================================================
🔄 Iniciando sincronização Google Sheets → JSON
============================================================

📥 Passo 1: Baixando dados do Google Sheets...
✅ Dados baixados: 151 linhas (incluindo cabeçalho)

🔄 Passo 2: Convertendo para formato JSON...
✅ 150 integrações convertidas com sucesso

💾 Passo 3: Salvando arquivo JSON...
💾 JSON salvo em: knowledge/integracoes.json
📊 Total: 150 integrações
📁 Tamanho do arquivo: 245.67 KB

============================================================
✅ Sincronização concluída com sucesso!
============================================================
```

### Automatização

Veja `README_JSON_NINA.md` para opções de automatização (cron, CI/CD, etc.)





