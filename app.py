from flask import Flask, request, jsonify
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier
from dotenv import load_dotenv
import os
import logging
import time
import json
from datetime import datetime
from handlers.zendesk_com_resumo import limpar_termo_busca
from handlers.gemini_handler import get_gemini_response
from handlers.jira import criar_chamado_jira
from handlers.google_sites import buscar_google_sites
from handlers.resumir_com_gemini import criar_resumo_simples
from handlers.resumir_conteudo_gemini import gerar_resposta_inteligente
from handlers.interpretar_intencao_gemini import interpretar_intencao_e_extrair_erp
from handlers.buscar_faq import buscar_faq, formatar_resposta_faq
from handlers.aprendizado_automatico import registrar_pergunta
from handlers.menu_topicos import criar_menu_boas_vindas
from handlers.cache_respostas import buscar_cache, salvar_cache, obter_estatisticas_cache
from handlers.tracking_perguntas import registrar_pergunta_sem_resposta, obter_estatisticas as obter_stats_tracking
from handlers.contexto_thread import buscar_historico_thread, extrair_referencias_contexto, bot_respondeu_na_thread
from handlers.pausa_thread import thread_esta_pausada, pausar_thread, retomar_thread
# NOVA ESTRUTURA ESTILO NINA
from core import KnowledgeManager, Recepcionista, FonteValidator
# from handlers.filtrar_links_relevantes import filtrar_links_relevantes, gerar_resposta_sem_resultados
import re

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# IMPORTANTE: Carregar .env apenas em desenvolvimento
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)

slack_token = os.getenv("SLACK_BOT_TOKEN")
signing_secret = os.getenv("SLACK_SIGNING_SECRET")
slack_client = WebClient(token=slack_token)
verifier = SignatureVerifier(signing_secret)

# 🧠 NOVA ESTRUTURA ESTILO NINA
# Inicializar sistema de conhecimento estilo Nina
knowledge_manager = KnowledgeManager()
recepcionista = Recepcionista()
fonte_validator = FonteValidator(knowledge_manager)
logger.info("✅ Sistema estilo Nina inicializado")

# 🛡️ SISTEMA ANTI-DUPLICAÇÃO
eventos_processados = {}
TEMPO_CACHE = 900  # 15 minutos - maior que o tempo de detecção de duplicatas

def event_ja_processado(event_id, user, text):
    """Verifica se o evento já foi processado recentemente - SISTEMA ANTI-DUPLICAÇÃO ROBUSTO"""
    agora = time.time()
    
    # Limpar cache antigo
    eventos_expirados = [k for k, v in eventos_processados.items() if agora - v['timestamp'] > TEMPO_CACHE]
    for k in eventos_expirados:
        del eventos_processados[k]
    
    # Múltiplas chaves para detectar duplicatas de forma robusta
    chaves = []
    
    # 1. Chave por event_ts (mais precisa)
    if event_id and event_id.strip():
        chaves.append(f"event_{event_id}")
    
    # 2. Chave por usuário + texto
    chaves.append(f"{user}:{text.strip()[:50]}")
    
    # 3. Chave por usuário + hash do texto completo
    import hashlib
    text_hash = hashlib.md5(text.strip().encode()).hexdigest()[:8]
    chaves.append(f"{user}:hash_{text_hash}")
    
    # Verificar se alguma chave já foi processada
    for chave in chaves:
        if chave in eventos_processados:
            tempo_desde_ultimo = agora - eventos_processados[chave]['timestamp']
            if tempo_desde_ultimo < 600:  # 10 minutos - detectar duplicatas por mais tempo
                logger.warning(f"Evento duplicado detectado: {chave}")
                return True
    
    # Marcar todas as chaves como processadas
    for chave in chaves:
        eventos_processados[chave] = {'timestamp': agora}
    
    return False

def extrair_resumo_e_link(resultado_texto):
    """Extrai resumo e link do resultado para mostrar de forma mais limpa"""
    
    logger.info(f"🔍 Extraindo resumo de: {resultado_texto[:100]}...")
    
    try:
        # Tentar extrair título, resumo e link do formato atual
        import re
        
        # Padrões para Zendesk: 🎫 **título** \n📝 _resumo_ \n🔗 link
        padrao_zendesk = r'🎫\s*\*\*(.*?)\*\*\s*\n📝\s*_(.*?)_\s*\n🔗\s*(.*?)$'
        match_zendesk = re.search(padrao_zendesk, resultado_texto, re.DOTALL)
        
        if match_zendesk:
            titulo = match_zendesk.group(1).strip()
            resumo = match_zendesk.group(2).strip()
            link = match_zendesk.group(3).strip()
            logger.info(f"✅ Padrão Zendesk encontrado: {titulo}")
            return {
                'tipo': 'zendesk',
                'titulo': titulo,
                'resumo': resumo,
                'link': link
            }
        
        # Padrões para Confluence: • **título** (Espaço: x) \n  📝 _resumo_ \n  🔗 link
        padrao_confluence = r'•\s*\*\*(.*?)\*\*.*?\n\s*📝\s*_(.*?)_\s*\n\s*🔗\s*(.*?)(?:\n|$)'
        match_confluence = re.search(padrao_confluence, resultado_texto, re.DOTALL)
        
        if match_confluence:
            titulo = match_confluence.group(1).strip()
            resumo = match_confluence.group(2).strip()
            link = match_confluence.group(3).strip()
            logger.info(f"✅ Padrão Confluence encontrado: {titulo}")
            return {
                'tipo': 'confluence',
                'titulo': titulo,
                'resumo': resumo,
                'link': link
            }
        
        # Para resultados do Zendesk com link de busca - extrair termo pesquisado
        if "🔍" in resultado_texto and "search?query=" in resultado_texto:
            import urllib.parse
            # Extrair o termo da URL de busca
            match_search = re.search(r'query=([^&\s]+)', resultado_texto)
            if match_search:
                termo_encoded = match_search.group(1)
                termo_decoded = urllib.parse.unquote_plus(termo_encoded)
                link_match = re.search(r'https://[^\s]+', resultado_texto)
                link = link_match.group(0) if link_match else 'Link não encontrado'
                logger.info(f"✅ Link de busca Zendesk encontrado: {termo_decoded}")
                return {
                    'tipo': 'busca_zendesk',
                    'titulo': f'Busca no Zendesk: "{termo_decoded}"',
                    'resumo': 'Encontre artigos relacionados no nosso centro de ajuda',
                    'link': link
                }
        
        # Fallback: retornar texto original formatado
        linhas = resultado_texto.strip().split('\n')
        primeira_linha = linhas[0] if linhas else resultado_texto
        
        # Tentar extrair link de qualquer lugar
        link_match = re.search(r'https://[^\s]+', resultado_texto)
        link = link_match.group(0) if link_match else 'Link não encontrado'
        
        logger.info(f"✅ Usando fallback genérico")
        return {
            'tipo': 'generico',
            'titulo': primeira_linha[:100] + "..." if len(primeira_linha) > 100 else primeira_linha,
            'resumo': resultado_texto[:200] + "..." if len(resultado_texto) > 200 else resultado_texto,
            'link': link
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao extrair resumo: {e}")
        return {
            'tipo': 'erro',
            'titulo': 'Informação encontrada',
            'resumo': resultado_texto[:200] + "..." if len(resultado_texto) > 200 else resultado_texto,
            'link': 'Ver texto acima'
        }

def eh_resultado_util(resultado):
    """Verifica se o resultado é útil - VERSÃO MAIS PERMISSIVA"""
    if not resultado:
        logger.info("Resultado vazio - não é útil")
        return False
    
    resultado_limpo = resultado.strip()
    
    # Aceitar qualquer resultado com conteúdo mínimo
    if len(resultado_limpo) < 20:
        logger.info("Resultado muito curto - não é útil")
        return False
    
    # Rejeitar apenas se for claramente um erro ou vazio
    if any(erro in resultado_limpo.lower() for erro in ['erro', 'error', 'falha', 'não foi possível']):
        logger.info("Resultado contém indicadores de erro")
        return False
    
    # ACEITAR TUDO QUE CHEGOU ATÉ AQUI - incluindo links de busca
    logger.info("Resultado considerado útil")
    return True

def criar_botoes_interacao(pergunta_limpa, resultados_encontrados, channel=None, thread_ts=None):
    """Cria os botões para interação com o usuário"""
    
    # Verificar se thread está pausada para mostrar botão correto
    botao_pausa = None
    if channel and thread_ts:
        if thread_esta_pausada(channel, thread_ts):
            # Thread está pausada - mostrar botão "Retomar"
            botao_pausa = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "▶️ Retomar Bot"
                },
                "value": json.dumps({
                    "action": "retomar_bot",
                    "channel": channel,
                    "thread_ts": thread_ts
                }),
                "action_id": "retomar_bot",
                "style": "primary"
            }
        else:
            # Thread não está pausada - mostrar botão "Pausar"
            botao_pausa = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "⏸️ Pausar Bot"
                },
                "value": json.dumps({
                    "action": "pausar_bot",
                    "channel": channel,
                    "thread_ts": thread_ts
                }),
                "action_id": "pausar_bot",
                "style": "danger"
            }
    
    elementos = [
        {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "✅ Sim, me ajudou!"
            },
            "value": json.dumps({
                "action": "resolvido",
                "pergunta": pergunta_limpa
            }),
            "action_id": "resolvido",
            "style": "primary"
        },
        {
            "type": "button", 
            "text": {
                "type": "plain_text",
                "text": "📋 Ver portal completo"
            },
            "value": json.dumps({
                "action": "portal",
                "pergunta": pergunta_limpa
            }),
            "action_id": "portal"
        },
        {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "🎫 Abrir chamado"
            },
            "value": json.dumps({
                "action": "chamado",
                "pergunta": pergunta_limpa
            }),
            "action_id": "chamado"
        }
    ]
    
    # Adicionar botão de pausa se disponível
    if botao_pausa:
        elementos.append(botao_pausa)
    
    return [{
        "type": "actions",
        "elements": elementos
    }]

def formatar_resultados_encontrados(resultados_json, pergunta_limpa, intencao="outro", resposta_esperada="detalhada", contexto_thread=None):
    """
    Formata resultados do JSON usando Gemini para gerar resposta inteligente e focada
    Responde diretamente à pergunta do usuário, não apenas lista tudo
    
    Args:
        resultados_json: Resultado formatado do JSON
        pergunta_limpa: Pergunta original do usuário
        intencao: Tipo de intenção detectada (verificar_existencia, detalhes, funcionalidades, contato, etc)
        resposta_esperada: Tipo de resposta esperada (sim_nao, lista, detalhada, especifica)
        contexto_thread: Histórico da thread (opcional)
    """
    
    logger.info(f"🎨 Formatando resultados do JSON (intenção: {intencao}, resposta: {resposta_esperada})")
    
    try:
        if resultados_json:
            logger.info("🤖 Gerando resposta inteligente e focada com Gemini...")
            
            # Construir prompt melhorado com contexto da intenção
            prompt_com_contexto = pergunta_limpa
            if intencao == "verificar_existencia":
                prompt_com_contexto = f"{pergunta_limpa} (responda primeiro com 'Sim' ou 'Não')"
            elif intencao == "contato":
                prompt_com_contexto = f"{pergunta_limpa} (foque apenas nos dados de contato/suporte)"
            elif intencao == "funcionalidades":
                prompt_com_contexto = f"{pergunta_limpa} (foque apenas nas funcionalidades)"
            
            # Tentar gerar resposta com Gemini (passando contexto da thread)
            resposta_gemini = gerar_resposta_inteligente(
                prompt_com_contexto, 
                resultados_json, 
                "base de conhecimento de integrações (JSON)",
                contexto_thread=contexto_thread
            )
            
            if resposta_gemini:
                # Formatar resposta final - focada e direta
                resposta_completa = resposta_gemini
                
                # Adicionar informações complementares apenas se necessário (resposta detalhada)
                # Mas manter foco na resposta direta
                if resposta_esperada == "detalhada" and intencao not in ["contato", "funcionalidades"]:
                    # Adicionar divisor e link para mais detalhes apenas se realmente necessário
                    resposta_completa += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    resposta_completa += "_💡 Precisa de mais informações? Digite sua próxima pergunta diretamente!_"
                
                logger.info("✅ Resposta inteligente e focada gerada com sucesso")
                return resposta_completa
            else:
                # Fallback: usar resultado direto, mas tentar extrair informação relevante
                logger.info("⚠️ Gemini falhou, usando resultado direto do JSON com formatação melhorada")
                # Se for pergunta sim/não, adicionar resposta direta
                if intencao == "verificar_existencia" and resultados_json:
                    resposta_fallback = "✅ *Sim*, temos integração com esta plataforma.\n\n"
                    resposta_fallback += resultados_json
                    return resposta_fallback
                return resultados_json
        
        logger.warning("⚠️ Nenhum resultado para formatar")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao formatar resultados: {e}")
        return None

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid signature", 403

    data = request.json

    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})

    if "event" in data:
        event = data["event"]
        event_type = event.get("type")
        
        # 🧵 SUPORTE A THREADS: Processar mensagens em threads sem precisar mencionar
        deve_processar = False
        
        if event_type == "app_mention":
            # Sempre processar mentions
            deve_processar = True
        elif event_type == "message":
            # Processar mensagens em threads onde o bot já respondeu
            # Ignorar mensagens do próprio bot e mensagens de sistema
            if event.get("subtype") or event.get("bot_id"):
                return jsonify({"ok": True})
            
            # Se a mensagem está em uma thread
            if event.get("thread_ts"):
                # Verificar se o bot já respondeu nesta thread
                channel = event.get("channel")
                thread_ts = event.get("thread_ts")
                if bot_respondeu_na_thread(slack_client, channel, thread_ts):
                    # 🛡️ VERIFICAR SE THREAD ESTÁ PAUSADA
                    # Mas sempre processar se for menção explícita (app_mention)
                    if event_type != "app_mention" and thread_esta_pausada(channel, thread_ts):
                        logger.info("⏸️ Thread está pausada - ignorando mensagem (menção explícita sempre responde)")
                        return jsonify({"ok": True})
                    
                    logger.info("📬 Mensagem em thread onde bot já participou - processando sem mention")
                    deve_processar = True
                else:
                    logger.debug("📭 Mensagem em thread onde bot não participou - ignorando")
            else:
                # Mensagem não está em thread - só processa se mencionar
                logger.debug("📭 Mensagem no canal principal sem mention - ignorando")
        
        if deve_processar:
            user = event["user"]
            text = event.get("text", "")
            channel = event["channel"]
            
            # 🧵 SUPORTE A THREADS: Se a mensagem já está em uma thread, usar o thread_ts
            # Se não, criar nova thread com o ts da mensagem atual
            thread_ts = event.get("thread_ts") or event.get("ts")
            logger.info(f"🧵 Thread TS: {thread_ts} | Original TS: {event.get('ts')}")
            
            # 🛡️ VERIFICAR SE É EVENTO DUPLICADO
            if event_ja_processado(event.get("event_ts", ""), user, text):
                logger.info("Evento duplicado ignorado")
                return jsonify({"ok": True})
            
            logger.info(f"Mensagem recebida de {user}: {text}")

            # Limpar termo de busca
            pergunta_limpa = limpar_termo_busca(text)
            
            try:
                # 🧠 ESTILO NINA: Usar Recepcionista para analisar a pergunta primeiro
                # 📚 Buscar contexto da thread (histórico de mensagens anteriores)
                # NOTA: Isso é opcional - se falhar por falta de permissão, continua sem contexto
                contexto_thread = None
                try:
                    contexto_thread = buscar_historico_thread(
                        slack_client=slack_client,
                        channel=channel,
                        thread_ts=thread_ts,
                        limite=10  # Últimas 10 mensagens
                    )
                    
                    if contexto_thread:
                        logger.info(f"📚 Contexto da thread carregado ({len(contexto_thread)} caracteres)")
                        # Extrair referências úteis do contexto
                        referencias = extrair_referencias_contexto(contexto_thread, pergunta_limpa)
                        if referencias.get('integracoes_mencionadas'):
                            logger.info(f"🔍 Integrações mencionadas anteriormente: {referencias['integracoes_mencionadas']}")
                    else:
                        logger.debug("📭 Sem contexto anterior na thread")
                except Exception as e:
                    # Erro não é crítico - bot continua funcionando sem contexto
                    error_msg = str(e)
                    if 'missing_scope' in error_msg or 'groups:history' in error_msg:
                        logger.debug("⚠️ Contexto de thread não disponível (falta permissão groups:history). Bot continua funcionando normalmente.")
                    else:
                        logger.debug(f"⚠️ Erro ao buscar contexto da thread: {e}")
                    contexto_thread = None
                
                logger.info("🧠 Recepcionista: Analisando pergunta...")
                analise_recepcionista = recepcionista.analisar_pergunta(pergunta_limpa, contexto_thread)
                
                # Se precisa esclarecimento, enviar mensagem e retornar
                if analise_recepcionista.get('needs_clarification'):
                    logger.info("❓ Recepcionista: Precisa esclarecimento")
                    mensagem_esclarecimento = analise_recepcionista.get('clarification_message', '')
                    if mensagem_esclarecimento:
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=mensagem_esclarecimento
                        )
                    return jsonify({"ok": True})
                
                # Extrair intent e query processada
                user_intent = analise_recepcionista.get('user_intent', 'search_knowledge')
                user_query = analise_recepcionista.get('user_detailed_query', pergunta_limpa)
                user_language = analise_recepcionista.get('user_detected_language', 'pt')
                
                logger.info(f"🎯 Intent detectado: {user_intent} | Query: {user_query[:50]}... | Idioma: {user_language}")
                
                # 🎯 TRATAR INTENTS ESPECÍFICOS
                
                # 1. GREETING - Mostrar menu
                if user_intent == 'greeting':
                    logger.info("👋 Intent: greeting - mostrando menu de boas-vindas")
                    try:
                        menu = criar_menu_boas_vindas()
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text="Menu de Boas-vindas",
                            blocks=menu["blocks"]
                        )
                    except Exception as e:
                        logger.error(f"❌ Erro ao enviar menu: {e}")
                    return jsonify({"ok": True})
                
                # 2. MENU - Mostrar menu
                if user_intent == 'menu':
                    logger.info("📋 Intent: menu - mostrando menu")
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text="Menu de Tópicos",
                        blocks=criar_menu_boas_vindas()["blocks"]
                    )
                    return jsonify({"ok": True})
                
                # 3. LIST_INTEGRATIONS - Listar integrações
                if user_intent == 'list_integrations':
                    logger.info("📋 Intent: list_integrations")
                    
                    # 🎯 VERIFICAR SE É BUSCA POR TIPO DE INTEGRAÇÃO ANTES DE LISTAR TODAS
                    query_lower = user_query.lower()
                    tipos_integracao_patterns = {
                        "tabela de frete": ["tabela de frete", "via tabela de frete", "tabela frete", "por tabela", "tipo tabela", "via tabela"],
                        "api": ["tipo api", "integração api", "via api", "por api"],
                        "apenas rastreio": ["apenas rastreio", "tipo rastreio", "só rastreio"]
                    }
                    
                    tipo_detectado = None
                    for tipo, patterns in tipos_integracao_patterns.items():
                        patterns_sorted = sorted(patterns, key=len, reverse=True)
                        for pattern in patterns_sorted:
                            if pattern in query_lower:
                                tipo_detectado = tipo
                                logger.info(f"🔍 Tipo de integração detectado em list_integrations: '{tipo}' (padrão: '{pattern}')")
                                break
                        if tipo_detectado:
                            break
                    
                    # Se detectou tipo de integração, buscar por tipo ao invés de listar todas
                    if tipo_detectado:
                        logger.info(f"🎯 Buscando integrações do tipo '{tipo_detectado}'")
                        try:
                            from handlers.buscar_integracoes_json import buscar_por_tipo_integracao
                            resultado_tipo = buscar_por_tipo_integracao(tipo_detectado)
                            
                            if resultado_tipo:
                                logger.info(f"✅ Encontradas integrações do tipo '{tipo_detectado}'")
                                resultado_mrkdwn = resultado_tipo.replace("**", "*")
                                slack_client.chat_postMessage(
                                    channel=channel,
                                    thread_ts=thread_ts,
                                    text=f"Integrações do tipo: {tipo_detectado.title()}",
                                    blocks=[{
                                        "type": "section",
                                        "text": {"type": "mrkdwn", "text": resultado_mrkdwn}
                                    }]
                                )
                                return jsonify({"ok": True})
                            else:
                                logger.warning(f"⚠️ Nenhuma integração encontrada para o tipo '{tipo_detectado}'")
                                slack_client.chat_postMessage(
                                    channel=channel,
                                    thread_ts=thread_ts,
                                    text=f"❌ Nenhuma integração encontrada para o tipo '{tipo_detectado.title()}'."
                                )
                                return jsonify({"ok": True})
                        except Exception as e:
                            logger.error(f"❌ Erro ao buscar por tipo '{tipo_detectado}': {e}", exc_info=True)
                            slack_client.chat_postMessage(
                                channel=channel,
                                thread_ts=thread_ts,
                                text=f"❌ Erro ao buscar integrações do tipo '{tipo_detectado.title()}'. Tente novamente."
                            )
                            return jsonify({"ok": True})
                    
                    # PRIORIDADE 1: JSON (estilo Nina)
                    from handlers.buscar_integracoes_json import buscar_integracoes_json
                    lista_integracoes = buscar_integracoes_json()
                    
                    # Apenas JSON agora
                    
                    if lista_integracoes:
                        lista_mrkdwn = lista_integracoes.replace("**", "*")
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text="Lista de integrações disponíveis",
                            blocks=[{
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": lista_mrkdwn}
                            }]
                        )
                    else:
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text="❌ Não foi possível buscar a lista de integrações no momento."
                        )
                    return jsonify({"ok": True})
                
                # 4. SPECIFIC_INTEGRATION - Buscar integração específica
                if user_intent == 'specific_integration':
                    logger.info(f"🔍 Intent: specific_integration - buscando: {user_query}")
                    
                    # 🎯 VERIFICAR SE É BUSCA POR TIPO DE INTEGRAÇÃO
                    query_lower = user_query.lower()
                    # Padrões para detectar busca por tipo de integração
                    tipos_integracao_patterns = {
                        "tabela de frete": ["tabela de frete", "via tabela de frete", "tabela frete", "por tabela", "tipo tabela", "via tabela"],
                        "api": ["tipo api", "integração api", "via api", "por api"],
                        "apenas rastreio": ["apenas rastreio", "tipo rastreio", "só rastreio"]
                    }
                    
                    tipo_detectado = None
                    # Verificar padrões mais específicos primeiro (mais longo primeiro)
                    for tipo, patterns in tipos_integracao_patterns.items():
                        # Ordenar padrões por tamanho (mais longo primeiro) para evitar falsos positivos
                        patterns_sorted = sorted(patterns, key=len, reverse=True)
                        for pattern in patterns_sorted:
                            if pattern in query_lower:
                                tipo_detectado = tipo
                                logger.info(f"🔍 Tipo de integração detectado: '{tipo}' (padrão: '{pattern}')")
                                break
                        if tipo_detectado:
                            break
                    
                    # Se detectou tipo de integração, buscar por tipo
                    if tipo_detectado:
                        logger.info(f"🎯 Buscando integrações do tipo '{tipo_detectado}' (specific_integration)")
                        try:
                            from handlers.buscar_integracoes_json import buscar_por_tipo_integracao
                            resultado_tipo = buscar_por_tipo_integracao(tipo_detectado)
                            
                            if resultado_tipo:
                                logger.info(f"✅ Encontradas integrações do tipo '{tipo_detectado}'")
                                resultado_mrkdwn = resultado_tipo.replace("**", "*")
                                slack_client.chat_postMessage(
                                    channel=channel,
                                    thread_ts=thread_ts,
                                    text=f"Integrações do tipo: {tipo_detectado.title()}",
                                    blocks=[{
                                        "type": "section",
                                        "text": {"type": "mrkdwn", "text": resultado_mrkdwn}
                                    }]
                                )
                                return jsonify({"ok": True})
                            else:
                                logger.warning(f"⚠️ Nenhuma integração encontrada para o tipo '{tipo_detectado}'")
                                slack_client.chat_postMessage(
                                    channel=channel,
                                    thread_ts=thread_ts,
                                    text=f"❌ Nenhuma integração encontrada para o tipo '{tipo_detectado.title()}'."
                                )
                                return jsonify({"ok": True})
                        except Exception as e:
                            logger.error(f"❌ Erro ao buscar por tipo '{tipo_detectado}' (specific_integration): {e}", exc_info=True)
                            slack_client.chat_postMessage(
                                channel=channel,
                                thread_ts=thread_ts,
                                text=f"❌ Erro ao buscar integrações do tipo '{tipo_detectado.title()}'. Tente novamente."
                            )
                            return jsonify({"ok": True})
                    
                    # 🧠 ESTILO NINA: Interpretar intenção com Gemini antes de buscar
                    logger.info("🧠 Interpretando intenção com Gemini...")
                    interpretacao = interpretar_intencao_e_extrair_erp(user_query)
                    
                    # Usar query otimizada se disponível
                    query_busca = interpretacao.get('query_busca') or interpretacao.get('nome_erp') or user_query
                    intencao = interpretacao.get('intencao', 'detalhes')
                    resposta_esperada = interpretacao.get('resposta_esperada', 'detalhada')
                    
                    logger.info(f"🎯 Intenção: {intencao} | Query busca: {query_busca} | Resposta esperada: {resposta_esperada}")
                    
                    # Buscar integração específica
                    logger.info(f"🔍 Buscando ERP na query: '{query_busca}'")
                    
                    resultado_integracao = knowledge_manager.search_integration_specific(query_busca)
                    
                    if resultado_integracao:
                        # Usar formatação inteligente também para specific_integration
                        resultado_json = resultado_integracao['content']
                        
                        # 💾 CACHE DESABILITADO: Sempre gerar nova resposta
                        resultado_formatado = formatar_resultados_encontrados(
                            resultado_json,
                            user_query,
                            intencao=intencao,
                            resposta_esperada=resposta_esperada,
                            contexto_thread=contexto_thread
                        )
                        
                        if resultado_formatado:
                            resultado_mrkdwn = resultado_formatado.replace("**", "*")
                            
                            # Criar blocos com a resposta
                            blocks_resposta = [{
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": resultado_mrkdwn}
                            }]
                            
                            # Se a resposta for focada em uma integração específica, adicionar botão para ver informações completas
                            nome_integracao = interpretacao.get('nome_erp')
                            # Mostrar botão sempre que temos uma integração específica identificada
                            # Independentemente de ser detalhada ou não, sempre permitir ver informações completas
                            mostrar_botao_completo = (
                                nome_integracao and 
                                resultado_json
                            )
                            
                            if mostrar_botao_completo:
                                blocks_resposta.append({
                                    "type": "actions",
                                    "elements": [{
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "📋 Ver Informações Completas"
                                        },
                                        "style": "primary",
                                        "action_id": "ver_completo",
                                        "value": json.dumps({
                                            "nome_integracao": nome_integracao,
                                            "query_original": user_query
                                        })
                                    }]
                                })
                            
                            slack_client.chat_postMessage(
                                channel=channel,
                                thread_ts=thread_ts,
                                text=f"📊 Encontrei informações sobre: {user_query}",
                                blocks=blocks_resposta
                            )
                            
                            # Botões de interação
                            slack_client.chat_postMessage(
                                channel=channel,
                                thread_ts=thread_ts,
                                text="Essas informações ajudaram?",
                                blocks=[{
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "💬 *Essas informações foram úteis?*\n"
                                                "Se precisar de mais detalhes ou tiver outras dúvidas, estou aqui! 😊"
                                    }
                                }] + criar_botoes_interacao(user_query, {'integracoes_json': resultado_json}, channel=channel, thread_ts=thread_ts)
                            )
                            return jsonify({"ok": True})
                        else:
                            # Fallback: usar resultado direto
                            resultado_mrkdwn = str(resultado_json).replace("**", "*")
                            slack_client.chat_postMessage(
                                channel=channel,
                                thread_ts=thread_ts,
                                text=f"Resultados para: {user_query}",
                                blocks=[{
                                    "type": "section",
                                    "text": {"type": "mrkdwn", "text": resultado_mrkdwn}
                                }]
                            )
                            return jsonify({"ok": True})
                    
                    # Se não encontrou integração específica, continuar para busca geral
                    logger.info("⚠️ Integração específica não encontrada, fazendo busca geral...")
                
                # 5. SEARCH_KNOWLEDGE (ou fallback) - Buscar em todas as fontes
                logger.info("🔍 Intent: search_knowledge - buscando em múltiplas fontes")
                
                # 🎯 VERIFICAR SE É BUSCA POR TIPO DE INTEGRAÇÃO
                query_lower = user_query.lower()
                # Padrões para detectar busca por tipo de integração
                tipos_integracao_patterns = {
                    "tabela de frete": ["tabela de frete", "tabela frete", "por tabela", "tipo tabela"],
                    "api": ["tipo api", "integração api", "via api", "por api"],
                    "apenas rastreio": ["apenas rastreio", "tipo rastreio", "só rastreio"]
                }
                
                tipo_detectado = None
                # Verificar padrões mais específicos primeiro (mais longo primeiro)
                for tipo, patterns in tipos_integracao_patterns.items():
                    # Ordenar padrões por tamanho (mais longo primeiro) para evitar falsos positivos
                    patterns_sorted = sorted(patterns, key=len, reverse=True)
                    for pattern in patterns_sorted:
                        if pattern in query_lower:
                            tipo_detectado = tipo
                            logger.info(f"🔍 Tipo de integração detectado na busca geral: '{tipo}' (padrão: '{pattern}')")
                            break
                    if tipo_detectado:
                        break
                
                # Se detectou tipo de integração, buscar por tipo
                if tipo_detectado:
                    from handlers.buscar_integracoes_json import buscar_por_tipo_integracao
                    resultado_tipo = buscar_por_tipo_integracao(tipo_detectado)
                    
                    if resultado_tipo:
                        resultado_mrkdwn = resultado_tipo.replace("**", "*")
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=f"Integrações do tipo: {tipo_detectado.title()}",
                            blocks=[{
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": resultado_mrkdwn}
                            }]
                        )
                        return jsonify({"ok": True})
                    else:
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=f"❌ Nenhuma integração encontrada para o tipo '{tipo_detectado.title()}'."
                        )
                        return jsonify({"ok": True})
                
                # 🧠 ESTILO NINA: Interpretar intenção com Gemini antes de buscar
                logger.info("🧠 Interpretando intenção com Gemini...")
                interpretacao = interpretar_intencao_e_extrair_erp(user_query)
                
                # Usar query otimizada se disponível
                query_busca = interpretacao.get('query_busca') or interpretacao.get('nome_erp') or user_query
                intencao = interpretacao.get('intencao', 'outro')
                resposta_esperada = interpretacao.get('resposta_esperada', 'detalhada')
                
                logger.info(f"🎯 Intenção: {intencao} | Query busca: {query_busca} | Resposta esperada: {resposta_esperada}")
                
                # 🧠 ESTILO NINA: Usar KnowledgeManager para buscar em todas as fontes (ordem de prioridade)
                resultados_busca = knowledge_manager.search(query_busca)
                
                # 🧠 ESTILO NINA: Validar se tem fonte válida antes de responder
                validacao = fonte_validator.validar_resultados(resultados_busca)
                
                if not validacao['tem_fonte_valida']:
                    # Estilo Nina: Só responder se tiver fonte válida
                    logger.warning("⚠️ Nenhuma fonte válida encontrada - não respondendo")
                    
                    # 📊 TRACKING: Registrar pergunta sem resposta
                    registrar_pergunta_sem_resposta(
                        pergunta=user_query,
                        query_usada=query_busca,
                        motivo="Nenhuma fonte válida encontrada"
                    )
                    
                    # Gerar mensagem melhorada com sugestões baseada na query
                    mensagem_sem_fonte = fonte_validator._gerar_mensagem_sem_resultado(user_query)
                    
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"Resultados para: {user_query}",
                        blocks=[{
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": mensagem_sem_fonte}
                        }] + criar_botoes_interacao(user_query, {}, channel=channel, thread_ts=thread_ts)
                    )
                    return jsonify({"ok": True})
                
                # Tem fonte válida - processar resposta
                resultados_validos = validacao['resultados_validos']
                logger.info(f"✅ {len(resultados_validos)} resultados válidos encontrados")
                
                # Converter resultados para formato compatível com função existente
                resultados_encontrados = {}
                for resultado in resultados_validos:
                    fonte_id = resultado['source']
                    resultados_encontrados[fonte_id] = resultado['content']
                
                # 🤖 REGISTRAR PERGUNTA PARA APRENDIZADO AUTOMÁTICO
                fonte_principal = resultados_validos[0]['source']
                resposta_bruta = resultados_validos[0]['content']
                resultado_registro = registrar_pergunta(user_query, resposta_bruta, fonte_principal)
                if resultado_registro.get('faq_criada'):
                    logger.info(f"🎉 FAQ AUTO-GERADA! Pergunta '{user_query}' apareceu {resultado_registro['contador']} vezes")
                
                # Formatar resposta usando função existente
                resultado_json = resultados_encontrados.get('integracoes_json')
                
                # 💾 CACHE DESABILITADO: Sempre gerar nova resposta
                # Passar informações de intenção para formatação inteligente (com contexto)
                resultado_formatado = formatar_resultados_encontrados(
                    resultado_json,
                    user_query,
                    intencao=intencao,
                    resposta_esperada=resposta_esperada,
                    contexto_thread=contexto_thread
                )
                
                if resultado_formatado:
                    resultado_mrkdwn = resultado_formatado.replace("**", "*")
                    
                    # Criar blocos com a resposta
                    blocks_resposta = [{
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": resultado_mrkdwn}
                    }]
                    
                    # Se a resposta for focada em uma integração específica, adicionar botão para ver informações completas
                    # Extrair nome da integração do resultado JSON
                    nome_integracao = None
                    try:
                        from handlers.buscar_integracoes_json import carregar_integracoes_json, buscar_integracao_especifica_json
                        # Tentar extrair nome da query ou usar a query diretamente
                        if interpretacao.get('nome_erp'):
                            nome_integracao = interpretacao.get('nome_erp')
                        elif query_busca:
                            # Buscar para garantir que temos o nome correto
                            erps = carregar_integracoes_json()
                            if erps:
                                for erp in erps:
                                    nome_erp_atual = erp.get("Nome", erp.get("ERP", "")).lower()
                                    if query_busca.lower() in nome_erp_atual or nome_erp_atual in query_busca.lower():
                                        nome_integracao = erp.get("Nome", erp.get("ERP", ""))
                                        break
                    except Exception as e:
                        logger.debug(f"Erro ao extrair nome da integração: {e}")
                    
                    # Mostrar botão sempre que temos uma integração específica identificada
                    # Independentemente de ser detalhada ou não, sempre permitir ver informações completas
                    mostrar_botao_completo = (
                        nome_integracao and 
                        resultado_json
                    )
                    
                    if mostrar_botao_completo:
                        # Adicionar botão para ver informações completas
                        blocks_resposta.append({
                            "type": "actions",
                            "elements": [{
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "📋 Ver Informações Completas"
                                },
                                "style": "primary",
                                "action_id": "ver_completo",
                                "value": json.dumps({
                                    "nome_integracao": nome_integracao,
                                    "query_original": user_query
                                })
                            }]
                        })
                    
                    response = slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"📊 Encontrei informações sobre: {user_query}",
                        blocks=blocks_resposta
                    )
                    
                    # Botões em mensagem separada - mais contextual e acolhedora
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text="Essas informações ajudaram?",
                        blocks=[{
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "💬 *Essas informações foram úteis?*\n"
                                        "Se precisar de mais detalhes ou tiver outras dúvidas, estou aqui! 😊"
                            }
                        }] + criar_botoes_interacao(user_query, resultados_encontrados, channel=channel, thread_ts=thread_ts)
                    )
                    return jsonify({"ok": True})
                
                # Fallback se formatação falhar
                logger.warning("⚠️ Formatação de resultado falhou")
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="Ops! Erro ao formatar resposta",
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "😅 *Ops! Não consegui formatar a resposta.*\n\n"
                                    "Tente fazer sua pergunta de forma diferente ou use 'listar integrações' para ver todas as opções disponíveis."
                        }
                    }]
                )
                return jsonify({"ok": True})

            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
                try:
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text="Ops! Algo deu errado",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "😅 *Ops! Algo deu errado*\n\n"
                                            "Não consegui processar sua solicitação no momento. "
                                            "Pode tentar novamente em alguns instantes?\n\n"
                                            "Se o problema persistir, abra um chamado para nossa equipe."
                                }
                            }
                        ]
                    )
                except:
                    pass

    return jsonify({"ok": True})

@app.route("/slack/actions", methods=["POST"])
def slack_actions():
    """Handler para botões interativos"""
    try:
        logger.info("🔘 Recebida ação do Slack")
        payload_str = request.form.get("payload")
        payload = json.loads(payload_str)
        
        logger.info(f"📊 Payload recebido: {payload.keys()}")
        
        user = payload["user"]["id"]
        channel = payload["channel"]["id"]
        
        # IMPORTANTE: Extrair thread_ts da mensagem original para manter na thread
        message = payload.get("message", {})
        thread_ts = message.get("thread_ts") or message.get("ts")
        
        action = payload["actions"][0]
        acao = action["action_id"]
        
        logger.info(f"🎯 Ação detectada: {acao}")
        
        # Para ações que usam JSON no value, extrair os dados
        if "value" in action and action["value"]:
            try:
                action_data = json.loads(action["value"])
                pergunta = action_data.get("pergunta", "")
            except (json.JSONDecodeError, TypeError):
                # Se não for JSON válido, usar o value diretamente
                action_data = {"value": action["value"]}
                pergunta = ""
        else:
            action_data = {}
            pergunta = ""
        
        # Responder com base na ação - RESPOSTAS SIMPLES E RÁPIDAS
        if acao == "resolvido":
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="🎉 Perfeito! Fico feliz que consegui ajudar! 😊"
            )
            
        elif acao == "portal":
            portal_url = "https://sites.google.com/nuvemshop.com.br/integracoesnuvemenvio/início"
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"📋 Portal de Integrações: {portal_url}"
            )
            
        elif acao == "chamado":
            jira_url = os.getenv("ATLASSIAN_BASE_URL", "https://tiendanube.atlassian.net")
            jira_create_url = f"{jira_url}/secure/CreateIssue.jspa?pid=13242&issuetype=13600"
            
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"🎫 Abrir chamado: {jira_create_url}"
            )
            
        elif acao == "pesquisa_global":
            logger.info("🔍 Usuário ativou modo pesquisa global")
            
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="🔍 *Modo Pesquisa Global Ativado*\n\nAgora você pode fazer qualquer pergunta sobre ERPs e eu vou buscar na base de conhecimento!\n\n*Exemplos:*\n• Informações sobre Tiny\n• Como funciona o Omie?\n• Quais funcionalidades tem o Eccosys?\n• Temos integração com Notazz?\n\n💡 *Dica:* Digite sua pergunta normalmente que eu buscarei na base de conhecimento de ERPs!"
            )

        elif acao == "ver_completo":
            logger.info("📋 Usuário solicitou ver informações completas")
            
            # Extrair nome da integração do action_data
            nome_integracao = None
            if "nome_integracao" in action_data:
                nome_integracao = action_data["nome_integracao"]
            elif "value" in action and isinstance(action["value"], str):
                try:
                    data = json.loads(action["value"])
                    nome_integracao = data.get("nome_integracao")
                except:
                    pass
            
            if nome_integracao:
                try:
                    from handlers.buscar_integracoes_json import buscar_integracao_especifica_json
                    
                    # Buscar informações completas da integração
                    informacoes_completas = buscar_integracao_especifica_json(nome_integracao)
                    
                    if informacoes_completas:
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=f"📋 Informações completas: {nome_integracao}",
                            blocks=[{
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": informacoes_completas.replace("**", "*")
                                }
                            }]
                        )
                    else:
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=f"😔 Não consegui encontrar informações completas sobre {nome_integracao}",
                            blocks=[{
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"😔 Não consegui encontrar informações completas sobre *{nome_integracao}*.\n\n"
                                            "Tente buscar pelo nome exato da integração ou use 'listar integrações' para ver todas as opções disponíveis."
                                }
                            }]
                        )
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar informações completas: {e}")
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text="😅 Ops! Erro ao buscar informações completas",
                        blocks=[{
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "😅 *Ops! Erro ao buscar informações completas.*\n\n"
                                        "Tente fazer uma nova pergunta com o nome exato da integração."
                            }
                        }]
                    )
            else:
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="⚠️ Não consegui identificar qual integração você quer ver",
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "⚠️ *Não consegui identificar qual integração você quer ver.*\n\n"
                                    "Por favor, faça uma nova pergunta com o nome exato da integração."
                        }
                    }]
                )
            
        elif acao == "listar_integracoes":
            logger.info("📋 Usuário solicitou lista de integrações")
            
            # Usar o fluxo atual de listar integrações (apenas JSON)
            from handlers.buscar_integracoes_json import buscar_integracoes_json
            lista_integracoes = buscar_integracoes_json()
            
            if lista_integracoes:
                lista_mrkdwn = lista_integracoes.replace("**", "*")
                
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="Lista de integrações disponíveis",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": lista_mrkdwn
                            }
                        }
                    ]
                )
            else:
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="❌ Não foi possível buscar a lista de integrações no momento."
                )

        elif acao == "voltar_menu":
            logger.info("⬅️ Usuário voltou ao menu principal")
            
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="Menu Principal",
                blocks=criar_menu_boas_vindas()["blocks"]
            )
            
        elif acao == "pausar_bot":
            logger.info("⏸️ Usuário pausou o bot na thread")
            
            channel_id = action_data.get("channel") or channel
            thread_id = action_data.get("thread_ts") or thread_ts
            
            if pausar_thread(channel_id, thread_id):
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="⏸️ *Bot pausado nesta thread*\n\n"
                         "Agora eu não vou responder automaticamente às mensagens aqui.\n\n"
                         "💡 *Nota:* Se alguém me mencionar explicitamente (@Tina), eu ainda vou responder mesmo com o bot pausado.\n\n"
                         "Use o botão \"▶️ Retomar Bot\" quando quiser que eu volte a responder automaticamente.",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "⏸️ *Bot pausado nesta thread*\n\n"
                                        "Agora eu não vou responder automaticamente às mensagens aqui.\n\n"
                                        "💡 *Nota:* Se alguém me mencionar explicitamente (@Tina), eu ainda vou responder mesmo com o bot pausado.\n\n"
                                        "Use o botão \"▶️ Retomar Bot\" quando quiser que eu volte a responder automaticamente."
                            }
                        }
                    ] + criar_botoes_interacao("", {}, channel=channel, thread_ts=thread_ts)
                )
            else:
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="😅 Ops! Não consegui pausar o bot. Tente novamente."
                )

        elif acao == "retomar_bot":
            logger.info("▶️ Usuário retomou o bot na thread")
            
            channel_id = action_data.get("channel") or channel
            thread_id = action_data.get("thread_ts") or thread_ts
            
            if retomar_thread(channel_id, thread_id):
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="▶️ *Bot retomado!*\n\n"
                         "Agora eu voltarei a responder automaticamente às mensagens nesta thread. 😊",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "▶️ *Bot retomado!*\n\n"
                                        "Agora eu voltarei a responder automaticamente às mensagens nesta thread. 😊"
                            }
                        }
                    ] + criar_botoes_interacao("", {}, channel=channel, thread_ts=thread_ts)
                )
            else:
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="😅 Ops! Não consegui retomar o bot. Tente novamente."
                )
            
        return jsonify({"ok": True})
        
    except Exception as e:
        logger.error(f"Erro ao processar ação: {e}")
        return jsonify({"ok": True})

@app.route("/test", methods=["GET"])
def test_endpoint():
    return jsonify({
        "status": "ok", 
        "message": "Bot está funcionando!",
        "ngrok": "conectado"
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar se todas as configurações estão ok"""
    import os
    
    configs = {
        "slack_token": "✅" if os.getenv("SLACK_BOT_TOKEN") else "❌",
        "slack_secret": "✅" if os.getenv("SLACK_SIGNING_SECRET") else "❌", 
        "atlassian_email": "✅" if os.getenv("ATLASSIAN_EMAIL") else "❌",
        "atlassian_token": "✅" if os.getenv("ATLASSIAN_TOKEN") else "❌",
        "atlassian_url": "✅" if os.getenv("ATLASSIAN_BASE_URL") else "❌",
        "zendesk_email": "✅" if os.getenv("ZENDESK_EMAIL") else "❌",
        "zendesk_token": "✅" if os.getenv("ZENDESK_API_TOKEN") else "❌",
        "zendesk_subdomain": "✅" if os.getenv("ZENDESK_SUBDOMAIN") else "❌ (usando padrão)"
    }
    
    return jsonify({
        "status": "healthy",
        "configurations": configs,
        "ready_for_slack": all(v == "✅" for k, v in configs.items() if k.startswith("slack")),
        "eventos_cache": len(eventos_processados),
        "cache_respostas": obter_estatisticas_cache(),
        "perguntas_sem_resposta": obter_stats_tracking()
    })

@app.errorhandler(404)
def not_found(error):
    """Captura todos os 404s para debug"""
    logger.warning(f"🚫 404 - Rota não encontrada: {request.method} {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    if request.form:
        logger.info(f"Form data: {dict(request.form)}")
    return jsonify({
        "error": "Endpoint não encontrado",
        "method": request.method,
        "path": request.path,
        "available_endpoints": [
            "POST /slack/events",
            "POST /slack/actions", 
            "GET /test",
            "GET /health"
        ]
    }), 404

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Chatbot Gemini está rodando! 🚀", 200


@app.route("/analytics", methods=["GET"])
def analytics():
    """
    Endpoint para visualizar estatísticas das perguntas (análise interna)
    """
    try:
        from handlers.aprendizado_automatico import obter_estatisticas
        
        stats = obter_estatisticas()
        
        if not stats:
            return jsonify({"error": "Não foi possível obter estatísticas"}), 500
        
        # Formatar resposta mais legível
        html_response = f"""
        <html>
        <head>
            <title>Analytics - Chatbot Perguntas</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .stat {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .pergunta {{ background: #e8f4fd; padding: 8px; margin: 5px 0; border-radius: 3px; }}
                .faq-criada {{ background: #d4edda; }}
            </style>
        </head>
        <body>
            <h1>📊 Analytics - Perguntas do Chatbot</h1>
            
            <div class="stat">
                <h3>📈 Resumo Geral</h3>
                <p><strong>Perguntas únicas:</strong> {stats['total_perguntas_unicas']}</p>
                <p><strong>Total de perguntas feitas:</strong> {stats['total_perguntas_feitas']}</p>
                <p><strong>FAQs auto-geradas:</strong> {stats['faqs_auto_geradas']}</p>
            </div>
            
            <div class="stat">
                <h3>🔥 Top 10 Perguntas Mais Frequentes</h3>
        """
        
        for i, pergunta in enumerate(stats['top_perguntas'], 1):
            faq_class = "faq-criada" if pergunta['faq_criada'] else ""
            faq_status = "✅ FAQ criada" if pergunta['faq_criada'] else "⏳ Aguardando"
            
            html_response += f"""
                <div class="pergunta {faq_class}">
                    <strong>{i}. {pergunta['pergunta']}</strong><br>
                    Apareceu: {pergunta['contador']} vezes | {faq_status}
                </div>
            """
        
        html_response += """
            </div>
            
            <div class="stat">
                <h3>💡 Como usar essas informações:</h3>
                <ul>
                    <li><strong>Perguntas frequentes:</strong> Considere criar documentação específica</li>
                    <li><strong>FAQs auto-geradas:</strong> Revise e melhore as respostas no faq_database.json</li>
                    <li><strong>Padrões:</strong> Identifique temas que precisam de mais documentação</li>
                </ul>
            </div>
            
            <p><em>Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}</em></p>
        </body>
        </html>
        """
        
        return html_response, 200
        
    except Exception as e:
        logger.error(f"❌ Erro no analytics: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False) 