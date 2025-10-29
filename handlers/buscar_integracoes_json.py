"""
Handler para buscar integrações do arquivo JSON
Estilo Nina - usa arquivo JSON estático ao invés de Google Sheets API
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

JSON_FILE = Path("knowledge/integracoes.json")

def carregar_integracoes_json():
    """Carrega integrações do arquivo JSON"""
    if not JSON_FILE.exists():
        logger.warning(f"Arquivo {JSON_FILE} não encontrado")
        return []
    
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        integracoes = dados.get("integracoes", [])
        logger.debug(f"✅ Carregadas {len(integracoes)} integrações do JSON")
        return integracoes
    except Exception as e:
        logger.error(f"❌ Erro ao carregar JSON: {e}")
        return []

def buscar_integracoes_json():
    """
    Lista todas as integrações (equivalente a buscar_integracoes_google_sheets_publico)
    Retorna string formatada para Slack
    """
    integracoes = carregar_integracoes_json()
    
    if not integracoes:
        return "📊 Nenhuma integração encontrada no arquivo JSON."
    
    resposta = "📊 *Integrações Disponíveis*\n\n"
    
    # Limitar a 50 para não ultrapassar limite do Slack
    integracoes_mostradas = integracoes[:50]
    
    for i, integ in enumerate(integracoes_mostradas, 1):
        resposta += f"*{i}. {integ['nome']}*"
        
        if integ.get('tipo'):
            resposta += f" | _{integ['tipo']}_"
        
        if integ.get('complexidade'):
            emoji_map = {
                "simples": "🟢", "baixa": "🟢",
                "média": "🟡", "medio": "🟡", "media": "🟡",
                "alta": "🔴", "complexa": "🔴"
            }
            emoji = "⚪"
            complexidade_lower = integ['complexidade'].lower()
            for key, em in emoji_map.items():
                if key in complexidade_lower:
                    emoji = em
                    break
            resposta += f" {emoji}"
        
        resposta += "\n"
        
        detalhes = []
        if integ.get('responsavel'):
            detalhes.append(f"👤 {integ['responsavel']}")
        if integ.get('status') and integ['status'].lower() not in ["ativo", "ativa", "sim", "yes", "disponivel", "disponível"]:
            detalhes.append(f"⚠️ {integ['status']}")
        
        if detalhes:
            resposta += f"   {' | '.join(detalhes)}\n"
        
        resposta += "\n"
    
    if len(integracoes) > 50:
        resposta += f"\n_... e mais {len(integracoes) - 50} integrações_\n"
    
    resposta += f"\n📊 *Total: {len(integracoes)} integrações*"
    resposta += f"\n💡 _Dados sincronizados do Google Sheets_"
    
    return resposta

def buscar_integracao_especifica_json(nome_integracao: str) -> Optional[str]:
    """
    Busca integração específica (equivalente a buscar_integracao_especifica_sheets_publico)
    
    Args:
        nome_integracao: Nome da integração a buscar
        
    Returns:
        String formatada ou None se não encontrar
    """
    integracoes = carregar_integracoes_json()
    
    if not integracoes:
        logger.warning("Nenhuma integração carregada do JSON")
        return None
    
    nome_lower = nome_integracao.lower()
    logger.info(f"🔍 Buscando integração: '{nome_integracao}'")
    
    # Buscar por match parcial no nome
    matches = []
    for integ in integracoes:
        if nome_lower in integ['nome'].lower():
            matches.append(integ)
    
    if not matches:
        logger.info(f"❌ Integração '{nome_integracao}' não encontrada")
        return None
    
    # Usar o primeiro match (ou melhor match se implementar scoring)
    integ = matches[0]
    
    logger.info(f"✅ Integração encontrada: {integ['nome']}")
    
    # Formatar resposta detalhada
    resposta = f"*📊 {integ['nome']}*\n\n"
    
    # Descrição
    if integ.get('descricao_longa'):
        resposta += f"{integ['descricao_longa']}\n\n"
    elif integ.get('descricao_curta'):
        resposta += f"{integ['descricao_curta']}\n\n"
    
    # Informações principais
    if integ.get('tipo'):
        resposta += f"*Tipo*: {integ['tipo']}\n"
    if integ.get('complexidade'):
        resposta += f"*Complexidade*: {integ['complexidade']}\n"
    if integ.get('responsavel'):
        resposta += f"*Responsável*: {integ['responsavel']}\n"
    if integ.get('status'):
        resposta += f"*Status*: {integ['status']}\n"
    
    # Funcionalidades
    if integ.get('funcionalidades'):
        resposta += f"\n*Funcionalidades*:\n"
        for func in integ['funcionalidades']:
            resposta += f"• {func}\n"
    
    # Link
    if integ.get('link'):
        resposta += f"\n🔗 *Link*: {integ['link']}\n"
    
    # Metadata adicional (campos extras que podem ser úteis)
    metadata_extra = integ.get('metadata', {})
    campos_interessantes = ['observacao', 'observação', 'detalhes', 'observacoes']
    for campo in campos_interessantes:
        if campo in metadata_extra and metadata_extra[campo]:
            resposta += f"\n*Observações*: {metadata_extra[campo]}\n"
            break
    
    return resposta

def formatar_json_para_contexto_gemini():
    """
    Formata o JSON para contexto do Gemini (estilo Nina)
    Retorna string formatada similar ao formatar_json_para_contexto da Nina
    """
    integracoes = carregar_integracoes_json()
    
    if not integracoes:
        return ""
    
    contexto = ""
    for integ in integracoes:
        contexto += f"Nome: {integ['nome']}\n"
        
        if integ.get('tipo'):
            contexto += f"Tipo: {integ['tipo']}\n"
        
        if integ.get('descricao_longa'):
            contexto += f"Detalhes: {integ['descricao_longa']}\n"
        elif integ.get('descricao_curta'):
            contexto += f"Detalhes: {integ['descricao_curta']}\n"
        
        if integ.get('funcionalidades'):
            contexto += f"Funcionalidades: {', '.join(integ['funcionalidades'])}\n"
        
        if integ.get('responsavel'):
            contexto += f"Responsável: {integ['responsavel']}\n"
        
        contexto += "\n"
    
    return contexto

