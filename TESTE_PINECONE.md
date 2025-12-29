# 🧪 Guia de Teste do Pinecone

## ✅ Configuração Concluída

As seguintes configurações foram adicionadas ao seu `.env`:

- ✅ `PINECONE_API_KEY` - Configurada
- ✅ `PINECONE_INDEX_NAME=tina-chatbot-index`
- ✅ `EMBEDDING_PROVIDER=gemini`

## 📋 Variáveis no Render

Certifique-se de que as seguintes variáveis estão configuradas no Render:

```
PINECONE_API_KEY=pcsk_3SAvoQ_Jr2iD9CLSh5WvRNDSH4DG7PVwFhY3cG5kAeQxjrJieVTLp7pJVYdqTtnK8b5uLt
PINECONE_INDEX_NAME=tina-chatbot-index
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=sua_chave_gemini_aqui
```

## 🚀 Próximos Passos

### 1. Testar Conexão (no Render ou localmente)

No Render, você pode testar via console ou criar um endpoint de teste:

```python
# Adicione ao app.py
@app.route("/test-pinecone", methods=["GET"])
def test_pinecone():
    try:
        from core.pinecone_manager import create_manager_from_env
        manager = create_manager_from_env()
        
        if manager.test_connection():
            stats = manager.get_stats()
            return jsonify({
                "status": "success",
                "provider": manager.embedding_provider,
                "dimension": manager.embedding_dimension,
                "stats": stats
            })
        else:
            return jsonify({"status": "failed", "error": "Connection test failed"}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
```

### 2. Sincronizar Dados

Após o deploy no Render, você pode sincronizar os dados de duas formas:

#### Opção A: Via Script Local (recomendado para primeira vez)

```bash
# Instalar dependências localmente (se necessário)
pip install pinecone-client google-generativeai python-dotenv

# Sincronizar
python scripts/sync_to_pinecone.py
```

#### Opção B: Via Console do Render

1. Acesse o console do serviço no Render
2. Execute:
```bash
python scripts/sync_to_pinecone.py
```

### 3. Verificar Sincronização

Após sincronizar, você pode verificar:

```python
from core.pinecone_manager import create_manager_from_env

manager = create_manager_from_env()
stats = manager.get_stats()

print(f"Total de vetores: {stats['total_vector_count']}")
for ns, ns_stats in stats['namespaces'].items():
    print(f"Namespace {ns}: {ns_stats['vector_count']} vetores")
```

## 🔍 Teste de Busca

Após sincronizar, teste uma busca:

```python
from core.knowledge_manager import KnowledgeManager

km = KnowledgeManager()
resultados = km.search("Tiny ERP", locale="pt_BR")

for resultado in resultados:
    print(f"Fonte: {resultado['source']}")
    print(f"Conteúdo: {resultado['content'][:200]}...")
```

## ⚠️ Troubleshooting

### Erro: "Biblioteca Pinecone não instalada"

**Solução**: Certifique-se de que `pinecone-client==5.0.1` está no `requirements.txt` e foi instalado.

### Erro: "Index dimension mismatch"

**Solução**: 
- Se você mudou de provider (Gemini ↔ OpenAI), precisa deletar o índice antigo
- O índice será recriado automaticamente com as dimensões corretas

### Erro: "GEMINI_API_KEY é obrigatória"

**Solução**: Configure `GEMINI_API_KEY` no Render (ou `.env` localmente)

## 📊 Monitoramento

Você pode adicionar um endpoint de monitoramento:

```python
@app.route("/pinecone-stats", methods=["GET"])
def pinecone_stats():
    try:
        from core.pinecone_manager import create_manager_from_env
        manager = create_manager_from_env()
        stats = manager.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## ✅ Checklist

- [ ] Variáveis configuradas no Render
- [ ] Dependências instaladas (`requirements.txt` atualizado)
- [ ] Deploy realizado no Render
- [ ] Teste de conexão bem-sucedido
- [ ] Dados sincronizados para Pinecone
- [ ] Busca vetorial funcionando

## 🎉 Pronto!

Após completar os passos acima, o sistema de busca vetorial estará funcionando!

