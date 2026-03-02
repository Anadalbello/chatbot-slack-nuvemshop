import google.generativeai as genai
import os
import logging
import re
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")

# Retry em caso de quota: esperar e tentar de novo 1x (evita fallback desnecessário)
QUOTA_RETRY_DELAY = int(os.getenv("GEMINI_QUOTA_RETRY_DELAY", "32"))  # segundos (API costuma pedir ~30s)
QUOTA_RETRY_ENABLED = os.getenv("GEMINI_QUOTA_RETRY_ENABLED", "true").lower() in ("true", "1", "yes")


def _is_quota_error(erro_str: str) -> bool:
    erro_msg = erro_str.lower()
    return (
        "429" in erro_str or
        "resource_exhausted" in erro_msg or
        "quota" in erro_msg or
        ("exceeded" in erro_msg and ("quota" in erro_msg or "limit" in erro_msg)) or
        "rate limit" in erro_msg
    )


def _extract_retry_seconds(erro_str: str) -> Optional[float]:
    if "retry_delay" in erro_str or "retry in" in erro_str.lower():
        m = re.search(r'retry.*?(\d+\.?\d*)\s*[sS]', erro_str)
        if m:
            return float(m.group(1))
    return None


def get_gemini_response(prompt):
    """
    Chama a API do Gemini para gerar resposta.
    Em erro de quota, espera e tenta uma vez antes de devolver erro.
    Returns:
        str: Texto da resposta ou string de erro se falhar
    """
    last_error = None
    for attempt in range(2 if QUOTA_RETRY_ENABLED else 1):
        try:
            response = model.generate_content(prompt)
            if not response or not response.text:
                logger.warning("⚠️ Gemini retornou resposta vazia")
                return None
            return response.text
        except Exception as e:
            last_error = e
            erro_str = str(e)
            if attempt == 0 and QUOTA_RETRY_ENABLED and _is_quota_error(erro_str):
                wait = _extract_retry_seconds(erro_str) or QUOTA_RETRY_DELAY
                logger.warning(f"⚠️ Gemini: Quota excedida. Aguardando {wait:.0f}s e tentando novamente...")
                time.sleep(w)
                continue
            break

    # Falhou (ou não é quota / retry desligado)
    erro_str = str(last_error)
    if _is_quota_error(erro_str):
        logger.warning("⚠️ Gemini: Quota excedida após retry. Usando fallback.")
    else:
        erro_resumido = erro_str.split("\n")[0][:150]
        logger.error(f"❌ Gemini: {erro_resumido}")
    return f"Erro ao acessar Gemini: {erro_str}"
