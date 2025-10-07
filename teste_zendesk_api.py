#!/usr/bin/env python3
"""
Teste da integração com API do Zendesk
"""

import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from handlers.zendesk_api import buscar_artigo_zendesk_api, testar_api_zendesk

def main():
    print("🎫 === TESTE COMPLETO DA API DO ZENDESK ===\n")
    
    # 1. Verificar configurações
    print("⚙️ 1. VERIFICANDO CONFIGURAÇÕES:")
    zendesk_email = os.getenv("ZENDESK_EMAIL")
    zendesk_token = os.getenv("ZENDESK_API_TOKEN")
    zendesk_subdomain = os.getenv("ZENDESK_SUBDOMAIN", "mandaenuvemenvio")
    
    print(f"📧 Email: {'✅ ' + zendesk_email if zendesk_email else '❌ Não configurado'}")
    print(f"🔑 Token: {'✅ Configurado' if zendesk_token else '❌ Não configurado'}")
    print(f"🌐 Subdomain: {zendesk_subdomain}")
    print()
    
    if not zendesk_email or not zendesk_token:
        print("❌ ERRO: Configure as variáveis ZENDESK_EMAIL e ZENDESK_API_TOKEN")
        print("\n📋 VARIÁVEIS NECESSÁRIAS:")
        print("ZENDESK_EMAIL=seu-email@exemplo.com")
        print("ZENDESK_API_TOKEN=sua-chave-api")
        print("ZENDESK_SUBDOMAIN=mandaenuvemenvio (opcional)")
        return
    
    # 2. Testar buscas diversas
    print("🔍 2. TESTANDO BUSCAS:")
    
    termos_teste = [
        "cte",
        "conhecimento de transporte",
        "api documentação",
        "webhook configurar",
        "login problema",
        "como fazer login"
    ]
    
    for i, termo in enumerate(termos_teste, 1):
        print(f"\n🔍 Teste {i}: '{termo}'")
        print("-" * 50)
        
        try:
            resultado = buscar_artigo_zendesk_api(termo)
            
            if resultado:
                print("✅ SUCESSO!")
                print(f"📄 Resultado:")
                print(resultado)
            else:
                print("❌ Nenhum resultado encontrado")
                
        except Exception as e:
            print(f"❌ ERRO: {e}")
    
    print("\n" + "="*60)
    print("🎉 TESTE CONCLUÍDO!")
    print("="*60)

if __name__ == "__main__":
    main()
