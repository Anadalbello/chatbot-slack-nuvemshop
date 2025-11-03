#!/usr/bin/env python3
"""
Sistema de cache para respostas do Gemini
Evita chamadas repetidas para perguntas similares
"""

import hashlib
import time
import logging
from typing import Optional, Dict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Cache em memória (persiste enquanto o servidor está rodando)
_cache_respostas = {}
_cache_max_size = 100  # Máximo de itens no cache
_cache_ttl = 1800  # 30 minutos em segundos


def _normalizar_pergunta(pergunta: str) -> str:
    """Normaliza a pergunta para usar como chave do cache"""
    # Converter para minúsculas e remover espaços extras
    pergunta_norm = " ".join(pergunta.lower().strip().split())
    return pergunta_norm


def _calcular_hash(pergunta: str) -> str:
    """Calcula hash da pergunta normalizada"""
    pergunta_norm = _normalizar_pergunta(pergunta)
    return hashlib.md5(pergunta_norm.encode()).hexdigest()


def _encontrar_cache_similar(pergunta: str) -> Optional[tuple]:
    """
    Encontra resposta em cache para pergunta similar (não exata)
    Retorna (resposta, similaridade) se encontrar algo com >80% similaridade
    """
    pergunta_norm = _normalizar_pergunta(pergunta)
    
    melhor_match = None
    melhor_score = 0
    
    agora = time.time()
    
    for chave, valor in _cache_respostas.items():
        # Verificar se não expirou
        if agora - valor['timestamp'] > _cache_ttl:
            continue
        
        # Calcular similaridade
        cache_pergunta_norm = _normalizar_pergunta(valor['pergunta'])
        similaridade = SequenceMatcher(None, pergunta_norm, cache_pergunta_norm).ratio()
        
        if similaridade > melhor_score and similaridade >= 0.80:  # 80% similaridade mínima
            melhor_score = similaridade
            melhor_match = (valor['resposta'], similaridade)
    
    return melhor_match


def buscar_cache(pergunta: str) -> Optional[str]:
    """
    Busca resposta em cache
    
    Args:
        pergunta: Pergunta original
        
    Returns:
        Resposta em cache (se existir e não expirada) ou None
    """
    try:
        # Limpar cache expirado primeiro
        _limpar_cache_expirado()
        
        # Tentar busca exata primeiro
        hash_pergunta = _calcular_hash(pergunta)
        if hash_pergunta in _cache_respostas:
            item = _cache_respostas[hash_pergunta]
            agora = time.time()
            
            # Verificar se não expirou
            if agora - item['timestamp'] <= _cache_ttl:
                logger.info(f"✅ Cache HIT (exato): '{pergunta[:50]}...'")
                return item['resposta']
            else:
                # Remover expirado
                del _cache_respostas[hash_pergunta]
        
        # Tentar busca similar (para perguntas reescritas mas com mesmo sentido)
        cache_similar = _encontrar_cache_similar(pergunta)
        if cache_similar:
            resposta, similaridade = cache_similar
            logger.info(f"✅ Cache HIT (similar {similaridade:.0%}): '{pergunta[:50]}...'")
            return resposta
        
        logger.debug(f"❌ Cache MISS: '{pergunta[:50]}...'")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar cache: {e}")
        return None


def salvar_cache(pergunta: str, resposta: str):
    """
    Salva resposta no cache
    
    Args:
        pergunta: Pergunta original
        resposta: Resposta gerada
    """
    try:
        # Limpar cache expirado antes de adicionar
        _limpar_cache_expirado()
        
        # Se cache está cheio, remover item mais antigo
        if len(_cache_respostas) >= _cache_max_size:
            _remover_item_mais_antigo()
        
        hash_pergunta = _calcular_hash(pergunta)
        _cache_respostas[hash_pergunta] = {
            'pergunta': pergunta,
            'resposta': resposta,
            'timestamp': time.time()
        }
        
        logger.debug(f"💾 Resposta salva em cache: '{pergunta[:50]}...'")
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar cache: {e}")


def _limpar_cache_expirado():
    """Remove itens expirados do cache"""
    agora = time.time()
    expirados = [
        chave for chave, valor in _cache_respostas.items()
        if agora - valor['timestamp'] > _cache_ttl
    ]
    
    for chave in expirados:
        del _cache_respostas[chave]
    
    if expirados:
        logger.debug(f"🧹 Cache limpo: {len(expirados)} itens expirados removidos")


def _remover_item_mais_antigo():
    """Remove o item mais antigo do cache"""
    if not _cache_respostas:
        return
    
    mais_antigo = min(
        _cache_respostas.items(),
        key=lambda x: x[1]['timestamp']
    )
    del _cache_respostas[mais_antigo[0]]
    logger.debug("🗑️ Item mais antigo removido do cache")


def obter_estatisticas_cache() -> Dict:
    """Retorna estatísticas do cache"""
    _limpar_cache_expirado()
    
    return {
        'tamanho': len(_cache_respostas),
        'max_size': _cache_max_size,
        'ttl_segundos': _cache_ttl,
        'ttl_minutos': _cache_ttl / 60
    }

