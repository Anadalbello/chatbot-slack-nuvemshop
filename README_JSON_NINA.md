# 📊 Sistema de Integrações em JSON - Estilo Nina

## 🎯 Visão Geral

O bot agora usa um arquivo JSON estático para buscar informações sobre integrações, similar à abordagem da Nina. Isso oferece:

- ✅ **Performance**: Leitura local instantânea
- ✅ **Resiliência**: Funciona mesmo se Google Sheets estiver offline
- ✅ **Consistência**: Dados sincronizados uma vez, usados sempre
- ✅ **Simplicidade**: Sem dependência de APIs externas em produção

## 📁 Estrutura

```
chatbot_gemini/
├── knowledge/
│   └── integracoes.json      # Arquivo JSON com todas as integrações
├── scripts/
│   └── sincronizar_sheets_para_json.py  # Script de sincronização
└── handlers/
    └── buscar_integracoes_json.py       # Handler para buscar no JSON
```

## 🚀 Como Usar

### 1. Primeira Sincronização

Execute o script para baixar e converter o Google Sheets em JSON:

```bash
# Ativar venv se necessário
source venv/bin/activate

# Executar sincronização
python scripts/sincronizar_sheets_para_json.py
```

O arquivo `knowledge/integracoes.json` será criado automaticamente.

### 2. Estrutura do JSON Gerado

```json
{
  "version": "1.0",
  "last_updated": "2025-10-29T23:30:00",
  "source": "Google Sheets",
  "total_integracoes": 150,
  "integracoes": [
    {
      "nome": "VTEX",
      "descricao_curta": "Plataforma de e-commerce...",
      "descricao_longa": "Detalhes completos...",
      "tipo": "E-commerce",
      "complexidade": "Média",
      "responsavel": "Time Integrações",
      "status": "Ativo",
      "funcionalidades": [
        "Cálculo de Frete",
        "Importação de pedidos"
      ],
      "link": "https://...",
      "metadata": {
        "nome": "VTEX",
        "tipo": "E-commerce",
        ...
      }
    }
  ]
}
```

### 3. Configuração das Fontes

O JSON está configurado como **prioridade 1** no `knowledge/sources_config.json`:

```json
{
  "id": "integracoes_json",
  "name": "Integrações (JSON estático)",
  "enabled": true,
  "priority": 1,
  ...
}
```

Google Sheets está desabilitado por padrão (mas pode ser reativado como fallback).

## 🔄 Sincronização Automática

### Opção 1: Manual (atual)

Execute quando quiser atualizar:

```bash
python scripts/sincronizar_sheets_para_json.py
```

### Opção 2: Automatizar (recomendado)

#### Via Cron (Linux/Mac):

```bash
# Editar crontab
crontab -e

# Adicionar linha para sincronizar a cada hora
0 * * * * cd /caminho/para/chatbot && python scripts/sincronizar_sheets_para_json.py
```

#### Via Git Hooks (antes de commit):

Adicione ao `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python scripts/sincronizar_sheets_para_json.py
```

#### Via CI/CD (Render/GitHub Actions):

Adicione ao workflow:

```yaml
- name: Sincronizar integrações
  run: python scripts/sincronizar_sheets_para_json.py
```

## 📊 Como o Bot Usa

### Busca Específica

Quando o usuário pergunta sobre uma integração específica:

```
@bot temos integração com VTEX?
```

1. Recepcionista detecta: `specific_integration`
2. KnowledgeManager busca em `integracoes_json` (prioridade 1)
3. Handler `buscar_integracao_especifica_json()` encontra e retorna detalhes

### Listar Integrações

Quando o usuário pede para listar:

```
@bot listar integrações
```

1. Recepcionista detecta: `list_integrations`
2. App.py chama `buscar_integracoes_json()`
3. Retorna lista formatada de até 50 integrações

### Busca Genérica

Quando o usuário faz pergunta genérica:

```
@bot como calcular frete?
```

1. KnowledgeManager busca no JSON primeiro
2. Se não encontrar, busca em Confluence e Zendesk

## 🔧 Configuração

### Variáveis de Ambiente Necessárias

```bash
# Google Sheets (para sincronização)
GOOGLE_SHEETS_ID="seu-id-aqui"
GOOGLE_SHEETS_TAB="Integrações"  # Nome da aba (opcional)
```

### Como Desabilitar JSON e Voltar para Google Sheets

No `knowledge/sources_config.json`:

```json
{
  "id": "integracoes_json",
  "enabled": false,  // ← Mudar para false
  ...
},
{
  "id": "google_sheets",
  "enabled": true,  // ← Mudar para true
  "priority": 1,    // ← Voltar para prioridade 1
  ...
}
```

## ✅ Vantagens do JSON

1. **Performance**: 100x mais rápido que API do Google Sheets
2. **Offline**: Funciona sem internet após sincronização
3. **Estável**: Dados não mudam durante execução
4. **Versionado**: Pode commitar JSON no git (se quiser)
5. **Debug**: Fácil inspecionar dados

## 📝 Notas Importantes

- ⚠️ O JSON precisa ser sincronizado manualmente ou via cron
- ✅ O bot funciona mesmo se o Google Sheets estiver offline
- 🔄 Recomenda-se sincronizar pelo menos 1x por dia
- 📁 Arquivo JSON não é versionado no git por padrão (adicionar ao .gitignore se contiver dados sensíveis)

## 🐛 Troubleshooting

### Erro: "Arquivo integracoes.json não encontrado"

**Solução:** Execute a sincronização:
```bash
python scripts/sincronizar_sheets_para_json.py
```

### Erro: "GOOGLE_SHEETS_ID não configurado"

**Solução:** Verifique o `.env`:
```bash
GOOGLE_SHEETS_ID="seu-id-aqui"
```

### JSON está desatualizado

**Solução:** Re-execute a sincronização:
```bash
python scripts/sincronizar_sheets_para_json.py
```

## 🎉 Pronto!

Agora seu bot funciona estilo Nina, usando JSON estático como fonte primária de dados sobre integrações!





