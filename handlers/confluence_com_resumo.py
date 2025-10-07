import os
import requests
from dotenv import load_dotenv
import logging
import re

logger = logging.getLogger(__name__)
load_dotenv()

def buscar_confluence(termo):
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    
    # NOVO: Espaço específico do Confluence
    confluence_space = os.getenv("CONFLUENCE_SPACE", "")  # Se vazio, busca global
    
    if not all([email, token, base_url]):
        logger.error("Configurações do Confluence não encontradas")
        return None

    headers = {"Accept": "application/json"}
    auth = (email, token)

    # Construir query CQL baseada no espaço configurado
    if confluence_space:
        # Busca apenas no espaço específico
        query = f"{base_url}/wiki/rest/api/content/search?cql=(title~\"{termo}\" OR text~\"{termo}\") AND type=page AND space=\"{confluence_space}\"&limit=3&expand=space,body.view,excerpt"
        logger.info(f"Buscando no espaço específico: {confluence_space}")
    else:
        # Busca global (comportamento atual)
        query = f"{base_url}/wiki/rest/api/content/search?cql=(title~\"{termo}\" OR text~\"{termo}\") AND type=page&limit=3&expand=space,body.view,excerpt"
        logger.info("Buscando globalmente no Confluence")
    
    try:
        logger.info(f"Buscando no Confluence com resumo: {termo}")
        res = requests.get(query, headers=headers, auth=auth, timeout=15)
        res.raise_for_status()
        
        data = res.json()
        if data["results"]:
            results = []
            for page in data["results"][:2]:  # Limitar a 2 resultados
                title = page["title"]
                space_name = page["space"]["name"]
                link = f"{base_url}/wiki{page['_links']['webui']}"
                
                # Extrair resumo do conteúdo
                resumo = extrair_resumo_confluence(page)
                
                if resumo:
                    resultado_formatado = f"• **{title}** (Espaço: {space_name})\n  📝 _{resumo}_\n  🔗 {link}"
                else:
                    resultado_formatado = f"• **{title}** (Espaço: {space_name}) → {link}"
                
                results.append(resultado_formatado)
            
            logger.info(f"Encontrados {len(results)} resultados no Confluence")
            return "\n\n".join(results)
        else:
            logger.info("Nenhum resultado encontrado no Confluence")
            
    except Exception as e:
        logger.error(f"Erro ao buscar no Confluence: {e}")
        
    return None

def extrair_resumo_confluence(page_data):
    """Extrai resumo do conteúdo da página do Confluence"""
    
    # Tentar extrair do campo excerpt (se disponível)
    if "excerpt" in page_data:
        excerpt = page_data["excerpt"]
        if excerpt:
            resumo = limpar_html(excerpt)
            if len(resumo) > 20:
                return resumo[:150] + "..." if len(resumo) > 150 else resumo
    
    # Tentar extrair do body.view (conteúdo HTML)
    if "body" in page_data and "view" in page_data["body"]:
        content_html = page_data["body"]["view"]["value"]
        if content_html:
            resumo = extrair_primeiro_paragrafo(content_html)
            if resumo:
                return resumo
    
    return None

def extrair_primeiro_paragrafo(html_content):
    """Extrai o primeiro parágrafo significativo do HTML"""
    
    from bs4 import BeautifulSoup
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Procurar por parágrafos
        for p in soup.find_all(['p', 'div']):
            texto = p.get_text(strip=True)
            
            # Filtrar parágrafos muito curtos ou que parecem ser metadados
            if (len(texto) > 30 and 
                not texto.startswith(('Autor:', 'Data:', 'Tags:', 'Categoria:')) and
                not re.match(r'^\d+[\./]\d+', texto)):  # Evitar datas
                
                # Limpar e retornar
                resumo_limpo = limpar_html(texto)
                return resumo_limpo[:150] + "..." if len(resumo_limpo) > 150 else resumo_limpo
        
        # Se não encontrou parágrafos, tentar qualquer texto
        texto_geral = soup.get_text(strip=True)
        if len(texto_geral) > 50:
            primeiro_trecho = texto_geral[:150]
            return primeiro_trecho + "..." if len(texto_geral) > 150 else primeiro_trecho
            
    except Exception as e:
        logger.debug(f"Erro ao extrair parágrafo: {e}")
    
    return None

def limpar_html(texto):
    """Remove tags HTML e limpa o texto"""
    
    # Remover tags HTML
    texto = re.sub(r'<[^>]+>', '', texto)
    
    # Converter entidades HTML comuns
    texto = texto.replace('&nbsp;', ' ')
    texto = texto.replace('&amp;', '&')
    texto = texto.replace('&lt;', '<')
    texto = texto.replace('&gt;', '>')
    texto = texto.replace('&quot;', '"')
    
    # Limpar múltiplos espaços
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip() 