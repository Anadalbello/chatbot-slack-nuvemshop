#!/usr/bin/env python3
"""
Sistema de contexto de thread/histórico
Busca mensagens anteriores na thread para melhorar respostas sequenciais
"""

import logging
import re
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
            # Tratar erros de permissão de forma mais elegante (não crítico)
            if error == 'missing_scope':
                needed_scope = response.get('needed', 'unknown')
                # Log mais suave - não é erro crítico, apenas aviso
                logger.debug(f"📝 Contexto de thread não disponível: falta permissão '{needed_scope}'. "
                           f"Configure em OAuth & Permissions → Bot Token Scopes e reinstale o app.")
            else:
                logger.debug(f"⚠️ Erro ao buscar histórico: {error}")
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
            texto_limpo = texto_limpo.replace('@Perguntaê', '').replace('@Perguntae', '').replace('@Tina', '')
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
        - integracao_principal: Nome da integração mais provável mencionada (se houver)
        - termos_chave: Termos importantes mencionados
        - pergunta_anterior: Pergunta mais recente
    """
    referencias = {
        'integracoes_mencionadas': [],
        'integracao_principal': None,
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
        
        # Combinar contexto e mensagem atual para busca mais completa
        texto_completo = f"{contexto}\n{mensagem_atual}".lower()
        
        # Carregar todas as integrações do JSON para busca mais precisa
        try:
            from handlers.buscar_integracoes_json import carregar_integracoes_json
            integracoes = carregar_integracoes_json()
            
            if integracoes:
                # Buscar integrações mencionadas no contexto
                integracoes_encontradas = []
                
                for integracao in integracoes:
                    nome_integracao = integracao.get('Nome', '')
                    if not nome_integracao:
                        continue
                    
                    # Normalizar nome para busca (remover parênteses e caracteres especiais)
                    nome_limpo = re.sub(r'\s*\(.*?\)', '', nome_integracao).strip()
                    nome_normalizado = re.sub(r'[^\w\s]', '', nome_limpo.lower())
                    
                    # Buscar por nome completo ou palavras-chave do nome
                    palavras_nome = nome_normalizado.split()
                    
                    # Verificar se o nome completo está no contexto
                    if nome_normalizado in texto_completo:
                        integracoes_encontradas.append({
                            'nome': nome_integracao,
                            'score': 100,  # Match completo = maior score
                            'match_type': 'completo'
                        })
                    # Verificar se palavras-chave do nome estão no contexto
                    elif len(palavras_nome) > 1:
                        palavras_encontradas = sum(1 for palavra in palavras_nome if len(palavra) > 2 and palavra in texto_completo)
                        if palavras_encontradas >= len(palavras_nome) * 0.6:  # Pelo menos 60% das palavras
                            integracoes_encontradas.append({
                                'nome': nome_integracao,
                                'score': palavras_encontradas * 10,
                                'match_type': 'parcial'
                            })
                    # Verificar match simples (uma palavra significativa)
                    elif len(palavras_nome) == 1 and len(palavras_nome[0]) > 3:
                        if palavras_nome[0] in texto_completo:
                            integracoes_encontradas.append({
                                'nome': nome_integracao,
                                'score': 50,
                                'match_type': 'simples'
                            })
                
                    # Ordenar por score e remover duplicatas
                    if integracoes_encontradas:
                        logger.debug(f"🔍 {len(integracoes_encontradas)} integrações encontradas no contexto")
                        # Remover duplicatas mantendo o maior score
                        integracoes_unicas = {}
                        for item in integracoes_encontradas:
                            nome = item['nome']
                            if nome not in integracoes_unicas or item['score'] > integracoes_unicas[nome]['score']:
                                integracoes_unicas[nome] = item
                        
                        # Ordenar por score (maior primeiro)
                        integracoes_ordenadas = sorted(
                            integracoes_unicas.values(),
                            key=lambda x: x['score'],
                            reverse=True
                        )
                        
                        referencias['integracoes_mencionadas'] = [item['nome'] for item in integracoes_ordenadas]
                        
                        # Definir integração principal (a de maior score)
                        if integracoes_ordenadas:
                            referencias['integracao_principal'] = integracoes_ordenadas[0]['nome']
                            logger.info(f"🎯 Integração principal identificada do contexto: {referencias['integracao_principal']} (score: {integracoes_ordenadas[0]['score']})")
                        else:
                            logger.debug("⚠️ Nenhuma integração ordenada encontrada")
                    else:
                        logger.debug(f"⚠️ Nenhuma integração encontrada no contexto. Texto completo: {texto_completo[:200]}...")
        
        except Exception as e:
            logger.debug(f"Erro ao carregar integrações para busca: {e}")
            # Fallback para lista hardcoded se houver erro
            erps_comuns = ['Bling', 'Notazz', 'Tiny', 'Omie', 'Eccosys', 'VTEX', 'Magento', 
                          'Shopify', 'WooCommerce', 'Nuvemshop', 'Tray', 'Loja Integrada', 'Freterápido']
            
            contexto_lower = contexto.lower()
            for erp in erps_comuns:
                if erp.lower() in contexto_lower:
                    referencias['integracoes_mencionadas'].append(erp)
                    if not referencias['integracao_principal']:
                        referencias['integracao_principal'] = erp
        
        # Remover duplicatas
        referencias['integracoes_mencionadas'] = list(set(referencias['integracoes_mencionadas']))
        
        logger.debug(f"🔍 Referências extraídas: {len(referencias['integracoes_mencionadas'])} integrações, principal: {referencias['integracao_principal']}")
        
    except Exception as e:
        logger.debug(f"Erro ao extrair referências: {e}")
    
    return referencias

