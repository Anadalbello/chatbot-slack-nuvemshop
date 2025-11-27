#!/usr/bin/env python3
"""
Sistema de pausa de threads
Permite que usuários pausem o bot em threads específicas
"""

import json
import logging
from pathlib import Path
from typing import Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)

# Arquivo para armazenar threads pausadas
PAUSA_FILE = Path(__file__).parent.parent / 'threads_pausadas.json'

# Cache em memória para performance
_threads_pausadas: Set[str] = set()


def carregar_threads_pausadas() -> Set[str]:
    """Carrega threads pausadas do arquivo"""
    global _threads_pausadas
    try:
        if PAUSA_FILE.exists():
            with open(PAUSA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _threads_pausadas = set(data.get('threads', []))
                logger.info(f"📋 Carregadas {len(_threads_pausadas)} threads pausadas")
        else:
            _threads_pausadas = set()
        return _threads_pausadas
    except Exception as e:
        logger.error(f"❌ Erro ao carregar threads pausadas: {e}")
        return set()


def salvar_threads_pausadas():
    """Salva threads pausadas no arquivo"""
    try:
        data = {
            'threads': list(_threads_pausadas),
            'ultima_atualizacao': datetime.now().isoformat(),
            'total': len(_threads_pausadas)
        }
        with open(PAUSA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"💾 Salvas {len(_threads_pausadas)} threads pausadas")
    except Exception as e:
        logger.error(f"❌ Erro ao salvar threads pausadas: {e}")


def thread_esta_pausada(channel: str, thread_ts: str) -> bool:
    """
    Verifica se uma thread está pausada
    
    Args:
        channel: ID do canal
        thread_ts: Timestamp da thread
        
    Returns:
        True se a thread está pausada
    """
    # Carregar se ainda não carregou
    if not _threads_pausadas:
        carregar_threads_pausadas()
    
    # Criar chave única: channel_thread_ts
    chave = f"{channel}_{thread_ts}"
    return chave in _threads_pausadas


def pausar_thread(channel: str, thread_ts: str) -> bool:
    """
    Pausa o bot em uma thread específica
    
    Args:
        channel: ID do canal
        thread_ts: Timestamp da thread
        
    Returns:
        True se pausou com sucesso
    """
    try:
        chave = f"{channel}_{thread_ts}"
        _threads_pausadas.add(chave)
        salvar_threads_pausadas()
        logger.info(f"⏸️ Thread pausada: {chave}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao pausar thread: {e}")
        return False


def retomar_thread(channel: str, thread_ts: str) -> bool:
    """
    Retoma o bot em uma thread específica
    
    Args:
        channel: ID do canal
        thread_ts: Timestamp da thread
        
    Returns:
        True se retomou com sucesso
    """
    try:
        chave = f"{channel}_{thread_ts}"
        if chave in _threads_pausadas:
            _threads_pausadas.remove(chave)
            salvar_threads_pausadas()
            logger.info(f"▶️ Thread retomada: {chave}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao retomar thread: {e}")
        return False


# Carregar threads pausadas ao importar
carregar_threads_pausadas()

