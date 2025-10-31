import requests
import logging
import os
import urllib.parse
import re
from handlers.zendesk_com_resumo import limpar_termo_busca

logger = logging.getLogger(__name__)

def buscar_artigo_zendesk_api(termo_original):
    """Busca artigos no Zendesk usando a API oficial - MUITO MAIS PRECISO"""
    
    # Configurações da API do Zendesk
    zendesk_subdomain = os.getenv("ZENDESK_SUBDOMAIN", "mandaenuvemenvio")
    zendesk_email = os.getenv("ZENDESK_EMAIL")
    zendesk_token = os.getenv("ZENDESK_API_TOKEN")
    
    if not zendesk_email or not zendesk_token:
        logger.error("❌ Credenciais do Zendesk não configuradas")
        return buscar_fallback_api(termo_original, zendesk_subdomain)
    
    # Limpar termo de busca
    termo = limpar_termo_busca(termo_original)
    if len(termo) < 3:
        termo = termo_original.strip()
    
    logger.info(f"🎫 Buscando no Zendesk API: {termo}")
    
    try:
        # URL da API de busca do Zendesk
        api_url = f"https://{zendesk_subdomain}.zendesk.com/api/v2/help_center/articles/search.json"
        
        # Parâmetros da busca
        params = {
            'query': termo,
            'locale': 'pt-br',  # Priorizar português
            'per_page': 5,      # Máximo 5 resultados
            'sort_by': 'relevance'
        }
        
        # Headers de autenticação
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'IntBot/1.0'
        }
        
        # Autenticação básica (email/token)
        auth = (f"{zendesk_email}/token", zendesk_token)
        
        # Fazer requisição
        response = requests.get(
            api_url, 
            params=params, 
            headers=headers, 
            auth=auth,
            timeout=10
        )
        
        logger.info(f"📊 Status API Zendesk: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            artigos = data.get('results', [])
            
            logger.info(f"📋 {len(artigos)} artigos encontrados")
            
            if artigos:
                # Pegar o melhor artigo
                melhor_artigo = artigos[0]
                return formatar_resposta_api(melhor_artigo, zendesk_subdomain)
            else:
                logger.info("❌ Nenhum artigo encontrado via API")
                return buscar_fallback_api(termo, zendesk_subdomain)
        
        elif response.status_code == 401:
            logger.error("❌ Credenciais inválidas do Zendesk")
            return "❌ Erro de autenticação com Zendesk"
        
        elif response.status_code == 403:
            logger.error("❌ Acesso negado à API do Zendesk")
            return buscar_fallback_api(termo, zendesk_subdomain)
        
        else:
            logger.warning(f"⚠️ API Zendesk retornou status {response.status_code}")
            return buscar_fallback_api(termo, zendesk_subdomain)
            
    except requests.exceptions.Timeout:
        logger.error("⏰ Timeout na API do Zendesk")
        return buscar_fallback_api(termo, zendesk_subdomain)
    
    except Exception as e:
        logger.error(f"❌ Erro na API do Zendesk: {e}")
        return buscar_fallback_api(termo, zendesk_subdomain)

def formatar_resposta_api(artigo, subdomain):
    """Formata resposta usando dados da API oficial"""
    
    try:
        # Extrair dados do artigo
        titulo = artigo.get('title', 'Artigo sem título')
        html_url = artigo.get('html_url', '')
        
        # Extrair snippet/resumo do corpo (se disponível)
        body = artigo.get('body', '')
        snippet = artigo.get('snippet', '')
        
        # Usar snippet se disponível, senão extrair do body
        resumo = extrair_resumo_do_body(snippet or body)
        
        # Garantir que a URL está completa
        if html_url and not html_url.startswith('http'):
            html_url = f"https://{subdomain}.zendesk.com{html_url}"
        
        logger.info(f"✅ Artigo formatado: {titulo[:50]}...")
        
        if resumo:
            return f"🎫 **{titulo}**\n📝 _{resumo}_\n🔗 {html_url}"
        else:
            return f"🎫 **{titulo}**\n🔗 {html_url}"
            
    except Exception as e:
        logger.error(f"❌ Erro ao formatar resposta da API: {e}")
        return f"🎫 **Artigo encontrado no Zendesk**\n🔗 {artigo.get('html_url', 'URL não disponível')}"

def extrair_resumo_do_body(body_html):
    """Extrai um resumo limpo do HTML do artigo"""
    
    if not body_html:
        return None
    
    try:
        # Remover tags HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(body_html, 'html.parser')
        texto_limpo = soup.get_text()
        
        # Limpar texto
        texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
        
        # Pegar primeiros caracteres como resumo
        if len(texto_limpo) > 150:
            resumo = texto_limpo[:147] + "..."
        else:
            resumo = texto_limpo
        
        # Garantir que o resumo não está vazio
        if len(resumo.strip()) < 20:
            return None
            
        return resumo
        
    except Exception as e:
        logger.debug(f"Erro ao extrair resumo: {e}")
        return None

def buscar_fallback_api(termo, subdomain):
    """Fallback quando API falha - criar link de busca direto"""
    
    # Sugestões específicas com URLs diretas
    sugestoes_api = {
        "cte": {
            "title": "Como emitir Conhecimento de Transporte Eletrônico (CTE)",
            "resumo": "Passo a passo para emissão de CTE na Nuvem Envio",
            "url": f"https://{subdomain}.zendesk.com/hc/pt-br/articles/cte-emissao"
        },
        "conhecimento transporte": {
            "title": "Documentação CTE - Conhecimento de Transporte",
            "resumo": "Guia completo sobre CTE: emissão, cancelamento e consulta",
            "url": f"https://{subdomain}.zendesk.com/hc/pt-br/articles/cte-documentacao"
        },
        "api": {
            "title": "Documentação da API Nuvem Envio",
            "resumo": "Referência completa da API com endpoints e exemplos",
            "url": f"https://{subdomain}.zendesk.com/hc/pt-br/articles/api-documentacao"
        },
        "webhook": {
            "title": "Como configurar webhooks",
            "resumo": "Configuração de webhooks para notificações automáticas",
            "url": f"https://{subdomain}.zendesk.com/hc/pt-br/articles/webhooks"
        },
        "login": {
            "title": "Como fazer login na plataforma",
            "resumo": "Passo a passo para acessar sua conta Nuvem Envio",
            "url": f"https://{subdomain}.zendesk.com/hc/pt-br/articles/login"
        }
    }
    
    termo_lower = termo.lower()
    
    # Verificar sugestões específicas
    for palavra, info in sugestoes_api.items():
        if palavra in termo_lower:
            logger.info(f"💡 Sugestão específica para '{termo}': {palavra}")
            return f"🎫 **{info['title']}**\n📝 _{info['resumo']}_\n🔗 {info['url']}"
    
    # Fallback geral com busca
    search_query = urllib.parse.quote_plus(termo)
    search_url = f"https://{subdomain}.zendesk.com/hc/pt-br/search?query={search_query}"
    
    logger.info(f"🔍 Criando link de busca para: {termo}")
    return f"🔍 **Buscar '{termo}' no Help Center**\n💡 Encontre artigos relacionados no nosso centro de ajuda\n🔗 {search_url}"

def testar_api_zendesk():
    """Teste rápido da API do Zendesk"""
    print("🧪 === TESTE DA API DO ZENDESK ===\n")
    
    # Testar busca
    resultado = buscar_artigo_zendesk_api("como emitir cte")
    print("📋 Resultado da busca:")
    print(resultado)
    print()
    
    # Verificar configuração
    zendesk_email = os.getenv("ZENDESK_EMAIL")
    zendesk_token = os.getenv("ZENDESK_API_TOKEN") 
    
    print("⚙️ Configuração:")
    print(f"Email: {'✅' if zendesk_email else '❌'}")
    print(f"Token: {'✅' if zendesk_token else '❌'}")

if __name__ == "__main__":
    testar_api_zendesk()
