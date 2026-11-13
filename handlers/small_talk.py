#!/usr/bin/env python3
"""
Detecção de "small talk" / saudações do tipo "Tina, tudo bem?", "como vai?".

Dá à Tina uma resposta com personalidade quando o usuário puxa conversa,
em vez de tratar como busca de integração. Se a mensagem for SÓ a saudação,
responde apenas a saudação; se houver também uma pergunta de verdade, o
chamador usa o prefixo de saudação e segue com a resposta normal.
"""

import re
import random

# Frases de "como você está?" (o alvo principal do recurso)
FRASES_SMALL_TALK = [
    "tudo bem", "tudo bom", "tudo certo", "tudo tranquilo", "tudo joia", "tudo jóia",
    "como vai", "como voce vai", "como você vai", "como vc vai",
    "como voce esta", "como você está", "como vc esta", "como vc está",
    "como voce ta", "como você tá", "como vc ta", "como vc tá",
    "como estas", "como está você", "como esta voce",
    "como anda", "como andas", "como voce anda", "como você anda",
    "beleza", "de boa", "suave", "como tem passado", "como você tá indo",
]

# Palavras "de enfeite" que, junto com a saudação, não contam como pergunta real
FILLERS = [
    "tina", "oi", "ola", "olá", "ei", "opa", "hey", "hi", "hello",
    "e", "ai", "aí", "eai", "prezada", "prezado", "por", "favor", "pfv",
    "bom", "dia", "boa", "tarde", "noite", "tudo", "bem", "voce", "você", "vc",
    "ta", "tá", "esta", "está", "com", "a", "o", "ola", "entao", "então",
]

# Variações de resposta para saudação pura (sorteadas a cada mensagem).
RESPOSTAS_PURAS = [
    "Olá! Estou funcionando perfeitamente por aqui 🤖 E você, tudo bem? 😊\n\n"
    "Se precisar de algo sobre as integrações da Nuvem Envio, é só me chamar!",
    "Oi! Tudo ótimo por aqui, obrigada por perguntar 😊 E com você?\n\n"
    "Qualquer dúvida sobre integrações, é só mandar!",
    "Olá! Tô 100% e prontinha para ajudar 🚀 E você, como vai?\n\n"
    "Pode me perguntar sobre qualquer integração da Nuvem Envio!",
]

# Variações de prefixo quando há uma pergunta junto da saudação.
PREFIXOS_COM_PERGUNTA = [
    "Olá! Estou funcionando por aqui, obrigada por perguntar 😊 Já te ajudo com isso:",
    "Oi! Tudo ótimo por aqui 🤖 Deixa eu te ajudar com a sua pergunta:",
    "Olá! Tô bem, obrigada 😊 Vamos ao que você precisa:",
]


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\sáéíóúàèìòùâêîôûãõç]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def detectar_small_talk(texto: str) -> dict:
    """
    Analisa o texto e detecta saudação do tipo "tudo bem?".

    Returns:
        dict com:
          - is_small_talk (bool): a mensagem contém uma saudação "como vai?"
          - is_pure (bool): a mensagem é SÓ a saudação (sem outra pergunta)
          - resposta (str): resposta pronta quando is_pure
          - prefixo (str): linha de saudação para prepender quando não é pura
    """
    resultado = {"is_small_talk": False, "is_pure": False, "resposta": "", "prefixo": ""}
    if not texto:
        return resultado

    norm = _normalizar(texto)
    if not norm:
        return resultado

    frase_encontrada = next((f for f in FRASES_SMALL_TALK if f in norm), None)
    if not frase_encontrada:
        return resultado

    resultado["is_small_talk"] = True

    # Remover a frase de saudação e os fillers para ver o que "sobra" de conteúdo real.
    restante = norm.replace(frase_encontrada, " ")
    palavras_restantes = [
        p for p in restante.split()
        if p not in FILLERS and len(p) > 1
    ]

    # Se sobrou pouco ou nada, é saudação pura.
    if len(palavras_restantes) == 0:
        resultado["is_pure"] = True
        resultado["resposta"] = random.choice(RESPOSTAS_PURAS)
    else:
        resultado["prefixo"] = random.choice(PREFIXOS_COM_PERGUNTA)

    return resultado


# ---------------------------------------------------------------------------
# Brincadeiras do tipo "bugou? rs", "travou, Tina?", "tá bugada kkk"
# ---------------------------------------------------------------------------

# Pelo menos uma destas precisa aparecer para contar como brincadeira
GATILHOS_BRINCADEIRA_BUG = {
    "bugou", "bugada", "bugado", "bugando", "travou", "travada", "travado", "pifou",
    "surtou", "surtando", "xilique", "estressada", "doida", "quebrou", "quebrada",
}

# Palavras que podem acompanhar sem virar pergunta de verdade
FILLERS_BRINCADEIRA = {
    "tina", "tininha", "ta", "tá", "esta", "está", "voce", "você", "vc", "ai", "aí",
    "de", "novo", "dando", "deu", "um", "uma", "e", "eh", "é", "foi", "ela", "a", "o",
    "hein", "ein", "ne", "né", "mesmo", "hoje", "aqui", "amiga", "filha", "coitada",
}

_RISADA = re.compile(r"^(k{2,}|(rs)+|(ha)+h?|(he)+h?|(hu)+e*|kk+|lol|aff|uai)$")

RESPOSTAS_BRINCADEIRA_BUG = [
    "Eu? Bugar? Jamais! 😅 Só dei uma travadinha pra pensar...\n\n"
    "Se eu não achei o que você procurava, pode ser que a integração ainda não esteja na minha base. "
    "Tenta me perguntar de outro jeito ou usa o *Ver portal completo* 😉",
    "Bugada não, só concentrada! 🤖💅\n\n"
    "Se minha resposta não ajudou, me pergunta de novo com o nome da integração "
    "que eu dou meu melhor!",
    "Tô firme e forte por aqui! 💪 Às vezes eu só não encontro a integração na base mesmo.\n\n"
    "Me manda o nome de novo ou dá uma olhada no portal completo, combinado? 😊",
]


def detectar_brincadeira_bug(texto: str) -> dict:
    """
    Detecta mensagens que são só uma brincadeira sobre a Tina ter bugado
    ("bugou? rs", "travou tina?", "tá bugada kkk").

    Returns:
        dict com is_brincadeira (bool) e resposta (str).
    """
    resultado = {"is_brincadeira": False, "resposta": ""}
    norm = _normalizar(texto or "")
    palavras = norm.split()
    if not palavras or len(palavras) > 8:
        return resultado

    if not any(p in GATILHOS_BRINCADEIRA_BUG for p in palavras):
        return resultado

    # Tudo o que sobrar precisa ser enfeite ou risada — senão é pergunta real
    for p in palavras:
        if p in GATILHOS_BRINCADEIRA_BUG or p in FILLERS_BRINCADEIRA or _RISADA.match(p):
            continue
        return resultado

    resultado["is_brincadeira"] = True
    resultado["resposta"] = random.choice(RESPOSTAS_BRINCADEIRA_BUG)
    return resultado


# ---------------------------------------------------------------------------
# Integração não encontrada — resposta direta e bem-humorada
# ---------------------------------------------------------------------------

# Vocativos carinhosos/engraçadinhos (sorteados a cada resposta)
VOCATIVOS = [
    "consagrado(a)", "companheiro(a)", "chefia", "criatura de luz", "meu bem",
    "nobre colega", "parceiro(a)", "pessoa iluminada", "meu anjo", "campeão(ã)",
]

# Abertura quando sabemos o nome da integração ({voc} e {nome})
ABERTURAS_NAO_TEMOS = [
    "Ih, {voc}... não temos integração com *{nome}* 😬",
    "Vou te dar a real, {voc}: não temos integração com *{nome}* 😅",
    "Procurei até debaixo do tapete, {voc}, e nada: não temos integração com *{nome}* 🕵️‍♀️",
    "Dói em mim dizer isso, {voc}, mas não temos integração com *{nome}* 💔",
    "Notícia triste, {voc}: *{nome}* não está na nossa lista de integrações 🥲",
]

# Abertura quando não sabemos qual integração foi perguntada
ABERTURAS_SEM_NOME = [
    "Ih, {voc}... procurei aqui e não achei nada sobre isso na minha base 😬",
    "Vou te dar a real, {voc}: não encontrei nada sobre isso por aqui 😅",
    "Revirei minha base todinha, {voc}, e não achei nada sobre isso 🕵️‍♀️",
]

FECHAMENTOS_NAO_TEMOS = [
    "Mas se quiser confirmar com mais certeza, dá uma olhadinha no nosso *portal* "
    "ou chama o *time de especialistas* — eles sabem até o que eu não sei 🤓",
    "Pra tirar a prova, dá uma espiadinha no *portal completo* ou confirma com o "
    "*time de especialistas* (eles são mais sabidos que eu, mas não conta pra ninguém 🤫)",
    "Se quiser ter certeza absoluta, confere no *portal* ou bate um papo com o nosso "
    "*time de especialistas* 😉",
]


def mensagem_integracao_nao_encontrada(nome: str = "", sugestoes: list = None) -> str:
    """
    Monta a resposta (mrkdwn do Slack) quando a integração não está na base:
    direta ("não temos"), bem-humorada e apontando para portal/especialistas.

    Args:
        nome: nome da integração perguntada (vazio se não souber)
        sugestoes: nomes de integrações parecidas que existem na base (possível typo)
    """
    voc = random.choice(VOCATIVOS)
    nome = (nome or "").strip()
    if nome.islower():
        nome = nome[:1].upper() + nome[1:]  # "hostgator" → "Hostgator"
    if nome:
        abertura = random.choice(ABERTURAS_NAO_TEMOS).format(voc=voc, nome=nome)
    else:
        abertura = random.choice(ABERTURAS_SEM_NOME).format(voc=voc)

    partes = [abertura]
    if sugestoes:
        lista = ", ".join(f"*{s}*" for s in sugestoes)
        partes.append(f"🤔 Será que você quis dizer {lista}? Se for, é só me perguntar de novo!")
    partes.append(random.choice(FECHAMENTOS_NAO_TEMOS))
    return "\n\n".join(partes)
