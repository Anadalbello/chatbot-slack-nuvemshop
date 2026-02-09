#!/usr/bin/env python3
"""
Script de Sincronização para Pinecone
Sincroniza integrações do JSON para o Pinecone Vector Database

Uso:
    python scripts/sync_to_pinecone.py
    
    # Sincronizar apenas namespace específico
    python scripts/sync_to_pinecone.py --namespace br
    
    # Forçar reindexação completa (deleta e recria)
    python scripts/sync_to_pinecone.py --force

Variáveis de Ambiente Necessárias:
    PINECONE_API_KEY: Chave API do Pinecone
    PINECONE_INDEX_NAME: Nome do índice Pinecone
    OPENAI_API_KEY: Chave API do OpenAI para embeddings
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pinecone_manager import create_manager_from_env, namespace_for_locale

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_integracoes_from_json(json_path: str) -> List[Dict]:
    """
    Carrega integrações do arquivo JSON
    
    Args:
        json_path: Caminho para o arquivo JSON
        
    Returns:
        Lista de dicionários de integrações
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Suportar diferentes formatos de JSON
        if isinstance(data, list):
            integracoes = data
        elif isinstance(data, dict):
            # Se for dict, tentar encontrar lista de integrações
            if 'integracoes' in data:
                integracoes = data['integracoes']
            elif 'erps' in data:
                integracoes = data['erps']
            else:
                # Assumir que o dict inteiro é uma integração
                integracoes = [data]
        else:
            raise ValueError(f"Formato JSON não suportado: {type(data)}")
        
        logger.info(f"✅ Carregadas {len(integracoes)} integrações do JSON")
        return integracoes
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar JSON: {e}")
        raise


def prepare_integracoes_for_pinecone(integracoes: List[Dict]) -> List[Dict]:
    """
    Prepara integrações para indexação no Pinecone
    
    Args:
        integracoes: Lista de integrações brutas
        
    Returns:
        Lista de integrações preparadas
    """
    prepared = []
    
    for i, integracao in enumerate(integracoes):
        # Normalizar campos (suportar diferentes nomes de campos)
        prepared_integracao = {
            "id": str(integracao.get("id", integracao.get("ID", f"integracao_{i}"))),
            "nome": integracao.get("nome", integracao.get("Nome", integracao.get("ERP", ""))),
            "descricao": integracao.get("descricao", integracao.get("Descrição", integracao.get("Descricao", ""))),
            "tipo": integracao.get("tipo", integracao.get("Tipo de Integração", integracao.get("Tipo", ""))),
            "fonte": "integracoes_json"
        }
        
        # Adicionar campos opcionais
        if "url" in integracao or "URL" in integracao:
            prepared_integracao["url"] = integracao.get("url", integracao.get("URL", ""))
        
        if "contato" in integracao or "Contato" in integracao:
            prepared_integracao["contato"] = integracao.get("contato", integracao.get("Contato", ""))
        
        # Adicionar funcionalidades se disponível
        if "funcionalidades" in integracao or "Funcionalidades" in integracao:
            funcionalidades = integracao.get("funcionalidades", integracao.get("Funcionalidades", ""))
            if funcionalidades:
                prepared_integracao["funcionalidades"] = str(funcionalidades)
        
        # Validar que tem pelo menos nome
        if prepared_integracao["nome"]:
            prepared.append(prepared_integracao)
        else:
            logger.warning(f"⚠️ Integração {i} sem nome, pulando...")
    
    logger.info(f"✅ Preparadas {len(prepared)} integrações para indexação")
    return prepared


def sync_to_pinecone(
    json_path: str,
    namespace: str = "br",
    force: bool = False
) -> bool:
    """
    Sincroniza integrações do JSON para Pinecone
    
    Args:
        json_path: Caminho para arquivo JSON
        namespace: Namespace Pinecone (br, ar, mx, etc.)
        force: Se True, deleta namespace antes de reindexar
        
    Returns:
        True se sincronização bem-sucedida
    """
    try:
        # Carregar integrações
        logger.info(f"📂 Carregando integrações de: {json_path}")
        integracoes = load_integracoes_from_json(json_path)
        
        if not integracoes:
            logger.warning("⚠️ Nenhuma integração encontrada no JSON")
            return False
        
        # Preparar integrações
        prepared = prepare_integracoes_for_pinecone(integracoes)
        
        if not prepared:
            logger.warning("⚠️ Nenhuma integração válida após preparação")
            return False
        
        # Inicializar Pinecone manager
        logger.info("🔌 Conectando ao Pinecone...")
        manager = create_manager_from_env()
        
        # Testar conexão
        if not manager.test_connection():
            logger.error("❌ Falha no teste de conexão com Pinecone")
            return False
        
        # Se force, deletar namespace existente
        if force:
            logger.warning(f"🗑️ Deletando namespace '{namespace}' (force=True)...")
            try:
                manager.delete_namespace(namespace, confirm=True)
                logger.info(f"✅ Namespace '{namespace}' deletado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao deletar namespace (pode não existir): {e}")
        
        # Indexar integrações
        logger.info(f"📤 Indexando {len(prepared)} integrações no namespace '{namespace}'...")
        upserted = manager.upsert_integracoes(prepared, namespace=namespace)
        
        logger.info(f"✅ Sincronização concluída: {upserted} integrações indexadas")
        
        # Obter estatísticas
        stats = manager.get_stats()
        namespace_stats = stats.get("namespaces", {}).get(namespace, {})
        logger.info(f"📊 Estatísticas do namespace '{namespace}': {namespace_stats.get('vector_count', 0)} vetores")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {e}", exc_info=True)
        return False


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Sincroniza integrações do JSON para Pinecone"
    )
    parser.add_argument(
        "--json",
        type=str,
        default="knowledge/integracoes.json",
        help="Caminho para arquivo JSON de integrações (padrão: knowledge/integracoes.json)"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="br",
        help="Namespace Pinecone (br, ar, mx, etc.) (padrão: br)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forçar reindexação completa (deleta namespace antes de indexar)"
    )
    parser.add_argument(
        "--locale",
        type=str,
        default="pt_BR",
        help="Locale para determinar namespace automaticamente (padrão: pt_BR)"
    )
    
    args = parser.parse_args()
    
    # Determinar namespace se não especificado explicitamente
    if args.namespace == "br" and args.locale:
        try:
            namespace = namespace_for_locale(args.locale)
            logger.info(f"🌍 Locale '{args.locale}' mapeado para namespace '{namespace}'")
        except ValueError:
            namespace = args.namespace
            logger.warning(f"⚠️ Locale '{args.locale}' não reconhecido, usando namespace padrão '{namespace}'")
    else:
        namespace = args.namespace
    
    # Verificar se arquivo existe
    json_path = Path(args.json)
    if not json_path.exists():
        logger.error(f"❌ Arquivo não encontrado: {json_path}")
        sys.exit(1)
    
    # Verificar variáveis de ambiente
    required_vars = ["PINECONE_API_KEY", "PINECONE_INDEX_NAME", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Executar sincronização
    logger.info("🚀 Iniciando sincronização para Pinecone...")
    success = sync_to_pinecone(
        json_path=str(json_path),
        namespace=namespace,
        force=args.force
    )
    
    if success:
        logger.info("✅ Sincronização concluída com sucesso!")
        sys.exit(0)
    else:
        logger.error("❌ Sincronização falhou")
        sys.exit(1)


if __name__ == "__main__":
    main()


