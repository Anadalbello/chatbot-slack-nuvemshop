# 🧪 Guia de Teste - Chatbot Estilo Nina

## ✅ Estrutura Validada

Todos os componentes foram criados e integrados com sucesso:
- ✅ `knowledge/` - Configurações das fontes
- ✅ `core/` - Módulos estilo Nina
- ✅ `app.py` - Integrado com nova estrutura

## 🚀 Como Testar

### 1. Ativar Ambiente Virtual

```bash
cd /home/anabello/Área\ de\ trabalho/Codes/chatbot_gemini_completo_final/chatbot_gemini
source venv/bin/activate
```

### 2. Verificar Configurações

```bash
# Verificar se .env existe e tem as variáveis necessárias
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('SLACK_BOT_TOKEN:', '✅' if os.getenv('SLACK_BOT_TOKEN') else '❌'); print('GEMINI_API_KEY:', '✅' if os.getenv('GEMINI_API_KEY') else '❌')"
```

### 3. Rodar o App

```bash
python3 app.py
```

Ou usando gunicorn (produção):
```bash
gunicorn app:app
```

### 4. Testar Endpoints

Em outro terminal:

```bash
# Health check
curl http://localhost:3000/health

# Test endpoint
curl http://localhost:3000/test
```

### 5. Testar no Slack

**Mensagens para testar:**

1. **Cumprimento (greeting):**
   - `@bot oi`
   - `@bot olá`
   - `@bot bom dia`

2. **Menu:**
   - `@bot menu`
   - `@bot ajuda`

3. **Listar integrações:**
   - `@bot listar integrações`
   - `@bot quais integrações temos?`

4. **Busca geral (search_knowledge):**
   - `@bot como integrar com Magento?`
   - `@bot temos integração com Tray?`
   - `@bot como calcular frete?`

5. **Integração específica:**
   - `@bot integração Magento`
   - `@bot informa sobre Bling`

6. **Sem resultado (para testar validação):**
   - `@bot como fazer um foguete?` (não deve responder se não tiver fonte)

## 📊 O Que Observar nos Logs

### ✅ Sinais de Sucesso:

1. **Inicialização:**
   ```
   ✅ Sistema estilo Nina inicializado
   ✅ Knowledge Manager inicializado: 3 fontes ativas
   ✅ Recepcionista inicializada
   ✅ FonteValidator inicializado
   ```

2. **Processamento de mensagem:**
   ```
   🧠 Recepcionista: Analisando pergunta...
   🎯 Intent detectado: search_knowledge
   🔍 Iniciando busca em 3 fontes para: 'como integrar...'
   ✅ Resultado válido encontrado em 'google_sheets'
   ```

3. **Validação:**
   ```
   🔍 Validando 1 resultados
   ✅ 1 resultados válidos encontrados
   ```

### ❌ Possíveis Problemas:

1. **Erro ao carregar fontes:**
   ```
   ❌ Erro ao carregar fonte 'google_sheets': ...
   ```
   → Verificar se handlers existem e estão corretos

2. **Nenhuma fonte válida:**
   ```
   ⚠️ Nenhuma fonte válida encontrada - não respondendo
   ```
   → Normal se a busca realmente não encontrar nada

3. **Erro na recepcionista:**
   ```
   ❌ Erro na recepcionista: ...
   ```
   → Verificar se GEMINI_API_KEY está configurada

## 🔧 Troubleshooting

### Problema: "ModuleNotFoundError: No module named 'core'"

**Solução:** Certifique-se de estar no diretório correto:
```bash
cd /home/anabello/Área\ de\ trabalho/Codes/chatbot_gemini_completo_final/chatbot_gemini
```

### Problema: "Erro ao carregar fonte"

**Solução:** Verificar se os handlers existem:
```bash
ls handlers/buscar_integracoes_sheets_publico.py
ls handlers/confluence_com_resumo.py
ls handlers/zendesk_api.py
```

### Problema: Recepcionista não funciona

**Solução:** Verificar variável de ambiente:
```bash
echo $GEMINI_API_KEY  # Deve mostrar a chave (ou estar no .env)
```

## 📝 Notas Importantes

1. **FAQ não é fonte de busca** - Como solicitado, FAQ foi removida das fontes

2. **Prioridades:**
   - Google Sheets (prioridade 1)
   - Confluence (prioridade 2)  
   - Zendesk (prioridade 3)

3. **Validação estilo Nina:**
   - Só responde se tiver fonte válida
   - Rejeita resultados com palavras de erro
   - Valida tamanho mínimo de resultado

4. **Mantido:**
   - Sistema de anti-duplicação
   - Menus e botões interativos
   - Sistema de aprendizado automático
   - Endpoints de health e analytics

## ✨ Próximos Passos

Após validar que tudo funciona:
- Testar com perguntas reais
- Ajustar prompts da recepcionista se necessário
- Implementar busca de contexto da thread
- Monitorar uso de tokens


