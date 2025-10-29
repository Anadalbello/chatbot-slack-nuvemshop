"""
Validador de Fontes - Estilo Nina
Valida se há fonte confiável antes de responder
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class FonteValidator:
    """
    Validador de fontes (estilo Nina)
    Garante que só respondemos quando temos fonte confiável
    """
    
    def __init__(self, knowledge_manager):
        self.kb = knowledge_manager
        self.context_rules = knowledge_manager.get_context_rules()
        self.validation_rules = self.context_rules.get('validation_rules', {})
        logger.info("✅ FonteValidator inicializado")
    
    def validar_resultados(self, resultados: List[Dict]) -> Dict:
        """
        Valida se há resultados suficientes para responder (estilo Nina)
        
        Args:
            resultados: Lista de resultados das buscas
            
        Returns:
            dict com:
            - tem_fonte_valida: bool
            - resultados_validos: List[Dict]
            - mensagem_erro: str (se não tem fonte)
        """
        logger.info(f"🔍 Validando {len(resultados)} resultados")
        
        require_source = self.validation_rules.get('require_source_before_response', True)
        
        # Filtrar resultados válidos
        resultados_validos = []
        for resultado in resultados:
            if self._eh_resultado_valido(resultado):
                resultados_validos.append(resultado)
        
        tem_fonte_valida = len(resultados_validos) > 0
        
        if not tem_fonte_valida and require_source:
            logger.warning("⚠️ Nenhuma fonte válida encontrada - resposta será rejeitada")
            return {
                'tem_fonte_valida': False,
                'resultados_validos': [],
                'mensagem_erro': self._gerar_mensagem_sem_resultado()
            }
        
        logger.info(f"✅ {len(resultados_validos)} resultados válidos encontrados")
        return {
            'tem_fonte_valida': True,
            'resultados_validos': resultados_validos,
            'mensagem_erro': None
        }
    
    def _eh_resultado_valido(self, resultado: Dict) -> bool:
        """Valida se um resultado individual é válido"""
        if not resultado:
            return False
        
        content = resultado.get('content')
        if not content:
            return False
        
        # Usar validação do KnowledgeManager
        return self.kb._is_valid_result(content)
    
    def _gerar_mensagem_sem_resultado(self) -> str:
        """
        Gera mensagem quando não há fonte (estilo Nina)
        Similar à mensagem atual do bot, mas garantindo clareza
        """
        return (
            "Olá!\n\n"
            "Com base nas informações disponíveis em meu contexto, não localizei documentação específica sobre sua pergunta em nossa base de conhecimento.\n\n"
            "Para verificar a disponibilidade dessa informação ou explorar alternativas, você pode:\n\n"
            "• Acessar nosso portal de integrações para documentação completa\n"
            "• Entrar em contato com o time de suporte para orientações específicas\n"
            "• Abrir um chamado no Jira para que possamos ajudar diretamente\n\n"
            "_Estou à disposição para ajudar com outras questões._"
        )
    
    def pode_responder(self, resultados: List[Dict]) -> bool:
        """
        Verifica se pode responder baseado nos resultados (estilo Nina)
        Só retorna True se tiver pelo menos uma fonte válida
        """
        validacao = self.validar_resultados(resultados)
        return validacao['tem_fonte_valida']

