#!/usr/bin/env python3
"""
Script para ajudar na configuração do arquivo .env
"""

import os

def criar_arquivo_env():
    """Cria um arquivo .env com todas as configurações necessárias"""
    
    conteudo_env = """# =================================
# CONFIGURAÇÕES DO SLACK BOT
# =================================

# Token do Bot do Slack (começa com xoxb-)
SLACK_BOT_TOKEN=xoxb-seu-token-aqui

# Signing Secret do Slack (para validar requisições)
SLACK_SIGNING_SECRET=seu-signing-secret-aqui

# =================================
# CONFIGURAÇÕES DO ATLASSIAN/JIRA
# =================================

# Email da conta Atlassian
ATLASSIAN_EMAIL=seu-email@exemplo.com

# Token de API do Atlassian
ATLASSIAN_TOKEN=seu-token-atlassian-aqui

# URL base do Atlassian
ATLASSIAN_BASE_URL=https://tiendanube.atlassian.net

# =================================
# CONFIGURAÇÕES DO ZENDESK (NOVO!)
# =================================

# Email da conta do Zendesk
ZENDESK_EMAIL=seu-email@exemplo.com

# Token de API do Zendesk
ZENDESK_API_TOKEN=sua-chave-api-zendesk-aqui

# Subdomínio do Zendesk (sem .zendesk.com)
ZENDESK_SUBDOMAIN=mandaenuvemenvio

# =================================
# OUTRAS CONFIGURAÇÕES
# =================================

# Porta para desenvolvimento local (opcional)
PORT=3000

# Ambiente (development/production)
ENVIRONMENT=development
"""
    
    # Verificar se .env já existe
    env_path = '.env'
    
    if os.path.exists(env_path):
        print("⚠️ Arquivo .env já existe!")
        resposta = input("Deseja sobrescrever? (s/N): ").lower()
        if resposta != 's':
            print("❌ Operação cancelada.")
            return
    
    # Criar arquivo .env
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(conteudo_env)
    
    print("✅ Arquivo .env criado com sucesso!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Abra o arquivo .env")
    print("2. Substitua 'seu-token-aqui' pelos valores reais")
    print("3. Salve o arquivo")
    print("\n🔑 VARIÁVEIS MAIS IMPORTANTES PARA ZENDESK:")
    print("- ZENDESK_EMAIL: Seu email do Zendesk")
    print("- ZENDESK_API_TOKEN: Sua chave API do Zendesk")
    print("- ZENDESK_SUBDOMAIN: mandaenuvemenvio (pode manter)")

def verificar_configuracao():
    """Verifica se as configurações estão corretas"""
    
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🔍 === VERIFICAÇÃO DE CONFIGURAÇÃO ===\n")
    
    configs = {
        "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
        "SLACK_SIGNING_SECRET": os.getenv("SLACK_SIGNING_SECRET"),
        "ATLASSIAN_EMAIL": os.getenv("ATLASSIAN_EMAIL"),
        "ATLASSIAN_TOKEN": os.getenv("ATLASSIAN_TOKEN"),
        "ATLASSIAN_BASE_URL": os.getenv("ATLASSIAN_BASE_URL"),
        "ZENDESK_EMAIL": os.getenv("ZENDESK_EMAIL"),
        "ZENDESK_API_TOKEN": os.getenv("ZENDESK_API_TOKEN"),
        "ZENDESK_SUBDOMAIN": os.getenv("ZENDESK_SUBDOMAIN")
    }
    
    for nome, valor in configs.items():
        if valor and valor != f"{nome.lower().replace('_', '-')}-aqui":
            print(f"✅ {nome}: Configurado")
        else:
            print(f"❌ {nome}: NÃO CONFIGURADO")
    
    print("\n" + "="*50)
    
    # Verificar especificamente Zendesk
    zendesk_ok = all([
        configs["ZENDESK_EMAIL"] and "seu-email" not in configs["ZENDESK_EMAIL"],
        configs["ZENDESK_API_TOKEN"] and "sua-chave" not in configs["ZENDESK_API_TOKEN"]
    ])
    
    if zendesk_ok:
        print("🎫 ✅ ZENDESK: Pronto para uso!")
    else:
        print("🎫 ❌ ZENDESK: Precisa configurar")

def main():
    print("🔧 === CONFIGURADOR DE AMBIENTE ===\n")
    
    print("1. Criar arquivo .env")
    print("2. Verificar configuração atual")
    print("3. Sair")
    
    escolha = input("\nEscolha uma opção (1-3): ")
    
    if escolha == "1":
        criar_arquivo_env()
    elif escolha == "2":
        verificar_configuracao()
    elif escolha == "3":
        print("👋 Até logo!")
    else:
        print("❌ Opção inválida!")

if __name__ == "__main__":
    main()
