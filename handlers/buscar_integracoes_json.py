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
        return "📊 Nenhuma integração encontrada no arquivo JSON."
    
    resposta = "📊 *Integrações Disponíveis*\n\n"
    
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
        
        # Adicionar informações básicas - Categoria e Tipo
        detalhes = []
        categoria = erp.get("Categoria", "")
        tipo_integracao = erp.get("Tipo_Integracao", "")
        if categoria:
            detalhes.append(f"📂 {categoria}")
        if tipo_integracao:
            detalhes.append(f"🔧 {tipo_integracao}")
        
        if detalhes:
            resposta += f"   {' | '.join(detalhes)}\n"
        
        resposta += "\n"
    
    if len(erps) > 50:
        resposta += f"\n_... e mais {len(erps) - 50} integrações_\n"
    
    resposta += f"\n📊 *Total: {len(erps)} integrações*"
    
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
    
    # Limpar query: remover pontuação e normalizar
    nome_limpo_query = re.sub(r'[?.,!;:]+', '', nome_erp.lower().strip())
    logger.info(f"🔍 Buscando ERP: '{nome_erp}'")
    
    # Lista expandida de palavras comuns a remover (stopwords em português)
    palavras_remover = {
        # Artigos e preposições
        "a", "o", "as", "os", "da", "do", "das", "dos", "de", "em", "na", "no", "nas", "nos", "para", "por", "com", "sem",
        # Pronomes
        "me", "te", "se", "nos", "vos", "lhe", "lhes", "que", "qual", "quais", "quem", "onde", "quando",
        # Verbos comuns
        "pode", "posso", "pode", "podem", "quer", "quero", "quer", "querem", "tem", "tenho", "tem", "têm",
        "fazer", "faço", "faz", "fazem", "estar", "estou", "está", "estão", "ser", "sou", "é", "são",
        "ter", "dar", "dá", "dão", "passar", "passa", "mostrar", "mostra", "ver", "vê", "conseguir", "consegue",
        # Palavras relacionadas a integrações
        "integração", "integracao", "integracoes", "integrações", "erp", "erps", "plataforma", "ferramenta",
        # Perguntas e pedidos
        "sobre", "acerca", "dados", "dado", "informações", "informacao", "info", "contato", "contatos", "contato",
        "como", "qual", "quais", "quando", "onde", "porque", "por que", "funciona", "funcionalidades", "funcionalidade",
        "preciso", "precisamos", "gostaria", "gostaríamos", "quero", "queremos"
    }
    
    # Extrair palavras-chave da query (remover palavras comuns e pontuação)
    palavras_query = set([p.strip('?.,!;:') for p in nome_limpo_query.split() 
                          if p.strip('?.,!;:') not in palavras_remover and len(p.strip('?.,!;:')) > 2])
    
    logger.debug(f"📝 Palavras extraídas da query: {palavras_query}")
    
    # Buscar por match: verificar se nome do ERP está na query OU se palavras-chave estão no nome do ERP
    matches = []
    for erp in erps:
        nome_erp_atual = erp.get("Nome", erp.get("ERP", "")).lower()
        # Busca parcial e também remove parênteses para busca mais flexível
        nome_limpo = re.sub(r'\s*\(.*?\)', '', nome_erp_atual)
        palavras_nome = set(nome_limpo.split())
        
        # ESTRATÉGIA 1: Verificar se o nome completo do ERP está contido na query (maior prioridade)
        # Ex: query="dados de contato da bling" -> nome="bling" deve ser encontrado
        if nome_limpo in nome_limpo_query:
            matches.append(erp)
            logger.debug(f"✅ Match por nome completo: '{nome_limpo}' encontrado na query")
            continue
        
        # ESTRATÉGIA 2: Verificar se qualquer palavra significativa do nome está na query (busca invertida)
        # Ex: query="quais funcionalidades tem o eccosys" -> nome="eccosys" deve ser encontrado
        palavras_significativas_nome = [p for p in palavras_nome if len(p) > 2 and p not in palavras_remover]
        if palavras_significativas_nome:
            for palavra_nome in palavras_significativas_nome:
                if palavra_nome in nome_limpo_query:
                    matches.append(erp)
                    logger.debug(f"✅ Match por palavra do nome: '{palavra_nome}' encontrado na query")
                    break
        
        # ESTRATÉGIA 3: Verificar se palavras-chave extraídas da query estão no nome do ERP
        # Ex: query="contato bling" -> palavras_query={"bling"} -> nome="bling" deve ser encontrado
        if palavras_query and palavras_query.intersection(palavras_nome):
            matches.append(erp)
            logger.debug(f"✅ Match por interseção: palavras {palavras_query.intersection(palavras_nome)} encontradas no nome '{nome_limpo}'")
    
    if not matches:
        logger.info(f"❌ ERP '{nome_erp}' não encontrado")
        return None
    
    # Usar o primeiro match (melhor match seria implementar scoring)
    erp = matches[0]
    nome_erp_encontrado = erp.get("Nome", erp.get("ERP", "Nome não informado"))
    
    logger.info(f"✅ ERP encontrado: {nome_erp_encontrado}")
    
    # Formatar resposta detalhada - mais visual e organizada
    resposta = f"✨ *{nome_erp_encontrado}*\n"
    
    # Categoria e Tipo de Integração (se disponíveis)
    categoria = erp.get("Categoria", "")
    tipo_integracao = erp.get("Tipo_Integracao", "")
    if categoria or tipo_integracao:
        resposta += f"📂 {categoria}" if categoria else ""
        resposta += f" | 🔧 {tipo_integracao}" if tipo_integracao else ""
        resposta += "\n\n"
    
    # Funcionalidades com emojis mais descritivos
    funcionalidades = erp.get("Funcionalidades", {})
    if funcionalidades:
        # Mapeamento de emojis por funcionalidade
        emoji_map = {
            "Calculo_de_Frete": "🚚",
            "Multiplos_Volumes_Pedidos": "📦",
            "Configuracao_Seguro_Pedidos": "🛡️",
            "Multi_CD": "🏢",
            "Impressao_Etiqueta": "🏷️",
            "Atualiza_Status_Rastreio": "🔄"
        }
        
        # Separar funcionalidades disponíveis e indisponíveis
        func_disponiveis = []
        func_indisponiveis = []
        
        for func_nome, func_valor in funcionalidades.items():
            emoji = emoji_map.get(func_nome, "•")
            func_nome_formatado = func_nome.replace("_", " ").title()
            func_info = f"{emoji} *{func_nome_formatado}*: {func_valor}"
            
            if "✔️" in str(func_valor):
                func_disponiveis.append(func_info)
            else:
                func_indisponiveis.append(func_info)
        
        # Mostrar disponíveis primeiro (mais importante)
        if func_disponiveis:
            resposta += "✅ *Funcionalidades Disponíveis:*\n"
            for func in func_disponiveis:
                resposta += f"{func}\n"
            resposta += "\n"
        
        # Depois mostrar indisponíveis (se houver)
        if func_indisponiveis:
            resposta += "❌ *Funcionalidades Indisponíveis:*\n"
            for func in func_indisponiveis:
                resposta += f"{func}\n"
            resposta += "\n"
    
    # Outras Informações - com divisores visuais
    outras_info = erp.get("Outras_Informacoes", {})
    if outras_info:
        resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        resposta += "📋 *Outras Informações:*\n\n"
        
        # Complexidade com emoji baseado no valor
        complexidade = outras_info.get("Complexidade", "")
        if complexidade:
            complexidade_lower = complexidade.lower()
            if "baixa" in complexidade_lower or "simples" in complexidade_lower:
                emoji_comp = "🟢"
            elif "média" in complexidade_lower or "medio" in complexidade_lower:
                emoji_comp = "🟡"
            elif "alta" in complexidade_lower or "complexa" in complexidade_lower:
                emoji_comp = "🔴"
            else:
                emoji_comp = "⚪"
            resposta += f"{emoji_comp} *Complexidade*: {complexidade}\n"
        
        # Responsáveis com emojis
        responsavel_config = outras_info.get("Responsavel_Configuracao", "")
        if responsavel_config:
            resposta += f"⚙️ *Responsável pela Configuração*: {responsavel_config}\n"
        
        responsavel_testes = outras_info.get("Responsavel_Testes", "")
        if responsavel_testes:
            resposta += f"🧪 *Responsável pelos Testes*: {responsavel_testes}\n"
        
        desenvolvedor = outras_info.get("Desenvolvedor_Integracao", "")
        if desenvolvedor:
            resposta += f"👨‍💻 *Desenvolvedor da Integração*: {desenvolvedor}\n"
        
        # Custos
        custos = outras_info.get("Custos_Envolvidos", "")
        if custos:
            resposta += f"💰 *Custos Envolvidos*: {custos}\n"
        
        # Limitações
        limitacoes = outras_info.get("Limitacoes_Ausencia", "")
        if limitacoes and limitacoes.lower() not in ["nada consta.", "nada consta", "n/a", ""]:
            resposta += f"⚠️ *Limitações/Ausências*: {limitacoes}\n"
        
        # Site
        site = outras_info.get("Site", "")
        if site and site.lower() not in ["não informado.", "não informado"]:
            resposta += f"🌐 *Site*: {site}\n"
        
        # Manual
        manual = outras_info.get("Manual", "")
        if manual and manual.lower() not in ["não forneceu.", "não forneceu"]:
            resposta += f"📚 *Manual*: {manual}\n"
    
    # Suporte e Contato (se disponível)
    suporte = erp.get("Suporte_Contato", {})
    if suporte:
        resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        resposta += "📞 *Suporte/Contato:*\n\n"
        email = suporte.get("Email", "")
        telefone = suporte.get("Telefone", "")
        if email and email != "N/A":
            resposta += f"📧 *Email*: {email}\n"
        if telefone and telefone != "N/A":
            resposta += f"📱 *Telefone*: {telefone}\n"
    
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
    
    # Limpar query: remover pontuação e normalizar
    query_limpa = re.sub(r'[?.,!;:]+', '', query.lower().strip())
    logger.info(f"🔍 Busca genérica: '{query}'")
    
    # Lista expandida de palavras comuns a ignorar (stopwords em português)
    palavras_ignorar = {
        # Artigos e preposições
        "a", "o", "as", "os", "da", "do", "das", "dos", "de", "em", "na", "no", "nas", "nos", "para", "por", "com", "sem",
        # Pronomes
        "me", "te", "se", "nos", "vos", "lhe", "lhes", "que", "qual", "quais", "quem", "onde", "quando",
        # Verbos comuns
        "pode", "posso", "pode", "podem", "quer", "quero", "quer", "querem", "tem", "tenho", "tem", "têm",
        "fazer", "faço", "faz", "fazem", "estar", "estou", "está", "estão", "ser", "sou", "é", "são",
        "ter", "dar", "dá", "dão", "passar", "passa", "mostrar", "mostra", "ver", "vê", "conseguir", "consegue",
        # Palavras relacionadas a integrações
        "integração", "integracao", "integracoes", "integrações", "erp", "erps", "plataforma", "ferramenta",
        # Perguntas e pedidos
        "sobre", "acerca", "dados", "dado", "informações", "informacao", "info", "contato", "contatos", "contato",
        "como", "qual", "quais", "quando", "onde", "porque", "por que", "funciona", "funcionalidades", "funcionalidade",
        "preciso", "precisamos", "gostaria", "gostaríamos", "quero", "queremos"
    }
    palavras_query = set([p.strip('?.,!;:') for p in query_limpa.split() 
                          if p.strip('?.,!;:') not in palavras_ignorar and len(p.strip('?.,!;:')) > 2])
    
    logger.debug(f"📝 Palavras extraídas da query genérica: {palavras_query}")
    
    matches = []
    scores = []
    
    for erp in erps:
        nome_erp = erp.get("Nome", erp.get("ERP", "")).lower()
        nome_limpo = re.sub(r'\s*\(.*?\)', '', nome_erp)
        palavras_nome = set(nome_limpo.split())
        
        score = 0
        
        # ESTRATÉGIA 1: Verificar se o nome completo do ERP está contido na query (maior pontuação)
        # Ex: query="dados de contato da bling" -> nome="bling" deve ser encontrado
        if nome_limpo in query_limpa:
            score = 100
        # ESTRATÉGIA 2: Verificar se qualquer palavra significativa do nome está na query (busca invertida)
        # Ex: query="quais funcionalidades tem o eccosys" -> nome="eccosys" deve ser encontrado
        elif palavras_nome:
            palavras_significativas_nome = [p for p in palavras_nome if len(p) > 2 and p not in palavras_ignorar]
            if palavras_significativas_nome:
                for palavra_nome in palavras_significativas_nome:
                    if palavra_nome in query_limpa:
                        score = 95  # Pouco menos que match completo, mas ainda muito alto
                        break
        # ESTRATÉGIA 3: Busca por palavras-chave: verificar se palavras da query estão no nome do ERP
        if score == 0 and palavras_query and palavras_query.intersection(palavras_nome):
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

def sugerir_integracoes_similares(query: str, limite: int = 3) -> List[str]:
    """
    Sugere integrações com nomes similares quando não encontra resultado exato
    Útil para quando o usuário digita errado ou busca algo parecido
    
    Args:
        query: Query original do usuário
        limite: Número máximo de sugestões
        
    Returns:
        Lista com nomes das integrações sugeridas
    """
    erps = carregar_integracoes_json()
    
    if not erps or not query:
        return []
    
    query_lower = query.lower().strip()
    # Lista expandida de palavras comuns a remover
    palavras_remover = {
        # Artigos e preposições
        "a", "o", "as", "os", "da", "do", "das", "dos", "de", "em", "na", "no", "nas", "nos", "para", "por", "com", "sem",
        # Pronomes
        "me", "te", "se", "nos", "vos", "lhe", "lhes", "que", "qual", "quais", "quem", "onde", "quando",
        # Verbos comuns
        "pode", "posso", "pode", "podem", "quer", "quero", "quer", "querem", "tem", "tenho", "tem", "têm",
        "fazer", "faço", "faz", "fazem", "estar", "estou", "está", "estão", "ser", "sou", "é", "são",
        "ter", "dar", "dá", "dão", "passar", "passa", "mostrar", "mostra", "ver", "vê", "conseguir", "consegue",
        # Palavras relacionadas a integrações
        "integração", "integracao", "integracoes", "integrações", "erp", "erps", "plataforma", "ferramenta",
        # Perguntas e pedidos
        "sobre", "acerca", "dados", "dado", "informações", "informacao", "info", "contato", "contatos", "contato",
        "como", "qual", "quais", "quando", "onde", "porque", "por que", "funciona", "funcionalidades", "funcionalidade",
        "preciso", "precisamos", "gostaria", "gostaríamos", "quero", "queremos"
    }
    palavras_query = set([p for p in query_lower.split() if p not in palavras_remover and len(p) > 2])
    
    if not palavras_query:
        return []
    
    sugestoes_com_score = []
    
    for erp in erps:
        nome_erp = erp.get("Nome", erp.get("ERP", "")).lower()
        nome_limpo = re.sub(r'\s*\(.*?\)', '', nome_erp)
        palavras_nome = set(nome_limpo.split())
        
        # Calcular similaridade: contar palavras em comum
        palavras_comuns = palavras_query.intersection(palavras_nome)
        
        if palavras_comuns:
            # Score baseado em número de palavras comuns e tamanho do nome
            score = len(palavras_comuns) / max(len(palavras_query), 1)
            sugestoes_com_score.append({
                'nome': erp.get("Nome", erp.get("ERP", "")),
                'score': score
            })
    
    # Ordenar por score (maior primeiro)
    sugestoes_com_score.sort(key=lambda x: x['score'], reverse=True)
    
    # Retornar apenas os nomes, limitado
    return [s['nome'] for s in sugestoes_com_score[:limite]]
