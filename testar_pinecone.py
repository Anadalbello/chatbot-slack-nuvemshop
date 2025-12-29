#!/usr/bin/env python3
"""
Script de teste rápido para Pinecone
"""

import sys
import os
from pathlib import Path

# Carregar .env manualmente
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

print("🔍 Verificando variáveis de ambiente...")
print()

vars_check = {
    'PINECONE_API_KEY': os.getenv('PINECONE_API_KEY'),
    'PINECONE_INDEX_NAME': os.getenv('PINECONE_INDEX_NAME'),
    'EMBEDDING_PROVIDER': os.getenv('EMBEDDING_PROVIDER', 'gemini'),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY')
}

for var, value in vars_check.items():
    if value:
        masked = value[:10] + '...' + value[-5:] if len(value) > 15 else '***'
        print(f'✅ {var}: {masked}')
    else:
        print(f'❌ {var}: NÃO CONFIGURADO')

print()
print('📋 Status:')
if all([vars_check['PINECONE_API_KEY'], vars_check['PINECONE_INDEX_NAME']]):
    print('✅ Pinecone: Configurado')
else:
    print('❌ Pinecone: Faltando configurações')
    sys.exit(1)

if vars_check['GEMINI_API_KEY']:
    print('✅ Gemini: Configurado')
else:
    print('⚠️ Gemini: Não configurado (necessário se EMBEDDING_PROVIDER=gemini)')

print()
print("=" * 50)
print()

# Tentar importar e testar
try:
    print('🔌 Testando conexão com Pinecone...')
    print()
    
    from core.pinecone_manager import create_manager_from_env
    
    manager = create_manager_from_env()
    print(f'✅ PineconeManager criado')
    print(f'   - Provider: {manager.embedding_provider}')
    print(f'   - Dimensão: {manager.embedding_dimension}')
    print()
    
    print('🧪 Testando conexão...')
    if manager.test_connection():
        print('✅ Conexão com Pinecone bem-sucedida!')
        print()
        
        # Obter estatísticas
        stats = manager.get_stats()
        print(f'📊 Estatísticas do índice:')
        print(f'   - Total de vetores: {stats["total_vector_count"]}')
        print(f'   - Dimensão: {stats["dimension"]}')
        if stats.get('namespaces'):
            print(f'   - Namespaces: {list(stats["namespaces"].keys())}')
            for ns, ns_stats in stats['namespaces'].items():
                print(f'      • {ns}: {ns_stats["vector_count"]} vetores')
        else:
            print('   - Namespaces: (nenhum dado indexado ainda)')
            print()
            print('💡 Próximo passo: Execute "python scripts/sync_to_pinecone.py" para indexar dados')
    else:
        print('❌ Falha na conexão com Pinecone')
        sys.exit(1)
        
except ImportError as e:
    print(f'❌ Erro de importação: {e}')
    print()
    print('💡 Instale as dependências:')
    print('   pip install pinecone-client google-generativeai python-dotenv')
    sys.exit(1)
except Exception as e:
    print(f'❌ Erro: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 50)
print("✅ Teste concluído com sucesso!")

