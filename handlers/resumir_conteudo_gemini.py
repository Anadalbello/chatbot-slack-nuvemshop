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
    model_name="models/gemini-2.5-flash",  # Modelo estável (gemini-2.0-flash-exp foi descontinuado)
    generation_config={
        "temperature": 0.5,  # Menor para respostas mais objetivas
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,  # Maior para evitar cortes em listas longas
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

INSTRUÇÕES CRÍTICAS E OBRIGATÓRIAS (LEIA COM ATENÇÃO):
1. ⚠️⚠️⚠️ USE APENAS AS INFORMAÇÕES FORNECIDAS NOS DADOS ACIMA - NÃO INVENTE NADA ⚠️⚠️⚠️
2. ⚠️ Se uma funcionalidade está marcada como "Não (❌)" ou "Não", NUNCA diga que ela está disponível
3. ⚠️ Se uma funcionalidade está marcada como "Sim (✔️)" ou "Sim", você pode dizer que está disponível
4. ⚠️ DIFERENÇA CRÍTICA ENTRE FUNCIONALIDADES:
   - "Devolucao_Codigo_Rastreamento" = retorna o código de rastreamento (pode ser Sim ou Não)
   - "Atualiza_Status_Rastreio" = atualiza automaticamente o status do rastreamento na plataforma (pode ser Sim ou Não)
   - São funcionalidades COMPLETAMENTE DIFERENTES - verifique CADA UMA separadamente nos dados
   - Se "Atualiza_Status_Rastreio" está como "Não (❌)", NÃO diga que atualiza status automaticamente
   - Se "Devolucao_Codigo_Rastreamento" está como "Sim (✔️)", você pode dizer que retorna o código
5. ⚠️ ANTES DE MENCIONAR QUALQUER FUNCIONALIDADE, VERIFIQUE NOS DADOS se ela está como "Sim" ou "Não"
6. ⚠️ Se perguntarem "como funciona", mencione APENAS as funcionalidades que estão como "Sim (✔️)" nos dados
7. ⚠️ Se perguntarem sobre funcionalidades específicas, verifique EXATAMENTE nos dados antes de responder
8. RESPONDA DIRETAMENTE A PERGUNTA primeiro, depois forneça detalhes se necessário
9. Se perguntarem "temos integração?" ou "existe integração?", responda: "Sim, temos integração com [nome]." ou "Não, não temos integração com [nome]."
10. Seja DIRETO e OBJETIVO - não liste tudo, foque no que foi perguntado
11. Use formatação markdown para destacar informações importantes (*negrito*)
12. Se você não tiver certeza sobre uma informação, NÃO invente - diga que precisa verificar

FORMATO OBRIGATÓRIO - RESPOSTA EM PARÁGRAFO FLUIDO:
⚠️ NÃO explique o que é cada funcionalidade (ex: não explique "cálculo de frete é...", "peso cubado serve para...")
⚠️ Use APENAS as informações do JSON - nada de explicações genéricas
⚠️ Escreva em parágrafos fluidos, não em lista de bullets

Se perguntarem "como funciona" ou visão geral:
- 1º parágrafo: "A integração com [Nome] funciona [através da X / via API], permitindo [lista o que está Sim: cálculo de frete, configuração de seguro, atualização de status, etc.]. [O que está Não ou é manual: ex: A importação de pedidos e impressão de etiquetas são feitas manualmente via WebApp.]"
- 2º parágrafo: Suporte e documentação - "Se precisar de ajuda, o responsável é [X] e você pode consultar o manual: [link]. Para suporte, entre em contato com [Y]."
- Escreva de forma natural, agrupando funcionalidades disponíveis e indisponíveis em frases
- Inclua link do manual e contato se estiver nos dados

EXEMPLO DO FORMATO IDEAL (Tray):
"A integração com a Tray funciona através da Mandaê, permitindo o cálculo de frete, configuração de seguro, atualização de status de rastreio, cálculo de peso cubado e múltiplos volumes. A importação de pedidos e impressão de etiquetas são feitas manualmente via WebApp da Mandaê.

Se precisar de ajuda com a configuração, o responsável é a Mandaê e você pode consultar o manual de integração: [link]. Para suporte, entre em contato diretamente com a Tray."

NÃO faça lista de bullets (• Sim • Não). Use parágrafos fluidos como no exemplo acima.

Sua resposta (em parágrafos fluidos, objetiva, baseada APENAS nos dados - SEM EXPLICAÇÕES do que cada termo significa):"""

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
            
            # Verificar se resposta parece truncada (cortada no meio)
            # Ex: termina com palavra incompleta ("cálculo de fre") ou finish_reason=MAX_TOKENS
            resposta_truncada = False
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 4:  # MAX_TOKENS
                    resposta_truncada = True
                    logger.warning("⚠️ Resposta truncada (MAX_TOKENS) - usando fallback")
            # Detectar se termina com palavra incompleta (ex: "fre" de "frete")
            # Só aplicar quando resposta é curta (<150 chars) - resposta completa seria mais longa
            PALAVRAS_CURTAS_VALIDAS = {'sim', 'não', 'nao', 'sim', 'etc', 'ok'}
            if resposta_gerada and len(resposta_gerada) > 10 and len(resposta_gerada) < 150:
                ultima_palavra = resposta_gerada.strip().split()[-1] if resposta_gerada.strip() else ""
                ultima_limpa = re.sub(r'[^\w]', '', ultima_palavra).lower()
                termina_com_pontuacao = ultima_palavra.rstrip().endswith(('.', '!', '?', ')'))
                if len(ultima_limpa) <= 4 and ultima_limpa not in PALAVRAS_CURTAS_VALIDAS and not termina_com_pontuacao:
                    resposta_truncada = True
                    logger.warning(f"⚠️ Resposta parece cortada (termina com '{ultima_palavra}') - usando fallback")
            
            # Validar que a resposta não é muito genérica ou truncada
            if resposta_gerada and len(resposta_gerada) > 30 and not resposta_truncada:
                # 🛡️ VALIDAÇÃO: Verificar se a resposta não contradiz os dados
                resposta_validada = _validar_resposta_contra_dados(resposta_gerada, conteudo_bruto, pergunta)
                
                if resposta_validada['valida']:
                    logger.info(f"✅ Resposta gerada e validada com sucesso ({len(resposta_gerada)} caracteres)")
                    return resposta_gerada
                else:
                    logger.warning(f"⚠️ Resposta gerada contém informações que podem contradizer os dados: {resposta_validada['problema']}")
                    logger.info("🔄 Tentando gerar resposta mais conservadora...")
                    # Tentar uma vez mais com prompt mais restritivo
                    return _gerar_resposta_conservadora(pergunta, conteudo_bruto, contexto_thread)
            elif resposta_truncada or (resposta_gerada and len(resposta_gerada) <= 30):
                logger.warning(f"⚠️ Resposta inválida ou truncada (len: {len(resposta_gerada) if resposta_gerada else 0}), usando fallback")
                return None
        else:
            logger.warning("⚠️ Gemini não retornou resposta")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resposta com Gemini: {e}")
        return None


def _validar_resposta_contra_dados(resposta, dados_originais, pergunta):
    """
    Valida se a resposta do Gemini não contradiz os dados fornecidos.
    
    Args:
        resposta: Resposta gerada pelo Gemini
        dados_originais: Dados originais do JSON
        pergunta: Pergunta original
        
    Returns:
        dict: {'valida': bool, 'problema': str}
    """
    resposta_lower = resposta.lower()
    dados_lower = dados_originais.lower()
    
    problemas = []
    
    # Verificar se menciona funcionalidades que estão como "Não" nos dados
    # Padrões para detectar menções de funcionalidades que podem estar incorretas
    # NOTA: "multi.*cd" deve ser específico para Multi CD (centros distribuição), não "múltiplos volumes"
    funcionalidades_criticas = {
        'atualiza.*status.*rastreio': r'atualiza.*status.*rastreio.*não|atualiza.*status.*rastreio.*❌',
        'atualiza.*automaticamente': r'atualiza.*automaticamente.*não|atualiza.*automaticamente.*❌',
        'múltiplos volumes': r'múltiplos volumes.*não|múltiplos volumes.*❌',
        r'multi[\s\-_]?cd\b': r'multi[\s\-_]?cd.*não|multi_cd.*❌',  # \b evita match em "múltiplos"
        'impressão.*etiqueta': r'impressão.*etiqueta.*não|impressão.*etiqueta.*❌'
    }
    
    for func_nome, padrao_negativo in funcionalidades_criticas.items():
        # Se a resposta menciona a funcionalidade positivamente
        if re.search(func_nome, resposta_lower, re.IGNORECASE):
            # Verificar se nos dados está como "Não"
            if re.search(padrao_negativo, dados_lower, re.IGNORECASE):
                problemas.append(f"Resposta menciona '{func_nome}' como disponível, mas dados indicam 'Não'")
    
    # Verificar se menciona "atualiza status" quando deveria ser apenas "devolve código"
    # Se a resposta menciona "atualiza status" ou "atualiza automaticamente" de forma positiva
    if re.search(r'atualiza.*status.*rastreio|atualiza.*automaticamente', resposta_lower, re.IGNORECASE):
        # Verificar se nos dados está marcado como "Não"
        if re.search(r'atualiza.*status.*rastreio.*não|atualiza.*status.*rastreio.*❌', dados_lower, re.IGNORECASE):
            # Se menciona de forma positiva (sem negativa), é um problema
            if not re.search(r'não.*atualiza|não.*atualiza.*status', resposta_lower, re.IGNORECASE):
                problemas.append("Resposta menciona atualização de status automaticamente, mas dados indicam 'Não (❌)'")
    
    if problemas:
        return {
            'valida': False,
            'problema': '; '.join(problemas)
        }
    
    return {'valida': True, 'problema': None}


def _gerar_resposta_conservadora(pergunta, conteudo_bruto, contexto_thread=None):
    """
    Gera uma resposta mais conservadora e restritiva quando a primeira tentativa falha na validação.
    
    Args:
        pergunta: Pergunta original
        conteudo_bruto: Conteúdo extraído do JSON
        contexto_thread: Contexto da thread (opcional)
        
    Returns:
        str: Resposta conservadora ou None
    """
    try:
        prompt_conservador = f"""Você é um assistente especializado em integrações da Nuvem Envio/Nuvemshop.

PERGUNTA: {pergunta}

DADOS DA INTEGRAÇÃO:
{conteudo_bruto}

INSTRUÇÕES - RESPOSTA EM PARÁGRAFO FLUIDO:
1. NÃO explique o que é cada funcionalidade - apenas informe o que está disponível
2. Escreva em parágrafos fluidos: "A integração funciona através de [X], permitindo [lista o que é Sim]. [O que é manual ou Não]."
3. Segundo parágrafo: suporte e manual - "Se precisar de ajuda, o responsável é [X] e manual: [link]."
4. Use APENAS os dados fornecidos - nada de explicações genéricas
5. Formato como exemplo Tray: parágrafos naturais, não lista de bullets

Responda em parágrafos fluidos como no exemplo da Tray:"""
        
        response = model.generate_content(prompt_conservador)
        
        if response and response.text:
            resposta = response.text.strip()
            if len(resposta) > 30:
                logger.info("✅ Resposta conservadora gerada com sucesso")
                return resposta
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resposta conservadora: {e}")
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

