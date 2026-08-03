"""
Pinecone Vector Database Manager para Chatbot Tina

Este módulo fornece operações de banco de dados vetorial usando Pinecone com embeddings
do Google Gemini ou OpenAI para armazenar e recuperar informações sobre integrações.

Características principais:
- Geração de embeddings Google Gemini (text-embedding-004, 768 dimensões) ou OpenAI (text-embedding-3-small, 1536 dimensões)
- Armazenamento vetorial no Pinecone com separação por namespace
- Operações em lote para processamento eficiente
- Tratamento robusto de erros e lógica de retry
- Validação e criação automática de índices

Uso:
    # Inicializar a partir de variáveis de ambiente
    manager = create_manager_from_env()
    
    # Testar conectividade
    if manager.test_connection():
        print("Todos os serviços conectados com sucesso")
    
    # Indexar integrações
    integracoes = [{"id": "1", "nome": "Tiny", "descricao": "...", ...}]
    manager.upsert_integracoes(integracoes, namespace="br")
    
    # Buscar integrações similares
    results = manager.query_similar("Tiny ERP", top_k=5, namespace="br")
    
    # Obter estatísticas do índice
    stats = manager.get_stats()

Variáveis de Ambiente Necessárias:
    PINECONE_API_KEY: Chave API do Pinecone
    PINECONE_INDEX_NAME: Nome do índice Pinecone
    EMBEDDING_PROVIDER: "gemini" ou "openai" (padrão: "gemini")
    GEMINI_API_KEY: Chave API do Google Gemini (se provider=gemini)
    OPENAI_API_KEY: Chave API do OpenAI (se provider=openai)
    PINECONE_CLOUD: (opcional) Provedor de nuvem Pinecone, padrão "aws"
    PINECONE_REGION: (opcional) Região Pinecone, padrão "us-east-1"
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None
    ServerlessSpec = None

# Constantes do módulo
# Gemini embeddings
# text-embedding-004 foi removido da API (retornava 404). Migrado para
# gemini-embedding-001, pedindo saída em 768 dims (output_dimensionality)
# para manter compatibilidade com o índice Pinecone existente (768).
GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"
GEMINI_EMBEDDING_DIMENSION = 768

# OpenAI embeddings
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIMENSION = 1536
BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 2
PINECONE_METRIC = "cosine"
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"
EMBED_MAX_CHARS = 10000  # Máximo de caracteres para embedding

# Provider padrão
DEFAULT_EMBEDDING_PROVIDER = "gemini"  # Usar Gemini por padrão

logger = logging.getLogger(__name__)


class PineconeManagerError(Exception):
    """Exceção base para operações do Pinecone manager."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class EmbeddingGenerationError(PineconeManagerError):
    """Exceção levantada quando a geração de embedding falha."""
    pass


class PineconeConnectionError(PineconeManagerError):
    """Exceção levantada quando a conexão com Pinecone falha."""
    pass


class PineconeIndexError(PineconeManagerError):
    """Exceção levantada quando operações de índice falham."""
    pass


class PineconeManager:
    """
    Gerencia operações de banco de dados vetorial Pinecone com embeddings Gemini ou OpenAI.
    
    Esta classe fornece uma interface abrangente para operações de banco de dados vetorial
    incluindo gerenciamento de índices, geração de embeddings e busca semântica.
    """
    
    def __init__(
        self,
        api_key: str,
        index_name: str,
        embedding_provider: str = "gemini",
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        cloud: str = PINECONE_CLOUD,
        region: str = PINECONE_REGION
    ):
        """
        Inicializa o Pinecone manager.
        
        Args:
            api_key: Chave API do Pinecone
            index_name: Nome do índice Pinecone
            embedding_provider: "gemini" ou "openai" (padrão: "gemini")
            gemini_api_key: Chave API do Google Gemini (obrigatório se provider=gemini)
            openai_api_key: Chave API do OpenAI (obrigatório se provider=openai)
            cloud: Provedor de nuvem Pinecone (padrão: aws)
            region: Região Pinecone (padrão: us-east-1)
        """
        if not PINECONE_AVAILABLE:
            raise PineconeManagerError(
                "Biblioteca Pinecone não instalada. Execute: pip install pinecone-client"
            )
        
        self.api_key = api_key
        self.index_name = index_name
        self.embedding_provider = embedding_provider.lower()
        self.cloud = cloud
        self.region = region
        
        self.logger = logging.getLogger(__name__)
        self.pinecone_client = None
        self.index = None
        self.gemini_client = None
        self.openai_client = None
        
        # Configurar provider de embeddings
        if self.embedding_provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise PineconeManagerError(
                    "Biblioteca google-generativeai não instalada. Execute: pip install google-generativeai"
                )
            if not gemini_api_key:
                raise ValueError("gemini_api_key é obrigatório quando embedding_provider='gemini'")
            genai.configure(api_key=gemini_api_key)
            self.gemini_client = genai
            self.embedding_dimension = GEMINI_EMBEDDING_DIMENSION
            self.embedding_model = GEMINI_EMBEDDING_MODEL
            self.logger.info("✅ Usando Google Gemini para embeddings")
        elif self.embedding_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise PineconeManagerError(
                    "Biblioteca OpenAI não instalada. Execute: pip install openai"
                )
            if not openai_api_key:
                raise ValueError("openai_api_key é obrigatório quando embedding_provider='openai'")
            self.openai_api_key = openai_api_key
            self.embedding_dimension = OPENAI_EMBEDDING_DIMENSION
            self.embedding_model = OPENAI_EMBEDDING_MODEL
            self.logger.info("✅ Usando OpenAI para embeddings")
        else:
            raise ValueError(f"embedding_provider inválido: {embedding_provider}. Use 'gemini' ou 'openai'")
        
        # Log de inicialização com parâmetros sanitizados
        self.logger.info(
            f"Inicializado PineconeManager com índice '{index_name}', "
            f"provider '{self.embedding_provider}', dimensão {self.embedding_dimension}, "
            f"cloud '{cloud}', região '{region}'"
        )
    
    def _to_int(self, value: Any, default: int = 0) -> int:
        """
        Converte com segurança um valor para int, lidando com None, strings vazias e valores inválidos.
        
        Args:
            value: Valor para converter para int
            default: Valor padrão para retornar se a conversão falhar
            
        Returns:
            Valor inteiro ou padrão se a conversão falhar
        """
        if value is None or value == "":
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _init_openai_client(self):
        """Inicializa cliente OpenAI com lógica de retry."""
        if self.openai_client is not None:
            return self.openai_client
        
        if self.embedding_provider != "openai":
            raise ValueError("Tentativa de inicializar OpenAI client mas provider é Gemini")
        
        try:
            openai.api_key = self.openai_api_key
            self.openai_client = openai
            self.logger.info("Cliente OpenAI inicializado")
            return self.openai_client
        except Exception as e:
            raise EmbeddingGenerationError(
                f"Falha ao inicializar cliente OpenAI: {str(e)}",
                original_error=e
            )
    
    def _init_pinecone_client(self):
        """Inicializa cliente Pinecone com lógica de retry."""
        if self.pinecone_client is not None:
            return self.pinecone_client
        
        try:
            self.pinecone_client = Pinecone(api_key=self.api_key)
            self.logger.info("Cliente Pinecone inicializado")
            return self.pinecone_client
        except Exception as e:
            raise PineconeConnectionError(
                f"Falha ao inicializar cliente Pinecone: {str(e)}",
                original_error=e
            )
    
    def ensure_index(self):
        """
        Garante que o índice Pinecone existe com especificações corretas.
        
        Returns:
            O objeto de índice Pinecone
            
        Raises:
            PineconeIndexError: Se a validação do índice falhar
            PineconeConnectionError: Se a conexão com Pinecone falhar
        """
        self._init_pinecone_client()
        
        try:
            # Listar índices existentes
            index_names = self.pinecone_client.list_indexes().names()
            
            if self.index_name in index_names:
                # Índice existe, validar especificações
                index_info = self.pinecone_client.describe_index(self.index_name)
                
                if index_info.dimension != self.embedding_dimension:
                    raise PineconeIndexError(
                        f"Incompatibilidade de dimensão do índice: esperado {self.embedding_dimension}, "
                        f"encontrado {index_info.dimension}. "
                        f"O índice foi criado com dimensão diferente. "
                        f"Delete o índice e recrie ou use um índice compatível."
                    )
                
                if index_info.metric != PINECONE_METRIC:
                    raise PineconeIndexError(
                        f"Incompatibilidade de métrica do índice: esperado {PINECONE_METRIC}, "
                        f"encontrado {index_info.metric}"
                    )
                
                # Conectar ao índice existente
                self.index = self.pinecone_client.Index(self.index_name)
                self.logger.info(
                    f"Conectado ao índice existente '{self.index_name}' com "
                    f"{index_info.dimension} dimensões e métrica {index_info.metric}"
                )
            else:
                # Criar novo índice serverless
                self.logger.info(f"Índice '{self.index_name}' não encontrado, criando novo índice serverless...")
                
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dimension,
                    metric=PINECONE_METRIC,
                    spec=ServerlessSpec(cloud=self.cloud, region=self.region)
                )
                
                # Aguardar o índice estar pronto
                max_wait_time = 300  # 5 minutos
                wait_interval = 10
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    try:
                        index_info = self.pinecone_client.describe_index(self.index_name)
                        status = index_info.status
                        # Suportar tanto atributo quanto estilo dict para status
                        ready = status.ready if hasattr(status, 'ready') else status.get('ready', False)
                        if ready:
                            break
                    except Exception:
                        pass
                    
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
                
                if elapsed_time >= max_wait_time:
                    raise PineconeIndexError(f"Criação do índice expirou após {max_wait_time} segundos")
                
                # Conectar ao novo índice
                self.index = self.pinecone_client.Index(self.index_name)
                self.logger.info(f"Criado e conectado ao novo índice '{self.index_name}'")
            
            return self.index
            
        except Exception as e:
            if isinstance(e, PineconeIndexError):
                raise
            raise PineconeConnectionError(
                f"Falha ao garantir que o índice existe: {str(e)}",
                original_error=e
            )
    
    def test_connection(self) -> bool:
        """
        Testa conectividade com os serviços Pinecone e OpenAI.
        
        Returns:
            True se ambos os serviços estão acessíveis, False caso contrário
        """
        try:
            # Testar conexão Pinecone
            self.ensure_index()
            stats = self.index.describe_index_stats()
            self.logger.info("Teste de conexão Pinecone bem-sucedido")
            
            # Testar conexão de embeddings
            test_embedding = self.generate_embeddings(["teste"], task_type="retrieval_query")
            if len(test_embedding) == 1 and len(test_embedding[0]) == self.embedding_dimension:
                provider_name = "Gemini" if self.embedding_provider == "gemini" else "OpenAI"
                self.logger.info(f"Teste de conexão {provider_name} bem-sucedido")
                return True
            else:
                self.logger.error(
                    f"Teste de embedding {self.embedding_provider} falhou: forma de embedding inválida "
                    f"(esperado {self.embedding_dimension}, obtido {len(test_embedding[0])})"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Teste de conexão falhou: {str(e)}", exc_info=True)
            return False
    
    def generate_embeddings(
        self,
        texts: List[str],
        task_type: str = "retrieval_document"
    ) -> List[List[float]]:
        """
        Gera embeddings para uma lista de textos usando Gemini ou OpenAI.
        
        Args:
            texts: Lista de textos para embedar
            task_type: Tipo de tarefa ("retrieval_document" ou "retrieval_query")
        
        Returns:
            Lista de vetores de embedding
            
        Raises:
            EmbeddingGenerationError: Se a geração de embedding falhar
        """
        if task_type not in ["retrieval_document", "retrieval_query"]:
            raise ValueError(
                f"task_type inválido: {task_type}. Deve ser 'retrieval_document' ou 'retrieval_query'"
            )
        
        all_embeddings = []
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            for attempt in range(MAX_RETRIES):
                try:
                    if self.embedding_provider == "gemini":
                        # Usar Gemini para embeddings
                        batch_embeddings = []
                        for text in batch_texts:
                            # Truncar se necessário
                            if len(text) > EMBED_MAX_CHARS:
                                text = text[:EMBED_MAX_CHARS]
                            
                            # Usar o modelo de embedding do Gemini
                            # O embed_content retorna um objeto com atributo 'embedding'
                            result = self.gemini_client.embed_content(
                                model=self.embedding_model,
                                content=text,
                                task_type=task_type,
                                # gemini-embedding-001 gera 3072 dims por padrão;
                                # truncar para 768 mantém o índice Pinecone atual.
                                output_dimensionality=self.embedding_dimension
                            )
                            
                            # Extrair embedding do resultado
                            # O resultado pode ser um objeto com atributo 'embedding' ou dict
                            if hasattr(result, 'embedding'):
                                embedding = result.embedding
                            elif isinstance(result, dict):
                                embedding = result.get('embedding')
                            else:
                                # Tentar acessar como atributo
                                embedding = getattr(result, 'embedding', None)
                            
                            if embedding is None:
                                raise EmbeddingGenerationError(
                                    f"Não foi possível extrair embedding do resultado Gemini. "
                                    f"Tipo do resultado: {type(result)}, "
                                    f"Atributos disponíveis: {dir(result) if hasattr(result, '__dict__') else 'N/A'}"
                                )
                            
                            batch_embeddings.append(embedding)
                        
                    elif self.embedding_provider == "openai":
                        # Usar OpenAI para embeddings
                        self._init_openai_client()
                        response = self.openai_client.embeddings.create(
                            model=self.embedding_model,
                            input=batch_texts,
                            dimensions=self.embedding_dimension
                        )
                        batch_embeddings = [item.embedding for item in response.data]
                    else:
                        raise ValueError(f"Provider de embedding desconhecido: {self.embedding_provider}")
                    
                    if not batch_embeddings or len(batch_embeddings) != len(batch_texts):
                        raise EmbeddingGenerationError(
                            f"Número inesperado de embeddings retornados: {len(batch_embeddings)}"
                        )
                    
                    # Validar dimensão
                    for emb in batch_embeddings:
                        if len(emb) != self.embedding_dimension:
                            raise EmbeddingGenerationError(
                                f"Dimensão de embedding incorreta: esperado {self.embedding_dimension}, "
                                f"obtido {len(emb)}"
                            )
                    
                    all_embeddings.extend(batch_embeddings)
                    self.logger.debug(
                        f"Gerados embeddings para lote {batch_num}/{total_batches} "
                        f"(provider: {self.embedding_provider})"
                    )
                    break
                    
                except Exception as e:
                    if attempt == MAX_RETRIES - 1:
                        raise EmbeddingGenerationError(
                            f"Falha ao gerar embeddings para lote {batch_num} após {MAX_RETRIES} tentativas: {str(e)}",
                            original_error=e
                        )
                    else:
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        self.logger.warning(
                            f"Geração de embedding falhou para lote {batch_num}, "
                            f"tentando novamente em {wait_time}s: {str(e)}"
                        )
                        time.sleep(wait_time)
            
            # Pequeno atraso entre lotes para evitar rate limiting
            if i + BATCH_SIZE < len(texts):
                time.sleep(0.5)
        
        self.logger.info(
            f"Gerados embeddings para {len(texts)} textos em {total_batches} lotes "
            f"(provider: {self.embedding_provider})"
        )
        return all_embeddings
    
    def upsert_integracoes(self, integracoes: List[Dict], namespace: str) -> int:
        """
        Faz upsert de integrações no Pinecone com embeddings e metadata.
        
        Args:
            integracoes: Lista de dicionários de integrações
            namespace: Namespace Pinecone para as integrações
            
        Returns:
            Número de integrações upsertadas com sucesso
            
        Raises:
            PineconeManagerError: Se a operação de upsert falhar
        """
        self.ensure_index()
        
        # Validar campos obrigatórios
        required_fields = ["id", "nome"]
        for i, integracao in enumerate(integracoes):
            missing_fields = [field for field in required_fields if field not in integracao]
            if missing_fields:
                raise ValueError(f"Integração {i} faltando campos obrigatórios: {missing_fields}")
        
        # Preparar textos para embedding
        texts = []
        for integracao in integracoes:
            # Combinar nome e descrição para embedding mais rico
            nome = integracao.get("nome", integracao.get("Nome", integracao.get("ERP", "")))
            descricao = integracao.get("descricao", integracao.get("Descrição", integracao.get("Descricao", "")))
            tipo = integracao.get("tipo", integracao.get("Tipo de Integração", ""))
            funcionalidades = integracao.get("funcionalidades", integracao.get("Funcionalidades", ""))
            
            # Combinar todos os campos relevantes (inclui outros nomes para ex.: WordPress -> Woocommerce)
            combined_text = f"{nome}"
            if descricao:
                combined_text += f"\n\n{descricao}"
            if tipo:
                combined_text += f"\n\nTipo: {tipo}"
            if funcionalidades:
                combined_text += f"\n\nFuncionalidades: {funcionalidades}"
            outros_nomes = integracao.get("outros_nomes", "")
            if outros_nomes:
                combined_text += f"\n\nOutros nomes: {outros_nomes}"
            
            # Truncar se exceder comprimento máximo
            if len(combined_text) > EMBED_MAX_CHARS:
                combined_text = combined_text[:EMBED_MAX_CHARS]
                self.logger.warning(
                    f"Conteúdo da integração {integracao.get('id')} truncado para {EMBED_MAX_CHARS} caracteres"
                )
            texts.append(combined_text)
        
        # Gerar embeddings
        embeddings = self.generate_embeddings(texts, task_type="retrieval_document")
        
        # Preparar vetores para Pinecone
        vectors = []
        for i, (integracao, embedding) in enumerate(zip(integracoes, embeddings)):
            # Preparar metadata
            nome = integracao.get("nome", integracao.get("Nome", integracao.get("ERP", "")))
            descricao = integracao.get("descricao", integracao.get("Descrição", integracao.get("Descricao", "")))
            
            # Truncar descrição para metadata (limite Pinecone: 40KB por metadata)
            descricao_metadata = str(descricao) if descricao else ""
            if len(descricao_metadata) > 3500:
                truncated = descricao_metadata[:3500]
                last_period = truncated.rfind('.')
                if last_period > 3000:
                    descricao_metadata = truncated[:last_period+1]
                else:
                    descricao_metadata = truncated + "..."
            
            metadata = {
                "nome": str(nome)[:500],  # Truncar para 500 caracteres
                "id": str(integracao.get("id", integracao.get("ID", ""))),
                "tipo": str(integracao.get("tipo", integracao.get("Tipo de Integração", "")))[:200],
                "descricao": descricao_metadata,
                "fonte": str(integracao.get("fonte", "integracoes_json"))[:100]
            }
            
            # Adicionar campos opcionais se disponíveis
            if "url" in integracao or "URL" in integracao:
                metadata["url"] = str(integracao.get("url", integracao.get("URL", "")))
            if "contato" in integracao or "Contato" in integracao:
                metadata["contato"] = str(integracao.get("contato", integracao.get("Contato", "")))[:500]
            
            vectors.append({
                "id": str(integracao.get("id", integracao.get("ID", f"integracao_{i}"))),
                "values": embedding,
                "metadata": metadata
            })
        
        # Upsert em lotes
        upserted_count = 0
        batch_size = 100
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            
            try:
                self.index.upsert(vectors=batch, namespace=namespace)
                upserted_count += len(batch)
                self.logger.debug(f"Upserted lote de {len(batch)} vetores no namespace '{namespace}'")
                
                # Pequeno atraso entre lotes
                if i + batch_size < len(vectors):
                    time.sleep(0.3)
                    
            except Exception as e:
                self.logger.error(f"Falha ao fazer upsert do lote: {str(e)}", exc_info=True)
                # Continuar com próximo lote
        
        self.logger.info(f"Upserted {upserted_count} integrações no namespace '{namespace}'")
        return upserted_count
    
    def query_similar(
        self,
        query_text: str,
        top_k: int = 5,
        namespace: str = None,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Busca integrações similares usando busca semântica.
        
        Args:
            query_text: Texto para buscar
            top_k: Número de integrações similares para retornar
            namespace: Namespace Pinecone para buscar
            filter_dict: Filtro opcional de metadata
            
        Returns:
            Lista de integrações similares com scores e metadata
            
        Raises:
            PineconeManagerError: Se a operação de query falhar
        """
        self.ensure_index()
        
        # Gerar embedding da query
        query_embedding = self.generate_embeddings([query_text], task_type="retrieval_query")[0]
        
        try:
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Parsear resultados
            matches = []
            for match in results.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                })
            
            max_score = max([m["score"] for m in matches]) if matches else 0
            self.logger.info(
                f"Encontradas {len(matches)} integrações similares para query no namespace '{namespace}' "
                f"(score máximo: {max_score:.4f})"
            )
            
            return matches
            
        except Exception as e:
            raise PineconeManagerError(
                f"Falha ao buscar integrações similares: {str(e)}",
                original_error=e
            )
    
    def delete_integracoes(self, integracao_ids: List[str], namespace: str) -> int:
        """
        Deleta integrações por seus IDs de um namespace.
        
        Args:
            integracao_ids: Lista de IDs de integrações para deletar
            namespace: Namespace Pinecone
            
        Returns:
            Número de integrações deletadas
        """
        self.ensure_index()
        
        deleted_count = 0
        batch_size = 1000  # Limite Pinecone
        
        for i in range(0, len(integracao_ids), batch_size):
            batch_ids = integracao_ids[i:i + batch_size]
            
            try:
                self.index.delete(ids=batch_ids, namespace=namespace)
                deleted_count += len(batch_ids)
                self.logger.debug(f"Deletado lote de {len(batch_ids)} integrações do namespace '{namespace}'")
                
            except Exception as e:
                self.logger.error(f"Falha ao deletar lote: {str(e)}", exc_info=True)
        
        self.logger.info(f"Deletadas {deleted_count} integrações do namespace '{namespace}'")
        return deleted_count
    
    def delete_namespace(self, namespace: str, confirm: bool = False) -> None:
        """
        Deleta todas as integrações em um namespace.
        
        Args:
            namespace: Namespace para deletar
            confirm: Deve ser True para confirmar deleção
            
        Raises:
            ValueError: Se confirm não for True
        """
        if not confirm:
            raise ValueError("Deleção de namespace requer confirmação explícita")
        
        self.ensure_index()
        
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            self.logger.warning(f"Deletadas todas as integrações do namespace '{namespace}'")
        except Exception as e:
            raise PineconeManagerError(
                f"Falha ao deletar namespace '{namespace}': {str(e)}",
                original_error=e
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do índice.
        
        Returns:
            Dicionário com estatísticas do índice
        """
        self.ensure_index()
        
        try:
            stats = self.index.describe_index_stats()
            
            result = {
                "total_vector_count": stats["total_vector_count"],
                "dimension": stats["dimension"],
                "namespaces": {}
            }
            
            # Parsear estatísticas de namespaces
            for ns_name, ns_stats in stats.get("namespaces", {}).items():
                result["namespaces"][ns_name] = {
                    "vector_count": ns_stats["vector_count"]
                }
            
            self.logger.info(
                f"Estatísticas do índice: {result['total_vector_count']} vetores totais, "
                f"{len(result['namespaces'])} namespaces"
            )
            
            return result
            
        except Exception as e:
            raise PineconeManagerError(
                f"Falha ao obter estatísticas do índice: {str(e)}",
                original_error=e
            )


def create_manager_from_env() -> PineconeManager:
    """
    Cria instância PineconeManager a partir de variáveis de ambiente.
    
    Returns:
        Instância PineconeManager configurada
        
    Raises:
        ValueError: Se variáveis de ambiente obrigatórias estiverem faltando
    """
    # Ler variáveis de ambiente obrigatórias
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
    
    if not pinecone_api_key:
        raise ValueError("Variável de ambiente PINECONE_API_KEY é obrigatória")
    if not pinecone_index_name:
        raise ValueError("Variável de ambiente PINECONE_INDEX_NAME é obrigatória")
    
    # Determinar provider de embeddings
    embedding_provider = os.getenv("EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER).lower()
    
    gemini_api_key = None
    openai_api_key = None
    
    if embedding_provider == "gemini":
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError(
                "Variável de ambiente GEMINI_API_KEY é obrigatória quando EMBEDDING_PROVIDER=gemini"
            )
    elif embedding_provider == "openai":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "Variável de ambiente OPENAI_API_KEY é obrigatória quando EMBEDDING_PROVIDER=openai"
            )
    else:
        raise ValueError(
            f"EMBEDDING_PROVIDER inválido: {embedding_provider}. Use 'gemini' ou 'openai'"
        )
    
    # Ler variáveis de ambiente opcionais
    pinecone_cloud = os.getenv("PINECONE_CLOUD", PINECONE_CLOUD)
    pinecone_region = os.getenv("PINECONE_REGION", PINECONE_REGION)
    
    manager = PineconeManager(
        api_key=pinecone_api_key,
        index_name=pinecone_index_name,
        embedding_provider=embedding_provider,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        cloud=pinecone_cloud,
        region=pinecone_region
    )
    
    logging.getLogger(__name__).info(
        f"Criado PineconeManager a partir de variáveis de ambiente (provider: {embedding_provider})"
    )
    return manager


def namespace_for_locale(locale: str) -> str:
    """
    Mapeia locale para namespace Pinecone.
    Cada país/locale obtém seu próprio namespace para separação adequada.
    
    Args:
        locale: String de locale (ex: 'pt_BR', 'es_ES', 'es_MX', 'es_AR', 'es_CO', 'BR', 'AR', 'MX', 'CO')
        
    Returns:
        String de namespace ('br' para Brasil, 'ar' para Argentina, 'mx' para México, etc.)
        
    Raises:
        ValueError: Se locale não for suportado
    """
    locale_lower = locale.lower()
    
    # Brasil (português)
    if locale_lower in ["pt_br", "br", "pt"]:
        return "br"
    # Argentina
    elif locale_lower in ["es_ar", "ar"]:
        return "ar"
    # México
    elif locale_lower in ["es_mx", "mx"]:
        return "mx"
    # Colombia
    elif locale_lower in ["es_co", "co"]:
        return "co"
    # Chile
    elif locale_lower in ["es_cl", "cl"]:
        return "cl"
    # Espanha
    elif locale_lower in ["es_es", "es"]:
        return "es"
    else:
        raise ValueError(
            f"Locale não suportado: {locale}. Locales suportados: "
            "pt_BR, es_ES, es_MX, es_AR, es_CO, es_CL, BR, ES, MX, AR, CO, CL"
        )

