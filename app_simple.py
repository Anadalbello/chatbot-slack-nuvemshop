#!/usr/bin/env python3
"""
Versão simplificada do app para debug
"""

from flask import Flask, request, jsonify
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier
from dotenv import load_dotenv
import os
import logging
import json

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

@app.route("/slack/events", methods=["POST"])
def slack_events():
    logger.info("🔘 Evento recebido do Slack")
    
    if not verifier.is_valid_request(request.get_data(), request.headers):
        logger.error("❌ Assinatura inválida")
        return "Invalid signature", 403

    data = request.json
    logger.info(f"📊 Tipo de evento: {data.get('type')}")

    if data.get("type") == "url_verification":
        logger.info("✅ URL verification")
        return jsonify({"challenge": data.get("challenge")})

    if "event" in data:
        event = data["event"]
        if event.get("type") == "app_mention":
            user = event["user"]
            text = event["text"]
            channel = event["channel"]
            thread_ts = event.get("thread_ts") or event.get("ts")
            
            logger.info(f"👤 Mensagem de {user}: {text}")
            
            # Resposta simples para teste
            try:
                response = slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="🤖 Bot funcionando! Esta é uma resposta de teste."
                )
                logger.info(f"✅ Resposta enviada! TS: {response.get('ts')}")
            except Exception as e:
                logger.error(f"❌ Erro ao enviar mensagem: {e}")

    return jsonify({"ok": True})

@app.route("/slack/actions", methods=["POST"])
def slack_actions():
    logger.info("🔘 Ação recebida do Slack")
    
    try:
        payload_str = request.form.get("payload")
        payload = json.loads(payload_str)
        
        logger.info(f"📊 Payload: {payload.keys()}")
        
        user = payload["user"]["id"]
        channel = payload["channel"]["id"]
        message = payload.get("message", {})
        thread_ts = message.get("thread_ts") or message.get("ts")
        
        action = payload["actions"][0]
        acao = action["action_id"]
        
        logger.info(f"🎯 Ação: {acao}")
        
        # Resposta simples para qualquer ação
        slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"🤖 Ação '{acao}' recebida! Bot funcionando."
        )
        
        return jsonify({"ok": True})
        
    except Exception as e:
        logger.error(f"❌ Erro no handler de ações: {e}")
        return jsonify({"ok": True})

@app.route("/test", methods=["GET"])
def test_endpoint():
    return jsonify({
        "status": "ok", 
        "message": "Bot simplificado funcionando!",
        "slack_token": "✅" if slack_token else "❌",
        "signing_secret": "✅" if signing_secret else "❌"
    })

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Bot simplificado está funcionando"
    })

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot Simplificado está rodando! 🚀", 200

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 3000))
    logger.info(f"🚀 Iniciando bot simplificado na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
