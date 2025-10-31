#!/usr/bin/env python3
"""
Script de teste para validar a nova estrutura estilo Nina
"""

import os
import sys
import json
from pathlib import Path

def testar_estrutura():
    """Testa se a estrutura está correta"""
    print("🧪 Testando estrutura estilo Nina...\n")
    
    erros = []
    
    # Testar diretórios
    print("1️⃣ Verificando diretórios...")
    if not Path("knowledge").exists():
        erros.append("❌ Diretório 'knowledge' não existe")
    else:
        print("   ✅ knowledge/ existe")
    
    if not Path("core").exists():
        erros.append("❌ Diretório 'core' não existe")
    else:
        print("   ✅ core/ existe")
    
    # Testar arquivos JSON
    print("\n2️⃣ Verificando arquivos de configuração...")
    
    if not Path("knowledge/sources_config.json").exists():
        erros.append("❌ knowledge/sources_config.json não existe")
    else:
        print("   ✅ sources_config.json existe")
        try:
            with open("knowledge/sources_config.json", 'r') as f:
                config = json.load(f)
                sources = config.get('sources', [])
                print(f"   ✅ {len(sources)} fontes configuradas")
                
                # Verificar prioridades
                for source in sources:
                    if source.get('enabled'):
                        print(f"      - {source['name']} (prioridade {source['priority']})")
        except Exception as e:
            erros.append(f"❌ Erro ao ler sources_config.json: {e}")
    
    if not Path("knowledge/context_rules.json").exists():
        erros.append("❌ knowledge/context_rules.json não existe")
    else:
        print("   ✅ context_rules.json existe")
    
    # Testar módulos Python
    print("\n3️⃣ Verificando módulos core...")
    
    arquivos_core = ['__init__.py', 'knowledge_manager.py', 'recepcionista.py', 'fonte_validator.py']
    for arquivo in arquivos_core:
        if not Path(f"core/{arquivo}").exists():
            erros.append(f"❌ core/{arquivo} não existe")
        else:
            print(f"   ✅ {arquivo} existe")
    
    # Verificar imports no app.py
    print("\n4️⃣ Verificando integração no app.py...")
    try:
        with open("app.py", 'r') as f:
            content = f.read()
            if "from core import" in content:
                print("   ✅ app.py importa módulos core")
            else:
                erros.append("❌ app.py não importa módulos core")
            
            if "KnowledgeManager" in content and "Recepcionista" in content:
                print("   ✅ app.py usa KnowledgeManager e Recepcionista")
            else:
                erros.append("❌ app.py não usa KnowledgeManager/Recepcionista")
    except Exception as e:
        erros.append(f"❌ Erro ao ler app.py: {e}")
    
    # Resumo
    print("\n" + "="*50)
    if erros:
        print("❌ ERROS ENCONTRADOS:")
        for erro in erros:
            print(f"   {erro}")
        return False
    else:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("\n📋 Estrutura criada com sucesso:")
        print("   - knowledge/ (configurações)")
        print("   - core/ (módulos estilo Nina)")
        print("   - app.py (integrado)")
        return True

if __name__ == "__main__":
    success = testar_estrutura()
    sys.exit(0 if success else 1)


