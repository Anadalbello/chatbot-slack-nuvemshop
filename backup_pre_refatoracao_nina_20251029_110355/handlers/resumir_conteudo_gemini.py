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
    model_name="models/gemini-2.0-flash-exp",  # Modelo experimental (filtros menos rigorosos)
    generation_config={
        "temperature": 1.0,  # Máxima criatividade
        "top_p": 0.99,
        "top_k": 100,
        "max_output_tokens": 500,
    },
    safety_settings=safety_settings
)


def extrair_conteudo_bruto(resultado_formatado):
    """
    Extrai o conteúdo bruto (título, resumo, texto) dos resultados formatados
    para enviar ao Gemini - SEM formatação markdown para evitar RECITATION
    """
    conteudo = []
    
    # Extrair títulos (sem os **)
    titulos = re.findall(r'\*\*([^*]+)\*\*', resultado_formatado)
    
    # Extrair resumos (sem os __)
    resumos = re.findall(r'_([^_]+)_', resultado_formatado)
    
    # Combinar de forma mais natural
    for i, titulo in enumerate(titulos):
        # Simplificar o título removendo termos técnicos
        titulo_simples = titulo.replace('Manual de configuração do', '').replace('copy', '').strip()
        
        if i < len(resumos):
            resumo_limpo = resumos[i].strip()
            texto = f"{titulo_simples}: {resumo_limpo}"
        else:
            texto = titulo_simples
        
        conteudo.append(texto)
    
    # Retornar texto limpo sem formatação
    return " | ".join(conteudo)


def gerar_resposta_inteligente(pergunta, conteudo_encontrado, fonte="base de conhecimento"):
    """
    Usa Gemini para gerar uma resposta natural e resumida baseada no conteúdo encontrado
    
    NOVA ABORDAGEM: Pedir para o Gemini CRIAR uma explicação nova,
    não resumir ou usar informações (para evitar RECITATION)
    
    Args:
        pergunta (str): Pergunta original do usuário
        conteudo_encontrado (str): Conteúdo formatado encontrado nas buscas
        fonte (str): Nome da fonte (Confluence, Zendesk, etc)
        
    Returns:
        str: Resposta natural gerada pelo Gemini (ou None se falhar)
    """
    
    try:
        logger.info(f"🤖 Gerando resposta inteligente com Gemini para: {pergunta}")
        
        # Extrair conteúdo bruto
        conteudo_bruto = extrair_conteudo_bruto(conteudo_encontrado)
        
        if not conteudo_bruto or len(conteudo_bruto.strip()) < 20:
            logger.warning("⚠️ Conteúdo muito curto, usando fallback")
            return None
        
        # Prompt com CONTEXTO específico sobre integrações
        # Extrair nomes de parceiros/sistemas mencionados
        parceiros_mencionados = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|[A-Z]{2,})\b', conteudo_bruto)
        parceiros_unicos = list(set([p for p in parceiros_mencionados if p not in ['Espaco', 'Base', 'Manual', 'Documento']]))[:10]
        
        prompt = f"""Voce e um assistente especializado em integracoes da Nuvemshop/Nuvem Envio.

CONTEXTO IMPORTANTE:
- Nuvemshop, Nuvem Envio e Mandae sao empresas do mesmo grupo (NAO sao parceiros)
- Todas as outras empresas sao PARCEIROS que se integram com a Nuvemshop
- Exemplos de parceiros: Magento, Wake OMS, SAP, Ativa, D2D On Platform, etc.

PERGUNTA: {pergunta}

DOCUMENTACAO ENCONTRADA: {conteudo_bruto}

PARCEIROS/SISTEMAS MENCIONADOS: {', '.join(parceiros_unicos) if parceiros_unicos else 'varios'}

INSTRUCOES:
- Se perguntarem para LISTAR parceiros, liste TODOS os sistemas/parceiros mencionados na documentacao
- Se perguntarem COMO integrar, explique o processo
- Seja direto e especifico
- Use bullet points se for lista

Sua resposta (2-4 frases ou lista):"""

        # Gerar resposta
        logger.info(f"📝 Tamanho do prompt: {len(prompt)} caracteres")
        response = model.generate_content(prompt)
        
        # Verificar prompt_feedback
        if hasattr(response, 'prompt_feedback'):
            logger.info(f"🔍 Prompt feedback: {response.prompt_feedback}")
        
        logger.info(f"📊 Resposta recebida, candidates: {len(response.candidates) if response.candidates else 0}")
        
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
                            finish_reason_map = {
                                0: "FINISH_REASON_UNSPECIFIED",
                                1: "STOP (normal)",
                                2: "RECITATION (conteúdo bloqueado)",
                                3: "SAFETY (filtro de segurança)",
                                4: "MAX_TOKENS"
                            }
                            reason_code = candidate.finish_reason
                            reason_name = finish_reason_map.get(reason_code, f"UNKNOWN({reason_code})")
                            logger.info(f"   Finish reason: {reason_code} = {reason_name}")
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
                                parts_len = len(parts) if parts is not None else 'None'
                                logger.warning(f"⚠️ Parts vazias! len={parts_len}, type={type(parts)}")
                                logger.warning(f"   Candidate finish_reason: {getattr(candidate, 'finish_reason', 'N/A')}")
                                logger.warning(f"   Content role: {getattr(content, 'role', 'N/A')}")
                                logger.warning(f"   Tentando converter content direto: {str(content)[:100] if content else 'vazio'}")
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

