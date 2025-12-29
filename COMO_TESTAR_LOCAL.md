# 🧪 Como Testar Pinecone Localmente

Guia passo a passo para testar o sistema de busca vetorial com Pinecone no seu ambiente local.

## 📋 Pré-requisitos

1. Python 3.8+ instalado
2. Arquivo `.env` configurado com as variáveis necessárias
3. Conexão com internet (para acessar Pinecone e Gemini APIs)

## 🔧 Passo 1: Instalar Dependências

### Opção A: Usando pip diretamente

```bash
cd "/home/anabello/Área de trabalho/Codes/Tina chatbot/chatbot_Tina"
pip install pinecone-client==5.0.1 google-generativeai==0.8.5 python-dotenv
```

### Opção B: Usando requirements.txt

```bash
cd "/home/anabello/Área de trabalho/Codes/Tina chatbot/chatbot_Tina"
pip install -r requirements.txt
```

### Opção C: Criar/Usar ambiente virtual (recomendado)

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## ✅ Passo 2: Verificar Configuração

Certifique-se de que o arquivo `.env` contém:

```bash
PINECONE_API_KEY=pcsk_3SAvoQ_Jr2iD9CLSh5WvRNDSH4DG7PVwFhY3cG5kAeQxjrJieVTLp7pJVYdqTtnK8b5uLt
PINECONE_INDEX_NAME=tina-chatbot-index
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=sua_chave_gemini_aqui
```

## 🧪 Passo 3: Testar Conexão

Execute o script de teste:

```bash
python testar_pinecone_local.py
```

Este script vai:
- ✅ Verificar variáveis de ambiente
- ✅ Verificar dependências instaladas
- ✅ Testar conexão com Pinecone
- ✅ Mostrar estatísticas do índice

**Saída esperada:**
```
🧪 TESTE LOCAL DO PINECONE
============================================================

1️⃣ Verificando variáveis de ambiente...
   ✅ PINECONE_API_KEY: pcsk_3SAvo...
   ✅ PINECONE_INDEX_NAME: tina-chatb...
   ✅ EMBEDDING_PROVIDER: gemini
   ✅ GEMINI_API_KEY: AIzaSyAMK8...

✅ Todas as variáveis configuradas!

2️⃣ Verificando dependências...
   ✅ pinecone-client instalado
   ✅ google-generativeai instalado

✅ Todas as dependências instaladas!

3️⃣ Testando conexão com Pinecone...
   ✅ PineconeManager criado
      - Provider: gemini
      - Dimensão: 768
      - Índice: tina-chatbot-index
   
   🔌 Testando conexão...
   ✅ Conexão bem-sucedida!
   
   📊 Estatísticas do índice:
      - Total de vetores: 0
      - Dimensão: 768
      - Namespaces: (nenhum dado indexado ainda)
   
   💡 Próximo passo: Execute 'python scripts/sync_to_pinecone.py' para indexar dados
```

## 📤 Passo 4: Sincronizar Dados

Após verificar que a conexão está funcionando, sincronize os dados:

```bash
python scripts/sync_to_pinecone.py
```

**Opções disponíveis:**
```bash
# Sincronização básica (namespace br)
python scripts/sync_to_pinecone.py

# Forçar reindexação completa
python scripts/sync_to_pinecone.py --force

# Especificar namespace diferente
python scripts/sync_to_pinecone.py --namespace br

# Especificar arquivo JSON diferente
python scripts/sync_to_pinecone.py --json knowledge/integracoes.json
```

**Saída esperada:**
```
📂 Carregando integrações de: knowledge/integracoes.json
✅ Carregadas 150 integrações do JSON
✅ Preparadas 150 integrações para indexação
🔌 Conectando ao Pinecone...
📤 Indexando 150 integrações no namespace 'br'...
✅ Sincronização concluída: 150 integrações indexadas
📊 Estatísticas do namespace 'br': 150 vetores
```

## 🔍 Passo 5: Testar Busca Vetorial

Teste a busca vetorial:

```bash
python testar_busca_local.py
```

Este script vai:
- ✅ Testar buscas diretas no Pinecone
- ✅ Testar buscas via KnowledgeManager (com fallback)
- ✅ Mostrar resultados e scores de relevância

## 🚀 Passo 6: Iniciar Servidor Local

Inicie o servidor Flask para testar os endpoints:

```bash
python app.py
```

O servidor iniciará em `http://localhost:3000`

## 🌐 Passo 7: Testar Endpoints

Com o servidor rodando, teste os endpoints:

### 1. Teste de Conexão
```bash
curl http://localhost:3000/test-pinecone
```

Ou abra no navegador:
```
http://localhost:3000/test-pinecone
```

### 2. Estatísticas
```bash
curl http://localhost:3000/pinecone-stats
```

### 3. Teste de Busca
```bash
curl "http://localhost:3000/test-vector-search?query=Tiny&namespace=br&top_k=3"
```

## 🐛 Troubleshooting

### Erro: "No module named 'pinecone'"

**Solução:**
```bash
pip install pinecone-client==5.0.1
```

### Erro: "No module named 'google'"

**Solução:**
```bash
pip install google-generativeai==0.8.5
```

### Erro: "PINECONE_API_KEY environment variable is required"

**Solução:**
1. Verifique se o arquivo `.env` existe
2. Verifique se a variável está configurada
3. Certifique-se de que está no diretório correto ao executar os scripts

### Erro: "Index dimension mismatch"

**Solução:**
O índice foi criado com dimensões diferentes. Delete e recrie:

```bash
# No console do Pinecone (app.pinecone.io) ou via código
python scripts/sync_to_pinecone.py --force
```

### Erro: "GEMINI_API_KEY é obrigatória"

**Solução:**
Configure `GEMINI_API_KEY` no `.env` ou mude para OpenAI:

```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sua_chave_openai
```

## 📊 Verificar Logs

Os scripts geram logs detalhados. Para ver mais informações:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## ✅ Checklist de Teste Local

- [ ] Dependências instaladas
- [ ] Variáveis de ambiente configuradas no `.env`
- [ ] Teste de conexão bem-sucedido (`testar_pinecone_local.py`)
- [ ] Dados sincronizados (`sync_to_pinecone.py`)
- [ ] Busca vetorial funcionando (`testar_busca_local.py`)
- [ ] Servidor local iniciado (`python app.py`)
- [ ] Endpoints respondendo corretamente

## 🎉 Pronto!

Após completar todos os passos, o sistema de busca vetorial estará funcionando localmente e você poderá testar todas as funcionalidades antes de fazer deploy no Render!

