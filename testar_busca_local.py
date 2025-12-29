#!/usr/bin/env python3
"""
Script para testar busca vetorial localmente
Execute: python testar_busca_local.py
"""

import sys
import os
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

# Carregar .env manualmente
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

print("=" * 60)
print("🔍 TESTE DE BUSCA VETORIAL")
print("=" * 60)
print()

try:
    from core.pinecone_manager import create_manager_from_env
    from core.knowledge_manager import KnowledgeManager
    
    # Inicializar
    print("🔌 Conectando ao Pinecone...")
    manager = create_manager_from_env()
    print(f"✅ Conectado (provider: {manager.embedding_provider})")
    print()
    
    # Verificar se há dados
    stats = manager.get_stats()
    total_vectors = stats.get('total_vector_count', 0)
    
    if total_vectors == 0:
        print("⚠️ Nenhum dado indexado ainda!")
        print("   Execute: python scripts/sync_to_pinecone.py")
        sys.exit(1)
    
    print(f"📊 Total de vetores no índice: {total_vectors}")
    print()
    
    # Testar buscas
    test_queries = [
        "Tiny ERP",
        "integração com tabela de frete",
        "Omie",
        "rastreio de pedidos"
    ]
    
    print("🔍 Testando buscas...")
    print()
    
    for query in test_queries:
        print(f"Query: '{query}'")
        print("-" * 40)
        
        try:
            # Busca direta no Pinecone
            results = manager.query_similar(
                query_text=query,
                top_k=3,
                namespace="br"
            )
            
            if results:
                for i, result in enumerate(results, 1):
                    metadata = result.get('metadata', {})
                    score = result.get('score', 0)
                    nome = metadata.get('nome', 'N/A')
                    print(f"  {i}. {nome} (score: {score:.3f})")
            else:
                print("  ⚠️ Nenhum resultado encontrado")
            
            print()
            
            # Busca via KnowledgeManager (com fallback)
            print(f"  Via KnowledgeManager:")
            km = KnowledgeManager()
            km_results = km.search(query, locale="pt_BR", limit=3)
            
            if km_results:
                for i, result in enumerate(km_results, 1):
                    source = result.get('source', 'unknown')
                    score = result.get('score', 'N/A')
                    content_preview = str(result.get('content', ''))[:100]
                    print(f"    {i}. [{source}] {content_preview}... (score: {score})")
            else:
                print("    ⚠️ Nenhum resultado encontrado")
            
        except Exception as e:
            print(f"  ❌ Erro: {e}")
        
        print()
    
    print("=" * 60)
    print("✅ TESTE DE BUSCA CONCLUÍDO!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

