"""
Sistema de Conversas Pendentes
Gerencia conversas que precisam de esclarecimento (ex: país não detectado)
"""

import logging
import threading
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Armazenamento em memória de conversas pendentes
# Formato: {thread_ts: {user_query, query_type, detected_language, channel, timestamp}}
conversas_pendentes: Dict[str, Dict] = {}
# Lock para operações thread-safe no dicionário de conversas pendentes
_conversas_lock = threading.Lock()

# Tempo de expiração de conversas pendentes (30 minutos)
TEMPO_EXPIRACAO = timedelta(minutes=30)


def salvar_conversa_pendente(
    thread_ts: str,
    user_query: str,
    query_type: str = "apps",
    detected_language: str = "pt",
    detected_country: str = "",
    channel: str = ""
) -> None:
    """
    Salva uma conversa pendente para processamento posterior
    
    Args:
        thread_ts: Timestamp da thread (usado como chave)
        user_query: Query original do usuário
        query_type: Tipo de query ("apps" ou "help_center")
        detected_language: Idioma detectado
        detected_country: País detectado (pode estar vazio)
        channel: ID do canal
    """
    # Thread-safe: usar lock para operações no dicionário compartilhado
    with _conversas_lock:
        conversas_pendentes[thread_ts] = {
            "user_query": user_query,
            "query_type": query_type,
            "detected_language": detected_language,
            "detected_country": detected_country,
            "channel": channel,
            "timestamp": datetime.now()
        }
    logger.info(f"💾 Conversa pendente salva: {thread_ts} (query: {user_query[:50]}...)")


def obter_conversa_pendente(thread_ts: str) -> Optional[Dict]:
    """
    Obtém uma conversa pendente se existir e não estiver expirada
    
    Args:
        thread_ts: Timestamp da thread
        
    Returns:
        Dict com dados da conversa ou None se não existir/expirada
    """
    # Thread-safe: usar lock para operações no dicionário compartilhado
    with _conversas_lock:
        if thread_ts not in conversas_pendentes:
            return None
        
        conversa = conversas_pendentes[thread_ts]
        
        # Verificar expiração
        tempo_decorrido = datetime.now() - conversa["timestamp"]
        if tempo_decorrido > TEMPO_EXPIRACAO:
            logger.info(f"⏰ Conversa pendente expirada: {thread_ts}")
            del conversas_pendentes[thread_ts]
            return None
    
    logger.info(f"📖 Conversa pendente encontrada: {thread_ts}")
    return conversa


def remover_conversa_pendente(thread_ts: str) -> None:
    """
    Remove uma conversa pendente
    
    Args:
        thread_ts: Timestamp da thread
    """
    # Thread-safe: usar lock para operações no dicionário compartilhado
    with _conversas_lock:
        if thread_ts in conversas_pendentes:
            del conversas_pendentes[thread_ts]
            logger.info(f"🗑️ Conversa pendente removida: {thread_ts}")


def processar_resposta_pais(user_text: str, conversa: Dict) -> Optional[str]:
    """
    Processa resposta do usuário sobre país e retorna código do país
    
    Args:
        user_text: Texto da resposta do usuário
        conversa: Dados da conversa pendente
        
    Returns:
        Código do país (BR, AR, MX, etc.) ou None se não detectado
    """
    user_text_normalized = user_text.upper().strip()
    
    # Mapeamento de países
    paises_map = {
        "BR": "BR", "BRASIL": "BR", "BRAZIL": "BR",
        "AR": "AR", "ARGENTINA": "AR",
        "MX": "MX", "MEXICO": "MX", "MÉXICO": "MX",
        "CO": "CO", "COLOMBIA": "CO",
        "CL": "CL", "CHILE": "CL",
        "ES": "ES", "ESPANA": "ES", "SPAIN": "ES", "ESPAÑA": "ES",
        "PT": "PT", "PORTUGAL": "PT"
    }
    
    # Buscar correspondência exata primeiro
    detected_country = paises_map.get(user_text_normalized, None)
    
    # Se não encontrou, buscar por substring
    if not detected_country:
        for country_text, country_code in paises_map.items():
            if country_text in user_text_normalized and len(country_text) > 1:
                detected_country = country_code
                break
    
    # Normalizar BR/PT para BR (português = Brasil)
    if detected_country in ["BR", "PT"]:
        detected_country = "BR"
    # Para espanhol, se não especificado, usar AR como padrão
    elif not detected_country:
        # Verificar se é espanhol
        detected_language = conversa.get("detected_language", "")
        if detected_language.startswith("es"):
            detected_country = "AR"  # Default para Argentina
            logger.info("🌍 País não detectado, usando AR como padrão para espanhol")
    
    if detected_country:
        logger.info(f"🌍 País detectado da resposta: {detected_country}")
    
    return detected_country


def limpar_conversas_expiradas() -> int:
    """
    Remove conversas pendentes expiradas
    
    Returns:
        Número de conversas removidas
    """
    agora = datetime.now()
    expiradas = []
    
    # Thread-safe: usar lock para operações no dicionário compartilhado
    with _conversas_lock:
        for thread_ts, conversa in conversas_pendentes.items():
            tempo_decorrido = agora - conversa["timestamp"]
            if tempo_decorrido > TEMPO_EXPIRACAO:
                expiradas.append(thread_ts)
        
        for thread_ts in expiradas:
            del conversas_pendentes[thread_ts]
    
    if expiradas:
        logger.info(f"🧹 {len(expiradas)} conversas pendentes expiradas removidas")
    
    return len(expiradas)


def obter_estatisticas() -> Dict:
    """
    Retorna estatísticas sobre conversas pendentes
    
    Returns:
        Dict com estatísticas
    """
    agora = datetime.now()
    ativas = 0
    expiradas = 0
    
    # Thread-safe: usar lock para operações no dicionário compartilhado
    with _conversas_lock:
        for conversa in conversas_pendentes.values():
            tempo_decorrido = agora - conversa["timestamp"]
            if tempo_decorrido > TEMPO_EXPIRACAO:
                expiradas += 1
            else:
                ativas += 1
        
        total = len(conversas_pendentes)
    
    return {
        "total": total,
        "ativas": ativas,
        "expiradas": expiradas
    }


