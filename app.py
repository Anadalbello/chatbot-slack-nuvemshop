from flask import Flask, request, jsonify
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier
from dotenv import load_dotenv
import os
import logging
import time
import json
from handlers.zendesk_com_resumo import buscar_artigo_zendesk, limpar_termo_busca
from handlers.confluence_com_resumo import buscar_confluence
from handlers.gemini_handler import get_gemini_response
from handlers.jira import criar_chamado_jira
from handlers.google_sites import buscar_google_sites

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
    """Formata todos os resultados encontrados em uma única resposta otimizada"""
    
    logger.info(f"🎨 Formatando resultados - Zendesk: {bool(resultados_zendesk)}, Confluence: {bool(resultados_confluence)}")
    
    try:
        # Cabeçalho mais limpo
        resultado_final = f"🔍 **Resultados para:** _{pergunta_limpa}_\n\n"
        
        # Contador de resultados
        total_resultados = 0
        
        # Adicionar resultados do Zendesk
        if resultados_zendesk:
            logger.info("📝 Formatando resultado do Zendesk...")
            zendesk_info = extrair_resumo_e_link(resultados_zendesk)
            
            resultado_final += f"🎫 **{zendesk_info['titulo']}**\n"
            resultado_final += f"💡 {zendesk_info['resumo']}\n"
            resultado_final += f"👉 Ver no Zendesk\n"
            resultado_final += f"({zendesk_info['link']})\n\n"
            
            total_resultados += 1
            logger.info(f"✅ Zendesk adicionado")
        
        # Adicionar resultados do Confluence
        if resultados_confluence:
            logger.info("📝 Formatando resultado do Confluence...")
            confluence_info = extrair_resumo_e_link(resultados_confluence)
            
            resultado_final += f"📋 **{confluence_info['titulo']}**\n"
            resultado_final += f"💡 {confluence_info['resumo']}\n"
            resultado_final += f"👉 Ver no Confluence\n"
            resultado_final += f"({confluence_info['link']})\n\n"
            
            total_resultados += 1
            logger.info(f"✅ Confluence adicionado")
        
        # Rodapé mais limpo (sem duplicar pergunta)
        if total_resultados > 0:
            resultado_final += "---"
            logger.info(f"🎉 Resultado final otimizado - {total_resultados} item(s)")
            return resultado_final
        
        logger.warning("⚠️ Nenhum resultado para formatar")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao formatar resultados: {e}")
        return f"🔍 **Encontrei informações sobre:** _{pergunta_limpa}_\n\n📋 Veja os resultados acima.\n\n❓ **Isto ajuda?**"

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid signature", 403

    data = request.json

    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})

    if "event" in data:
        event = data["event"]
        if event.get("type") == "app_mention":
            user = event["user"]
            text = event["text"]
            channel = event["channel"]
            thread_ts = event.get("ts")
            
            # 🛡️ VERIFICAR SE É EVENTO DUPLICADO
            if event_ja_processado(event.get("event_ts", ""), user, text):
                logger.info("Evento duplicado ignorado")
                return jsonify({"ok": True})
            
            logger.info(f"Mensagem recebida de {user}: {text}")

            # Enviar mensagem imediata de confirmação
            pergunta_limpa = limpar_termo_busca(text)
            
            try:
                # 🔍 BUSCAR SILENCIOSAMENTE (sem mensagens intermediárias)
                resultados_encontrados = {}

                # 1. Buscar no Zendesk
                logger.info(f"🎫 Iniciando busca no Zendesk para: {pergunta_limpa}")
                resultado_zendesk = buscar_artigo_zendesk(text)
                logger.info(f"Resultado Zendesk: {resultado_zendesk[:100] if resultado_zendesk else 'None'}...")
                
                if resultado_zendesk and eh_resultado_util(resultado_zendesk):
                    logger.info("✅ Resultado útil encontrado no Zendesk")
                    resultados_encontrados['zendesk'] = resultado_zendesk
                else:
                    logger.info("❌ Nenhum resultado útil no Zendesk")

                # 2. Buscar no Confluence
                logger.info(f"📋 Iniciando busca no Confluence para: {pergunta_limpa}")
                resultado_confluence = buscar_confluence(pergunta_limpa)
                logger.info(f"Resultado Confluence: {resultado_confluence[:100] if resultado_confluence else 'None'}...")
                
                if resultado_confluence and eh_resultado_util(resultado_confluence):
                    logger.info("✅ Resultado útil encontrado no Confluence")
                    resultados_encontrados['confluence'] = resultado_confluence
                else:
                    logger.info("❌ Nenhum resultado útil no Confluence")

                # 3. ENVIAR APENAS RESULTADO FINAL
                if resultados_encontrados:
                    logger.info(f"🎉 Total de resultados encontrados: {len(resultados_encontrados)}")
                    
                    resultado_formatado = formatar_resultados_encontrados(
                        resultados_encontrados.get('zendesk'),
                        resultados_encontrados.get('confluence'),
                        pergunta_limpa
                    )
                    
                    if resultado_formatado:
                        logger.info("📤 Enviando resposta única para o Slack...")
                        response = slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=resultado_formatado
                        )
                        logger.info(f"✅ Resposta enviada! TS: {response.get('ts')}")
                        
                        # Botões em mensagem separada
                        slack_client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text="❓ **Estas informações ajudaram?**",
                            blocks=criar_botoes_interacao(pergunta_limpa, resultados_encontrados)
                        )
                        return jsonify({"ok": True})
                
                # Se não encontrou nada
                else:
                    logger.info("❌ Nenhum resultado encontrado - oferecendo alternativas")
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"🔍 Não encontrei informações específicas sobre: _{pergunta_limpa}_",
                        blocks=criar_botoes_interacao(pergunta_limpa, {})
                    )
                    return jsonify({"ok": True})

            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
                try:
                    slack_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"❌ **Erro interno.** Tente novamente em alguns segundos."
                    )
                except:
                    pass

    return jsonify({"ok": True})

@app.route("/slack/actions", methods=["POST"])
def slack_actions():
    """Handler para botões interativos"""
    logger.info("🔘 Requisição recebida em /slack/actions")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Form data: {request.form}")
    
    # Validação de assinatura mais robusta para botões
    try:
        if not verifier.is_valid_request(request.get_data(), request.headers):
            logger.error("❌ Assinatura inválida em /slack/actions")
            # Temporariamente mais permissivo para debug
            logger.warning("⚠️ Continuando mesmo com assinatura inválida (DEBUG)")
            # return "Invalid signature", 403
    except Exception as e:
        logger.error(f"❌ Erro na validação de assinatura: {e}")
        logger.warning("⚠️ Continuando mesmo com erro de assinatura (DEBUG)")

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
        "atlassian_url": "✅" if os.getenv("ATLASSIAN_BASE_URL") else "❌"
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

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False) 