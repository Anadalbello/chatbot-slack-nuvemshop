"""
Handler para buscar integrações do arquivo JSON
NOVO FORMATO: Lista direta de ERPs com Funcionalidades e Outras_Informacoes
"""

import json
import logging
from pathlib import Path
from typing import Optional, List
import re

logger = logging.getLogger(__name__)

JSON_FILE = Path("knowledge/integracoes.json")

def carregar_integracoes_json() -> List[dict]:
    """Carrega ERPs do arquivo JSON (novo formato)"""
    if not JSON_FILE.exists():
        logger.warning(f"Arquivo {JSON_FILE} não encontrado")
        return []
    
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # O JSON agora é uma lista direta de ERPs
        if isinstance(dados, list):
            erps = dados
        else:
            # Fallback para formato antigo se necessário
            erps = dados.get("integracoes", [])
        
        logger.debug(f"✅ Carregados {len(erps)} ERPs do JSON")
        return erps
    except Exception as e:
        logger.error(f"❌ Erro ao carregar JSON: {e}")
        return []

def buscar_integracoes_json() -> str:
    """
    Lista todas as integrações (ERPs)
    Retorna string formatada para Slack
    """
    erps = carregar_integracoes_json()
    
    if not erps:
        return "📊 Nenhum ERP encontrado no arquivo JSON."
    
    resposta = "📊 *ERPs Disponíveis*\n\n"
    
    # Limitar a 50 para não ultrapassar limite do Slack
    erps_mostrados = erps[:50]
    
    for i, erp in enumerate(erps_mostrados, 1):
        nome_erp = erp.get("Nome", erp.get("ERP", "Nome não informado"))
        resposta += f"*{i}. {nome_erp}*"
        
        # Adicionar complexidade se disponível
        outras_info = erp.get("Outras_Informacoes", {})
        complexidade = outras_info.get("Complexidade", "")
        if complexidade:
            emoji_map = {
                "simples": "🟢", "baixa": "🟢",
                "média": "🟡", "medio": "🟡", "media": "🟡",
                "alta": "🔴", "complexa": "🔴"
            }
            emoji = "⚪"
            complexidade_lower = complexidade.lower()
            for key, em in emoji_map.items():
                if key in complexidade_lower:
                    emoji = em
                    break
            resposta += f" {emoji}"
        
        resposta += "\n"
        
        # Adicionar informações básicas
        detalhes = []
        responsavel_config = outras_info.get("Responsavel_Configuracao", "")
        if responsavel_config:
            detalhes.append(f"⚙️ Config: {responsavel_config}")
        
        if detalhes:
            resposta += f"   {' | '.join(detalhes)}\n"
        
        resposta += "\n"
    
    if len(erps) > 50:
        resposta += f"\n_... e mais {len(erps) - 50} ERPs_\n"
    
    resposta += f"\n📊 *Total: {len(erps)} ERPs*"
    
    return resposta

def buscar_integracao_especifica_json(nome_erp: str) -> Optional[str]:
    """
    Busca ERP específico pelo nome
    
    Args:
        nome_erp: Nome do ERP a buscar
        
    Returns:
        String formatada ou None se não encontrar
    """
    erps = carregar_integracoes_json()
    
    if not erps:
        logger.warning("Nenhum ERP carregado do JSON")
        return None
    
    nome_lower = nome_erp.lower().strip()
    logger.info(f"🔍 Buscando ERP: '{nome_erp}'")
    
    # Extrair palavras-chave da query (remover palavras comuns)
    palavras_remover = {"temos", "tenho", "integração", "integracao", "com", "a", "o", "da", "do", "de", "para", "em", 
                        "qual", "quais", "sobre", "tem", "tem o", "tem a", "funcionalidades", "funcionalidade", "como", "funciona"}
    palavras_query = set([p for p in nome_lower.split() if p not in palavras_remover and len(p) > 2])
    
    # Buscar por match: verificar se nome do ERP está na query OU se palavras-chave estão no nome do ERP
    matches = []
    for erp in erps:
        nome_erp_atual = erp.get("Nome", erp.get("ERP", "")).lower()
        # Busca parcial e também remove parênteses para busca mais flexível
        nome_limpo = re.sub(r'\s*\(.*?\)', '', nome_erp_atual)
        palavras_nome = set(nome_limpo.split())
        
        # Verificar se o nome do ERP está contido na query (busca invertida)
        # Ex: query="quais funcionalidades tem o eccosys" -> nome="eccosys" deve ser encontrado
        if nome_limpo in nome_lower or any(palavra in nome_lower for palavra in palavras_nome if len(palavra) > 2):
            matches.append(erp)
        # Verificar se palavras da query estão no nome do ERP
        elif palavras_query and palavras_query.intersection(palavras_nome):
            matches.append(erp)
    
    if not matches:
        logger.info(f"❌ ERP '{nome_erp}' não encontrado")
        return None
    
    # Usar o primeiro match (melhor match seria implementar scoring)
    erp = matches[0]
    nome_erp_encontrado = erp.get("Nome", erp.get("ERP", "Nome não informado"))
    
    logger.info(f"✅ ERP encontrado: {nome_erp_encontrado}")
    
    # Formatar resposta detalhada
    resposta = f"*📊 {nome_erp_encontrado}*\n\n"
    
    # Categoria e Tipo de Integração (se disponíveis)
    categoria = erp.get("Categoria", "")
    tipo_integracao = erp.get("Tipo_Integracao", "")
    if categoria:
        resposta += f"*Categoria*: {categoria}\n"
    if tipo_integracao:
        resposta += f"*Tipo de Integração*: {tipo_integracao}\n"
    if categoria or tipo_integracao:
        resposta += "\n"
    
    # Funcionalidades
    funcionalidades = erp.get("Funcionalidades", {})
    if funcionalidades:
        resposta += "*Funcionalidades:*\n"
        for func_nome, func_valor in funcionalidades.items():
            # Formatar nome da funcionalidade (remover underscores)
            func_nome_formatado = func_nome.replace("_", " ").title()
            resposta += f"• *{func_nome_formatado}*: {func_valor}\n"
        resposta += "\n"
    
    # Outras Informações
    outras_info = erp.get("Outras_Informacoes", {})
    if outras_info:
        resposta += "*Outras Informações:*\n"
        
        # Complexidade
        complexidade = outras_info.get("Complexidade", "")
        if complexidade:
            resposta += f"• *Complexidade*: {complexidade}\n"
        
        # Responsáveis
        responsavel_config = outras_info.get("Responsavel_Configuracao", "")
        if responsavel_config:
            resposta += f"• *Responsável pela Configuração*: {responsavel_config}\n"
        
        responsavel_testes = outras_info.get("Responsavel_Testes", "")
        if responsavel_testes:
            resposta += f"• *Responsável pelos Testes*: {responsavel_testes}\n"
        
        desenvolvedor = outras_info.get("Desenvolvedor_Integracao", "")
        if desenvolvedor:
            resposta += f"• *Desenvolvedor da Integração*: {desenvolvedor}\n"
        
        # Custos
        custos = outras_info.get("Custos_Envolvidos", "")
        if custos:
            resposta += f"• *Custos Envolvidos*: {custos}\n"
        
        # Limitações
        limitacoes = outras_info.get("Limitacoes_Ausencia", "")
        if limitacoes and limitacoes.lower() not in ["nada consta.", "nada consta", ""]:
            resposta += f"• *Limitações/Ausências*: {limitacoes}\n"
        
        # Site
        site = outras_info.get("Site", "")
        if site and site.lower() not in ["não informado.", "não informado"]:
            resposta += f"• *Site*: {site}\n"
        
        # Manual
        manual = outras_info.get("Manual", "")
        if manual:
            resposta += f"• *Manual*: {manual}\n"
    
    # Suporte e Contato (se disponível)
    suporte = erp.get("Suporte_Contato", {})
    if suporte:
        resposta += "\n*Suporte/Contato:*\n"
        email = suporte.get("Email", "")
        telefone = suporte.get("Telefone", "")
        if email and email != "N/A":
            resposta += f"• *Email*: {email}\n"
        if telefone and telefone != "N/A":
            resposta += f"• *Telefone*: {telefone}\n"
    
    return resposta

def buscar_erp_generico(query: str) -> Optional[str]:
    """
    Busca genérica em ERPs - função para uso do KnowledgeManager
    Busca pelo nome do ERP ou por termos relacionados às funcionalidades
    
    Args:
        query: Termo de busca genérico
        
    Returns:
        String formatada ou None se não encontrar
    """
    erps = carregar_integracoes_json()
    
    if not erps:
        return None
    
    query_lower = query.lower().strip()
    logger.info(f"🔍 Busca genérica: '{query}'")
    
    # Lista de palavras comuns a ignorar
    palavras_ignorar = {"temos", "tenho", "integração", "integracao", "com", "a", "o", "da", "do", "de", "para", "em", 
                        "qual", "quais", "sobre", "tem", "tem o", "tem a", "funcionalidades", "funcionalidade", "como", "funciona"}
    palavras_query = set([p for p in query_lower.split() if p not in palavras_ignorar and len(p) > 2])
    
    matches = []
    scores = []
    
    for erp in erps:
        nome_erp = erp.get("Nome", erp.get("ERP", "")).lower()
        nome_limpo = re.sub(r'\s*\(.*?\)', '', nome_erp)
        palavras_nome = set(nome_limpo.split())
        
        score = 0
        
        # Busca invertida: verificar se o nome do ERP está na query (maior pontuação)
        # Ex: query="quais funcionalidades tem o eccosys" -> nome="eccosys" deve ser encontrado
        if nome_limpo in query_lower or any(palavra in query_lower for palavra in palavras_nome if len(palavra) > 2):
            score = 100
        # Busca por palavras-chave: verificar se palavras da query estão no nome do ERP
        elif palavras_query and palavras_query.intersection(palavras_nome):
            score = 90
        
        # Buscar em funcionalidades
        funcionalidades = erp.get("Funcionalidades", {})
        for func_nome, func_valor in funcionalidades.items():
            func_texto = (func_nome + " " + str(func_valor)).lower()
            if query_lower in func_texto:
                score = max(score, 60)
            elif any(palavra in func_texto for palavra in palavras_query):
                score = max(score, 40)
        
        # Buscar em outras informações
        outras_info = erp.get("Outras_Informacoes", {})
        for chave, valor in outras_info.items():
            info_texto = (chave + " " + str(valor)).lower()
            if query_lower in info_texto:
                score = max(score, 50)
            elif any(palavra in info_texto for palavra in palavras_query):
                score = max(score, 30)
        
        if score > 0:
            matches.append(erp)
            scores.append(score)
    
    # Ordenar por score (maior primeiro)
    if matches:
        matches_ordenados = [m for _, m in sorted(zip(scores, matches), reverse=True)]
        # Retornar apenas o melhor match
        erp_encontrado = matches_ordenados[0]
        nome_erp = erp_encontrado.get("Nome", erp_encontrado.get("ERP", ""))
        return buscar_integracao_especifica_json(nome_erp)
    
    logger.info(f"❌ Nenhum resultado encontrado para: '{query}'")
    return None

def formatar_json_para_contexto_gemini() -> str:
    """
    Formata o JSON para contexto do Gemini (estilo Nina)
    Retorna string formatada com todas as informações dos ERPs
    """
    erps = carregar_integracoes_json()
    
    if not erps:
        return ""
    
    contexto = ""
    for erp in erps:
        nome_erp = erp.get("Nome", erp.get("ERP", "Nome não informado"))
        categoria = erp.get("Categoria", "")
        tipo_integracao = erp.get("Tipo_Integracao", "")
        contexto += f"Nome: {nome_erp}\n"
        if categoria:
            contexto += f"Categoria: {categoria}\n"
        if tipo_integracao:
            contexto += f"Tipo de Integração: {tipo_integracao}\n"
        
        # Funcionalidades
        funcionalidades = erp.get("Funcionalidades", {})
        if funcionalidades:
            contexto += "Funcionalidades:\n"
            for func_nome, func_valor in funcionalidades.items():
                func_nome_formatado = func_nome.replace("_", " ")
                contexto += f"  - {func_nome_formatado}: {func_valor}\n"
        
        # Outras Informações
        outras_info = erp.get("Outras_Informacoes", {})
        if outras_info:
            contexto += "Outras Informações:\n"
            for chave, valor in outras_info.items():
                chave_formatada = chave.replace("_", " ")
                contexto += f"  - {chave_formatada}: {valor}\n"
        
        contexto += "\n"
    
    return contexto
