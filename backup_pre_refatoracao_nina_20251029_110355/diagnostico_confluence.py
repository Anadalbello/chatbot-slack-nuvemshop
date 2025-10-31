#!/usr/bin/env python3
"""
Script de diagnóstico completo para Confluence
Este script será executado no Render para verificar o problema
"""

import os
import sys
import requests
from dotenv import load_dotenv

def diagnostico_confluence():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO COMPLETO DO CONFLUENCE")
    print("=" * 80)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Verificar configurações
    print("\n📊 CONFIGURAÇÕES:")
    print("-" * 80)
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    confluence_space = os.getenv("CONFLUENCE_SPACE")
    
    print(f"Email: {email}")
    print(f"Token: {token[:10]}...{token[-4:] if token else 'N/A'}")
    print(f"Base URL: {base_url}")
    print(f"Espaço: {confluence_space}")
    
    if not all([email, token, base_url]):
        print("\n❌ ERRO: Configurações faltando!")
        return False
    
    # Teste 1: Autenticação
    print("\n" + "=" * 80)
    print("🔐 TESTE 1: AUTENTICAÇÃO")
    print("-" * 80)
    
    headers = {"Accept": "application/json"}
    auth = (email, token)
    
    try:
        url = f"{base_url}/wiki/rest/api/user/current"
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Autenticação OK!")
            print(f"   Usuário: {user_data.get('displayName', 'N/A')}")
            print(f"   Email retornado: {user_data.get('emailAddress', 'N/A')}")
            print(f"   Account ID: {user_data.get('accountId', 'N/A')}")
        elif response.status_code == 403:
            print(f"❌ ERRO 403: Sem acesso ao Confluence")
            print(f"   Mensagem: {response.text[:200]}")
            print(f"\n💡 POSSÍVEIS CAUSAS:")
            print(f"   1. Token criado por outro usuário")
            print(f"   2. Token expirado ou inválido")
            print(f"   3. Usuário não tem acesso ao Confluence")
            return False
        else:
            print(f"❌ ERRO {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")
        return False
    
    # Teste 2: Acesso ao espaço BDGCI
    print("\n" + "=" * 80)
    print(f"🎯 TESTE 2: ACESSO AO ESPAÇO {confluence_space}")
    print("-" * 80)
    
    try:
        url = f"{base_url}/wiki/rest/api/space/{confluence_space}"
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            space_data = response.json()
            print(f"✅ Acesso OK!")
            print(f"   Nome: {space_data.get('name', 'N/A')}")
            print(f"   Key: {space_data.get('key', 'N/A')}")
            print(f"   Tipo: {space_data.get('type', 'N/A')}")
        elif response.status_code == 403:
            print(f"❌ ERRO 403: Sem permissão para acessar {confluence_space}")
            print(f"   Mensagem: {response.text[:200]}")
            print(f"\n💡 SOLUÇÃO:")
            print(f"   O usuário {email} precisa ter permissão de LEITURA no espaço {confluence_space}")
            return False
        elif response.status_code == 404:
            print(f"❌ ERRO 404: Espaço {confluence_space} não encontrado")
            print(f"   Verifique se o Space Key está correto (case-sensitive)")
            return False
        else:
            print(f"❌ ERRO {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")
        return False
    
    # Teste 3: Busca no espaço
    print("\n" + "=" * 80)
    print(f"🔍 TESTE 3: BUSCA NO ESPAÇO {confluence_space}")
    print("-" * 80)
    
    try:
        query = f"{base_url}/wiki/rest/api/content/search?cql=space=\"{confluence_space}\"&limit=3"
        response = requests.get(query, headers=headers, auth=auth, timeout=15)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('size', 0)
            print(f"✅ Busca OK!")
            print(f"   Páginas encontradas: {total}")
            
            if total > 0:
                print(f"\n   Primeiras páginas:")
                for page in data.get('results', [])[:3]:
                    print(f"   • {page.get('title', 'N/A')}")
        elif response.status_code == 403:
            print(f"❌ ERRO 403: Sem permissão para buscar no espaço")
            print(f"   Mensagem: {response.text[:200]}")
            return False
        else:
            print(f"❌ ERRO {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")
        return False
    
    # Teste 4: Busca com termo
    print("\n" + "=" * 80)
    print(f"🔍 TESTE 4: BUSCA COM TERMO 'template'")
    print("-" * 80)
    
    try:
        termo = "template"
        query = f"{base_url}/wiki/rest/api/content/search?cql=(title~\"{termo}\" OR text~\"{termo}\") AND type=page AND space=\"{confluence_space}\"&limit=3&expand=space,body.view,excerpt"
        response = requests.get(query, headers=headers, auth=auth, timeout=15)
        
        print(f"URL: {query}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('size', 0)
            print(f"✅ Busca OK!")
            print(f"   Resultados encontrados: {total}")
            
            if total > 0:
                print(f"\n   Resultados:")
                for page in data.get('results', [])[:3]:
                    print(f"   • {page.get('title', 'N/A')}")
                    print(f"     Espaço: {page.get('space', {}).get('name', 'N/A')}")
                    print(f"     Link: {base_url}/wiki{page.get('_links', {}).get('webui', 'N/A')}")
        elif response.status_code == 403:
            print(f"❌ ERRO 403: Sem permissão para buscar")
            print(f"   Mensagem: {response.text[:200]}")
            return False
        else:
            print(f"❌ ERRO {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("🎉 TODOS OS TESTES PASSARAM!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    sucesso = diagnostico_confluence()
    sys.exit(0 if sucesso else 1)

