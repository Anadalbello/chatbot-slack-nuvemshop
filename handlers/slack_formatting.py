"""
Módulo de formatação de mensagens para Slack (estilo Nina)
- Conversão de Markdown para formato Slack
- Divisão inteligente de mensagens longas
- Preservação de estrutura (listas, parágrafos)
- Mensagens de feedback por idioma
"""

import re
import logging

logger = logging.getLogger(__name__)


def converter_markdown_para_slack(texto):
    """
    Converte markdown padrão para o formato do Slack.
    
    Slack usa um formato especial:
    - *texto* para negrita (deve ter espaços ou estar no início/fim)
    - _texto_ para cursiva
    - ~texto~ para tachado
    - `texto` para código inline
    - ``` para blocos de código
    
    Args:
        texto (str): Texto com markdown padrão
        
    Returns:
        str: Texto formatado para Slack
    """
    if not texto:
        return ""
    
    # Primeiro, proteger blocos de código para não modificar seu conteúdo
    code_blocks = []
    def protect_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    # Proteger blocos de código (```...```)
    texto = re.sub(r'```[\s\S]*?```', protect_code, texto)
    
    # Proteger código inline (`...`)
    inline_code = []
    def protect_inline_code(match):
        inline_code.append(match.group(0))
        return f"__INLINE_CODE_{len(inline_code)-1}__"
    
    texto = re.sub(r'`[^`]+`', protect_inline_code, texto)
    
    # Converter **texto** a *texto* (negrita)
    # Slack interpreta *texto* como negrita automaticamente
    texto = re.sub(r'\*\*([^*]+?)\*\*', r'*\1*', texto)
    
    # Converter __texto__ a _texto_ (cursiva) - só se não estiver dentro de negrita
    texto = re.sub(r'__(?!_)([^_]+?)__(?!_)', r'_\1_', texto)
    
    # Converter encabezados (## Texto, ### Texto) a negrita com salto de línea
    texto = re.sub(r'^##+\s+(.+)$', r'\n\n*\1*\n', texto, flags=re.MULTILINE)
    
    # Converter listas numeradas (1. texto) a formato Slack com melhor espaçamento
    # Primeiro, agregar espaço antes de listas se não há
    texto = re.sub(r'\n(\d+\.\s)', r'\n\n\1', texto)
    
    # Converter listas numeradas a bullets com melhor formato
    texto = re.sub(r'^\d+\.\s+', r'• ', texto, flags=re.MULTILINE)
    
    # Converter listas com guiones o asteriscos também
    texto = re.sub(r'^[-*]\s+', r'• ', texto, flags=re.MULTILINE)
    
    # Asegurar que cada item de lista esteja em sua própria linha com espaço depois
    # Agregar salto de línea depois de cada item de lista se não há outro item ou parágrafo
    texto = re.sub(r'(• [^\n]+)\n(?!• |\n|$)', r'\1\n', texto)
    
    # Agregar salto de línea doble depois de parágrafos que terminam com dois pontos seguidos de lista
    texto = re.sub(r'(:\s*)\n(• )', r'\1\n\n\2', texto)
    
    # Melhorar espaçamento: agregar salto de línea antes de listas se vêm depois de texto
    texto = re.sub(r'([^\n])\n(• )', r'\1\n\n\2', texto)
    
    # Restaurar blocos de código protegidos
    for i, code_block in enumerate(code_blocks):
        texto = texto.replace(f"__CODE_BLOCK_{i}__", code_block)
    
    for i, code in enumerate(inline_code):
        texto = texto.replace(f"__INLINE_CODE_{i}__", code)
    
    # Limpar múltiplos espaços em branco (mas manter saltos de línea)
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r' \n', '\n', texto)
    
    # Limpar múltiplos saltos de línea consecutivos (máximo 2)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    
    # Limpar espaços ao início e final de cada línea
    texto = '\n'.join(line.strip() for line in texto.split('\n'))
    
    # Limpar saltos de línea ao início e final do texto
    texto = texto.strip()
    
    return texto


def dividir_resposta_inteligente(texto, max_length=3000):
    """
    Divide uma resposta longa em partes, respeitando a estrutura e formato.
    Tenta cortar em pontos naturais (fim de parágrafos, fim de listas, etc.)
    para manter o formato legível no Slack.
    
    Args:
        texto (str): Texto a dividir
        max_length (int): Longitude máxima por parte (default: 3000)
        
    Returns:
        list: Lista de partes do texto
    """
    if not texto:
        return [""]
    
    if len(texto) <= max_length:
        return [texto]
    
    partes = []
    texto_restante = texto
    
    while len(texto_restante) > max_length:
        # Buscar ponto de corte ideal (em ordem de preferência):
        # 1. Fim de lista completa (dois saltos de línea depois de um item de lista)
        # 2. Fim de parágrafo (dois saltos de línea)
        # 3. Fim de item de lista (salto de línea depois de "•")
        # 4. Fim de oração (ponto seguido de espaço)
        # 5. Salto de línea simple
        # 6. Espaço
        
        melhor_corte = -1
        melhor_tipo = None
        
        # Buscar nos últimos 500 caracteres antes do limite (para ter margem)
        inicio_busqueda = max(0, max_length - 500)
        area_busqueda = texto_restante[inicio_busqueda:max_length]
        
        # 1. Fim de lista completa: "\n\n" depois de um item de lista
        patron_lista_completa = r'(• [^\n]+)\n\n(?!• )'
        matches = list(re.finditer(patron_lista_completa, area_busqueda))
        if matches:
            melhor_corte = inicio_busqueda + matches[-1].end()
            melhor_tipo = "lista_completa"
        
        # 2. Fim de parágrafo: "\n\n" (dois saltos de línea)
        if melhor_corte == -1:
            patron_parrafo = r'\n\n'
            matches = list(re.finditer(patron_parrafo, area_busqueda))
            if matches:
                melhor_corte = inicio_busqueda + matches[-1].end()
                melhor_tipo = "parrafo"
        
        # 3. Fim de item de lista: "\n" depois de "•" (mas só se não há mais items depois)
        if melhor_corte == -1:
            patron_item_lista = r'(• [^\n]+)\n(?!• )'
            matches = list(re.finditer(patron_item_lista, area_busqueda))
            if matches:
                melhor_corte = inicio_busqueda + matches[-1].end()
                melhor_tipo = "item_lista"
        
        # 4. Fim de oração: ". " (ponto seguido de espaço)
        if melhor_corte == -1:
            patron_oracion = r'\. '
            matches = list(re.finditer(patron_oracion, area_busqueda))
            if matches:
                melhor_corte = inicio_busqueda + matches[-1].end()
                melhor_tipo = "oracion"
        
        # 5. Salto de línea simple
        if melhor_corte == -1:
            pos = area_busqueda.rfind('\n')
            if pos != -1:
                melhor_corte = inicio_busqueda + pos + 1
                melhor_tipo = "salto_linea"
        
        # 6. Espaço (último recurso)
        if melhor_corte == -1:
            pos = area_busqueda.rfind(' ')
            if pos != -1:
                melhor_corte = inicio_busqueda + pos + 1
                melhor_tipo = "espacio"
        
        # Se não encontramos ponto de corte ideal, cortar no limite exato
        if melhor_corte == -1:
            melhor_corte = max_length
            melhor_tipo = "forzado"
        
        # Extrair a parte
        parte = texto_restante[:mejor_corte].strip()
        if parte:
            partes.append(parte)
        
        # Continuar com o resto
        texto_restante = texto_restante[mejor_corte:].strip()
        
        # Se o resto é muito pequeno, agregá-lo à última parte se é possível
        if len(texto_restante) < 200 and partes and len(partes[-1]) + len(texto_restante) + 1 <= max_length:
            partes[-1] += "\n\n" + texto_restante
            texto_restante = ""
            break
    
    # Agregar o resto se fica algo
    if texto_restante:
        partes.append(texto_restante)
    
    return partes if partes else [""]


def obter_mensagem_feedback(idioma="pt", mostrar_feedback=True):
    """
    Retorna mensagem de feedback no idioma especificado.
    
    Args:
        idioma (str): Idioma da resposta (pt, es, en) - default: pt
        mostrar_feedback (bool): Se True, retorna mensagem. False retorna string vazia.
        
    Returns:
        str: Mensagem de feedback ou string vazia
    """
    if not mostrar_feedback:
        return ""
    
    mensagens_feedback = {
        "pt": "\n\n💡 Te ajudou? Reaja com 👍 ou 👎",
        "es": "\n\n💡 ¿Te ayudó? Reacciona con 👍 o 👎",
        "en": "\n\n💡 Did this help? React with 👍 or 👎"
    }
    
    # Normalizar idioma (pt_BR -> pt, es_AR -> es, etc)
    idioma_base = idioma.split('_')[0].lower() if '_' in idioma else idioma.lower()
    
    return mensagens_feedback.get(idioma_base, mensagens_feedback["pt"])


def formatar_e_enviar_slack(
    slack_client,
    channel,
    texto,
    thread_ts=None,
    idioma="pt",
    mostrar_feedback=True,
    max_length=3000
):
    """
    Formata texto (markdown -> Slack), divide se necessário e envia ao Slack.
    Função helper para facilitar o uso.
    
    Args:
        slack_client: Cliente do Slack (WebClient)
        channel (str): ID do canal
        texto (str): Texto da resposta (pode conter markdown)
        thread_ts (str, optional): Timestamp do thread para responder em thread
        idioma (str): Idioma da resposta (pt, es, en) - default: pt
        mostrar_feedback (bool): Se True, mostra mensagem de feedback
        max_length (int): Longitude máxima por mensagem (default: 3000)
        
    Returns:
        list: Lista de timestamps das mensagens enviadas
    """
    try:
        # Converter markdown a formato Slack
        texto_original = texto
        texto = converter_markdown_para_slack(texto)
        logger.debug(f"Markdown convertido - Original tinha **: {'**' in texto_original}, Convertido tem *: {'*' in texto}")
        
        # Obter mensagem de feedback
        mensagem_feedback = obter_mensagem_feedback(idioma, mostrar_feedback and thread_ts is not None)
        
        # Reservar espaço para mensagem de feedback se necessário
        max_length_efetivo = max_length - len(mensagem_feedback) if mensagem_feedback else max_length
        
        # Dividir resposta em partes se é muito longa
        if len(texto) <= max_length_efetivo:
            partes_resposta = [texto]
        else:
            # Dividir de forma inteligente, respeitando estrutura e formato
            partes_resposta = dividir_resposta_inteligente(texto, max_length_efetivo)
        
        # Agregar mensagem de feedback à última parte (só se há thread_ts e mostrar_feedback=True)
        if thread_ts and mostrar_feedback and mensagem_feedback and partes_resposta:
            partes_resposta[-1] += mensagem_feedback
        
        # Enviar cada parte
        timestamps = []
        for i, parte in enumerate(partes_resposta):
            logger.debug(f"Enviando parte {i+1} de {len(partes_resposta)} da resposta (tamanho: {len(parte)} caracteres)")
            
            try:
                resultado = slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=parte
                )
                
                if resultado and 'ts' in resultado:
                    timestamps.append(resultado['ts'])
                
                logger.debug(f"Resposta (parte {i+1}) enviada com sucesso")
            except Exception as e:
                logger.error(f"Erro ao enviar resposta (parte {i+1}): {str(e)}", exc_info=True)
                raise
        
        return timestamps
        
    except Exception as e:
        logger.error(f"Erro ao formatar e enviar resposta ao Slack: {str(e)}", exc_info=True)
        raise

