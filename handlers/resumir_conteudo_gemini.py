#!/usr/bin/env python3
"""
Módulo para gerar resumos inteligentes do conteúdo encontrado usando Gemini
Similar a como IAs respondem perguntas de forma natural
"""

import os
import logging
import re
import time
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
    Extrai o conteúdo bruto dos resultados formatados para enviar ao Gemini
    Funciona tanto com formato markdown antigo quanto com formato novo do JSON
    """
    if not resultado_formatado:
        return ""
    
    # Se já é uma string simples, tentar extrair informação útil
    # Remover formatação markdown
    texto_limpo = resultado_formatado
    
    # Remover emojis e markdown básico
    texto_limpo = re.sub(r'\*([^*]+)\*', r'\1', texto_limpo)  # *texto* -> texto
    texto_limpo = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto_limpo)  # **texto** -> texto
    texto_limpo = re.sub(r'_([^_]+)_', r'\1', texto_limpo)  # _texto_ -> texto
    
    # Remover divisores
    texto_limpo = re.sub(r'━+', '', texto_limpo)
    
    # Extrair informações principais: nome, funcionalidades, outras info
    conteudo = []
    
    # Extrair nome do ERP (primeira linha com emoji e nome)
    nome_match = re.search(r'✨\s*([^\n]+)', texto_limpo)
    if nome_match:
        conteudo.append(f"Nome: {nome_match.group(1).strip()}")
    
    # Extrair TODAS as funcionalidades (disponíveis e indisponíveis) - CRÍTICO para precisão
    # Buscar seção de funcionalidades disponíveis
    func_disponiveis_match = re.search(r'✅[^\n]*Funcionalidades Disponíveis[^\n]*\n(.*?)(?=\n❌|\n━|\n📋|$)', texto_limpo, re.DOTALL)
    if func_disponiveis_match:
        func_disponiveis_text = func_disponiveis_match.group(1).strip()
        conteudo.append(f"Funcionalidades disponíveis:\n{func_disponiveis_text}")
    
    # Buscar seção de funcionalidades indisponíveis - IMPORTANTE para não inventar informações
    func_indisponiveis_match = re.search(r'❌[^\n]*Funcionalidades Indisponíveis[^\n]*\n(.*?)(?=\n✅|\n━|\n📋|$)', texto_limpo, re.DOTALL)
    if func_indisponiveis_match:
        func_indisponiveis_text = func_indisponiveis_match.group(1).strip()
        conteudo.append(f"Funcionalidades indisponíveis (NÃO disponíveis):\n{func_indisponiveis_text}")
    
    # Se não encontrou seções separadas, tentar extrair todas as funcionalidades de uma vez
    if not func_disponiveis_match and not func_indisponiveis_match:
        # Buscar todas as linhas que parecem ser funcionalidades (com emojis ou marcadores)
        todas_func = re.findall(r'[🚚🛡️⚙️✏️📏📦💰🏢🏷️🔄•]\s*\*?([^:]+):\s*([^\n]+)', texto_limpo)
        if todas_func:
            func_text = "\n".join([f"  - {nome.strip()}: {valor.strip()}" for nome, valor in todas_func])
            conteudo.append(f"Todas as funcionalidades:\n{func_text}")
    
    # Extrair outras informações (complexidade, responsáveis, etc)
    outras_info_match = re.search(r'📋[^\n]*Outras Informações[^\n]*\n(.*?)(?=\n📞|\n━|$)', texto_limpo, re.DOTALL)
    if outras_info_match:
        conteudo.append(f"Outras informações: {outras_info_match.group(1).strip()}")
    
    # Extrair contato
    contato_match = re.search(r'📞[^\n]*Suporte/Contato[^\n]*\n(.*?)(?=\n|$)', texto_limpo, re.DOTALL)
    if contato_match:
        conteudo.append(f"Contato: {contato_match.group(1).strip()}")
    
    # Se conseguiu extrair partes estruturadas, retornar
    if conteudo:
        return "\n".join(conteudo)
    
    # Fallback: remover emojis e formatação, manter texto
    # Remover emojis comuns
    emojis = ['✨', '📂', '🔧', '✅', '❌', '🚚', '📦', '🛡️', '🏢', '🏷️', '🔄', 
              '🟢', '🟡', '🔴', '⚪', '⚙️', '🧪', '👨‍💻', '💰', '⚠️', '🌐', '📚', '📞', '📧', '📱']
    for emoji in emojis:
        texto_limpo = texto_limpo.replace(emoji, '')
    
    # Limpar espaços múltiplos
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
    
    # Se ainda tem conteúdo suficiente, retornar
    if len(texto_limpo) > 50:
        return texto_limpo
    
    # Último fallback: retornar texto original limpo sem quebras excessivas
    return re.sub(r'\n\s*\n+', '\n', resultado_formatado).strip()


def gerar_resposta_inteligente(pergunta, conteudo_encontrado, fonte="base de conhecimento", contexto_thread=None):
    """
    Usa Gemini para gerar uma resposta natural e resumida baseada no conteúdo encontrado
    
    NOVA ABORDAGEM: Pedir para o Gemini CRIAR uma explicação nova,
    não resumir ou usar informações (para evitar RECITATION)
    
    Args:
        pergunta (str): Pergunta original do usuário
        conteudo_encontrado (str): Conteúdo formatado encontrado nas buscas
        fonte (str): Nome da fonte (Confluence, Zendesk, etc)
        contexto_thread (str): Histórico da thread para contexto adicional (opcional)
        
    Returns:
        str: Resposta natural gerada pelo Gemini (ou None se falhar)
    """
    
    try:
        logger.info(f"🤖 Gerando resposta inteligente com Gemini para: {pergunta}")
        
        # Extrair conteúdo bruto
        conteudo_bruto = extrair_conteudo_bruto(conteudo_encontrado)
        
        logger.debug(f"📄 Conteúdo extraído ({len(conteudo_bruto)} chars): {conteudo_bruto[:200]}...")
        
        if not conteudo_bruto or len(conteudo_bruto.strip()) < 10:
            logger.warning(f"⚠️ Conteúdo muito curto ({len(conteudo_bruto) if conteudo_bruto else 0} chars), usando fallback")
            return None
        
        # Prompt com CONTEXTO específico sobre integrações
        # Extrair nomes de parceiros/sistemas mencionados
        parceiros_mencionados = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|[A-Z]{2,})\b', conteudo_bruto)
        parceiros_unicos = list(set([p for p in parceiros_mencionados if p not in ['Espaco', 'Base', 'Manual', 'Documento']]))[:10]
        
        # Montar contexto completo
        contexto_completo = ""
        if contexto_thread:
            contexto_completo = f"\nCONTEXTO DA CONVERSA ANTERIOR:\n{contexto_thread}\n\n"
            contexto_completo += "IMPORTANTE: Use o contexto acima para entender referências. "
            contexto_completo += "Se o usuário usar pronomes como 'ela', 'ele', 'essa integração', "
            contexto_completo += "refira-se ao contexto da conversa anterior.\n\n"
        
        prompt = f"""Você é um assistente especializado em integrações da Nuvem Envio/Nuvemshop.

CONTEXTO IMPORTANTE:
- Nuvemshop, Nuvem Envio e Mandaê são empresas do mesmo grupo (NÃO são parceiros)
- Todas as outras empresas são PARCEIROS que se integram
- Exemplos de parceiros/ERPs: Notazz, Bling, Eccosys, Tiny, Omie, etc.
{contexto_completo}
PERGUNTA ORIGINAL: {pergunta}

DADOS DA INTEGRAÇÃO ENCONTRADA:
{conteudo_bruto}

INSTRUÇÕES CRÍTICAS E OBRIGATÓRIAS:
1. ⚠️ USE APENAS AS INFORMAÇÕES FORNECIDAS NOS DADOS ACIMA - NÃO INVENTE NADA
2. ⚠️ Se uma funcionalidade está marcada como "Não (❌)" ou "Não", NÃO diga que ela está disponível
3. ⚠️ Se uma funcionalidade está marcada como "Sim (✔️)" ou "Sim", você pode dizer que está disponível
4. ⚠️ DIFERENÇA IMPORTANTE:
   - "Devolucao_Codigo_Rastreamento" = retorna o código de rastreamento (pode ser Sim ou Não)
   - "Atualiza_Status_Rastreio" = atualiza automaticamente o status do rastreamento na plataforma (pode ser Sim ou Não)
   - São funcionalidades DIFERENTES - verifique cada uma separadamente nos dados
5. RESPONDA DIRETAMENTE A PERGUNTA primeiro, depois forneça detalhes se necessário
6. Se perguntarem "temos integração?" ou "existe integração?", responda: "Sim, temos integração com [nome]." ou "Não, não temos integração com [nome]."
7. Se perguntarem sobre funcionalidades específicas, responda sobre essas funcionalidades PRIMEIRO e de forma PRECISA
8. Se perguntarem sobre contato/suporte, responda com os dados de contato primeiro
9. Seja DIRETO e OBJETIVO - não liste tudo, foque no que foi perguntado
10. Use formatação markdown para destacar informações importantes (*negrito*)
11. Se você não tiver certeza sobre uma informação, NÃO invente - diga que precisa verificar

FORMATO DA RESPOSTA:
- 1-2 frases respondendo diretamente a pergunta com PRECISÃO
- Depois, se necessário, 1-2 frases com informações complementares relevantes
- NÃO liste tudo - apenas o que é relevante para a pergunta
- NÃO invente informações que não estão nos dados fornecidos

Sua resposta (focada, direta e PRECISA baseada apenas nos dados fornecidos):"""

        # Gerar resposta com retry
        logger.info(f"📝 Tamanho do prompt: {len(prompt)} caracteres")
        
        max_retries = 3
        retry_delay = 1  # segundos
        
        response = None
        for tentativa in range(max_retries):
            try:
                response = model.generate_content(prompt)
                break  # Sucesso, sair do loop
            except Exception as e:
                if tentativa < max_retries - 1:
                    logger.warning(f"⚠️ Erro na tentativa {tentativa + 1}/{max_retries}: {e}. Tentando novamente em {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponencial
                else:
                    logger.error(f"❌ Falha após {max_retries} tentativas: {e}")
                    raise
        
        if not response:
            return None
        
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

