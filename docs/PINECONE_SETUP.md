# 🧠 Guia de Configuração do Pinecone para Chatbot Tina

Este guia explica como configurar e usar o sistema de busca vetorial com Pinecone no Chatbot Tina.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Configuração Inicial](#configuração-inicial)
4. [Sincronização de Dados](#sincronização-de-dados)
5. [Como Funciona](#como-funciona)
6. [Troubleshooting](#troubleshooting)

## 🎯 Visão Geral

O Pinecone permite busca semântica (por significado) ao invés de busca por palavras-chave exatas. Isso significa que o bot pode encontrar respostas relevantes mesmo quando:

- As palavras são diferentes mas o significado é similar
- O usuário usa sinônimos ou variações
- A pergunta está em formato diferente do texto indexado

### Vantagens da Busca Vetorial

✅ **Busca por significado**: Encontra resultados mesmo com palavras diferentes  
✅ **Melhor relevância**: Resultados ordenados por similaridade semântica  
✅ **Suporte multi-idioma**: Namespaces separados por país/idioma  
✅ **Escalável**: Suporta milhões de documentos  

## 📦 Pré-requisitos

### 1. Contas Necessárias

- **Pinecone**: Conta gratuita disponível em [pinecone.io](https://www.pinecone.io)
- **Google Gemini**: Conta com API key (para gerar embeddings) - **RECOMENDADO**
- **OpenAI**: Conta com API key (opcional, para usar OpenAI ao invés de Gemini)

### 2. Dependências Python

As dependências já estão no `requirements.txt`:

```bash
pip install pinecone-client==5.0.1
pip install google-generativeai==0.8.5  # Para Gemini (padrão)
# pip install openai==1.54.5  # Apenas se usar OpenAI
```

Ou instale todas as dependências:

```bash
pip install -r requirements.txt
```

**Nota**: Se usar apenas Gemini (padrão), não precisa instalar `openai`.

## ⚙️ Configuração Inicial

### 1. Obter Credenciais

#### Pinecone API Key

1. Acesse [app.pinecone.io](https://app.pinecone.io)
2. Crie uma conta ou faça login
3. Vá em **API Keys** e copie sua API key
4. Anote o nome do seu índice (ou crie um novo)

#### Google Gemini API Key (Recomendado)

1. Acesse [aistudio.google.com](https://aistudio.google.com)
2. Vá em **Get API Key** ou **API Keys**
3. Crie uma nova API key ou use uma existente

#### OpenAI API Key (Opcional)

1. Acesse [platform.openai.com](https://platform.openai.com)
2. Vá em **API Keys**
3. Crie uma nova API key ou use uma existente
4. **Nota**: Só necessário se quiser usar OpenAI ao invés de Gemini

### 2. Configurar Variáveis de Ambiente

Adicione as seguintes variáveis ao seu arquivo `.env` ou variáveis de ambiente:

```bash
# Pinecone
PINECONE_API_KEY=sua_api_key_aqui
PINECONE_INDEX_NAME=tina-chatbot-index
PINECONE_CLOUD=aws  # Opcional, padrão: aws
PINECONE_REGION=us-east-1  # Opcional, padrão: us-east-1

# Embeddings (escolha um provider)
EMBEDDING_PROVIDER=gemini  # ou "openai" (padrão: gemini)
GEMINI_API_KEY=sua_gemini_api_key_aqui  # Obrigatório se provider=gemini
OPENAI_API_KEY=sua_openai_api_key_aqui  # Obrigatório se provider=openai
```

### 3. Criar Índice no Pinecone

O índice será criado automaticamente na primeira execução, mas você pode criar manualmente:

1. Acesse [app.pinecone.io](https://app.pinecone.io)
2. Clique em **Create Index**
3. Configure:
   - **Name**: `tina-chatbot-index` (ou o nome que você escolheu)
   - **Dimensions**: 
     - `768` se usar **Gemini** (padrão)
     - `1536` se usar **OpenAI**
   - **Metric**: `cosine` (recomendado)
   - **Cloud**: `AWS` (ou sua preferência)
   - **Region**: `us-east-1` (ou região próxima)

**Nota**: O índice será criado automaticamente com as dimensões corretas na primeira execução, então você não precisa criar manualmente.

## 📤 Sincronização de Dados

### Sincronizar Integrações para Pinecone

Use o script de sincronização para indexar as integrações:

```bash
# Sincronização básica (namespace br)
python scripts/sync_to_pinecone.py

# Sincronizar namespace específico
python scripts/sync_to_pinecone.py --namespace br

# Forçar reindexação completa (deleta e recria)
python scripts/sync_to_pinecone.py --force

# Especificar arquivo JSON diferente
python scripts/sync_to_pinecone.py --json knowledge/integracoes.json

# Usar locale para determinar namespace automaticamente
python scripts/sync_to_pinecone.py --locale pt_BR
```

### Namespaces por País/Idioma

O sistema suporta múltiplos namespaces para separar dados por país:

- `br` - Brasil (português)
- `ar` - Argentina (espanhol)
- `mx` - México (espanhol)
- `co` - Colômbia (espanhol)
- `cl` - Chile (espanhol)
- `es` - Espanha (espanhol)

Para sincronizar para diferentes países:

```bash
# Brasil
python scripts/sync_to_pinecone.py --namespace br --locale pt_BR

# Argentina
python scripts/sync_to_pinecone.py --namespace ar --locale es_AR

# México
python scripts/sync_to_pinecone.py --namespace mx --locale es_MX
```

## 🔍 Como Funciona

### Fluxo de Busca

1. **Usuário faz pergunta**: "Tiny tem etiquetas?"
2. **Recepcionista analisa**: Detecta idioma e intent
3. **Busca Vetorial (Pinecone)**:
   - Gera embedding da pergunta usando OpenAI
   - Busca no Pinecone por similaridade semântica
   - Retorna top 5 resultados mais relevantes
4. **Busca Tradicional** (fallback):
   - Se busca vetorial não encontrar resultados relevantes
   - Busca nas fontes tradicionais (JSON, Confluence, etc.)
5. **Formatação e Resposta**:
   - Formata resultados usando Gemini
   - Envia resposta ao usuário

### Prioridade de Busca

O sistema usa a seguinte ordem de prioridade:

1. **Pinecone (Busca Vetorial)** - Prioridade 0
   - Busca por significado
   - Threshold de relevância: 0.7 (70%)
   - Se encontrar resultados relevantes, pode parar aqui

2. **Integrações JSON** - Prioridade 1
   - Busca em arquivo JSON local

3. **Google Sheets** - Prioridade 2
   - Busca em planilha Google (se habilitado)

4. **Confluence** - Prioridade 3
   - Busca no Confluence (se habilitado)

5. **Zendesk** - Prioridade 4
   - Busca no Zendesk (se habilitado)

### Configuração de Estratégia

Edite `knowledge/sources_config.json` para ajustar a estratégia:

```json
{
  "search_strategy": {
    "mode": "priority_based",
    "stop_on_first_success": false,
    "max_results": 5,
    "combine_results": true,
    "require_at_least_one_source": true,
    "use_vector_search_first": true,
    "vector_search_threshold": 0.7
  }
}
```

- `use_vector_search_first`: Usar busca vetorial primeiro (padrão: true)
- `vector_search_threshold`: Score mínimo para considerar relevante (0.0-1.0)
- `stop_on_first_success`: Parar após primeiro resultado válido

## 🐛 Troubleshooting

### Erro: "PINECONE_API_KEY environment variable is required"

**Solução**: Verifique se a variável de ambiente está configurada:

```bash
# Linux/Mac
export PINECONE_API_KEY=sua_chave

# Windows
set PINECONE_API_KEY=sua_chave

# Ou adicione ao .env
echo "PINECONE_API_KEY=sua_chave" >> .env
```

### Erro: "GEMINI_API_KEY é obrigatória quando EMBEDDING_PROVIDER=gemini"

**Solução**: Configure a chave do Gemini:

```bash
export EMBEDDING_PROVIDER=gemini
export GEMINI_API_KEY=sua_chave_gemini
```

Ou se preferir usar OpenAI:

```bash
export EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY=sua_chave_openai
```

### Erro: "Index dimension mismatch"

**Solução**: O índice deve ter dimensão correta baseada no provider:
- **768** para Gemini (padrão)
- **1536** para OpenAI

O script criará automaticamente com dimensões corretas:

```bash
python scripts/sync_to_pinecone.py --force
```

**Importante**: Se você mudar de provider (Gemini ↔ OpenAI), precisa deletar o índice antigo e criar um novo, pois as dimensões são diferentes.

### Busca vetorial não está funcionando

**Verificações**:

1. **Teste de conexão**:
```python
from core.pinecone_manager import create_manager_from_env
manager = create_manager_from_env()
if manager.test_connection():
    print(f"✅ Pinecone conectado! Provider: {manager.embedding_provider}")
else:
    print("❌ Erro na conexão")
```

2. **Verificar se há dados indexados**:
```python
stats = manager.get_stats()
print(f"Vetores totais: {stats['total_vector_count']}")
print(f"Namespaces: {list(stats['namespaces'].keys())}")
```

3. **Verificar logs**: Procure por mensagens como:
   - `✅ Pinecone inicializado e conectado`
   - `🔍 [Vetorial] Buscando no Pinecone`

### Resultados não relevantes

**Ajustes**:

1. **Aumentar threshold** em `sources_config.json`:
```json
"vector_search_threshold": 0.8  // Mais restritivo
```

2. **Reindexar dados**: Garanta que os dados estão atualizados:
```bash
python scripts/sync_to_pinecone.py --force
```

3. **Verificar qualidade dos dados**: Certifique-se de que o JSON tem descrições completas

### Performance lenta

**Otimizações**:

1. **Reduzir top_k**: Buscar menos resultados:
```python
# Em knowledge_manager.py, ajustar limit
resultados_busca = knowledge_manager.search(query_busca, limit=3)
```

2. **Usar stop_on_first_success**: Parar após primeiro resultado:
```json
"stop_on_first_success": true
```

3. **Cache de embeddings**: Os embeddings são gerados a cada busca. Para otimizar, considere cachear embeddings de queries frequentes.

## 📊 Monitoramento

### Verificar Estatísticas

```python
from core.pinecone_manager import create_manager_from_env

manager = create_manager_from_env()
stats = manager.get_stats()

print(f"Total de vetores: {stats['total_vector_count']}")
for namespace, ns_stats in stats['namespaces'].items():
    print(f"Namespace '{namespace}': {ns_stats['vector_count']} vetores")
```

### Logs

O sistema gera logs detalhados:

- `✅ Pinecone inicializado` - Pinecone configurado com sucesso
- `🔍 [Vetorial] Buscando` - Busca vetorial iniciada
- `✅ [Vetorial] Resultado encontrado` - Resultado relevante encontrado
- `⚠️ Erro na busca vetorial` - Erro (continua com busca tradicional)

## 🔄 Atualização de Dados

### Quando Reindexar

Reindexe quando:

- ✅ Novas integrações adicionadas ao JSON
- ✅ Descrições de integrações atualizadas
- ✅ Mudanças significativas nos dados
- ✅ Problemas de relevância nos resultados

### Processo de Reindexação

```bash
# 1. Fazer backup (opcional)
cp knowledge/integracoes.json knowledge/integracoes.json.backup

# 2. Atualizar JSON
# (edite knowledge/integracoes.json)

# 3. Reindexar
python scripts/sync_to_pinecone.py --force
```

## 📚 Referências

- [Documentação Pinecone](https://docs.pinecone.io/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Como Funciona a Vectorização](./HOW_VECTORIZATION_WORKS.md) (baseado no Nina)

## ✅ Checklist de Configuração

- [ ] Conta Pinecone criada
- [ ] Conta Google Gemini com API key (ou OpenAI se preferir)
- [ ] Variáveis de ambiente configuradas (`EMBEDDING_PROVIDER`, `GEMINI_API_KEY` ou `OPENAI_API_KEY`)
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Índice Pinecone criado automaticamente na primeira execução
- [ ] Dados sincronizados (`python scripts/sync_to_pinecone.py`)
- [ ] Teste de conexão bem-sucedido
- [ ] Busca vetorial funcionando (verificar logs)

## 🎉 Pronto!

Agora o Chatbot Tina está configurado com busca vetorial usando **Google Gemini**! As buscas serão mais inteligentes e encontrarão resultados relevantes mesmo com palavras diferentes.

### Provider de Embeddings

Por padrão, o sistema usa **Gemini** para gerar embeddings. Isso significa:
- ✅ Usa a mesma API key do Gemini que você já tem configurada
- ✅ Não precisa de conta OpenAI adicional
- ✅ Embeddings de 768 dimensões (mais eficiente)
- ✅ Integração nativa com o resto do sistema

Para usar OpenAI ao invés de Gemini, configure:

```bash
export EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY=sua_chave_openai
```

### Desabilitar Busca Vetorial

Para desabilitar temporariamente a busca vetorial, edite `knowledge/sources_config.json`:

```json
"use_vector_search_first": false
```

