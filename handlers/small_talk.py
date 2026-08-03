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
