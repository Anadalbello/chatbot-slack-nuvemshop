#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

def verificar_configuracoes():
    print("🔍 === DIAGNÓSTICO DE CONFIGURAÇÕES ===\n")
    
    # Verificar se arquivo .env existe e está sendo carregado
    configs = {
        "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
        "SLACK_SIGNING_SECRET": os.getenv("SLACK_SIGNING_SECRET"),
        "ATLASSIAN_EMAIL": os.getenv("ATLASSIAN_EMAIL"),
        "ATLASSIAN_TOKEN": os.getenv("ATLASSIAN_TOKEN"),
        "ATLASSIAN_BASE_URL": os.getenv("ATLASSIAN_BASE_URL"),
        "JIRA_PROJECT_KEY": os.getenv("JIRA_PROJECT_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY")
    }
    
    print("📊 Status das Variáveis:")
    for key, value in configs.items():
        if value:
            # Mostrar apenas primeiros e últimos caracteres por segurança
            masked = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***configurado***"
            print(f"✅ {key}: {masked}")
        else:
            print(f"❌ {key}: NÃO CONFIGURADO")
    
    print(f"\n🔧 Configurações obrigatórias para testar:")
    obrigatorios = ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"]
    
    if all(configs[key] for key in obrigatorios):
        print("✅ Configurações mínimas OK - pode testar básico!")
    else:
        print("❌ Faltam configurações básicas do Slack")
    
    print(f"\n📍 Local do arquivo .env esperado:")
    import pathlib
    env_path = pathlib.Path(".env").absolute()
    print(f"   {env_path}")
    print(f"   Existe: {'✅ SIM' if env_path.exists() else '❌ NÃO'}")

if __name__ == "__main__":
    verificar_configuracoes() 