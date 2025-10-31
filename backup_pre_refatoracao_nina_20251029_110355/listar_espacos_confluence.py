#!/usr/bin/env python3
"""
Script para listar todos os espaços disponíveis no Confluence
"""

import os
import requests
from dotenv import load_dotenv

def listar_espacos_confluence():
    print("🔍 === LISTANDO ESPAÇOS DO CONFLUENCE ===\n")
    
    load_dotenv()
    
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    
    print(f"👤 Usuário: {email}")
    print(f"🌐 Base URL: {base_url}\n")
    
    if not all([email, token, base_url]):
        print("❌ Configurações faltando!")
        return
    
    headers = {"Accept": "application/json"}
    auth = (email, token)
    
    try:
        # Listar todos os espaços
        url = f"{base_url}/wiki/rest/api/space?limit=100"
        response = requests.get(url, headers=headers, auth=auth, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            spaces = data.get("results", [])
            
            print(f"✅ Encontrados {len(spaces)} espaços:\n")
            print("=" * 80)
            print(f"{'Nome do Espaço':<40} {'Key':<15} {'Tipo':<10}")
            print("=" * 80)
            
            for space in spaces:
                nome = space.get("name", "N/A")
                key = space.get("key", "N/A")
                tipo = space.get("type", "N/A")
                print(f"{nome:<40} {key:<15} {tipo:<10}")
            
            print("=" * 80)
            
            # Procurar por BDGCI ou similar
            print("\n🔍 Procurando por espaços relacionados a 'BDGCI':")
            bdgci_spaces = [s for s in spaces if "BDGCI" in s.get("key", "").upper() or "BDGCI" in s.get("name", "").upper()]
            
            if bdgci_spaces:
                print("✅ Encontrados:")
                for space in bdgci_spaces:
                    print(f"  • Nome: {space['name']}")
                    print(f"    Key: {space['key']}")
                    print(f"    URL: {base_url}/wiki/spaces/{space['key']}")
            else:
                print("❌ Nenhum espaço com 'BDGCI' encontrado")
                print("💡 Use um dos Space Keys listados acima")
            
        elif response.status_code == 403:
            print("❌ Erro 403: Sem permissão para listar espaços")
            print("💡 Tente com outro usuário ou peça permissão ao administrador")
        else:
            print(f"❌ Erro {response.status_code}: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    listar_espacos_confluence()

