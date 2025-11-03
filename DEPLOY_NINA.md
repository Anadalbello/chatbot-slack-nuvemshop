# 🚀 Deploy no Render - Chatbot Estilo Nina

## 📋 Checklist Pré-Deploy

### ✅ Estrutura Criada
- [x] `knowledge/` - Diretório criado
- [x] `knowledge/sources_config.json` - Configurado
- [x] `knowledge/context_rules.json` - Configurado  
- [x] `core/` - Módulos criados
- [x] `app.py` - Integrado com nova estrutura

### ✅ Configuração Render

O `render.yaml` já está configurado corretamente:
```yaml
services:
  - type: web
    name: chatbot-slack
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: PORT
        generateValue: true
      - key: PYTHON_VERSION
        value: 3.11.9
```

## 🔧 Como Fazer Deploy no Render

### 1. Preparar o Repositório

```bash
# Verificar se todos os arquivos estão no git
git status

# Adicionar novos arquivos se necessário
git add knowledge/ core/ app.py
git commit -m "feat: adaptação para estrutura estilo Nina"
git push origin main
```

### 2. Configurar Variáveis de Ambiente no Render

Acesse o dashboard do Render e configure estas variáveis:

**Obrigatórias:**
- `SLACK_BOT_TOKEN` - Token do bot do Slack
- `SLACK_SIGNING_SECRET` - Secret do Slack
- `GEMINI_API_KEY` - Chave da API do Gemini
- `ATLASSIAN_EMAIL` - Email do Atlassian (Confluence)
- `ATLASSIAN_TOKEN` - Token do Atlassian
- `ATLASSIAN_BASE_URL` - URL base do Atlassian
- `ZENDESK_EMAIL` - Email do Zendesk
- `ZENDESK_API_TOKEN` - Token do Zendesk
- `ZENDESK_SUBDOMAIN` - Subdomínio do Zendesk (opcional)

**Opcionais:**
- `CONFLUENCE_SPACE` - Espaço do Confluence (padrão: BDGCI)
- `ENV` - Ambiente (production/staging)

### 3. Arquivos que SERÃO Incluídos no Deploy

✅ **Incluídos automaticamente:**
- `knowledge/` - Diretório e arquivos JSON
- `core/` - Todos os módulos Python
- `handlers/` - Todos os handlers
- `app.py` - App principal
- `requirements.txt` - Dependências
- `render.yaml` - Configuração Render
- `runtime.txt` - Versão Python

❌ **NÃO incluídos (por segurança):**
- `.env` - Variáveis de ambiente (configurar no Render)
- `venv/` - Ambiente virtual
- `__pycache__/` - Arquivos compilados
- `backup_*/` - Backups locais

### 4. O Que Acontece no Deploy

1. **Build:**
   ```bash
   pip install -r requirements.txt
   ```
   - Instala todas as dependências
   - Inclui automaticamente `knowledge/` e `core/`

2. **Start:**
   ```bash
   gunicorn app:app
   ```
   - Inicia o app na porta fornecida pelo Render
   - O app carrega automaticamente:
     - `KnowledgeManager` - Lê `knowledge/sources_config.json`
     - `Recepcionista` - Inicializa
     - `FonteValidator` - Inicializa

## 🔍 Verificações Após Deploy

### 1. Logs no Render

Procure por estas mensagens de sucesso:
```
✅ Sistema estilo Nina inicializado
✅ Knowledge Manager inicializado: 3 fontes ativas
✅ Recepcionista inicializada
✅ FonteValidator inicializado
```

### 2. Teste Endpoints

```bash
# Health check
curl https://seu-app.onrender.com/health

# Test endpoint  
curl https://seu-app.onrender.com/test
```

### 3. Teste no Slack

- `@bot oi` → Deve mostrar menu
- `@bot listar integrações` → Deve buscar do Google Sheets
- `@bot como integrar Magento?` → Deve buscar e responder

## 🚨 Possíveis Problemas

### Problema 1: "ModuleNotFoundError: No module named 'core'"

**Causa:** Arquivos não estão no git

**Solução:**
```bash
git add knowledge/ core/
git commit -m "Add estrutura estilo Nina"
git push
```

### Problema 2: "FileNotFoundError: knowledge/sources_config.json"

**Causa:** Arquivos JSON não foram commitados

**Solução:**
```bash
# Verificar se estão no git
git ls-files | grep knowledge/

# Se não estiverem, adicionar
git add knowledge/*.json
git commit -m "Add arquivos de configuração"
git push
```

### Problema 3: "Erro ao carregar fonte"

**Causa:** Variáveis de ambiente não configuradas

**Solução:**
- Verificar todas as variáveis no dashboard do Render
- Especialmente: `ATLASSIAN_TOKEN`, `ZENDESK_API_TOKEN`, `GEMINI_API_KEY`

### Problema 4: Gunicorn não inicia

**Causa:** Problema com dependências ou código

**Solução:**
- Ver logs no Render para erro específico
- Testar localmente primeiro: `gunicorn app:app`

## ✅ Checklist Final

Antes de fazer deploy, verifique:

- [ ] Todos os arquivos `knowledge/` estão commitados
- [ ] Todos os arquivos `core/` estão commitados  
- [ ] `app.py` foi atualizado com imports corretos
- [ ] Variáveis de ambiente configuradas no Render
- [ ] Testou localmente primeiro
- [ ] `render.yaml` está correto
- [ ] `requirements.txt` tem todas as dependências

## 🎯 Comandos Úteis

```bash
# Verificar o que será enviado
git ls-files | grep -E "(knowledge|core|app.py)"

# Testar build localmente (simular Render)
pip install -r requirements.txt
python3 -c "from core import KnowledgeManager; print('OK')"

# Verificar sintaxe
python3 -m py_compile app.py core/*.py
```

## 📝 Notas Importantes

1. **Arquivos JSON são versionados** - `knowledge/*.json` vão para o git (não são secretos)

2. **Variáveis de ambiente** - Sempre configure no Render, nunca no código

3. **Primeiro deploy pode demorar** - Render precisa instalar todas as dependências

4. **Monitorar logs** - Após deploy, verifique logs para erros de inicialização

5. **Backup existe** - Se algo der errado, você tem o backup em `backup_pre_refatoracao_nina_20251029_110355/`

## 🚀 Pronto para Deploy!

Se tudo estiver OK, faça:

```bash
git add .
git commit -m "feat: estrutura estilo Nina integrada"
git push origin main
```

O Render vai fazer deploy automático! 🎉




