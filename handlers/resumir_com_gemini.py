#!/usr/bin/env python3
"""
Módulo para criar resumos inteligentes usando Gemini AI
"""

import logging
from handlers.gemini_handler import get_gemini_response

logger = logging.getLogger(__name__)

def criar_resumo_resposta(pergunta, conteudo_encontrado, fonte="Confluence"):
    """
    Usa Gemini para criar um resumo personalizado da resposta
    
    Args:
        pergunta (str): Pergunta original do usuário
        conteudo_encontrado (str): Conteúdo encontrado na busca
        fonte (str): Fonte do conteúdo (Confluence, Zendesk, etc)
        
    Returns:
        str: Resumo formatado no estilo Ask Nina
    """
    
    prompt = f"""Você é um assistente técnico profissional que ajuda com integrações de e-commerce.

Crie uma resposta clara e profissional para esta pergunta, baseada no conteúdo encontrado.

Pergunta do usuário: {pergunta}

Conteúdo encontrado em nossa base de conhecimento:
{conteudo_encontrado[:800]}

Instruções para a resposta:
1. Comece com "Olá!"
2. Use um tom profissional mas amigável
3. Resuma as informações principais em 2-3 frases
4. Mantenha o foco na pergunta do usuário
5. Não invente informações que não estão no conteúdo
6. Use formatação markdown (*negrito* para destaque)

Formato da resposta:
Olá!

[Resumo das informações encontradas em 2-3 frases]

[Se relevante, adicione um próximo passo ou sugestão]

Resposta:"""
    
    try:
        logger.info(f"🤖 Criando resumo personalizado com Gemini para: {pergunta[:50]}...")
        resposta = get_gemini_response(prompt)
        
        # Limpar resposta
        resposta = resposta.strip()
        
        # Validar que a resposta não é muito longa
        if len(resposta) > 1000:
            logger.warning(f"⚠️ Resposta do Gemini muito longa ({len(resposta)} chars), usando fallback")
            return criar_resumo_simples(pergunta, conteudo_encontrado, fonte)
        
        # Validar que começa com "Olá"
        if not resposta.startswith("Olá"):
            logger.warning(f"⚠️ Resposta não começa com 'Olá', ajustando...")
            resposta = "Olá!\n\n" + resposta
        
        logger.info(f"✅ Resumo criado com sucesso ({len(resposta)} chars)")
        return resposta
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar resumo com Gemini: {e}")
        logger.info(f"🔄 Usando resumo simples como fallback")
        return criar_resumo_simples(pergunta, conteudo_encontrado, fonte)

def criar_resumo_simples(pergunta, conteudo, fonte="Confluence"):
    """
    Cria um resumo simples sem usar IA (fallback)
    
    Args:
        pergunta (str): Pergunta original
        conteudo (str): Conteúdo encontrado
        fonte (str): Fonte do conteúdo
        
    Returns:
        str: Resumo simples formatado
    """
    
    # Extrair título e resumo do conteúdo
    linhas = [l.strip() for l in conteudo.split('\n') if l.strip()]
    
    # Tentar extrair título
    titulo = ""
    resumo_conteudo = ""
    
    for linha in linhas:
        if '**' in linha:
            # Linha com título
            titulo = linha.replace('•', '').replace('**', '').replace('*', '').strip()
            titulo = titulo.split('(Espaço:')[0].strip()  # Remover "(Espaço: ...)"
        elif '📝' in linha or '_' in linha:
            # Linha com resumo
            resumo_conteudo = linha.replace('📝', '').replace('_', '').strip()
            if resumo_conteudo:
                break
    
    # Construir resposta no estilo Ask Nina
    resposta = "Olá!\n\n"
    
    if titulo:
        resposta += f"Com base nas informações disponíveis em nossa base de conhecimento, encontrei documentação sobre *{titulo}*.\n\n"
    else:
        resposta += f"Com base nas informações disponíveis em nossa base de conhecimento, encontrei conteúdo relacionado a sua pergunta sobre *{pergunta}*.\n\n"
    
    if resumo_conteudo and len(resumo_conteudo) > 20:
        # Se temos um resumo, incluir ele
        resposta += f"{resumo_conteudo[:300]}{'...' if len(resumo_conteudo) > 300 else ''}\n\n"
        resposta += "Para informações completas e detalhadas, acesse o link disponibilizado abaixo."
    else:
        resposta += "Você pode acessar os detalhes completos através do link disponibilizado abaixo."
    
    return resposta

def formatar_resposta_com_resumo(pergunta, conteudo_encontrado, link, fonte="Confluence"):
    """
    Formata a resposta completa com resumo e link
    
    Args:
        pergunta (str): Pergunta original
        conteudo_encontrado (str): Conteúdo encontrado
        link (str): Link para o conteúdo completo
        fonte (str): Fonte do conteúdo
        
    Returns:
        str: Resposta completa formatada
    """
    
    # Criar resumo inteligente
    resumo = criar_resumo_resposta(pergunta, conteudo_encontrado, fonte)
    
    # Adicionar link e próximos passos
    resposta_completa = resumo + "\n\n"
    resposta_completa += f"📎 Para mais detalhes, acesse: {link}\n\n"
    resposta_completa += "Se precisar de mais informações ou tiver dúvidas específicas, estou à disposição para ajudar."
    
    return resposta_completa

if __name__ == "__main__":
    # Teste
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🧪 === TESTE DE RESUMO COM GEMINI ===\n")
    
    pergunta_teste = "como integrar magento?"
    conteudo_teste = """
    • **Integração Magento 2** (Espaço: Documentação Técnica)
      📝 _O Magento 2 é uma plataforma de e-commerce robusta. Para integrar com nossa API, você precisa:
      1. Configurar credenciais OAuth
      2. Instalar o módulo de integração
      3. Configurar webhooks
      4. Testar em ambiente de homologação_
      🔗 https://confluence.example.com/magento-integration
    """
    
    resultado = formatar_resposta_com_resumo(
        pergunta_teste, 
        conteudo_teste,
        "https://confluence.example.com/magento-integration",
        "Confluence"
    )
    
    print(resultado)

