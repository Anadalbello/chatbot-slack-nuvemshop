"""
Gerenciador de Base de Conhecimento
Estilo Nina - Adaptado para múltiplas fontes
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import importlib

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """Gerenciador unificado de todas as fontes de conhecimento"""
    
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.sources_config = self._load_sources_config()
        self.context_rules = self._load_context_rules()
        self.sources = self._initialize_sources()
        
        logger.info(f"✅ Knowledge Manager inicializado: {len(self.sources)} fontes ativas")
    
    def _load_sources_config(self) -> Dict:
        """Carrega configuração das fontes"""
        sources_file = self.knowledge_dir / "sources_config.json"
        try:
            with open(sources_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Erro ao carregar sources_config: {e}")
            return {"sources": [], "search_strategy": {}}
    
    def _load_context_rules(self) -> Dict:
        """Carrega regras de contexto"""
        rules_file = self.knowledge_dir / "context_rules.json"
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Erro ao carregar context_rules: {e}")
            return {}
    
    def _initialize_sources(self) -> Dict[str, Any]:
        """Inicializa handlers das fontes de conhecimento"""
        sources = {}
        sources_list = self.sources_config.get('sources', [])
        
        for source_config in sources_list:
            if not source_config.get('enabled', False):
                continue
            
            source_id = source_config['id']
            try:
                # Importar módulo dinamicamente
                module_name = source_config['handler_module']
                function_name = source_config['handler_function']
                
                module = importlib.import_module(module_name)
                handler_function = getattr(module, function_name)
                
                # Handler opcional para buscar integração específica
                handler_integracao = None
                if 'handler_integracao_especifica' in source_config:
                    try:
                        handler_integracao = getattr(module, source_config['handler_integracao_especifica'])
                    except AttributeError:
                        logger.debug(f"Handler de integração específica não encontrado para {source_id}")
                
                sources[source_id] = {
                    'handler': handler_function,
                    'handler_integracao': handler_integracao,
                    'config': source_config,
                    'priority': source_config.get('priority', 999)
                }
                
                logger.info(f"✅ Fonte '{source_id}' carregada (prioridade: {source_config.get('priority')})")
            except Exception as e:
                logger.error(f"❌ Erro ao carregar fonte '{source_id}': {e}")
        
        # Ordenar por prioridade (menor número = maior prioridade)
        sources = dict(sorted(sources.items(), key=lambda x: x[1]['priority']))
        return sources
    
    def search(self, query: str, sources: Optional[List[str]] = None, limit: int = 5) -> List[Dict]:
        """
        Busca unificada em múltiplas fontes (estilo Nina)
        
        Args:
            query: Termo de busca
            sources: Lista de IDs de fontes (None = todas habilitadas, por prioridade)
            limit: Limite de resultados por fonte
            
        Returns:
            Lista de resultados padronizados
        """
        if sources is None:
            # Usar todas as fontes na ordem de prioridade
            sources = list(self.sources.keys())
        
        results = []
        strategy = self.sources_config.get('search_strategy', {})
        stop_on_first = strategy.get('stop_on_first_success', False)
        
        logger.info(f"🔍 Iniciando busca em {len(sources)} fontes para: '{query[:50]}...'")
        
        for source_id in sources:
            if source_id not in self.sources:
                continue
            
            source_data = self.sources[source_id]
            handler = source_data['handler']
            config = source_data['config']['config']
            
            try:
                logger.info(f"🔍 Buscando em '{source_id}' (prioridade {source_data['priority']})")
                
                # Chamar handler de acordo com a assinatura específica
                # Google Sheets: não suporta busca genérica (apenas lista todas ou busca específica)
                # Integracoes JSON: usa handler de integração específica para busca
                if source_id == 'google_sheets':
                    logger.debug(f"⚠️ Google Sheets não suporta busca genérica, pulando...")
                    continue
                elif source_id == 'integracoes_json':
                    # Para JSON, usar handler de integração específica se disponível
                    handler_integracao = source_data.get('handler_integracao')
                    if handler_integracao:
                        result = handler_integracao(query)
                    else:
                        logger.debug(f"⚠️ Handler de integração não disponível para JSON, pulando...")
                        continue
                else:
                    # Todos os outros handlers aceitam apenas termo como argumento posicional
                    # Confluence: buscar_confluence(termo)
                    # Zendesk: buscar_artigo_zendesk_api(termo_original)
                    result = handler(query)
                
                if result and self._is_valid_result(result):
                    results.append({
                        'source': source_id,
                        'source_name': source_data['config']['name'],
                        'content': result,
                        'priority': source_data['priority']
                    })
                    logger.info(f"✅ Resultado válido encontrado em '{source_id}'")
                    
                    if stop_on_first:
                        logger.info(f"🛑 Parando busca após primeiro sucesso em '{source_id}'")
                        break
                        
            except Exception as e:
                logger.error(f"❌ Erro ao buscar em '{source_id}': {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue
        
        # Ordenar por prioridade (menor = melhor)
        results.sort(key=lambda x: x['priority'])
        
        logger.info(f"📊 Total de resultados encontrados: {len(results)}")
        return results
    
    def _is_valid_result(self, result: Any) -> bool:
        """
        Valida se o resultado é útil (estilo Nina - não aceita resultados vazios/erros)
        """
        if not result:
            return False
        
        result_str = str(result).strip()
        
        # Verificar tamanho mínimo
        validation_rules = self.context_rules.get('validation_rules', {})
        min_length = validation_rules.get('min_result_length', 20)
        
        if len(result_str) < min_length:
            return False
        
        # Verificar keywords de erro
        if validation_rules.get('reject_error_messages', True):
            error_keywords = validation_rules.get('error_keywords', [])
            result_lower = result_str.lower()
            if any(keyword in result_lower for keyword in error_keywords):
                logger.debug(f"Resultado rejeitado por conter palavras de erro")
                return False
        
        return True
    
    def get_context_rules(self) -> Dict:
        """Obtém regras de contexto"""
        return self.context_rules
    
    def get_domain_context(self) -> Dict:
        """Obtém contexto do domínio"""
        return self.context_rules.get('domain', {})
    
    def search_integration_specific(self, integration_name: str) -> Optional[Dict]:
        """
        Busca uma integração específica nas fontes que suportam essa funcionalidade
        Prioriza Google Sheets (maior prioridade)
        """
        logger.info(f"🔍 Buscando integração específica: '{integration_name}'")
        
        # Tentar fontes na ordem de prioridade
        for source_id, source_data in self.sources.items():
            handler_integracao = source_data.get('handler_integracao')
            if not handler_integracao:
                continue
            
            try:
                logger.info(f"🔍 Buscando '{integration_name}' em '{source_id}'")
                result = handler_integracao(integration_name)
                
                if result and self._is_valid_result(result):
                    logger.info(f"✅ Integração encontrada em '{source_id}'")
                    return {
                        'source': source_id,
                        'source_name': source_data['config']['name'],
                        'content': result,
                        'priority': source_data['priority']
                    }
            except Exception as e:
                logger.debug(f"Erro ao buscar em '{source_id}': {e}")
                continue
        
        logger.info(f"❌ Integração '{integration_name}' não encontrada em nenhuma fonte")
        return None

