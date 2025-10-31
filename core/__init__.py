"""
Core module - Sistema central de gerenciamento de conhecimento
Estilo Nina adaptado para múltiplas fontes
"""

from .knowledge_manager import KnowledgeManager
from .recepcionista import Recepcionista
from .fonte_validator import FonteValidator

__all__ = ['KnowledgeManager', 'Recepcionista', 'FonteValidator']


