#!/usr/bin/env python3
"""
Módulo para refinar buscas usando Gemini AI
"""

import logging
from handlers.gemini_handler import get_gemini_response
from handlers.extrair_palavras_chave import melhorar_busca_confluence

logger = logging.getLogger(__name__)

def refinar_busca_com_gemini(pergunta):
    """
    Usa Gemini AI para extrair palavras-chave relevantes de uma pergunta
    
    Args:
        pergunta (str): Pergunta em linguagem natural
        
    Returns:
        str: Palavras-chave otimizadas para busca
    """
    
    prompt = f"""Extraia 2-3 palavras-chave desta pergunta. Retorne APENAS as palavras separadas por espaço, sem explicação.

Exemplos:
"como integrar magento?" → integração magento
"temos doc de template?" → template documentação  
"qual processo criar integração?" → processo integração

Pergunta: {pergunta}
Palavras-chave:"""
    
    try:
        logger.info(f"🤖 Usando Gemini para refinar busca: {pergunta}")
        resposta = get_gemini_response(prompt)
        
        # Limpar resposta
        palavras_chave = resposta.strip().lower()
        
        # Remover possíveis artefatos
        palavras_chave = palavras_chave.replace('"', '').replace("'", '')
        palavras_chave = palavras_chave.replace('\n', ' ').replace('\r', ' ')
        
        # Se a resposta for muito longa ou estranha, usar fallback
        if len(palavras_chave) > 50 or len(palavras_chave.split()) > 5:
            logger.warning(f"⚠️ Resposta do Gemini muito longa, usando fallback")
            return melhorar_busca_confluence(pergunta)
        
        logger.info(f"✅ Gemini extraiu: {palavras_chave}")
        return palavras_chave
        
    except Exception as e:
        logger.error(f"❌ Erro ao usar Gemini para refinar busca: {e}")
        logger.info(f"🔄 Usando método de fallback")
        # Fallback para método de extração de palavras-chave
        return melhorar_busca_confluence(pergunta)

if __name__ == "__main__":
    # Testes
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🧪 === TESTE DE REFINAMENTO COM GEMINI ===\n")
    
    exemplos = [
        "oque temos de integrações?",
        "como integrar magento?",
        "temos alguma doc de template?",
        "qual o processo para criar uma integração?",
        "onde encontro a documentação da API?",
        "como configurar webhook?"
    ]
    
    for exemplo in exemplos:
        print(f"Pergunta: {exemplo}")
        resultado = refinar_busca_com_gemini(exemplo)
        print(f"Palavras-chave: {resultado}")
        print("-" * 80)

