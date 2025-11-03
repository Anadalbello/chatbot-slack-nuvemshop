#!/usr/bin/env python3
"""
Sistema de tracking de perguntas não respondidas
Registra perguntas que não encontraram resposta para análise futura
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Caminho do arquivo de tracking
TRACKING_FILE = Path(__file__).parent.parent / 'perguntas_sem_resposta.json'


def registrar_pergunta_sem_resposta(pergunta: str, query_usada: str = "", motivo: str = ""):
    """
    Registra uma pergunta que não encontrou resposta
    
    Args:
        pergunta: Pergunta original do usuário
        query_usada: Query que foi usada na busca (pode ser diferente da pergunta)
        motivo: Motivo pelo qual não encontrou resposta
    """
    try:
        # Carregar tracking existente
        tracking_data = carregar_tracking()
        
        # Adicionar nova entrada
        entrada = {
            'pergunta': pergunta,
            'query_usada': query_usada,
            'motivo': motivo,
            'timestamp': datetime.now().isoformat(),
            'data': datetime.now().strftime('%Y-%m-%d')
        }
        
        tracking_data['perguntas'].append(entrada)
        tracking_data['metadata']['total'] += 1
        tracking_data['metadata']['ultima_atualizacao'] = datetime.now().isoformat()
        
        # Salvar
        salvar_tracking(tracking_data)
        
        logger.info(f"📝 Pergunta sem resposta registrada: '{pergunta[:50]}...'")
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar pergunta sem resposta: {e}")


def carregar_tracking() -> dict:
    """Carrega o arquivo de tracking"""
    try:
        if not TRACKING_FILE.exists():
            return {
                'perguntas': [],
                'metadata': {
                    'total': 0,
                    'ultima_atualizacao': None
                }
            }
        
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"❌ Erro ao carregar tracking: {e}")
        return {
            'perguntas': [],
            'metadata': {
                'total': 0,
                'ultima_atualizacao': None
            }
        }


def salvar_tracking(data: dict):
    """Salva o arquivo de tracking"""
    try:
        # Criar diretório se não existir
        TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar tracking: {e}")
        return False


def obter_estatisticas() -> dict:
    """Retorna estatísticas sobre perguntas sem resposta"""
    try:
        tracking = carregar_tracking()
        
        # Agrupar por data
        por_data = {}
        for pergunta in tracking['perguntas']:
            data = pergunta.get('data', 'desconhecida')
            por_data[data] = por_data.get(data, 0) + 1
        
        return {
            'total': tracking['metadata']['total'],
            'ultima_atualizacao': tracking['metadata'].get('ultima_atualizacao'),
            'por_data': por_data,
            'ultimas_10': tracking['perguntas'][-10:] if tracking['perguntas'] else []
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {e}")
        return {}


def limpar_tracking_antigo(dias_manter: int = 30):
    """Remove entradas mais antigas que X dias"""
    try:
        tracking = carregar_tracking()
        
        data_limite = datetime.now()
        from datetime import timedelta
        data_limite = data_limite - timedelta(days=dias_manter)
        
        perguntas_manter = []
        removidas = 0
        
        for pergunta in tracking['perguntas']:
            try:
                timestamp = datetime.fromisoformat(pergunta['timestamp'])
                if timestamp >= data_limite:
                    perguntas_manter.append(pergunta)
                else:
                    removidas += 1
            except:
                perguntas_manter.append(pergunta)  # Manter se não conseguir parsear
        
        tracking['perguntas'] = perguntas_manter
        tracking['metadata']['total'] = len(perguntas_manter)
        
        salvar_tracking(tracking)
        
        if removidas > 0:
            logger.info(f"🧹 Limpeza: {removidas} perguntas antigas removidas")
        
        return removidas
        
    except Exception as e:
        logger.error(f"❌ Erro ao limpar tracking: {e}")
        return 0

