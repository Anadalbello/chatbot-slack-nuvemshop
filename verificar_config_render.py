#!/usr/bin/env python3
"""
Script para verificar se as configurações estão corretas para o Render
"""

import os
from dotenv import load_dotenv

def verificar_configuracao_render():
    print("🔍 === VERIFICAÇÃO DE CONFIGURAÇÃO PARA RENDER ===\n")
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Lista de variáveis necessárias
    variaveis_necessarias = {
        "SLACK_BOT_TOKEN": "Token do bot do Slack",
        "SLACK_SIGNING_SECRET": "Signing secret do Slack",
        "ATLASSIAN_EMAIL": "Email da conta Atlassian",
        "ATLASSIAN_TOKEN": "Token de API do Atlassian",
        "ATLASSIAN_BASE_URL": "URL base do Atlassian",
        "CONFLUENCE_SPACE": "Espaço específico do Confluence",
        "ZENDESK_EMAIL": "Email da conta Zendesk",
        "ZENDESK_API_TOKEN": "Token de API do Zendesk",
        "ZENDESK_SUBDOMAIN": "Subdomínio do Zendesk"
    }
    
    print("📊 Status das Variáveis de Ambiente:")
    print("=" * 50)
    
    configuradas = 0
    total = len(variaveis_necessarias)
    
    for variavel, descricao in variaveis_necessarias.items():
        valor = os.getenv(variavel)
        if valor:
            # Mascarar valores sensíveis
            if "TOKEN" in variavel or "SECRET" in variavel:
                valor_mascarado = f"{valor[:10]}...{valor[-4:]}" if len(valor) > 14 else "***configurado***"
                print(f"✅ {variavel}: {valor_mascarado}")
            else:
                print(f"✅ {variavel}: {valor}")
            configuradas += 1
        else:
            print(f"❌ {variavel}: NÃO CONFIGURADO")
    
    print("=" * 50)
    print(f"📈 Progresso: {configuradas}/{total} variáveis configuradas")
    
    # Verificar especificamente o Confluence
    print(f"\n🎯 VERIFICAÇÃO ESPECÍFICA DO CONFLUENCE:")
    print("=" * 50)
    
    confluence_ok = all([
        os.getenv("ATLASSIAN_EMAIL"),
        os.getenv("ATLASSIAN_TOKEN"),
        os.getenv("ATLASSIAN_BASE_URL")
    ])
    
    if confluence_ok:
        print("✅ Configurações básicas do Confluence: OK")
        espaco = os.getenv("CONFLUENCE_SPACE")
        if espaco:
            print(f"✅ Espaço específico configurado: {espaco}")
        else:
            print("⚠️ Espaço específico não configurado (busca global)")
    else:
        print("❌ Configurações básicas do Confluence: FALTANDO")
    
    # Verificar Zendesk
    print(f"\n🎫 VERIFICAÇÃO ESPECÍFICA DO ZENDESK:")
    print("=" * 50)
    
    zendesk_ok = all([
        os.getenv("ZENDESK_EMAIL"),
        os.getenv("ZENDESK_API_TOKEN"),
        os.getenv("ZENDESK_SUBDOMAIN")
    ])
    
    if zendesk_ok:
        print("✅ Configurações do Zendesk: OK")
    else:
        print("❌ Configurações do Zendesk: FALTANDO")
    
    # Resumo final
    print(f"\n🎉 RESUMO FINAL:")
    print("=" * 50)
    
    if configuradas == total:
        print("✅ TODAS as variáveis estão configuradas!")
        print("🚀 Pronto para deploy no Render!")
    else:
        print(f"⚠️ Faltam {total - configuradas} variáveis")
        print("📝 Configure as variáveis faltantes no Render:")
        print("   1. Vá para render.com")
        print("   2. Acesse seu serviço")
        print("   3. Vá para Environment")
        print("   4. Adicione as variáveis faltantes")
    
    return configuradas == total

if __name__ == "__main__":
    verificar_configuracao_render()
