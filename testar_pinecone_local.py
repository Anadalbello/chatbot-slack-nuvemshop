#!/usr/bin/env python3
"""
Script para testar Pinecone localmente
Execute: python testar_pinecone_local.py
"""

import sys
import os
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

# Carregar .env manualmente
env_file = Path('.env')
if env_file.exists():
    print("📂 Carregando variáveis do .env...")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    print("✅ Variáveis carregadas\n")
else:
    print("⚠️ Arquivo .env não encontrado\n")

print("=" * 60)
print("🧪 TESTE LOCAL DO PINECONE")
print("=" * 60)
print()

# 1. Verificar variáveis
print("1️⃣ Verificando variáveis de ambiente...")
print()

vars_check = {
    'PINECONE_API_KEY': os.getenv('PINECONE_API_KEY'),
    'PINECONE_INDEX_NAME': os.getenv('PINECONE_INDEX_NAME'),
    'EMBEDDING_PROVIDER': os.getenv('EMBEDDING_PROVIDER', 'gemini'),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY')
}

all_ok = True
for var, value in vars_check.items():
    if value:
        masked = value[:10] + '...' + value[-5:] if len(value) > 15 else '***'
        print(f'   ✅ {var}: {masked}')
    else:
        print(f'   ❌ {var}: NÃO CONFIGURADO')
        all_ok = False

if not all_ok:
    print("\n❌ Algumas variáveis estão faltando!")
    print("   Configure-as no arquivo .env")
    sys.exit(1)

print("\n✅ Todas as variáveis configuradas!")
print()

# 2. Verificar dependências
print("2️⃣ Verificando dependências...")
print()

try:
    import pinecone
    print("   ✅ pinecone-client instalado")
except ImportError:
    print("   ❌ pinecone-client NÃO instalado")
    print("   Execute: pip install pinecone-client==5.0.1")
    sys.exit(1)

try:
    import google.generativeai
    print("   ✅ google-generativeai instalado")
except ImportError:
    print("   ❌ google-generativeai NÃO instalado")
    print("   Execute: pip install google-generativeai==0.8.5")
    sys.exit(1)

print("\n✅ Todas as dependências instaladas!")
print()

# 3. Testar conexão
print("3️⃣ Testando conexão com Pinecone...")
print()

try:
    from core.pinecone_manager import create_manager_from_env
    
    manager = create_manager_from_env()
    print(f"   ✅ PineconeManager criado")
    print(f"      - Provider: {manager.embedding_provider}")
    print(f"      - Dimensão: {manager.embedding_dimension}")
    print(f"      - Índice: {manager.index_name}")
    print()
    
    print("   🔌 Testando conexão...")
    if manager.test_connection():
        print("   ✅ Conexão bem-sucedida!")
        print()
        
        # Obter estatísticas
        stats = manager.get_stats()
        print("   📊 Estatísticas do índice:")
        print(f"      - Total de vetores: {stats['total_vector_count']}")
        print(f"      - Dimensão: {stats['dimension']}")
        
        if stats.get('namespaces'):
            print(f"      - Namespaces: {list(stats['namespaces'].keys())}")
            for ns, ns_stats in stats['namespaces'].items():
                print(f"         • {ns}: {ns_stats['vector_count']} vetores")
        else:
            print("      - Namespaces: (nenhum dado indexado ainda)")
            print()
            print("   💡 Próximo passo: Execute 'python scripts/sync_to_pinecone.py' para indexar dados")
    else:
        print("   ❌ Falha na conexão")
        sys.exit(1)
        
except ValueError as e:
    print(f"   ❌ Erro de configuração: {e}")
    print("   Verifique as variáveis de ambiente no .env")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("✅ TESTE CONCLUÍDO COM SUCESSO!")
print("=" * 60)
print()
print("📋 Próximos passos:")
print("   1. Sincronizar dados: python scripts/sync_to_pinecone.py")
print("   2. Testar busca: python testar_busca_local.py")
print("   3. Iniciar servidor: python app.py")
print("   4. Testar endpoints: http://localhost:3000/test-pinecone")


