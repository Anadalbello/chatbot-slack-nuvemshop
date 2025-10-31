"""
Handler para filtrar links relevantes baseado na pergunta do usuário
"""

import re
import logging

logger = logging.getLogger(__name__)

def extrair_palavras_chave_pergunta(pergunta):
    """
    Extrai palavras-chave relevantes da pergunta do usuário
    """
    # Normalizar pergunta
    pergunta_limpa = pergunta.lower().strip()
    
    # Remover stop words
    stop_words = {
        'como', 'qual', 'quais', 'onde', 'quando', 'porque', 'o', 'a', 'os', 'as',
        'um', 'uma', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas',
        'com', 'para', 'por', 'que', 'é', 'são', 'tem', 'temos', 'posso', 'pode',
        'fazer', 'funciona', 'sobre', 'me', 'meu', 'minha', 'integração', 'integracoes',
        'integra', 'integram', 'envia', 'enviar', 'atualização', 'atualizacao'
    }
    
    # Dividir em palavras
    palavras = re.findall(r'\b\w+\b', pergunta_limpa)
    
    # Filtrar stop words e palavras muito curtas
    palavras_chave = [p for p in palavras if p not in stop_words and len(p) > 2]
    
    # Adicionar variações comuns
    palavras_expandidas = []
    for palavra in palavras_chave:
        palavras_expandidas.append(palavra)
        
        # Variações comuns
        if palavra == 'nuvemshop':
            palavras_expandidas.extend(['nuvem', 'shop'])
        elif palavra == 'mandae':
            palavras_expandidas.extend(['mandaê', 'manda'])
        elif palavra == 'rastreio':
            palavras_expandidas.extend(['tracking', 'rastrear', 'acompanhar'])
        elif palavra == 'frete':
            palavras_expandidas.extend(['shipping', 'envio'])
    
    return list(set(palavras_expandidas))


def calcular_relevancia_link(link, palavras_chave):
    """
    Calcula a relevância de um link baseado nas palavras-chave da pergunta
    Retorna score de 0 a 1
    """
    if not link or not palavras_chave:
        return 0
    
    # Normalizar link
    link_lower = link.lower()
    
    # Contar quantas palavras-chave aparecem no link
    matches = 0
    for palavra in palavras_chave:
        if palavra in link_lower:
            matches += 1
    
    # Score baseado na proporção de matches
    score = matches / len(palavras_chave)
    
    # Bonus para links que contêm palavras-chave importantes
    palavras_importantes = ['nuvemshop', 'mandae', 'mandaê', 'nuvem', 'envio']
    for palavra_imp in palavras_importantes:
        if palavra_imp in link_lower and palavra_imp in [p.lower() for p in palavras_chave]:
            score += 0.3
    
    # Penalizar links genéricos
    links_genericos = ['teste', 'acesso', 'ambiente', 'manual', 'geral']
    for gen in links_genericos:
        if gen in link_lower and gen not in [p.lower() for p in palavras_chave]:
            score -= 0.2
    
    return min(1.0, max(0.0, score))


def filtrar_links_relevantes(conteudo_encontrado, pergunta, max_links=3):
    """
    Filtra links relevantes baseado na pergunta do usuário
    
    Args:
        conteudo_encontrado: Conteúdo bruto do Confluence
        pergunta: Pergunta original do usuário
        max_links: Máximo de links a retornar
        
    Returns:
        Lista de links relevantes ordenados por relevância
    """
    try:
        logger.info(f"🔗 Filtrando links relevantes para: '{pergunta}'")
        
        # Extrair todos os links do conteúdo
        links_encontrados = re.findall(r'🔗 (https?://[^\s\)]+)', conteudo_encontrado)
        
        if not links_encontrados:
            logger.warning("⚠️ Nenhum link encontrado no conteúdo")
            return []
        
        logger.info(f"📋 Encontrados {len(links_encontrados)} links no conteúdo")
        
        # Extrair palavras-chave da pergunta
        palavras_chave = extrair_palavras_chave_pergunta(pergunta)
        logger.info(f"🔍 Palavras-chave extraídas: {palavras_chave}")
        
        # Calcular relevância de cada link
        links_com_score = []
        for link in links_encontrados:
            score = calcular_relevancia_link(link, palavras_chave)
            links_com_score.append((link, score))
            logger.debug(f"  Link: {link[:50]}... | Score: {score:.2f}")
        
        # Ordenar por relevância (maior score primeiro)
        links_com_score.sort(key=lambda x: x[1], reverse=True)
        
        # Filtrar apenas links com score > 0.1
        links_relevantes = [(link, score) for link, score in links_com_score if score > 0.1]
        
        if not links_relevantes:
            logger.warning("⚠️ Nenhum link relevante encontrado")
            return []
        
        # Retornar apenas os top links
        top_links = [link for link, score in links_relevantes[:max_links]]
        
        logger.info(f"✅ {len(top_links)} links relevantes selecionados")
        for i, link in enumerate(top_links, 1):
            score = next(score for l, score in links_com_score if l == link)
            logger.info(f"  {i}. {link[:60]}... (score: {score:.2f})")
        
        return top_links
        
    except Exception as e:
        logger.error(f"❌ Erro ao filtrar links: {e}")
        import traceback
        traceback.print_exc()
        return []


def gerar_resposta_sem_resultados(pergunta):
    """
    Gera uma resposta quando não há resultados relevantes
    """
    resposta = f"**{pergunta}**\n\n"
    resposta += "Não encontrei informações específicas sobre essa pergunta na nossa base de conhecimento.\n\n"
    resposta += "**💡 Sugestões:**\n"
    resposta += "• 📋 **Portal de Integrações:** Acesse nossa documentação completa\n"
    resposta += "• 🎫 **Abrir chamado:** Nossa equipe pode ajudar com casos específicos\n"
    resposta += "• 🔍 **Reformule a pergunta:** Tente usar termos mais específicos\n\n"
    resposta += "_Se precisar de ajuda imediata, recomendo abrir um chamado para nossa equipe de integrações._"
    
    return resposta


if __name__ == "__main__":
    # Teste local
    logging.basicConfig(level=logging.INFO)
    
    print("=== Teste de filtro de links ===\n")
    
    # Simular conteúdo com links
    conteudo_teste = """
    • **Integração Wake OMS + Mandaê** (Espaço: Base de dados de gerenciamento de conhecimento - Integrações)
    📝 _Manual de integração entre Wake OMS e Mandaê para envio de pedidos..._
    🔗 https://tiendanube.atlassian.net/wiki/spaces/BDGCI/pages/551655262/Integra+o+Wake+OMS+Manda
    
    • **Manual de Ativação Nuvem Envio Coleta** (Espaço: Base de dados de gerenciamento de conhecimento - Integrações)
    📝 _Como ativar o serviço de coleta do Nuvem Envio..._
    🔗 https://tiendanube.atlassian.net/wiki/spaces/BDGCI/pages/551655250/Manual+de+Ativa+o+Nuvem+Envio+Coleta
    
    • **Lojas de Teste - Acessos e Ambientes** (Espaço: Base de dados de gerenciamento de conhecimento - Integrações)
    📝 _Informações sobre ambientes de teste..._
    🔗 https://tiendanube.atlassian.net/wiki/spaces/BDGCI/pages/551655149/Lojas+de+Teste+Acessos+e+Ambientes
    """
    
    perguntas_teste = [
        "a integração Mandaê com nuvemshop envia atualização de rastreio?",
        "como integrar com wake oms?",
        "como ativar coleta no nuvem envio?",
        "quais são os ambientes de teste?"
    ]
    
    for pergunta in perguntas_teste:
        print(f"\n📝 Pergunta: {pergunta}")
        links = filtrar_links_relevantes(conteudo_teste, pergunta)
        
        if links:
            print(f"✅ Links relevantes ({len(links)}):")
            for i, link in enumerate(links, 1):
                print(f"  {i}. {link}")
        else:
            print("❌ Nenhum link relevante")
            print("Resposta sugerida:")
            print(gerar_resposta_sem_resultados(pergunta)[:200] + "...")
