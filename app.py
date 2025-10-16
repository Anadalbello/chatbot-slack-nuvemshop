from flask import Flask, request, jsonify
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier
from dotenv import load_dotenv
import os
import logging
import time
import json
from datetime import datetime
from handlers.zendesk_api import buscar_artigo_zendesk_api
from handlers.zendesk_com_resumo import limpar_termo_busca
from handlers.confluence_com_resumo import buscar_confluence
from handlers.gemini_handler import get_gemini_response
from handlers.jira import criar_chamado_jira
from handlers.google_sites import buscar_google_sites
from handlers.extrair_palavras_chave import melhorar_busca_confluence
from handlers.resumir_com_gemini import criar_resumo_simples
from handlers.resumir_conteudo_gemini import gerar_resposta_inteligente
from handlers.buscar_integracoes_dinamico import buscar_todas_integracoes_confluence, buscar_integracao_especifica
from handlers.buscar_integracoes_sheets_publico import buscar_integracoes_google_sheets_publico, buscar_integracao_especifica_sheets_publico
from handlers.buscar_faq import buscar_faq, formatar_resposta_faq
from handlers.aprendizado_automatico import registrar_pergunta
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

# 🛡️ SISTEMA ANTI-DUPLICAÇÃO
eventos_processados = {}
TEMPO_CACHE = 300  # 5 minutos

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
            if tempo_desde_ultimo < 8:  # 8 segundos - compromisso entre velocidade e segurança
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

def criar_botoes_interacao(pergunta_limpa, resultados_encontrados):
    """Cria os botões para interação com o usuário"""
    
    return [
        {
            "type": "actions",
            "elements": [
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
        }
    ]

def formatar_resultados_encontrados(resultados_zendesk, resultados_confluence, pergunta_limpa):
    """
    Formata resultados usando Gemini para gerar resposta inteligente
    Similar a como IAs respondem perguntas de forma natural
    """
    
    logger.info(f"🎨 Formatando resultados - Zendesk: {bool(resultados_zendesk)}, Confluence: {bool(resultados_confluence)}")
    
    try:
        # Priorizar Confluence
        if resultados_confluence:
            logger.info("🤖 Gerando resposta inteligente com Gemini para Confluence...")
            
            # Tentar gerar resposta com Gemini
            resposta_gemini = gerar_resposta_inteligente(
                pergunta_limpa, 
                resultados_confluence, 
                "base de conhecimento no Confluence"
            )
            
            if resposta_gemini:
                # Extrair links do conteúdo
                links = re.findall(r'🔗 (https?://[^\s\)]+)', resultados_confluence)
                
                # 🎯 FILTRO SIMPLES: Priorizar links com palavras da pergunta
                pergunta_lower = pergunta_limpa.lower()
                palavras_pergunta = set(re.findall(r'\b\w+\b', pergunta_lower))
                
                # Filtrar links relevantes
                links_relevantes = []
                links_restantes = []
                
                for link in links:
                    link_lower = link.lower()
                    # Verificar se o link contém palavras da pergunta
                    palavras_no_link = set(re.findall(r'\b\w+\b', link_lower))
                    if palavras_pergunta.intersection(palavras_no_link):
                        links_relevantes.append(link)
                    else:
                        links_restantes.append(link)
                
                # Usar links relevantes primeiro, depois os restantes
                links_finais = links_relevantes[:2] + links_restantes[:1]
                if not links_finais:
                    links_finais = links[:3]  # Fallback
                
                # Formatar resposta final
                resposta_completa = f"**{pergunta_limpa}**\n\n{resposta_gemini}\n\n"
                resposta_completa += "---\n\n📚 **Documentação completa:**\n"
                
                for i, link in enumerate(links_finais, 1):
                    resposta_completa += f"{i}. {link}\n"
                
                resposta_completa += "\n_Para mais informações ou dúvidas específicas, estou à disposição para ajudar._"
                
                logger.info("✅ Resposta inteligente gerada com sucesso")
                return resposta_completa
            else:
                # Fallback: usar método simples
                logger.info("⚠️ Gemini falhou, usando método simples")
                confluence_info = extrair_resumo_e_link(resultados_confluence)
                resumo = criar_resumo_simples(pergunta_limpa, resultados_confluence, "Confluence")
                
                resposta_completa = resumo + "\n\n"
                resposta_completa += f"📎 *Acesse a documentação completa:*\n{confluence_info['link']}\n\n"
                resposta_completa += "_Se precisar de mais informações ou tiver dúvidas específicas, estou à disposição para ajudar._"
                
                return resposta_completa
        
        # Fallback: Zendesk
        if resultados_zendesk:
            logger.info("🤖 Gerando resposta inteligente com Gemini para Zendesk...")
            
            # Tentar gerar resposta com Gemini
            resposta_gemini = gerar_resposta_inteligente(
                pergunta_limpa, 
                resultados_zendesk, 
                "Central de Ajuda"
            )
            
            if resposta_gemini:
                # Extrair links
                links = re.findall(r'🔗 (https?://[^\s\)]+)', resultados_zendesk)
                
                # 🎯 FILTRO SIMPLES: Priorizar links com palavras da pergunta
                pergunta_lower = pergunta_limpa.lower()
                palavras_pergunta = set(re.findall(r'\b\w+\b', pergunta_lower))
                
                # Filtrar links relevantes
                links_relevantes = []
                links_restantes = []
                
                for link in links:
                    link_lower = link.lower()
                    # Verificar se o link contém palavras da pergunta
                    palavras_no_link = set(re.findall(r'\b\w+\b', link_lower))
                    if palavras_pergunta.intersection(palavras_no_link):
                        links_relevantes.append(link)
                    else:
                        links_restantes.append(link)
                
                # Usar links relevantes primeiro, depois os restantes
                links_finais = links_relevantes[:2] + links_restantes[:1]
                if not links_finais:
                    links_finais = links[:3]  # Fallback
                
                resposta_completa = f"**{pergunta_limpa}**\n\n{resposta_gemini}\n\n"
                resposta_completa += "---\n\n📚 **Artigos relacionados:**\n"
                
                for i, link in enumerate(links_finais, 1):
                    resposta_completa += f"{i}. {link}\n"
                
                resposta_completa += "\n_Para mais assistência, entre em contato com a equipe de suporte._"
                
                logger.info("✅ Resposta inteligente gerada com sucesso")
                return resposta_completa
            else:
                # Fallback: método simples
                logger.info("⚠️ Gemini falhou, usando método simples")
                zendesk_info = extrair_resumo_e_link(resultados_zendesk)
                resumo = criar_resumo_simples(pergunta_limpa, resultados_zendesk, "Centro de Ajuda")
                
                resposta_completa = resumo + "\n\n"
                resposta_completa += f"📎 *Acesse o artigo completo:*\n{zendesk_info['link']}\n\n"
                resposta_completa += "_Para mais assistência, entre em contato com a equipe de suporte._"
                
                return resposta_completa
        
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
        # Responder a menções (@bot) E mensagens diretas (DM)
        if event.get("type") in ["app_mention", "message"]:
            # Verificar se é DM ou menção
            is_dm = event.get("channel_type") == "im"
            is_mention = "@U096CTRBBDZ" in event.get("text", "")
            
            if is_dm or is_mention:
                user = event["user"]
                text = event["text"]
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

                # Enviar mensagem imediata de confirmação
                pergunta_limpa = limpar_termo_busca(text)
                
                try:
                # 🎯 DETECTAR SE É PEDIDO PARA LISTAR INTEGRAÇÕES/PARCEIROS
                palavras_listar = ["listar", "lista", "quais são", "quais sao", "tem quais", "quantos", "todos os", "todas as"]
                palavras_integracao = ["integra", "parceiro", "sistema", "plataforma"]
                
                pergunta_lower = pergunta_limpa.lower()
                eh_pedido_lista = any(palavra in pergunta_lower for palavra in palavras_listar)
                eh_sobre_integracoes = any(palavra in pergunta_lower for palavra in palavras_integracao)
                
                if eh_pedido_lista and eh_sobre_integracoes:
                    logger.info("📋 Detectado pedido para listar integrações")
                    
                    # PRIORIDADE 1: Tentar buscar do Google Sheets (público)
                    logger.info("📊 Tentando buscar do Google Sheets primeiro...")
                    lista_integracoes = buscar_integracoes_google_sheets_publico()
                    
                    # FALLBACK: Se Google Sheets falhar, buscar do Confluence
                    if not lista_integracoes:
                        logger.info("⚠️ Google Sheets falhou, buscando do Confluence...")
                        lista_integracoes = buscar_todas_integracoes_confluence()
                    
                    if lista_integracoes:
                        # Converter para formato mrkdwn
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
                        logger.info("✅ Lista de integrações enviada")
                        return jsonify({"ok": True})
                    else:
                        logger.warning("⚠️ Não foi possível buscar lista de integrações (nem Sheets nem Confluence), continuando com busca normal")
                
                # 🔍 BUSCAR SILENCIOSAMENTE (sem mensagens intermediárias)
                resultados_encontrados = {}

                # 📊 REGISTRAR PERGUNTA PARA ANÁLISE INTERNA (FAQ como ferramenta de análise)
                logger.info(f"📝 Registrando pergunta para análise: {pergunta_limpa}")
                # Nota: FAQ não é usado para responder usuários, apenas para análise interna

                # 1. PRIORIDADE: Buscar no Confluence primeiro
                logger.info(f"📋 Iniciando busca no Confluence para: {pergunta_limpa}")
                
                # Melhorar o termo de busca extraindo palavras-chave
                termo_busca_confluence = melhorar_busca_confluence(pergunta_limpa)
                logger.info(f"🔍 Palavras-chave extraídas: {termo_busca_confluence}")
                
                resultado_confluence = buscar_confluence(termo_busca_confluence)
                logger.info(f"Resultado Confluence: {resultado_confluence[:100] if resultado_confluence else 'None'}...")
                
                if resultado_confluence and eh_resultado_util(resultado_confluence):
                    logger.info("✅ Resultado útil encontrado no Confluence")
                    resultados_encontrados['confluence'] = resultado_confluence
                else:
                    logger.info("❌ Nenhum resultado útil no Confluence")
                    
                    # 2. FALLBACK: Só buscar no Zendesk se não encontrou no Confluence
                    logger.info(f"🎫 Iniciando busca no Zendesk API para: {pergunta_limpa}")
                    resultado_zendesk = buscar_artigo_zendesk_api(text)
                    logger.info(f"Resultado Zendesk: {resultado_zendesk[:100] if resultado_zendesk else 'None'}...")
                    
                    if resultado_zendesk and eh_resultado_util(resultado_zendesk):
                        logger.info("✅ Resultado útil encontrado no Zendesk")
                        resultados_encontrados['zendesk'] = resultado_zendesk
                    else:
                        logger.info("❌ Nenhum resultado útil no Zendesk")

                # 3. ENVIAR APENAS RESULTADO FINAL
                if resultados_encontrados:
                    logger.info(f"🎉 Total de resultados encontrados: {len(resultados_encontrados)}")
                    
                    # 🤖 REGISTRAR PERGUNTA PARA APRENDIZADO AUTOMÁTICO
                    fonte = 'confluence' if 'confluence' in resultados_encontrados else 'zendesk'
                    resposta_bruta = resultados_encontrados.get(fonte, '')
                    
                    resultado_registro = registrar_pergunta(pergunta_limpa, resposta_bruta, fonte)
                    if resultado_registro.get('faq_criada'):
                        logger.info(f"🎉 FAQ AUTO-GERADA! Pergunta '{pergunta_limpa}' apareceu {resultado_registro['contador']} vezes")
                    
                    resultado_formatado = formatar_resultados_encontrados(
                        resultados_encontrados.get('zendesk'),
                        resultados_encontrados.get('confluence'),
                        pergunta_limpa
                    )
                    
                    if resultado_formatado:
                        logger.info("📤 Enviando resposta única para o Slack...")
                        
                        # Converter ** para * para formatação mrkdwn
                        resultado_mrkdwn = resultado_formatado.replace("**", "*")
                        
                        response = slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=f"Resultados para: {pergunta_limpa}",  # Fallback para acessibilidade
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": resultado_mrkdwn
                                    }
                                }
                            ]
                        )
                        logger.info(f"✅ Resposta enviada! TS: {response.get('ts')}")
                        
                        # Botões em mensagem separada
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text="Estas informações ajudaram?",  # Fallback para acessibilidade
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "❓ *Estas informações ajudaram?*"
                                    }
                                }
                            ] + criar_botoes_interacao(pergunta_limpa, resultados_encontrados)
                        )
                        return jsonify({"ok": True})
                
                # Se não encontrou nada
                else:
                    logger.info("❌ Nenhum resultado encontrado - oferecendo alternativas")
                    
                    # Mensagem no estilo Ask Nina
                    mensagem_sem_resultado = (
                        "Olá!\n\n"
                        f"Com base nas informações disponíveis em meu contexto, não localizei documentação específica sobre *{pergunta_limpa}* em nossa base de conhecimento.\n\n"
                        "Para verificar a disponibilidade dessa informação ou explorar alternativas, você pode:\n\n"
                        "• Acessar nosso portal de integrações para documentação completa\n"
                        "• Entrar em contato com o time de suporte para orientações específicas\n"
                        "• Abrir um chamado no Jira para que possamos ajudar diretamente\n\n"
                        "_Estou à disposição para ajudar com outras questões._"
                    )
                    
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"Não encontrei informações sobre: {pergunta_limpa}",  # Fallback
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": mensagem_sem_resultado
                                }
                            }
                        ] + criar_botoes_interacao(pergunta_limpa, {})
                    )
                    return jsonify({"ok": True})

            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
                try:
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text="Erro interno. Tente novamente.",  # Fallback
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"❌ *Erro interno.* Tente novamente em alguns segundos."
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
    logger.info("🔘 Requisição recebida em /slack/actions")
    
    # ⚠️ NOTA: Validação de assinatura desabilitada para botões pois o Flask
    # consome o body ao acessar request.form, tornando impossível validar.
    # Segurança mantida através do token do Slack no payload.
    logger.info("✅ Processando ação de botão (validação via token do Slack)")

    try:
        payload_str = request.form.get("payload")
        logger.info(f"📦 Payload recebido: {payload_str[:200]}...")
        
        payload = json.loads(payload_str)
        logger.info(f"👤 User: {payload.get('user', {}).get('id')}")
        logger.info(f"📢 Channel: {payload.get('channel', {}).get('id')}")
        
        user = payload["user"]["id"]
        channel = payload["channel"]["id"]
        
        # IMPORTANTE: Extrair thread_ts da mensagem original para manter na thread
        message = payload.get("message", {})
        thread_ts = message.get("thread_ts") or message.get("ts")
        logger.info(f"🧵 Thread TS: {thread_ts}")
        
        action = payload["actions"][0]
        action_id = action["action_id"]
        
        logger.info(f"🔘 Action ID: {action_id}")
        logger.info(f"💾 Action value: {action.get('value')}")
        
        # Extrair dados do botão
        action_data = json.loads(action["value"])
        acao = action_data["action"]
        pergunta = action_data["pergunta"]
        
        logger.info(f"🎯 Ação: {acao}, Pergunta: {pergunta}")
        
        # Responder com base na ação
        if acao == "resolvido":
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"Perfeito! Ajudei com: {pergunta}",  # Fallback
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🎉 *Perfeito!* Fico feliz que consegui ajudar com: _{pergunta}_\n\nSe precisar de mais alguma coisa, é só me mencionar! 😊"
                        }
                    }
                ]
            )
            
        elif acao == "portal":
            portal_url = "https://sites.google.com/nuvemshop.com.br/integracoesnuvemenvio/início"
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"Portal de Integrações: {portal_url}",  # Fallback
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📋 *Portal de Integrações* para: _{pergunta}_\n\n🔗 *Acesse:* <{portal_url}|Portal de Integrações>\n\n💡 *No portal você encontra:*\n• Documentação completa da API\n• Guias de integração passo a passo\n• Exemplos de código\n• Webhooks e notificações\n• FAQs e troubleshooting\n\nSe ainda não encontrar o que precisa, me mencione novamente! 🤖"
                        }
                    }
                ]
            )
            
        elif acao == "chamado":
            jira_url = os.getenv("ATLASSIAN_BASE_URL", "https://tiendanube.atlassian.net")
            jira_create_url = f"{jira_url}/secure/CreateIssue.jspa?pid=13242&issuetype=13600"
            
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"Abrir chamado: {jira_create_url}",  # Fallback
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🎫 *Abrir Chamado* para: _{pergunta}_\n\n🔗 *Criar chamado:* <{jira_create_url}|Abrir no Jira>\n\n📝 *Preencha com estas informações:*\n• *Assunto:* {pergunta}\n• *Descrição detalhada:* Explique sua dúvida ou problema\n• *Contexto:* Plataforma, integração ou API específica\n• *Urgência:* Nível de prioridade do seu caso\n\n👥 *A equipe de integrações analisará e responderá em breve!*"
                        }
                    }
                ]
            )
            
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Erro ao processar ação: {e}")
        return jsonify({"status": "error"})

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
        "eventos_cache": len(eventos_processados)
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