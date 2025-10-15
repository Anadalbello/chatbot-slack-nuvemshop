#!/usr/bin/env python3
"""
Handler para buscar dinamicamente todas as integrações disponíveis no Confluence
Busca páginas reais em vez de usar lista estática
"""

import os
import requests
import re
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


def buscar_todas_integracoes_confluence():
    """
    Busca todas as páginas de integrações no Confluence
    Retorna lista formatada com todas as integrações encontradas
    """
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    space = os.getenv("CONFLUENCE_SPACE", "BDGCI")
    
    if not all([email, token, base_url]):
        logger.error("Configurações do Confluence não encontradas")
        return None
    
    headers = {"Accept": "application/json"}
    auth = (email, token)
    
    try:
        # Buscar todas as páginas relacionadas a integrações
        # Usando CQL para encontrar páginas com "integra" no título
        cql = f'space={space} AND (title~"integra*" OR title~"Manual*" OR title~"Configura*") AND type=page'
        url = f"{base_url}/wiki/rest/api/content/search?cql={cql}&limit=100&expand=metadata.labels"
        
        logger.info(f"🔍 Buscando integrações no Confluence...")
        response = requests.get(url, headers=headers, auth=auth, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return None
        
        logger.info(f"✅ Encontradas {len(results)} páginas de integrações")
        
        # Processar e extrair nomes de integrações
        integracoes = []
        for page in results:
            title = page.get("title", "")
            page_id = page.get("id")
            link = f"{base_url}/wiki{page['_links']['webui']}"
            
            # Extrair nome da integração do título
            # Limpar prefixos comuns
            nome_limpo = title
            for prefixo in ["copy ", "Manual de ", "Integração ", "Configurações de integração ", "[HUB] ", "Manuais de "]:
                nome_limpo = nome_limpo.replace(prefixo, "")
            
            # Pegar só a primeira parte (antes de - ou +)
            nome_principal = re.split(r'[\-\+\[]', nome_limpo)[0].strip()
            
            if len(nome_principal) > 3:  # Evitar nomes muito curtos
                integracoes.append({
                    "nome": nome_principal,
                    "titulo_completo": title,
                    "link": link
                })
        
        # Remover duplicatas mantendo a ordem
        integracoes_unicas = []
        nomes_vistos = set()
        
        for integracao in integracoes:
            nome_lower = integracao["nome"].lower()
            if nome_lower not in nomes_vistos:
                nomes_vistos.add(nome_lower)
                integracoes_unicas.append(integracao)
        
        # Formatar resposta
        if integracoes_unicas:
            resultado = f"📋 **Integrações e Parceiros Disponíveis** ({len(integracoes_unicas)} encontrados):\n\n"
            
            for i, integracao in enumerate(integracoes_unicas, 1):
                resultado += f"{i}. **{integracao['nome']}**\n"
                resultado += f"   📄 {integracao['titulo_completo']}\n"
                resultado += f"   🔗 {integracao['link']}\n\n"
            
            return resultado
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar integrações: {e}")
        return None


def buscar_integracao_especifica(nome_busca):
    """
    Busca uma integração específica pelo nome
    """
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    space = os.getenv("CONFLUENCE_SPACE", "BDGCI")
    
    if not all([email, token, base_url]):
        return None
    
    headers = {"Accept": "application/json"}
    auth = (email, token)
    
    try:
        # Buscar páginas que mencionem o nome
        cql = f'space={space} AND title~"{nome_busca}" AND type=page'
        url = f"{base_url}/wiki/rest/api/content/search?cql={cql}&limit=5&expand=body.view,metadata.labels"
        
        response = requests.get(url, headers=headers, auth=auth, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if results:
            page = results[0]
            resultado = f"📦 **{page['title']}**\n\n"
            resultado += f"🔗 Link: {base_url}/wiki{page['_links']['webui']}\n\n"
            
            # Se tiver conteúdo, extrair um resumo
            if 'body' in page and 'view' in page['body']:
                html_content = page['body']['view']['value']
                # Limpar HTML básico
                texto_limpo = re.sub(r'<[^>]+>', '', html_content)
                texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
                
                if len(texto_limpo) > 50:
                    resultado += f"📝 Resumo: {texto_limpo[:300]}...\n"
            
            return resultado
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar integração: {e}")
        return None


if __name__ == "__main__":
    print("=== TESTE: Buscar todas as integrações ===\n")
    resultado = buscar_todas_integracoes_confluence()
    if resultado:
        print(resultado)
    else:
        print("❌ Não foi possível buscar")
    
    print("\n=== TESTE: Buscar Magento ===\n")
    resultado_magento = buscar_integracao_especifica("Magento")
    if resultado_magento:
        print(resultado_magento)
    else:
        print("❌ Não encontrado")

