# 🚀 Como Fazer Deploy no Render - Chatbot Estilo Nina

## ✅ Status Atual

A estrutura está **PRONTA** para deploy, mas precisa ser **commitada no git** primeiro!

## 📋 Passo a Passo para Deploy

### 1. Verificar Arquivos no Git

Os novos arquivos ainda não estão no git. Execute:

```bash
# Ver o que precisa ser adicionado
git status

# Adicionar novos arquivos
git add knowledge/
git add core/
git add app.py  # Se foi modificado
git add render.yaml  # Se foi modificado
```

### 2. Commit e Push

```bash
# Fazer commit
git commit -m "feat: adaptação para estrutura estilo Nina - sistema de conhecimento centralizado"

# Push para o repositório
git push origin main
```

### 3. O Render fará Deploy Automático

Quando você faz push para `main`, o Render detecta automaticamente e inicia o deploy!

## 🔍 O Que Será Incluído no Deploy

✅ **Será incluído:**
- ✅ `knowledge/` - Diretório completo com JSONs
- ✅ `core/` - Todos os módulos Python
- ✅ `handlers/` - Todos os handlers (já existentes)
- ✅ `app.py` - App principal (atualizado)
- ✅ `requirements.txt` - Dependências
- ✅ `render.yaml` - Configuração do Render
- ✅ `runtime.txt` - Versão Python

❌ **NÃO será incluído (por .gitignore):**
- ❌ `venv/` - Ambiente virtual
- ❌ `__pycache__/` - Cache Python
- ❌ `.env` - Variáveis de ambiente (configure no Render)
- ❌ `backup_*/` - Backups locais

## ⚙️ Configuração no Render

### Variáveis de Ambiente Necessárias

No dashboard do Render, configure todas estas variáveis:

#### Obrigatórias:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
GEMINI_API_KEY=...
ATLASSIAN_EMAIL=...
ATLASSIAN_TOKEN=...
ATLASSIAN_BASE_URL=https://tiendanube.atlassian.net
ZENDESK_EMAIL=...
ZENDESK_API_TOKEN=...
```

#### Opcionais (com valores padrão):
```
CONFLUENCE_SPACE=BDGCI
ZENDESK_SUBDOMAIN=tiendanube
ENV=production
```

## 🧪 Teste Local Antes de Deployar

```bash
# 1. Ativar venv
source venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Testar imports
python3 -c "from core import KnowledgeManager; print('✅ OK')"

# 4. Rodar app localmente
python3 app.py

# Ou com gunicorn (como no Render)
gunicorn app:app
```

## 📊 Logs no Render

Após o deploy, verifique os logs e procure por:

### ✅ Sinais de Sucesso:
```
✅ Sistema estilo Nina inicializado
✅ Knowledge Manager inicializado: 3 fontes ativas
✅ Fonte 'google_sheets' carregada (prioridade: 1)
✅ Fonte 'confluence' carregada (prioridade: 2)
✅ Fonte 'zendesk' carregada (prioridade: 3)
✅ Recepcionista inicializada
✅ FonteValidator inicializado
```

### ❌ Possíveis Erros:

1. **"ModuleNotFoundError: No module named 'core'"**
   - **Causa:** Arquivos `core/` não foram commitados
   - **Solução:** `git add core/ && git commit && git push`

2. **"FileNotFoundError: knowledge/sources_config.json"**
   - **Causa:** Arquivos `knowledge/` não foram commitados
   - **Solução:** `git add knowledge/ && git commit && git push`

3. **"Erro ao carregar fonte"**
   - **Causa:** Variáveis de ambiente não configuradas
   - **Solução:** Configurar todas as variáveis no dashboard do Render

## 🎯 Ordem Recomendada

```bash
# 1. Testar localmente primeiro
python3 testar_nina.py  # Deve passar todos os testes

# 2. Adicionar ao git
git add knowledge/ core/ app.py
git status  # Verificar o que vai ser commitado

# 3. Commit
git commit -m "feat: estrutura estilo Nina - sistema centralizado de conhecimento"

# 4. Push (Render vai fazer deploy automaticamente)
git push origin main

# 5. Monitorar logs no Render
# Dashboard → Seu serviço → Logs
```

## ✅ Checklist Final

Antes de fazer push, certifique-se:

- [ ] Testou localmente: `python3 testar_nina.py` passa
- [ ] Todos os arquivos `knowledge/` existem
- [ ] Todos os arquivos `core/` existem
- [ ] `app.py` tem os imports corretos
- [ ] Variáveis de ambiente estão configuradas no Render
- [ ] `render.yaml` está correto
- [ ] Backups foram feitos (já feito! ✅)

## 🚨 Importante!

**Os arquivos `knowledge/` e `core/` PRECISAM estar no git** para funcionar no Render!

Execute:
```bash
git add knowledge/ core/
git commit -m "feat: estrutura estilo Nina"
git push origin main
```

Depois disso, o Render fará deploy automático! 🎉




