import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")

def get_gemini_response(prompt):
    """
    Chama a API do Gemini para gerar resposta.
    
    Returns:
        str: Texto da resposta ou string de erro se falhar
    """
    try:
        response = model.generate_content(prompt)
        
        # Verificar se a resposta tem texto
        if not response or not response.text:
            logger.warning("⚠️ Gemini retornou resposta vazia")
            return None
        
        return response.text
        
    except Exception as e:
        erro_str = str(e)
        erro_msg = erro_str.lower()
        
        # Detectar tipo de erro
        is_quota_error = (
            "429" in erro_str or 
            "resource_exhausted" in erro_msg or 
            "quota" in erro_msg or 
            ("exceeded" in erro_msg and ("quota" in erro_msg or "limit" in erro_msg)) or
            "rate limit" in erro_msg
        )
        
        if is_quota_error:
            logger.warning(f"⚠️ Gemini: Erro de quota/rate limit: {erro_str}")
        else:
            logger.error(f"❌ Gemini: Erro ao gerar resposta: {erro_str}", exc_info=True)
        
        return f"Erro ao acessar Gemini: {erro_str}"
