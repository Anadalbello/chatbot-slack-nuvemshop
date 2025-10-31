# Backup do Chatbot - 20251029_110355

## 📋 Informações do Backup

- **Data:** 29/10/2025 11:03:55
- **Motivo:** Backup antes da refatoração para padrão Nina
- **Arquivos salvos:** 24 arquivos, 1 diretórios

## 📁 Conteúdo do Backup

### Arquivos principais:
- `app.py`
- `app_emergency.py`
- `app_simple.py`
- `requirements.txt`
- `runtime.txt`
- `render.yaml`
- `.env`
- `faq_database.json`
- `perguntas_log.json`
- `test_google_sheets.py`
- `testar_token_confluence.py`
- `teste_pre_deploy.py`
- `teste_zendesk_api.py`
- `diagnostico_confluence.py`
- `diagnostico.py`
- `config_zendesk.py`
- `configurar_env.py`
- `verificar_config_render.py`
- `sincronizar_integracoes_manual.py`
- `listar_espacos_confluence.py`
- `rovo_alternatives.md`
- `CONFLUENCE_DATABASE_LIMITACOES.md`
- `GOOGLE_SHEETS_SETUP.md`
- `DEPLOY_RESUMO.md`


### Diretórios:
- `handlers//`

## 🔄 Como Restaurar

Se precisar voltar à versão antiga:

1. **Fazer backup da versão nova primeiro:**
   ```bash
   # Garantir que não perde nada da nova versão
   ```

2. **Restaurar arquivos:**
   ```bash
   # Da raiz do projeto, copiar arquivos do backup
   cp -r backup_pre_refatoracao_nina_20251029_110355/* .
   ```

3. **Ou restaurar seletivamente:**
   ```bash
   # Restaurar apenas app.py
   cp backup_pre_refatoracao_nina_20251029_110355/app.py .
   
   # Restaurar handlers
   cp -r backup_pre_refatoracao_nina_20251029_110355/handlers/* handlers/
   
   # Restaurar .env (cuidado!)
   cp backup_pre_refatoracao_nina_20251029_110355/.env .env
   ```

## ⚠️ Observações Importantes

- O arquivo `.env` **FOI incluído** no backup (conforme solicitado)
- O ambiente virtual `venv/` não foi incluído (recrie com `python -m venv venv`)
- Arquivos compilados `__pycache__` não foram incluídos

## 🚀 Próximos Passos

Após este backup, podemos iniciar a refatoração seguramente!

## 📊 Estatísticas

- **Total de arquivos:** 24
- **Total de diretórios:** 1
- **Erros durante cópia:** 0
