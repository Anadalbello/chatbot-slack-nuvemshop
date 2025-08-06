import logging

logger = logging.getLogger(__name__)

def buscar_google_sites(termo):
    """
    Retorna informações básicas sobre o portal - usado apenas como fallback
    """
    portal_url = "https://sites.google.com/nuvemshop.com.br/integracoesnuvemenvio/início"
    
    # Base de conhecimento simples para dar dicas sobre onde procurar
    dicas = {
        "api": "Consulte a seção 'APIs' no portal para documentação completa dos endpoints",
        "webhook": "Veja a seção 'Webhooks' para configuração e exemplos",
        "integracao": "Confira os guias de integração para diferentes plataformas",
        "checkout": "Documentação completa do processo de checkout está disponível",
        "pagamento": "Informações sobre APIs de pagamento e fluxos",
        "autenticacao": "Documentação sobre OAuth e autenticação de apps"
    }
    
    # Procurar dica relacionada ao termo
    for palavra_chave, dica in dicas.items():
        if palavra_chave in termo.lower():
            logger.info(f"Dica encontrada para '{termo}': {palavra_chave}")
            return f"📋 **{dica}**\n🔗 {portal_url}"
    
    # Dica genérica
    return f"📋 Consulte o portal de integrações para informações sobre '{termo}'\n🔗 {portal_url}" 