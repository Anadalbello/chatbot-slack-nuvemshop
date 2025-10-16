#!/usr/bin/env python3
"""
Script para testar se o token do Confluence está funcionando
"""

import os
import requests
from dotenv import load_dotenv

def testar_token_confluence():
    print("🔍 === TESTE DE TOKEN DO CONFLUENCE ===\n")
    
    load_dotenv()
    
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    
    print(f"👤 Email configurado: {email}")
    print(f"🔑 Token: {token[:10]}...{token[-4:] if token else 'N/A'}")
    print(f"🌐 Base URL: {base_url}\n")
    
    if not all([email, token, base_url]):
        print("❌ Configurações faltando!")
        return
    
    headers = {"Accept": "application/json"}
    auth = (email, token)
    
    # Teste 1: Verificar usuário autenticado
    print("=" * 80)
    print("🔐 Teste 1: Verificando autenticação...")
    print("=" * 80)
    
    try:
        url = f"{base_url}/wiki/rest/api/user/current"
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Autenticação OK!")
            print(f"   Nome: {user_data.get('displayName', 'N/A')}")
            print(f"   Email: {user_data.get('emailAddress', 'N/A')}")
            print(f"   Account ID: {user_data.get('accountId', 'N/A')}")
            
            # Verificar se email corresponde
            email_autenticado = user_data.get('emailAddress')
            if email_autenticado == email:
                print(f"   ✅ Email e token são compatíveis!")
            else:
                print(f"   ⚠️ ATENÇÃO: Email configurado ({email}) diferente do autenticado ({email_autenticado})")
                print(f"   💡 O token foi criado por {email_autenticado}, não por {email}")
        else:
            print(f"❌ Erro de autenticação: {response.status_code}")
            print(f"   Resposta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    
    # Teste 2: Verificar acesso ao espaço BDGCI
    print("\n" + "=" * 80)
    print("🎯 Teste 2: Verificando acesso ao espaço BDGCI...")
    print("=" * 80)
    
    try:
        url = f"{base_url}/wiki/rest/api/space/BDGCI"
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        
        if response.status_code == 200:
            space_data = response.json()
            print(f"✅ Acesso ao BDGCI OK!")
            print(f"   Nome: {space_data.get('name', 'N/A')}")
            print(f"   Key: {space_data.get('key', 'N/A')}")
            print(f"   Tipo: {space_data.get('type', 'N/A')}")
            print(f"   URL: {base_url}/wiki/spaces/{space_data.get('key', 'N/A')}")
        elif response.status_code == 403:
            print(f"❌ Erro 403: Sem permissão para acessar o espaço BDGCI")
            print(f"   💡 Possíveis causas:")
            print(f"   1. O token foi criado por outro usuário ({email_autenticado if 'email_autenticado' in locals() else 'desconhecido'})")
            print(f"   2. O usuário não tem permissão no espaço BDGCI")
            print(f"   3. O espaço é privado")
            return False
        elif response.status_code == 404:
            print(f"❌ Erro 404: Espaço BDGCI não encontrado")
            print(f"   💡 Verifique se o Space Key é 'BDGCI' (case-sensitive)")
            return False
        else:
            print(f"❌ Erro {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    
    # Teste 3: Tentar busca no BDGCI
    print("\n" + "=" * 80)
    print("🔍 Teste 3: Testando busca no espaço BDGCI...")
    print("=" * 80)
    
    try:
        query = f"{base_url}/wiki/rest/api/content/search?cql=space=\"BDGCI\"&limit=3"
        response = requests.get(query, headers=headers, auth=auth, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('size', 0)
            print(f"✅ Busca funcionando!")
            print(f"   Total de páginas encontradas: {total}")
            
            if total > 0:
                print(f"   Primeiras páginas:")
                for page in data.get('results', [])[:3]:
                    print(f"   • {page.get('title', 'N/A')}")
            else:
                print(f"   ⚠️ Nenhuma página encontrada no espaço BDGCI")
                
            return True
        else:
            print(f"❌ Erro na busca: {response.status_code}")
            print(f"   Resposta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    sucesso = testar_token_confluence()
    print("\n" + "=" * 80)
    if sucesso:
        print("🎉 SUCESSO! Token está funcionando perfeitamente!")
    else:
        print("❌ PROBLEMA! Token precisa ser atualizado.")
        print("\n📝 PRÓXIMOS PASSOS:")
        print("1. Acesse: https://id.atlassian.com/manage-profile/security/api-tokens")
        print("2. Faça login com: ana.bello@nuvemshop.com.br")
        print("3. Crie um novo token")
        print("4. Atualize ATLASSIAN_TOKEN no .env e no Render")
    print("=" * 80)

