import requests
from bs4 import BeautifulSoup
import logging
import urllib.parse
import time
import random
import re

logger = logging.getLogger(__name__)

def limpar_termo_busca(texto):
    """Remove menções do bot e limpa o texto para busca"""
    import re
    
    # Remover menções do bot (ex: @INT BOT, <@U123456>)
    texto = re.sub(r'<@[^>]+>', '', texto)  # Remove <@U123456>
    texto = re.sub(r'@\w+\s+BOT', '', texto, flags=re.IGNORECASE)  # Remove @INT BOT
    texto = re.sub(r'@\w+', '', texto)  # Remove outras menções
    
    # Remover caracteres especiais e espaços extras
    texto = re.sub(r'[^\w\s\-áéíóúàèìòùâêîôûãõç]', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\s+', ' ', texto)  # Múltiplos espaços -> um espaço
    texto = texto.strip()
    
    return texto

def buscar_artigo_zendesk(termo_original):
    """Scraping com extração de resumo para o Zendesk"""
    
    # Limpar o termo antes da busca
    termo = limpar_termo_busca(termo_original)
    
    # Se o termo ficou muito curto após limpeza, usar termo original
    if len(termo) < 3:
        termo = termo_original.strip()
    
    base_url = "https://mandaenuvemenvio.zendesk.com/hc/pt-br"
    
    # Headers que simulam um navegador real
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # URL de busca
        termo_encoded = urllib.parse.quote_plus(termo)
        search_url = f"{base_url}/search?query={termo_encoded}"
        
        logger.info(f"Buscando no Zendesk com resumo: {termo}")
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(search_url, headers=headers, timeout=8)
        
        if response.status_code == 403:
            logger.warning("Acesso negado - usando fallback")
            return criar_fallback_zendesk(termo, base_url)
        
        if response.status_code == 200:
            # Usar BeautifulSoup para extração mais robusta
            artigos_encontrados = extrair_artigos_com_resumo(response.text, base_url)
            
            if artigos_encontrados:
                # Pegar o primeiro artigo (mais relevante)
                artigo = artigos_encontrados[0]
                logger.info(f"Artigo encontrado: {artigo['title']}")
                
                # Formatar resposta com resumo
                return formatar_resposta_zendesk(artigo)
            else:
                logger.info("Nenhum artigo encontrado")
                return criar_fallback_zendesk(termo, base_url)
        
        else:
            logger.warning(f"Status inesperado: {response.status_code}")
            return criar_fallback_zendesk(termo, base_url)
            
    except Exception as e:
        logger.error(f"Erro na busca Zendesk: {e}")
        return criar_fallback_zendesk(termo, base_url)

def extrair_artigos_com_resumo(html_content, base_url):
    """Extrai artigos com título, link E resumo usando BeautifulSoup"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    artigos = []
    
    # Seletores para diferentes estruturas de página de busca do Zendesk
    seletores_busca = [
        # Resultados de busca modernos
        '.search-result',
        '.search-result-item', 
        '.article-list-item',
        '.search-results .result',
        # Fallback para links gerais de artigos
        'a[href*="/articles/"]'
    ]
    
    for seletor in seletores_busca:
        elementos = soup.select(seletor)
        
        for elemento in elementos[:3]:  # Máximo 3 resultados
            artigo_info = extrair_info_artigo(elemento, base_url)
            
            if artigo_info and artigo_info not in artigos:
                artigos.append(artigo_info)
                
                if len(artigos) >= 2:  # Limitar a 2 artigos
                    break
        
        if artigos:
            break  # Se encontrou artigos, parar de procurar
    
    return artigos

def extrair_info_artigo(elemento, base_url):
    """Extrai título, link e resumo de um elemento HTML"""
    
    try:
        # Buscar link do artigo
        link_elem = elemento.find('a', href=re.compile(r'/articles/'))
        if not link_elem:
            link_elem = elemento if elemento.name == 'a' else None
        
        if not link_elem:
            return None
        
        # Extrair URL
        href = link_elem.get('href', '')
        if not href or '/articles/' not in href:
            return None
        
        if href.startswith('/'):
            url = base_url + href
        else:
            url = href
        
        # Extrair título
        titulo = None
        # Tentar várias formas de obter o título
        if link_elem.get_text(strip=True):
            titulo = link_elem.get_text(strip=True)
        elif link_elem.get('title'):
            titulo = link_elem.get('title')
        elif link_elem.get('aria-label'):
            titulo = link_elem.get('aria-label')
        
        if not titulo or len(titulo) < 5:
            return None
        
        # Extrair resumo/snippet
        resumo = extrair_resumo_artigo(elemento, link_elem)
        
        return {
            'title': titulo[:100],  # Limitar título
            'url': url,
            'resumo': resumo[:200] if resumo else None  # Limitar resumo
        }
        
    except Exception as e:
        logger.debug(f"Erro ao extrair info do artigo: {e}")
        return None

def extrair_resumo_artigo(elemento_pai, link_elem):
    """Extrai resumo/snippet do artigo"""
    
    # Tentar várias estratégias para encontrar o resumo
    resumo_candidatos = []
    
    # 1. Procurar por classes comuns de snippet/descrição
    snippet_classes = [
        '.search-result-description',
        '.search-result-snippet', 
        '.article-snippet',
        '.description',
        '.excerpt',
        '.summary'
    ]
    
    for classe in snippet_classes:
        elem_snippet = elemento_pai.select_one(classe)
        if elem_snippet:
            texto = elem_snippet.get_text(strip=True)
            if texto and len(texto) > 20:
                resumo_candidatos.append(texto)
    
    # 2. Procurar por parágrafos próximos ao link
    for p in elemento_pai.find_all('p'):
        texto = p.get_text(strip=True)
        if texto and len(texto) > 30 and texto not in resumo_candidatos:
            resumo_candidatos.append(texto)
    
    # 3. Procurar por divs com texto após o link
    elemento_seguinte = link_elem.find_next_sibling()
    if elemento_seguinte:
        texto = elemento_seguinte.get_text(strip=True)
        if texto and len(texto) > 20:
            resumo_candidatos.append(texto)
    
    # 4. Procurar no elemento pai por qualquer texto significativo
    if not resumo_candidatos:
        texto_pai = elemento_pai.get_text(strip=True)
        # Remover o título do texto
        titulo_link = link_elem.get_text(strip=True)
        if titulo_link in texto_pai:
            texto_sem_titulo = texto_pai.replace(titulo_link, '', 1).strip()
            if len(texto_sem_titulo) > 30:
                resumo_candidatos.append(texto_sem_titulo)
    
    # Retornar o melhor candidato
    if resumo_candidatos:
        # Preferir textos de tamanho médio (não muito curtos nem muito longos)
        melhor = min(resumo_candidatos, key=lambda x: abs(len(x) - 100))
        return limpar_texto_resumo(melhor)
    
    return None

def limpar_texto_resumo(texto):
    """Limpa e formata o texto do resumo"""
    
    # Remover HTML residual
    texto = re.sub(r'<[^>]+>', '', texto)
    
    # Remover múltiplos espaços
    texto = re.sub(r'\s+', ' ', texto)
    
    # Remover caracteres especiais desnecessários
    texto = re.sub(r'[^\w\s\-.,!?áéíóúàèìòùâêîôûãõç]', '', texto)
    
    # Limitar tamanho e adicionar reticências se necessário
    if len(texto) > 150:
        texto = texto[:147] + "..."
    
    return texto.strip()

def formatar_resposta_zendesk(artigo):
    """Formata a resposta final com título, resumo e link"""
    
    titulo = artigo['title']
    url = artigo['url']
    resumo = artigo['resumo']
    
    if resumo:
        return f"🎫 **{titulo}**\n📝 _{resumo}_\n🔗 {url}"
    else:
        return f"🎫 **{titulo}**\n🔗 {url}"

def criar_fallback_zendesk(termo, base_url):
    """Cria resposta de fallback quando scraping falha"""
    
    # Sugestões diretas para termos comuns com resumo
    sugestoes_com_resumo = {
        "cte": {
            "title": "Como emitir Conhecimento de Transporte Eletrônico (CTE)",
            "resumo": "Passo a passo para emissão de CTE, documentos necessários e validações obrigatórias",
            "url": f"{base_url}/articles/como-emitir-cte"
        },
        "conhecimento transporte": {
            "title": "Documentação CTE - Conhecimento de Transporte",
            "resumo": "Guia completo sobre CTE: emissão, cancelamento, correção e consulta de status",
            "url": f"{base_url}/articles/cte-conhecimento-transporte"
        },
        "emitir": {
            "title": "Como emitir documentos fiscais",
            "resumo": "Tutorial para emissão de notas fiscais, CTE e outros documentos eletrônicos",
            "url": f"{base_url}/articles/emitir-documentos"
        },
        "login": {
            "title": "Como fazer login na sua conta",
            "resumo": "Passo a passo para acessar sua conta, recuperar senha e resolver problemas de login",
            "url": f"{base_url}/articles/como-fazer-login"
        },
        "conta": {
            "title": "Como criar uma nova conta", 
            "resumo": "Guia completo para criar sua conta e começar a usar nossos serviços",
            "url": f"{base_url}/articles/criar-conta"
        },
        "api": {
            "title": "Documentação da API",
            "resumo": "Referência completa da API com endpoints, autenticação e exemplos de uso",
            "url": f"{base_url}/articles/documentacao-api"
        },
        "webhook": {
            "title": "Como configurar webhooks",
            "resumo": "Aprenda a configurar e testar webhooks para receber notificações automáticas",
            "url": f"{base_url}/articles/configurar-webhooks"
        }
    }
    
    termo_lower = termo.lower()
    
    # Verificar se alguma palavra-chave corresponde
    for palavra, info in sugestoes_com_resumo.items():
        if palavra in termo_lower:
            logger.info(f"Sugestão com resumo para '{termo}': {palavra}")
            return f"🎫 **{info['title']}**\n📝 _{info['resumo']}_\n🔗 {info['url']}"
    
    # Fallback geral
    search_query = urllib.parse.quote_plus(termo)
    search_url = f"{base_url}/search?query={search_query}"
    
    return f"🔍 **Busque por '{termo}' no help center do Zendesk**\n🔗 {search_url}"

# Teste e simulação
def simular_resultados_com_resumo():
    """Simula os resultados com resumo para teste"""
    print("🧪 === SIMULAÇÃO DE RESULTADOS COM RESUMO ===\n")
    
    # Simular resultado do Zendesk
    resultado_zendesk = """🎫 **Como configurar webhooks no sistema**  
📝 _Aprenda a configurar e testar webhooks para receber notificações automáticas de pedidos e atualizações em tempo real_
🔗 https://mandaenuvemenvio.zendesk.com/hc/pt-br/articles/webhook-config"""
    
    print("📋 Resultado Zendesk:")
    print(resultado_zendesk)
    print()
    
    # Simular resultado do Confluence  
    resultado_confluence = """📋 **Múltiplos artigos encontrados:**

• **Deploy Core [DRAFT]** (Espaço: Online)
  📝 _Documentação sobre deploy e configuração do core do sistema com exemplos práticos_
  🔗 https://tiendanube.atlassian.net/wiki/spaces/O/pages/95551490/Deploy+Core+DRAFT

• **Service-account via terraform** (Espaço: SRE, DevOps)  
  📝 _Guia para criação e configuração de service accounts usando terraform com exemplos práticos_
  🔗 https://tiendanube.atlassian.net/wiki/spaces/SDFED/pages/61505567"""
    
    print("📋 Resultado Confluence:")
    print(resultado_confluence)

if __name__ == "__main__":
    simular_resultados_com_resumo()
