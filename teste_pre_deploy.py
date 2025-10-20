#!/usr/bin/env python3
"""
Script para testar todas as funcionalidades antes do deploy
"""

import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Testa se as variáveis de ambiente estão configuradas"""
    print("🔍 Testando variáveis de ambiente...")
    
    load_dotenv()
    
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET", 
        "ATLASSIAN_EMAIL",
        "ATLASSIAN_TOKEN",
        "ATLASSIAN_BASE_URL",
        "ZENDESK_EMAIL",
        "ZENDESK_API_TOKEN",
        "ZENDESK_SUBDOMAIN",
        "GEMINI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variáveis faltando: {missing_vars}")
        return False
    else:
        print("✅ Todas as variáveis de ambiente estão configuradas")
        return True

def test_imports():
    """Testa se todos os módulos podem ser importados"""
    print("\n📦 Testando imports...")
    
    try:
        from app import app
        print("✅ app.py importado com sucesso")
        
        from handlers.gemini_handler import get_gemini_response
        print("✅ gemini_handler importado com sucesso")
        
        from handlers.confluence_com_resumo import buscar_confluence
        print("✅ confluence_com_resumo importado com sucesso")
        
        from handlers.zendesk_api import buscar_artigo_zendesk_api
        print("✅ zendesk_api importado com sucesso")
        
        from handlers.zendesk_com_resumo import limpar_termo_busca
        print("✅ zendesk_com_resumo importado com sucesso")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao importar módulos: {e}")
        return False

def test_gemini():
    """Testa se o Gemini está funcionando"""
    print("\n🤖 Testando Gemini...")
    
    try:
        from handlers.gemini_handler import get_gemini_response
        
        response = get_gemini_response("Teste simples: responda apenas 'OK'")
        
        if response and "OK" in response:
            print("✅ Gemini funcionando corretamente")
            return True
        else:
            print(f"❌ Resposta inesperada do Gemini: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar Gemini: {e}")
        return False

def test_handlers():
    """Testa se os handlers estão funcionando"""
    print("\n🔧 Testando handlers...")
    
    try:
        from handlers.zendesk_com_resumo import limpar_termo_busca
        from handlers.confluence_com_resumo import buscar_confluence
        from handlers.zendesk_api import buscar_artigo_zendesk_api
        
        # Teste básico
        pergunta = "teste integração"
        pergunta_limpa = limpar_termo_busca(pergunta)
        
        if pergunta_limpa:
            print("✅ Limpeza de termo funcionando")
        else:
            print("❌ Limpeza de termo falhou")
            return False
        
        # Teste Confluence (pode falhar se não houver resultados, mas não deve dar erro)
        try:
            resultado_confluence = buscar_confluence(pergunta_limpa)
            print("✅ Busca no Confluence funcionando")
        except Exception as e:
            print(f"⚠️ Busca no Confluence com erro: {e}")
        
        # Teste Zendesk (pode falhar se não houver resultados, mas não deve dar erro)
        try:
            resultado_zendesk = buscar_artigo_zendesk_api(pergunta)
            print("✅ Busca no Zendesk funcionando")
        except Exception as e:
            print(f"⚠️ Busca no Zendesk com erro: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar handlers: {e}")
        return False

def test_flask_app():
    """Testa se o app Flask pode ser criado"""
    print("\n🌐 Testando app Flask...")
    
    try:
        from app import app
        
        # Testar se o app tem as rotas necessárias
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        
        required_routes = [
            "/slack/events",
            "/slack/actions", 
            "/test",
            "/health"
        ]
        
        missing_routes = []
        for route in required_routes:
            if not any(route in r for r in routes):
                missing_routes.append(route)
        
        if missing_routes:
            print(f"❌ Rotas faltando: {missing_routes}")
            return False
        else:
            print("✅ Todas as rotas necessárias estão presentes")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao testar app Flask: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🚀 === TESTE PRÉ-DEPLOY ===\n")
    
    tests = [
        ("Variáveis de Ambiente", test_environment),
        ("Imports", test_imports),
        ("Gemini", test_gemini),
        ("Handlers", test_handlers),
        ("App Flask", test_flask_app)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Erro inesperado em {test_name}: {e}")
    
    print(f"\n📊 RESULTADO FINAL: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM! Pronto para deploy!")
        return True
    else:
        print("⚠️ ALGUNS TESTES FALHARAM! Corrija os problemas antes do deploy.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
