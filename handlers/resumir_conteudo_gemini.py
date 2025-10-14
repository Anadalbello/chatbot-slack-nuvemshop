#!/usr/bin/env python3
"""
Módulo para gerar resumos inteligentes do conteúdo encontrado usando Gemini
Similar a como IAs respondem perguntas de forma natural
"""

import os
import logging
import re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
logger = logging.getLogger(__name__)

# Configurar Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configurações de segurança mais permissivas
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    },
]

model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash",  # Modelo rápido e eficiente
    generation_config={
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 500,  # Resumo conciso
    },
    safety_settings=safety_settings
)


def extrair_conteudo_bruto(resultado_formatado):
    """
    Extrai o conteúdo bruto (título, resumo, texto) dos resultados formatados
    para enviar ao Gemini
    """
    conteudo = []
    
    # Extrair títulos
    titulos = re.findall(r'\*\*([^*]+)\*\*', resultado_formatado)
    
    # Extrair resumos (texto entre _..._)
    resumos = re.findall(r'_([^_]+)_', resultado_formatado)
    
    # Combinar tudo
    for i, titulo in enumerate(titulos):
        texto = f"Documento: {titulo}"
        if i < len(resumos):
            texto += f"\nConteúdo: {resumos[i]}"
        conteudo.append(texto)
    
    return "\n\n".join(conteudo)


def gerar_resposta_inteligente(pergunta, conteudo_encontrado, fonte="base de conhecimento"):
    """
    Usa Gemini para gerar uma resposta natural e resumida baseada no conteúdo encontrado
    
    Similar a como IAs respondem perguntas:
    - Lê o conteúdo disponível
    - Sintetiza uma resposta direta e clara
    - Responde de forma natural
    
    Args:
        pergunta (str): Pergunta original do usuário
        conteudo_encontrado (str): Conteúdo formatado encontrado nas buscas
        fonte (str): Nome da fonte (Confluence, Zendesk, etc)
        
    Returns:
        str: Resposta natural gerada pelo Gemini
    """
    
    try:
        logger.info(f"🤖 Gerando resposta inteligente com Gemini para: {pergunta}")
        
        # Extrair conteúdo bruto
        conteudo_bruto = extrair_conteudo_bruto(conteudo_encontrado)
        
        if not conteudo_bruto or len(conteudo_bruto.strip()) < 20:
            logger.warning("⚠️ Conteúdo muito curto, usando fallback")
            return None
        
        # Construir prompt para o Gemini
        prompt = f"""Você é um assistente técnico especializado em integrações e documentação.

Sua tarefa é responder à pergunta do usuário de forma clara, direta e profissional, usando APENAS as informações fornecidas abaixo.

**REGRAS IMPORTANTES:**
1. Responda de forma natural, como se estivesse explicando para um colega
2. Use APENAS as informações fornecidas - não invente nada
3. Seja conciso - máximo 4-5 linhas
4. Se a informação não for suficiente para responder, seja honesto sobre isso
5. Use linguagem técnica mas acessível
6. NÃO mencione "de acordo com a documentação" ou similar - responda diretamente

**Pergunta do usuário:**
{pergunta}

**Informações disponíveis em nossa {fonte}:**
{conteudo_bruto}

**Resposta (seja direto, claro e conciso):**"""

        # Gerar resposta
        response = model.generate_content(prompt)
        
        if response:
            resposta_gerada = None
            
            # Tentar acessar o texto de forma segura
            try:
                # Método 1: Tentar .text diretamente
                resposta_gerada = response.text.strip()
                logger.info("✅ Acesso direto ao .text funcionou")
            except (ValueError, AttributeError) as e:
                # Método 2: Acessar através das parts
                logger.info(f"⚡ Tentando acesso alternativo às parts (erro: {type(e).__name__})")
                
                try:
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        logger.info(f"   Candidate encontrado, tipo: {type(candidate)}")
                        
                        # Verificar finish_reason e safety_ratings
                        if hasattr(candidate, 'finish_reason'):
                            logger.info(f"   Finish reason: {candidate.finish_reason}")
                        if hasattr(candidate, 'safety_ratings'):
                            logger.info(f"   Safety ratings: {candidate.safety_ratings}")
                        
                        if hasattr(candidate, 'content') and candidate.content:
                            content = candidate.content
                            logger.info(f"   Content encontrado, tipo: {type(content)}")
                            
                            # Tentar diferentes formas de acessar parts
                            parts = None
                            if hasattr(content, 'parts'):
                                parts = content.parts
                                logger.info(f"   Parts via atributo: {type(parts)}, len: {len(parts) if parts else 0}")
                            
                            if not parts and hasattr(content, '_parts'):
                                parts = content._parts
                                logger.info(f"   Parts via _parts: {type(parts)}, len: {len(parts) if parts else 0}")
                            
                            if parts and len(parts) > 0:
                                parts_text = []
                                for i, part in enumerate(parts):
                                    logger.info(f"   Part {i}: {type(part)}")
                                    
                                    # Tentar diferentes formas de acessar o texto
                                    text = None
                                    if hasattr(part, 'text'):
                                        text = part.text
                                    elif hasattr(part, '_text'):
                                        text = part._text
                                    elif isinstance(part, str):
                                        text = part
                                    
                                    if text:
                                        parts_text.append(str(text))
                                        logger.info(f"   Part {i} adicionada: {len(text)} chars")
                                    else:
                                        logger.warning(f"   Part {i} sem texto detectável")
                                
                                if parts_text:
                                    resposta_gerada = ' '.join(parts_text).strip()
                                    logger.info(f"✅ {len(parts_text)} parts combinadas com sucesso")
                                else:
                                    logger.warning("⚠️ Parts encontradas mas sem texto")
                            else:
                                logger.warning(f"⚠️ Parts não encontradas ou vazias. Content dict: {dir(content)[:5]}...")
                        else:
                            logger.warning("⚠️ Candidate sem content")
                    else:
                        logger.warning("⚠️ Nenhum candidate encontrado na resposta")
                except Exception as inner_e:
                    logger.error(f"❌ Erro ao acessar parts: {inner_e}", exc_info=True)
                    return None
            
            # Validar que a resposta não é muito genérica
            if resposta_gerada and len(resposta_gerada) > 30:
                logger.info(f"✅ Resposta gerada com sucesso ({len(resposta_gerada)} caracteres)")
                return resposta_gerada
            else:
                logger.warning(f"⚠️ Resposta inválida (len: {len(resposta_gerada) if resposta_gerada else 0}), usando fallback")
                return None
        else:
            logger.warning("⚠️ Gemini não retornou resposta")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resposta com Gemini: {e}")
        return None


def formatar_resposta_final(pergunta, resposta_gemini, conteudo_original, links):
    """
    Formata a resposta final combinando:
    - Resposta inteligente do Gemini
    - Links para documentação completa
    
    Args:
        pergunta (str): Pergunta original
        resposta_gemini (str): Resposta gerada pelo Gemini
        conteudo_original (str): Conteúdo formatado original (com links)
        links (list): Lista de links extraídos
        
    Returns:
        str: Resposta final formatada
    """
    
    resposta_final = f"**{pergunta}**\n\n"
    resposta_final += f"{resposta_gemini}\n\n"
    resposta_final += "---\n\n"
    resposta_final += "📚 **Documentação completa:**\n"
    
    # Extrair links
    links_encontrados = re.findall(r'🔗 (https?://[^\s\)]+)', conteudo_original)
    
    if links_encontrados:
        for i, link in enumerate(links_encontrados[:3], 1):  # Máximo 3 links
            resposta_final += f"{i}. {link}\n"
    
    resposta_final += "\n_Para mais informações ou dúvidas específicas, estou à disposição._"
    
    return resposta_final


if __name__ == "__main__":
    # Teste
    print("🧪 === TESTE DE RESPOSTA INTELIGENTE COM GEMINI ===\n")
    
    pergunta = "como integrar magento?"
    
    conteudo = """• **Manual de configuração do Regra Frete no WebApp** (Espaço: Base de dados)
  📝 _Descrição do Problema e Área de Negócio Impactada. Configure o frete por região_
  🔗 https://tiendanube.atlassian.net/wiki/spaces/BDGCI/pages/551654678

• **Integração Wake OMS + Mandaê** (Espaço: Integrações)
  📝 _Wake OMS é uma plataforma de gestão de pedidos que ajuda empresas a gerenciar seus pedidos_
  🔗 https://tiendanube.atlassian.net/wiki/spaces/BDGCI/pages/551654902"""
    
    print("Pergunta:", pergunta)
    print("\nConteúdo encontrado:")
    print(conteudo)
    print("\n" + "="*80 + "\n")
    
    resposta = gerar_resposta_inteligente(pergunta, conteudo, "Confluence")
    
    if resposta:
        print("🤖 Resposta do Gemini:")
        print(resposta)
        print("\n" + "="*80 + "\n")
        
        links = re.findall(r'🔗 (https?://[^\s\)]+)', conteudo)
        resposta_final = formatar_resposta_final(pergunta, resposta, conteudo, links)
        
        print("📤 Resposta final formatada:")
        print(resposta_final)
    else:
        print("❌ Não foi possível gerar resposta")

