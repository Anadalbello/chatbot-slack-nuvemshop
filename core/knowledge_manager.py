"""
Gerenciador de Base de Conhecimento
Estilo Nina - Adaptado para múltiplas fontes
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import importlib

logger = logging.getLogger(__name__)

# Tentar importar PineconeManager (opcional)
try:
    from core.pinecone_manager import create_manager_from_env, namespace_for_locale
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("⚠️ Pinecone não disponível - busca vetorial desabilitada")

class KnowledgeManager:
    """Gerenciador unificado de todas as fontes de conhecimento"""
    
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.sources_config = self._load_sources_config()
        self.context_rules = self._load_context_rules()
        self.sources = self._initialize_sources()
        
        # Inicializar Pinecone se disponível
        self.pinecone_manager = None
        self.pinecone_enabled = False
        if PINECONE_AVAILABLE:
            try:
                # Verificar provider de embeddings
                embedding_provider = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
                
                # Verificar variáveis de ambiente necessárias
                has_pinecone_key = bool(os.getenv("PINECONE_API_KEY"))
                has_index_name = bool(os.getenv("PINECONE_INDEX_NAME"))
                
                if embedding_provider == "gemini":
                    has_embedding_key = bool(os.getenv("GEMINI_API_KEY"))
                    missing_vars = []
                    if not has_pinecone_key:
                        missing_vars.append("PINECONE_API_KEY")
                    if not has_index_name:
                        missing_vars.append("PINECONE_INDEX_NAME")
                    if not has_embedding_key:
                        missing_vars.append("GEMINI_API_KEY")
                    
                    if missing_vars:
                        logger.debug(f"ℹ️ Pinecone não configurado (faltando: {', '.join(missing_vars)})")
                    else:
                        self.pinecone_manager = create_manager_from_env()
                        # Testar conexão
                        if self.pinecone_manager.test_connection():
                            self.pinecone_enabled = True
                            logger.info("✅ Pinecone inicializado e conectado - busca vetorial habilitada")
                        else:
                            logger.warning("⚠️ Pinecone configurado mas teste de conexão falhou")
                elif embedding_provider == "openai":
                    has_embedding_key = bool(os.getenv("OPENAI_API_KEY"))
                    missing_vars = []
                    if not has_pinecone_key:
                        missing_vars.append("PINECONE_API_KEY")
                    if not has_index_name:
                        missing_vars.append("PINECONE_INDEX_NAME")
                    if not has_embedding_key:
                        missing_vars.append("OPENAI_API_KEY")
                    
                    if missing_vars:
                        logger.debug(f"ℹ️ Pinecone não configurado (faltando: {', '.join(missing_vars)})")
                    else:
                        self.pinecone_manager = create_manager_from_env()
                        # Testar conexão
                        if self.pinecone_manager.test_connection():
                            self.pinecone_enabled = True
                            logger.info("✅ Pinecone inicializado e conectado - busca vetorial habilitada")
                        else:
                            logger.warning("⚠️ Pinecone configurado mas teste de conexão falhou")
                else:
                    logger.debug(f"ℹ️ Pinecone não configurado (EMBEDDING_PROVIDER inválido: {embedding_provider})")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar Pinecone: {e}")
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
                logger.debug("Busca vetorial desabilitada, usando apenas fontes tradicionais")
        
        logger.info(f"✅ Knowledge Manager inicializado: {len(self.sources)} fontes ativas" + 
                   (f" + Pinecone" if self.pinecone_enabled else ""))
        
        # Log detalhado sobre Pinecone para debug
        if PINECONE_AVAILABLE:
            if self.pinecone_enabled:
                logger.info(f"🔍 Pinecone: HABILITADO (provider: {self.pinecone_manager.embedding_provider}, dimensão: {self.pinecone_manager.embedding_dimension})")
            else:
                logger.info("🔍 Pinecone: DESABILITADO (verifique variáveis de ambiente ou logs acima)")
        else:
            logger.info("🔍 Pinecone: NÃO DISPONÍVEL (biblioteca não instalada)")
    
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
    
    def search(self, query: str, sources: Optional[List[str]] = None, limit: int = 5, locale: str = "pt_BR") -> List[Dict]:
        """
        Busca unificada em múltiplas fontes (estilo Nina)
        Agora com suporte a busca vetorial via Pinecone
        
        Args:
            query: Termo de busca
            sources: Lista de IDs de fontes (None = todas habilitadas, por prioridade)
            limit: Limite de resultados por fonte
            locale: Locale para busca vetorial (padrão: pt_BR)
            
        Returns:
            Lista de resultados padronizados
        """
        results = []
        strategy = self.sources_config.get('search_strategy', {})
        stop_on_first = strategy.get('stop_on_first_success', False)
        use_vector_search = strategy.get('use_vector_search_first', True)
        
        # PRIORIDADE 1: Busca vetorial (Pinecone) se disponível
        if self.pinecone_enabled and use_vector_search:
            try:
                logger.info(f"🔍 [Vetorial] Buscando no Pinecone para: '{query[:50]}...'")
                namespace = namespace_for_locale(locale)
                
                # Buscar no Pinecone
                vector_results = self.pinecone_manager.query_similar(
                    query_text=query,
                    top_k=limit,
                    namespace=namespace
                )
                
                logger.info(f"📊 [Vetorial] Pinecone retornou {len(vector_results)} resultados")
                
                # Converter resultados do Pinecone para formato padrão
                for match in vector_results:
                    score = match.get('score', 0)
                    logger.debug(f"   - Score: {score:.3f}")
                    
                    if score >= 0.7:  # Threshold de relevância
                        metadata = match.get('metadata', {})
                        content = self._format_pinecone_result(metadata, score)
                        
                        if content and self._is_valid_result(content):
                            results.append({
                                'source': 'pinecone',
                                'source_name': 'Busca Vetorial (Pinecone)',
                                'content': content,
                                'priority': 0,  # Prioridade máxima
                                'score': score,
                                'metadata': metadata
                            })
                            logger.info(f"✅ [Vetorial] Resultado encontrado (score: {score:.3f})")
                    else:
                        logger.debug(f"   ⚠️ Resultado rejeitado (score {score:.3f} < 0.7)")
                
                # Se encontrou resultados vetoriais relevantes e stop_on_first, retornar
                if results and stop_on_first:
                    logger.info(f"🛑 Parando busca após encontrar resultados vetoriais")
                    return results
                elif results:
                    logger.info(f"✅ [Vetorial] {len(results)} resultados vetoriais válidos encontrados")
                else:
                    logger.info(f"⚠️ [Vetorial] Nenhum resultado acima do threshold (0.7)")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro na busca vetorial: {e}")
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
                logger.debug("Continuando com busca tradicional...")
        elif not self.pinecone_enabled:
            logger.debug("ℹ️ Busca vetorial desabilitada (Pinecone não disponível ou não configurado)")
        
        # PRIORIDADE 2: Busca tradicional nas outras fontes
        if sources is None:
            # Usar todas as fontes na ordem de prioridade
            sources = list(self.sources.keys())
        
        logger.info(f"🔍 Iniciando busca tradicional em {len(sources)} fontes para: '{query[:50]}...'")
        
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
    
    def _format_pinecone_result(self, metadata: Dict, score: float) -> str:
        """
        Formata resultado do Pinecone para formato de texto legível
        
        Args:
            metadata: Metadata do resultado do Pinecone
            score: Score de similaridade
            
        Returns:
            String formatada com informações da integração
        """
        nome = metadata.get('nome', 'Integração')
        descricao = metadata.get('descricao', '')
        tipo = metadata.get('tipo', '')
        url = metadata.get('url', '')
        contato = metadata.get('contato', '')
        
        resultado = f"**{nome}**"
        
        if tipo:
            resultado += f"\n*Tipo:* {tipo}"
        
        if descricao:
            # Limitar descrição para não ficar muito longa
            desc_limpa = descricao[:500] + "..." if len(descricao) > 500 else descricao
            resultado += f"\n\n{desc_limpa}"
        
        if url:
            resultado += f"\n\n🔗 {url}"
        
        if contato:
            resultado += f"\n📧 *Contato:* {contato}"
        
        resultado += f"\n\n_Relevância: {score:.1%}_"
        
        return resultado
    
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
    
    def search_integration_specific(self, integration_name: str, locale: str = "pt_BR") -> Optional[Dict]:
        """
        Busca uma integração específica nas fontes que suportam essa funcionalidade
        Agora com suporte a busca vetorial via Pinecone
        
        Args:
            integration_name: Nome da integração para buscar
            locale: Locale para busca vetorial (padrão: pt_BR)
            
        Returns:
            Dict com resultado da busca ou None se não encontrado
        """
        logger.info(f"🔍 Buscando integração específica: '{integration_name}'")
        
        # PRIORIDADE 1: Busca vetorial (Pinecone) se disponível
        if self.pinecone_enabled:
            try:
                logger.info(f"🔍 [Vetorial] Buscando '{integration_name}' no Pinecone")
                namespace = namespace_for_locale(locale)
                
                # Buscar no Pinecone
                vector_results = self.pinecone_manager.query_similar(
                    query_text=integration_name,
                    top_k=3,  # Buscar top 3 para ter mais opções
                    namespace=namespace
                )
                
                # Verificar se algum resultado tem score alto e nome similar
                for match in vector_results:
                    metadata = match.get('metadata', {})
                    match_nome = metadata.get('nome', '').lower()
                    score = match.get('score', 0)
                    
                    # Verificar se o nome corresponde bem ou score é alto
                    if (integration_name.lower() in match_nome or 
                        match_nome in integration_name.lower() or 
                        score >= 0.85):
                        
                        content = self._format_pinecone_result(metadata, score)
                        
                        if content and self._is_valid_result(content):
                            logger.info(f"✅ [Vetorial] Integração encontrada (score: {score:.3f})")
                            return {
                                'source': 'pinecone',
                                'source_name': 'Busca Vetorial (Pinecone)',
                                'content': content,
                                'priority': 0,
                                'score': score,
                                'metadata': metadata
                            }
            except Exception as e:
                logger.warning(f"⚠️ Erro na busca vetorial específica: {e}")
        
        # PRIORIDADE 2: Busca tradicional nas outras fontes
        # Tentar fontes na ordem de prioridade usando handler específico
        for source_id, source_data in self.sources.items():
            handler_integracao = source_data.get('handler_integracao')
            if not handler_integracao:
                continue
            
            try:
                logger.info(f"🔍 Buscando '{integration_name}' em '{source_id}' (handler específico)")
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
        
        # Se não encontrou com handler específico, tentar busca genérica
        logger.info(f"⚠️ Handler específico não encontrou, tentando busca genérica...")
        generic_results = self.search(integration_name, limit=3, locale=locale)  # Buscar mais resultados para ter opções
        
        if generic_results:
            # Verificar se algum resultado tem nome similar (busca mais flexível)
            for resultado in generic_results:
                content = resultado.get('content', '')
                # Verificar se o nome da integração aparece no conteúdo
                if integration_name.lower() in content.lower():
                    logger.info(f"✅ Integração encontrada via busca genérica (match por conteúdo)")
                    return resultado
            
            # Se não encontrou match exato, retornar o primeiro resultado mesmo assim
            logger.info(f"✅ Integração encontrada via busca genérica (primeiro resultado)")
            return generic_results[0]
        
        logger.info(f"❌ Integração '{integration_name}' não encontrada em nenhuma fonte")
        
        # Tentar buscar sugestões similares
        try:
            from handlers.buscar_integracoes_json import sugerir_integracoes_similares
            sugestoes = sugerir_integracoes_similares(integration_name, limite=5)
            if sugestoes:
                logger.info(f"💡 Sugestões de integrações similares para '{integration_name}': {', '.join(sugestoes[:3])}")
        except Exception as e:
            logger.debug(f"Erro ao buscar sugestões: {e}")
        
        return None

