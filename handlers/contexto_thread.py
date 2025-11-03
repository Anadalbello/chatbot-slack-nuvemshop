#!/usr/bin/env python3
"""
Sistema de contexto de thread/histórico
Busca mensagens anteriores na thread para melhorar respostas sequenciais
"""

import logging
from typing import Optional, List, Dict
from slack_sdk.web import WebClient
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def bot_respondeu_na_thread(
    slack_client: WebClient,
    channel: str,
    thread_ts: str,
    bot_user_id: Optional[str] = None
) -> bool:
    """
    Verifica se o bot já respondeu nesta thread
    
    Args:
        slack_client: Cliente do Slack
        channel: ID do canal
        thread_ts: Timestamp da thread
        bot_user_id: ID do usuário do bot (opcional, busca automaticamente se não fornecido)
        
    Returns:
        True se o bot já respondeu na thread, False caso contrário
    """
    try:
        # Obter bot_user_id se não fornecido
        if not bot_user_id:
            try:
                auth_response = slack_client.auth_test()
                bot_user_id = auth_response.get('user_id')
                logger.debug(f"Bot user ID: {bot_user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao obter bot user ID: {e}")
                return False
        
        # Buscar mensagens da thread
        response = slack_client.conversations_replies(
            channel=channel,
            ts=thread_ts,
            limit=50  # Verificar mais mensagens para ter certeza
        )
        
        if not response.get('ok'):
            error = response.get('error', 'unknown')
            # Se for erro de permissão, logar mas não quebrar (tratamento gracioso)
            if error == 'missing_scope':
                needed_scope = response.get('needed', 'unknown')
                logger.debug(f"⚠️ Permissão faltando para verificar thread: {needed_scope}")
            return False
        
        mensagens = response.get('messages', [])
        
        # Verificar se alguma mensagem é do bot
        for msg in mensagens:
            # Verificar por bot_id ou user_id
            if msg.get('bot_id') or msg.get('user') == bot_user_id:
                logger.debug(f"✅ Bot encontrado na thread (TS: {msg.get('ts')})")
                return True
        
        logger.debug("📭 Bot não encontrado na thread")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar se bot respondeu na thread: {e}")
        return False


def buscar_historico_thread(
    slack_client: WebClient,
    channel: str,
    thread_ts: str,
    limite: int = 10
) -> Optional[str]:
    """
    Busca histórico de mensagens na thread do Slack
    
    Args:
        slack_client: Cliente do Slack
        channel: ID do canal
        thread_ts: Timestamp da thread (identificador único)
        limite: Número máximo de mensagens anteriores a buscar
        
    Returns:
        String formatada com contexto da thread ou None se erro
    """
    try:
        logger.info(f"📚 Buscando histórico da thread: {thread_ts}")
        
        # Buscar mensagens da thread usando conversations.replies
        response = slack_client.conversations_replies(
            channel=channel,
            ts=thread_ts,
            limit=limite,
            inclusive=False  # Não incluir a mensagem atual
        )
        
        if not response.get('ok'):
            error = response.get('error', 'unknown')
            # Tratar erros de permissão de forma mais elegante
            if error == 'missing_scope':
                needed_scope = response.get('needed', 'unknown')
                logger.warning(f"⚠️ Permissão faltando: {needed_scope}. Configure no Slack App: https://api.slack.com/apps")
            else:
                logger.warning(f"⚠️ Erro ao buscar histórico: {error}")
            return None
        
        mensagens = response.get('messages', [])
        
        if not mensagens:
            logger.debug("📭 Nenhuma mensagem anterior na thread")
            return None
        
        # Filtrar apenas mensagens de usuários (não do bot) e formatar
        contexto = []
        
        for msg in reversed(mensagens):  # Ordem cronológica (mais antiga primeiro)
            # Ignorar mensagens do bot
            if msg.get('bot_id') or msg.get('subtype') == 'bot_message':
                continue
            
            # Ignorar mensagens de sistema
            if msg.get('subtype'):
                continue
            
            texto = msg.get('text', '').strip()
            user = msg.get('user', '')
            timestamp = msg.get('ts', '')
            
            # Limpar menções ao bot e formatação
            texto_limpo = texto.replace('<@', '').replace('>', '')
            texto_limpo = texto_limpo.replace('@Perguntaê', '').replace('@Perguntae', '')
            texto_limpo = texto_limpo.strip()
            
            if texto_limpo and len(texto_limpo) > 2:
                # Converter timestamp para hora legível (opcional)
                try:
                    ts_float = float(timestamp)
                    dt = datetime.fromtimestamp(ts_float)
                    hora = dt.strftime('%H:%M')
                    contexto.append(f"[{hora}] Usuário: {texto_limpo}")
                except:
                    contexto.append(f"Usuário: {texto_limpo}")
        
        if not contexto:
            logger.debug("📭 Nenhuma mensagem útil encontrada no histórico")
            return None
        
        # Limitar contexto (últimas N mensagens mais relevantes)
        contexto_limitado = contexto[-5:]  # Últimas 5 mensagens
        
        contexto_formatado = "\n".join(contexto_limitado)
        
        logger.info(f"✅ Contexto da thread carregado: {len(contexto_limitado)} mensagens anteriores")
        logger.debug(f"📄 Contexto: {contexto_formatado[:200]}...")
        
        return contexto_formatado
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar histórico da thread: {e}")
        return None


def extrair_referencias_contexto(contexto: str, mensagem_atual: str) -> Dict[str, str]:
    """
    Extrai referências do contexto que podem ser úteis para a mensagem atual
    
    Args:
        contexto: Histórico da thread formatado
        mensagem_atual: Mensagem atual do usuário
        
    Returns:
        Dict com referências extraídas:
        - integracoes_mencionadas: Lista de integrações mencionadas antes
        - termos_chave: Termos importantes mencionados
        - pergunta_anterior: Pergunta mais recente
    """
    referencias = {
        'integracoes_mencionadas': [],
        'termos_chave': [],
        'pergunta_anterior': None
    }
    
    if not contexto:
        return referencias
    
    try:
        # Extrair pergunta anterior (última linha)
        linhas = contexto.strip().split('\n')
        if linhas:
            referencias['pergunta_anterior'] = linhas[-1]
        
        # Tentar extrair nomes de integrações mencionadas (palavras com maiúsculas)
        import re
        # Padrão para encontrar possíveis nomes de ERPs (palavras começando com maiúscula)
        erps_comuns = ['Bling', 'Notazz', 'Tiny', 'Omie', 'Eccosys', 'VTEX', 'Magento', 
                      'Shopify', 'WooCommerce', 'Nuvemshop', 'Tray', 'Loja Integrada']
        
        contexto_lower = contexto.lower()
        for erp in erps_comuns:
            if erp.lower() in contexto_lower:
                referencias['integracoes_mencionadas'].append(erp)
        
        # Remover duplicatas
        referencias['integracoes_mencionadas'] = list(set(referencias['integracoes_mencionadas']))
        
        logger.debug(f"🔍 Referências extraídas: {referencias}")
        
    except Exception as e:
        logger.debug(f"Erro ao extrair referências: {e}")
    
    return referencias

