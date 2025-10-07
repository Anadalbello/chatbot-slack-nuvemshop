#!/usr/bin/env python3
"""
Script simples para configurar as chaves API do Zendesk
"""

import os
import re

def configurar_zendesk():
    """Configura as variáveis do Zendesk no arquivo .env"""
    
    print("🔑 === CONFIGURAÇÃO ZENDESK API ===\n")
    
    # Verificar se .env existe
    if not os.path.exists('.env'):
        print("❌ Arquivo .env não encontrado!")
        print("Execute primeiro: cp .env.template .env")
        return
    
    # Ler arquivo atual
    with open('.env', 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    print("📋 Preencha as informações do Zendesk:\n")
    
    # Coletar informações
    email = input("📧 Email do Zendesk: ").strip()
    if not email:
        print("❌ Email é obrigatório!")
        return
    
    api_token = input("🔑 Token API do Zendesk: ").strip()
    if not api_token:
        print("❌ Token API é obrigatório!")
        return
    
    subdomain = input("🏢 Subdomínio (pressione Enter para manter 'mandaenuvemenvio'): ").strip()
    if not subdomain:
        subdomain = "mandaenuvemenvio"
    
    # Atualizar arquivo .env
    conteudo = re.sub(r'ZENDESK_EMAIL=.*', f'ZENDESK_EMAIL={email}', conteudo)
    conteudo = re.sub(r'ZENDESK_API_TOKEN=.*', f'ZENDESK_API_TOKEN={api_token}', conteudo)
    conteudo = re.sub(r'ZENDESK_SUBDOMAIN=.*', f'ZENDESK_SUBDOMAIN={subdomain}', conteudo)
    
    # Salvar
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("\n✅ Configuração salva com sucesso!")
    print(f"📧 Email: {email}")
    print(f"🔑 Token: {'*' * (len(api_token) - 4) + api_token[-4:] if len(api_token) > 4 else '****'}")
    print(f"🏢 Subdomínio: {subdomain}")
    
    print("\n🚀 Próximo passo: Testar a configuração!")

def verificar_configuracao():
    """Verifica se as configurações estão corretas"""
    
    if not os.path.exists('.env'):
        print("❌ Arquivo .env não encontrado!")
        return False
    
    # Simular carregamento das variáveis
    env_vars = {}
    with open('.env', 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if '=' in linha and not linha.startswith('#'):
                chave, valor = linha.split('=', 1)
                env_vars[chave] = valor
    
    print("🔍 === VERIFICAÇÃO DE CONFIGURAÇÃO ===\n")
    
    # Verificar Zendesk
    zendesk_configs = ['ZENDESK_EMAIL', 'ZENDESK_API_TOKEN', 'ZENDESK_SUBDOMAIN']
    zendesk_ok = True
    
    for config in zendesk_configs:
        valor = env_vars.get(config, '')
        if valor and 'seu-' not in valor and 'sua-' not in valor:
            print(f"✅ {config}: Configurado")
        else:
            print(f"❌ {config}: NÃO CONFIGURADO")
            zendesk_ok = False
    
    if zendesk_ok:
        print("\n🎫 ✅ ZENDESK: Pronto para uso!")
        return True
    else:
        print("\n🎫 ❌ ZENDESK: Precisa configurar")
        return False

def main():
    print("🔧 === CONFIGURADOR ZENDESK ===\n")
    
    while True:
        print("1. Configurar Zendesk API")
        print("2. Verificar configuração")
        print("3. Sair")
        
        escolha = input("\nEscolha uma opção (1-3): ").strip()
        
        if escolha == "1":
            configurar_zendesk()
        elif escolha == "2":
            verificar_configuracao()
        elif escolha == "3":
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida!")
        
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()

