import os
import requests
from dotenv import load_dotenv
import logging
import re

logger = logging.getLogger(__name__)
load_dotenv()

def buscar_confluence(termo):
    """
    Busca no Confluence com estratégias múltiplas:
    1. Busca exata com todas as palavras
    2. Busca com palavras individuais (OR)
    3. Busca palavra por palavra (fallback)
    """
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    confluence_space = os.getenv("CONFLUENCE_SPACE", "")
    
    if not all([email, token, base_url]):
        logger.error("Configurações do Confluence não encontradas")
        return None

    headers = {"Accept": "application/json"}
    auth = (email, token)
    
    # Extrair palavras-chave relevantes
    palavras = [p for p in termo.split() if len(p) > 2]
    
    logger.info(f"🔍 Buscando no Confluence: '{termo}' | Palavras-chave: {palavras}")
    
    # ESTRATÉGIA 1: Busca com frase exata (melhor match)
    resultados = _buscar_com_estrategia(
        base_url, headers, auth, confluence_space,
        f'title~"{termo}" OR text~"{termo}"',
        "busca exata",
        limit=5
    )
    
    if resultados:
        return resultados
    
    # ESTRATÉGIA 2: Busca com palavras combinadas (OR)
    if len(palavras) >= 2:
        logger.info("⚡ Tentando busca com palavras combinadas (OR)")
        
        # Criar query com todas as palavras (OR)
        conditions = []
        for palavra in palavras:
            conditions.append(f'title~"{palavra}"')
            conditions.append(f'text~"{palavra}"')
        
        cql_or = " OR ".join(conditions)
        
        resultados = _buscar_com_estrategia(
            base_url, headers, auth, confluence_space,
            cql_or,
            "busca OR combinada",
            limit=8
        )
        
        if resultados:
            return resultados
    
    # ESTRATÉGIA 3: Busca palavra por palavra (fallback mais agressivo)
    logger.info("🔄 Tentando busca palavra por palavra")
    
    for palavra in palavras:
        if len(palavra) > 3:
            logger.info(f"   Tentando palavra: '{palavra}'")
            
            resultados = _buscar_com_estrategia(
                base_url, headers, auth, confluence_space,
                f'title~"{palavra}" OR text~"{palavra}"',
                f"palavra '{palavra}'",
                limit=5
            )
            
            if resultados:
                return resultados
    
    logger.info("❌ Nenhum resultado encontrado em todas as estratégias")
    return None


def _buscar_com_estrategia(base_url, headers, auth, confluence_space, cql_condition, estrategia_nome, limit=5):
    """Executa uma busca no Confluence com uma condição CQL específica"""
    
    try:
        # Construir query base
        space_filter = f' AND space="{confluence_space}"' if confluence_space else ''
        query = f"{base_url}/wiki/rest/api/content/search?cql=({cql_condition}) AND type=page{space_filter}&limit={limit}&expand=space,body.view,excerpt"
        
        logger.info(f"   📡 Executando {estrategia_nome}...")
        
        res = requests.get(query, headers=headers, auth=auth, timeout=15)
        res.raise_for_status()
        
        data = res.json()
        
        if data["results"]:
            logger.info(f"   ✅ {len(data['results'])} resultado(s) encontrado(s) com {estrategia_nome}")
            
            results = []
            seen_links = set()  # Evitar duplicatas
            
            for page in data["results"][:3]:  # Top 3 resultados
                title = page["title"]
                space_name = page["space"]["name"]
                link = f"{base_url}/wiki{page['_links']['webui']}"
                
                # Evitar duplicatas
                if link in seen_links:
                    continue
                seen_links.add(link)
                
                # Extrair resumo
                resumo = extrair_resumo_confluence(page)
                
                if resumo:
                    resultado_formatado = f"• **{title}** (Espaço: {space_name})\n  📝 _{resumo}_\n  🔗 {link}"
                else:
                    resultado_formatado = f"• **{title}** (Espaço: {space_name})\n  🔗 {link}"
                
                results.append(resultado_formatado)
            
            return "\n\n".join(results) if results else None
        else:
            logger.info(f"   ⚠️ Nenhum resultado com {estrategia_nome}")
            return None
            
    except Exception as e:
        logger.error(f"   ❌ Erro na {estrategia_nome}: {e}")
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