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

# Funcionalidades filtráveis: chave no JSON -> (rótulo amigável, descrição p/ o Gemini)
FUNCIONALIDADES_ROTULOS = {
    "Calculo_de_Frete": ("calculam o frete", "calcular/cotar o valor do frete"),
    "Seguro_Incluido_Calculo_Frete": ("incluem seguro no cálculo do frete", "incluir seguro no cálculo do frete"),
    "Seguro_Configuravel_Calculo_Frete": ("permitem configurar o seguro no frete", "configurar (sim/não) o seguro no cálculo do frete"),
    "Nome_Transportador_Checkout_Personalizavel": ("personalizam o nome da transportadora no checkout", "personalizar o nome da transportadora no checkout"),
    "Calcula_Peso_Cubado": ("calculam peso cubado", "calcular o peso cubado no frete"),
    "Integracao_Pedidos": ("integram pedidos", "integrar/importar pedidos"),
    "Multiplos_Volumes_Pedidos": ("suportam múltiplos volumes", "integrar pedidos com múltiplos volumes"),
    "Configuracao_Seguro_Pedidos": ("permitem configurar o seguro na integração de pedidos", "configurar (sim/não) o seguro na integração de pedidos"),
    "Valor_Minimo_Seguro_Configuravel": ("permitem configurar valor mínimo de seguro", "configurar um valor mínimo de seguro"),
    "Multi_CD": ("suportam operação de Multi-CD", "operar com múltiplos centros de distribuição (Multi-CD)"),
    "Impressao_Etiqueta": ("imprimem etiqueta na plataforma", "imprimir etiqueta na plataforma"),
    "Devolucao_Codigo_Rastreamento": ("devolvem o código de rastreamento", "devolver o código de rastreamento"),
    "Atualiza_Status_Rastreio": ("atualizam o status de rastreamento", "atualizar o status de rastreamento"),
}


def _normalize_text_for_word_matching(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^\w]+', ' ', text.lower()).strip()


def _has_whole_word(word: str, text: str) -> bool:
    if not word or not text:
        return False
    word_norm = _normalize_text_for_word_matching(word)
    text_norm = _normalize_text_for_word_matching(text)
    if not word_norm:
        return False
    return bool(re.search(rf'\b{re.escape(word_norm)}\b', text_norm, flags=re.IGNORECASE))


def _has_prefix_with_boundary(shorter: str, longer: str) -> bool:
    if not shorter or not longer:
        return False
    shorter_norm = _normalize_text_for_word_matching(shorter)
    longer_norm = _normalize_text_for_word_matching(longer)
    if not shorter_norm or not longer_norm or shorter_norm == longer_norm:
        return False
    if not longer_norm.startswith(shorter_norm):
        return False
    next_char_index = len(shorter_norm)
    if next_char_index >= len(longer_norm):
        return True
    return not longer_norm[next_char_index].isalnum()


def _has_conflicting_prefix(candidate_name: str, query: str) -> bool:
    """
    Detecta conflitos onde um nome curto aparece na query,
    mas a query também contém uma palavra mais longa com o mesmo prefixo.
    Ex: "jet." deve ser rejeitado se a query mencionar "jetro".
    """
    if not candidate_name or not query:
        return False
    candidate_norm = _normalize_text_for_word_matching(candidate_name)
    query_norm = _normalize_text_for_word_matching(query)

    if candidate_norm == "jet":
        return bool(re.search(r'\bjetro\b', query_norm))

    return False


def normalizar_typos_nome_integracao_na_query(texto: str) -> str:
    """
    Corrige typos que confundem a busca.
    Ex.: recepcionista/modelo gera 'JetCommerce' (Jet. + alcula); só 'commerce' batia em Wake Commerce.
    """
    if not texto:
        return texto
    return re.sub(r"\bjetcommerce\b", "jet.", texto, flags=re.IGNORECASE)

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
    
    # Limpar query: remover pontuação, espaços extras e normalizar
    nome_erp = normalizar_typos_nome_integracao_na_query(nome_erp.strip())
    nome_limpo_query = re.sub(r'[?.,!;:\s]+', ' ', nome_erp.lower().strip())
    nome_limpo_query = re.sub(r'\s+', ' ', nome_limpo_query).strip()  # Normalizar espaços múltiplos
    logger.info(f"🔍 Buscando ERP: '{nome_erp}' (query limpa: '{nome_limpo_query}')")
    
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
                          if p.strip('?.,!;:') not in palavras_remover and len(p.strip('?.,!;:')) > 1])
    
    logger.debug(f"📝 Palavras extraídas da query: {palavras_query}")
    logger.debug(f"📝 Query limpa: '{nome_limpo_query}'")
    
    # Buscar por match com sistema de scoring para priorizar matches melhores
    matches_com_score = []
    for erp in erps:
        nome_erp_atual = erp.get("Nome", erp.get("ERP", "")).lower()
        # Outros nomes (ex: WordPress para Woocommerce)
        outras_info = erp.get("Outras_Informacoes") or {}
        outros_nomes_raw = outras_info.get("Outros_nomes_integracao", "") or ""
        outros_nomes_list = [s.strip().lower() for s in re.split(r"[,;]|\s+e\s+", str(outros_nomes_raw)) if s.strip()]
        # Busca parcial: remove parênteses E pontuação para busca mais flexível
        nome_limpo = re.sub(r'\s*\(.*?\)', '', nome_erp_atual)
        nome_limpo = re.sub(r'[?.,!;:\s]+', ' ', nome_limpo)  # Remove pontuação e normaliza espaços
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()  # Normalizar espaços múltiplos
        palavras_nome_raw = nome_limpo.split()
        palavras_nome = set([p.strip('?.,!;:') for p in palavras_nome_raw])

        if _has_conflicting_prefix(nome_limpo, nome_limpo_query):
            logger.debug(f"⚠️ Ignorando '{nome_limpo}' por conflito de prefixo na query")
            continue

        score = 0

        # ESTRATÉGIA 0.5: Verificar se a query bate com "Outros nomes" da integração (ex: WordPress -> Woocommerce)
        for outro in outros_nomes_list:
            outro_limpo = re.sub(r'[?.,!;:\s]+', ' ', outro).strip()
            if outro_limpo and (_has_whole_word(outro_limpo, nome_limpo_query) or _has_whole_word(nome_limpo_query, outro_limpo)):
                score = 98
                logger.debug(f"✅ Match por outros nomes: '{outro_limpo}' (score: {score})")
                break

        # ESTRATÉGIA 1: Verificar se o nome completo do ERP está contido na query (maior prioridade - score 100)
        # Ex: query="dados de contato da bling" -> nome="bling" deve ser encontrado
        if score == 0 and _has_whole_word(nome_limpo, nome_limpo_query):
            score = 100
            logger.debug(f"✅ Match por nome completo: '{nome_limpo}' encontrado na query (score: {score})")

        # ESTRATÉGIA 1.5: Verificar se o nome sem pontuação está contido na query ou vice-versa (score 95)
        if score == 0 and nome_limpo.strip():
            if len(nome_limpo.strip()) <= 3:
                if _has_whole_word(nome_limpo.strip(), nome_limpo_query):
                    score = 95
                    logger.debug(f"✅ Match por nome curto com whole-word: '{nome_limpo.strip()}' encontrado (score: {score})")
            elif nome_limpo.strip() in nome_limpo_query or nome_limpo_query in nome_limpo.strip():
                score = 95
                logger.debug(f"✅ Match por nome sem pontuação: '{nome_limpo.strip()}' encontrado (score: {score})")
        # ESTRATÉGIA 1.6: Busca sem espaços (para casos como "IDWorks" vs "ID Works")
        if score == 0 and len(nome_limpo.replace(' ', '').strip()) >= 4 and (
            nome_limpo.replace(' ', '') in nome_limpo_query.replace(' ', '') or nome_limpo_query.replace(' ', '') in nome_limpo.replace(' ', '')
        ):
            score = 94
            logger.debug(f"✅ Match por nome sem espaços: '{nome_limpo}' (score: {score})")
        # ESTRATÉGIA 2: Verificar se a query começa com o nome do ERP ou vice-versa,
        # mas apenas quando o limite de palavras ou separadores indica uma fronteira de palavra.
        # Evita falsos matches como 'Jetro' acertando 'jet.' por prefixo comum.
        if score == 0 and (_has_prefix_with_boundary(nome_limpo, nome_limpo_query) or _has_prefix_with_boundary(nome_limpo_query, nome_limpo)):
            score = 90
            logger.debug(f"✅ Match por início com boundary: '{nome_limpo}' (score: {score})")
        # ESTRATÉGIAS 3–5 só se ainda não houve match forte (evita sobrescrever score 100 com score menor — ex.: jet. vs Wake Commerce)
        if score == 0:
            # ESTRATÉGIA 3: Verificar se palavras significativas do nome estão na query (score baseado em similaridade)
            palavras_significativas_nome = [p.strip('?.,!;:') for p in palavras_nome_raw 
                                           if len(p.strip('?.,!;:')) > 1 and p.strip('?.,!;:') not in palavras_remover]
            if palavras_significativas_nome:
                palavras_match = []
                for palavra_nome in palavras_significativas_nome:
                    palavra_nome_limpa = palavra_nome.strip('?.,!;:')
                    # Verificar se palavra do nome aparece como whole word na query
                    if _has_whole_word(palavra_nome_limpa, nome_limpo_query):
                        palavras_match.append(palavra_nome_limpa.lower())
                
                if palavras_match:
                    # Score baseado em quantas palavras e tamanho das palavras (priorizar palavras maiores)
                    score = min(85, 50 + (len(palavras_match) * 10) + (sum(len(p) for p in palavras_match) // 2))
                    # Nome composto: exigir todas as palavras significativas (evita só "commerce" em "JetCommerce" -> Wake Commerce)
                    nsig = len(palavras_significativas_nome)
                    if nsig >= 2 and len(palavras_match) < nsig:
                        score = min(score, 44)
                    logger.debug(f"✅ Match por palavras do nome: {palavras_match} (score: {score})")
            
            # ESTRATÉGIA 4: Verificar se palavras-chave extraídas da query estão no nome do ERP (score menor)
            if score == 0:
                palavras_nome_normalizadas = set([p.strip('?.,!;:').lower() for p in palavras_nome_raw])
                palavras_comuns = palavras_query.intersection(palavras_nome_normalizadas) if palavras_query else set()
                if palavras_comuns:
                    # Score menor para matches parciais - priorizar palavras maiores
                    palavras_comuns_list = list(palavras_comuns)
                    score = min(70, 30 + (len(palavras_comuns_list) * 10) + (sum(len(p) for p in palavras_comuns_list) // 3))
                    logger.debug(f"✅ Match por interseção: palavras {palavras_comuns} encontradas no nome '{nome_limpo}' (score: {score})")
            
            # ESTRATÉGIA 5: Busca por substring (para casos como "idworks" em "IDWorks" ou vice-versa)
            if score == 0:
                # Remover espaços e comparar substrings
                nome_sem_espacos = nome_limpo.replace(' ', '').lower()
                query_sem_espacos = nome_limpo_query.replace(' ', '').lower()
                
                # Verificar se há substring comum significativa (mínimo 4 caracteres)
                if len(nome_sem_espacos) >= 4 and len(query_sem_espacos) >= 4:
                    # Verificar se uma está contida na outra
                    if nome_sem_espacos in query_sem_espacos or query_sem_espacos in nome_sem_espacos:
                        # Calcular score baseado no tamanho da substring comum
                        substring_comum = min(len(nome_sem_espacos), len(query_sem_espacos))
                        score = min(75, 40 + (substring_comum * 2))
                        logger.debug(f"✅ Match por substring: '{nome_limpo}' contém ou está contido em '{nome_limpo_query}' (score: {score})")
        
        if score > 0:
            matches_com_score.append((score, erp))
    
    if not matches_com_score:
        logger.info(f"❌ ERP '{nome_erp}' não encontrado")
        
        # Tentar buscar integrações similares para sugerir
        sugestoes = sugerir_integracoes_similares(nome_erp, limite=5)
        if sugestoes:
            logger.info(f"💡 Sugestões de integrações similares: {', '.join(sugestoes[:3])}")
        
        return None
    
    # Ordenar por score (maior primeiro); em empate, preferir nome mais curto (evita confundir "jet." com integrações de nome longo)
    matches_com_score.sort(
        key=lambda x: (-x[0], len((x[1].get("Nome") or x[1].get("ERP") or "")))
    )
    melhor_score, erp = matches_com_score[0]
    logger.info(f"✅ Melhor match encontrado com score {melhor_score}: {erp.get('Nome', erp.get('ERP', ''))}")
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
            "Seguro_Incluido_Calculo_Frete": "🛡️",
            "Seguro_Configuravel_Calculo_Frete": "⚙️",
            "Nome_Transportador_Checkout_Personalizavel": "✏️",
            "Calcula_Peso_Cubado": "📏",
            "Multiplos_Volumes_Pedidos": "📦",
            "Configuracao_Seguro_Pedidos": "🛡️",
            "Valor_Minimo_Seguro_Configuravel": "💰",
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
    query = normalizar_typos_nome_integracao_na_query(query.strip())
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
        outras_info = erp.get("Outras_Informacoes") or {}
        outros_nomes_raw = outras_info.get("Outros_nomes_integracao", "") or ""
        outros_nomes_list = [s.strip().lower() for s in re.split(r"[,;]|\s+e\s+", str(outros_nomes_raw)) if s.strip()]

        if _has_conflicting_prefix(nome_limpo, query_limpa):
            logger.debug(f"⚠️ Ignorando '{nome_limpo}' por conflito de prefixo na query genérica")
            continue

        score = 0

        # ESTRATÉGIA 0.5: Verificar se a query bate com "Outros nomes" da integração
        for outro in outros_nomes_list:
            outro_limpo = re.sub(r'[?.,!;:\s]+', ' ', outro).strip()
            if outro_limpo and (_has_whole_word(outro_limpo, query_limpa) or _has_whole_word(query_limpa, outro_limpo)):
                score = 98
                logger.debug(f"✅ Match genérico por outros nomes: '{outro_limpo}' (score: {score})")
                break

        # ESTRATÉGIA 1: Verificar se o nome completo do ERP está contido na query (maior pontuação)
        # Ex: query="dados de contato da bling" -> nome="bling" deve ser encontrado
        if score == 0 and _has_whole_word(nome_limpo, query_limpa):
            score = 100
        # ESTRATÉGIA 2: Verificar se qualquer palavra significativa do nome está na query (busca invertida)
        # Ex: query="quais funcionalidades tem o eccosys" -> nome="eccosys" deve ser encontrado
        elif score == 0 and palavras_nome:
            palavras_significativas_nome = [p for p in palavras_nome if len(p) > 2 and p not in palavras_ignorar]
            if palavras_significativas_nome:
                for palavra_nome in palavras_significativas_nome:
                    if _has_whole_word(palavra_nome, query_limpa):
                        score = 95  # Pouco menos que match completo, mas ainda muito alto
                        break
        # ESTRATÉGIA 3: Busca por palavras-chave: verificar se palavras da query estão no nome do ERP
        if score == 0 and palavras_query and palavras_query.intersection(palavras_nome):
            score = 90
        
        # Buscar em funcionalidades
        funcionalidades = erp.get("Funcionalidades", {})
        for func_nome, func_valor in funcionalidades.items():
            func_texto = (func_nome + " " + str(func_valor)).lower()
            if query_limpa in func_texto:
                score = max(score, 60)
            elif any(palavra in func_texto for palavra in palavras_query):
                score = max(score, 40)
        
        # Buscar em outras informações
        outras_info = erp.get("Outras_Informacoes", {})
        for chave, valor in outras_info.items():
            info_texto = (chave + " " + str(valor)).lower()
            if query_limpa in info_texto:
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

def buscar_por_tipo_integracao(tipo: str) -> Optional[str]:
    """
    Busca integrações por tipo de integração (ex: "Tabela de Frete", "API", "Apenas Rastreio")
    
    Args:
        tipo: Tipo de integração a buscar
        
    Returns:
        String formatada com lista de integrações ou None se não encontrar
    """
    erps = carregar_integracoes_json()
    
    if not erps:
        return None
    
    # Normalizar tipo de busca
    tipo_busca = tipo.lower().strip()
    
    # Mapeamento de variações comuns
    tipo_map = {
        "tabela de frete": "tabela de frete",
        "tabela frete": "tabela de frete",
        "frete tabela": "tabela de frete",
        "api": "api",
        "apenas rastreio": "apenas rastreio",
        "rastreio": "apenas rastreio",
        "rastreamento": "apenas rastreio"
    }
    
    # Normalizar tipo usando mapa
    tipo_normalizado = tipo_map.get(tipo_busca, tipo_busca)
    
    logger.info(f"🔍 Buscando integrações do tipo: '{tipo}' (normalizado: '{tipo_normalizado}')")
    
    # Filtrar integrações por tipo
    integracoes_filtradas = []
    for erp in erps:
        tipo_integracao = erp.get("Tipo_Integracao", "").strip()
        
        # Pular se não tiver tipo definido
        if not tipo_integracao:
            continue
        
        tipo_integracao_lower = tipo_integracao.lower()
        
        # Verificar match exato primeiro (mais preciso)
        if tipo_normalizado == tipo_integracao_lower:
            integracoes_filtradas.append(erp)
            logger.debug(f"✅ Match exato: '{tipo_integracao}'")
        # Verificar match parcial apenas se não foi match exato
        elif tipo_normalizado in tipo_integracao_lower:
            integracoes_filtradas.append(erp)
            logger.debug(f"✅ Match parcial: '{tipo_integracao}' contém '{tipo_normalizado}'")
        # Verificar se o tipo da integração está contido no tipo buscado (caso raro)
        elif tipo_integracao_lower in tipo_normalizado and len(tipo_integracao_lower) > 3:
            integracoes_filtradas.append(erp)
            logger.debug(f"✅ Match reverso: '{tipo_normalizado}' contém '{tipo_integracao}'")
    
    if not integracoes_filtradas:
        logger.info(f"❌ Nenhuma integração encontrada para o tipo '{tipo}'")
        return None
    
    logger.info(f"✅ Encontradas {len(integracoes_filtradas)} integrações do tipo '{tipo}'")
    
    # Formatar resposta
    resposta = f"📋 *Integrações do tipo: {tipo.title()}*\n\n"
    
    for i, erp in enumerate(integracoes_filtradas, 1):
        nome = erp.get("Nome", "Nome não informado")
        categoria = erp.get("Categoria", "")
        
        resposta += f"*{i}. {nome}*"
        if categoria:
            resposta += f" | 📂 {categoria}"
        resposta += "\n"
        
        # Adicionar informação sobre complexidade se disponível
        outras_info = erp.get("Outras_Informacoes", {})
        complexidade = outras_info.get("Complexidade", "")
        if complexidade:
            resposta += f"   ⚙️ Complexidade: {complexidade}\n"
        
        resposta += "\n"
    
    resposta += f"\n📊 *Total: {len(integracoes_filtradas)} integrações*"

    return resposta


def _funcionalidade_e_positiva(valor: str) -> bool:
    """Retorna True se o valor de uma funcionalidade indica 'Sim' (disponível)."""
    v = str(valor).strip().lower()
    if not v:
        return False
    if v.startswith("não") or v.startswith("nao") or "❌" in v:
        return False
    return v.startswith("sim") or "✔" in v


def buscar_por_funcionalidade(campo: str, rotulo: str) -> Optional[str]:
    """
    Lista as integrações que possuem uma determinada funcionalidade = "Sim".

    Args:
        campo: chave dentro de "Funcionalidades" (ex: "Calculo_de_Frete")
        rotulo: descrição amigável para o título (ex: "calculam o frete")

    Returns:
        String formatada com a lista, ou None se nenhuma integração tiver a funcionalidade.
    """
    erps = carregar_integracoes_json()
    if not erps:
        return None

    encontradas = [
        erp for erp in erps
        if _funcionalidade_e_positiva(erp.get("Funcionalidades", {}).get(campo, ""))
    ]

    if not encontradas:
        logger.info(f"❌ Nenhuma integração com funcionalidade '{campo}' = Sim")
        return None

    logger.info(f"✅ {len(encontradas)} integrações com funcionalidade '{campo}' = Sim")

    encontradas.sort(key=lambda e: e.get("Nome", "").lower())

    resposta = f"📋 *Integrações que {rotulo}* ({len(encontradas)}):\n\n"
    for i, erp in enumerate(encontradas, 1):
        nome = erp.get("Nome", "Nome não informado")
        categoria = erp.get("Categoria", "")
        resposta += f"*{i}. {nome}*"
        if categoria:
            resposta += f" | 📂 {categoria}"
        resposta += "\n"

    resposta += f"\n📊 *Total: {len(encontradas)} integrações*"
    return resposta


def detectar_funcionalidade_com_gemini(pergunta: str) -> Optional[tuple]:
    """
    Usa o Gemini para descobrir a qual funcionalidade uma pergunta se refere,
    quando os padrões de texto fixos não casam (fraseados variados).

    Args:
        pergunta: pergunta do usuário

    Returns:
        (campo, rotulo) se identificar uma funcionalidade conhecida, ou None.
    """
    try:
        # Import tardio para evitar dependência circular e custo na importação.
        from handlers.gemini_handler import get_gemini_response

        linhas = "\n".join(
            f"- {campo}: {descricao}"
            for campo, (_rotulo, descricao) in FUNCIONALIDADES_ROTULOS.items()
        )
        prompt = (
            "Você classifica perguntas sobre funcionalidades de integrações de "
            "e-commerce/ERP. Dada a pergunta, responda APENAS com a CHAVE exata da "
            "funcionalidade que ela procura, ou a palavra 'nenhuma' se não for uma "
            "pergunta pedindo a lista de integrações que têm uma funcionalidade.\n\n"
            f"Chaves possíveis:\n{linhas}\n\n"
            f'PERGUNTA: "{pergunta}"\n\n'
            "Responda somente com a chave (ex: Calculo_de_Frete) ou 'nenhuma'."
        )

        resposta = get_gemini_response(prompt)
        if not resposta or str(resposta).startswith("Erro ao acessar"):
            return None

        chave = str(resposta).strip().strip('"').strip("'").split()[0] if resposta.strip() else ""
        # Normalizar removendo pontuação final e mantendo o formato da chave
        chave = re.sub(r"[^A-Za-z_]", "", chave)

        if chave in FUNCIONALIDADES_ROTULOS:
            rotulo = FUNCIONALIDADES_ROTULOS[chave][0]
            logger.info(f"🧠 Gemini identificou funcionalidade: '{chave}'")
            return (chave, rotulo)

        logger.info(f"🧠 Gemini não identificou funcionalidade filtrável (retorno: '{resposta[:40]}')")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Falha ao detectar funcionalidade com Gemini: {e}")
        return None

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
