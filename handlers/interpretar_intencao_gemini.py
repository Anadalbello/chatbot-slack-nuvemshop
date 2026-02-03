#!/usr/bin/env python3
"""
Módulo para usar Gemini para interpretar a intenção do usuário antes de buscar
"""

import os
import logging
import json
import re
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
logger = logging.getLogger(__name__)

# Configurar Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configurações de segurança
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    },
]

model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash",  # Modelo estável (gemini-2.0-flash-exp foi descontinuado)
    generation_config={
        "temperature": 0.3,  # Menor temperatura para respostas mais precisas
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 200,
    },
    safety_settings=safety_settings
)


def interpretar_intencao_e_extrair_erp(pergunta: str) -> dict:
    """
    Usa Gemini para interpretar a intenção do usuário e extrair o nome do ERP/integração
    
    Args:
        pergunta: Pergunta original do usuário
        
    Returns:
        dict com:
        - intencao: tipo de pergunta ("verificar_existencia", "detalhes", "funcionalidades", "contato", "listar", "outro")
        - nome_erp: nome do ERP/integração extraído (se houver)
        - query_busca: query otimizada para busca
        - resposta_esperada: tipo de resposta esperada ("sim_nao", "lista", "detalhada", "especifica")
    """
    
    try:
        logger.info(f"🧠 Interpretando intenção da pergunta: '{pergunta[:50]}...'")
        
        prompt = f"""Você é um assistente que analisa perguntas sobre integrações de ERP/sistemas.

PERGUNTA DO USUÁRIO: "{pergunta}"

Sua tarefa é analisar a pergunta e retornar APENAS um JSON válido com:
{{
    "intencao": "verificar_existencia" | "detalhes" | "funcionalidades" | "contato" | "listar" | "outro",
    "nome_erp": "nome exato do ERP/integração mencionado (ou null se não mencionar nenhum)",
    "query_busca": "nome limpo para busca (extrair apenas palavras significativas, sem stopwords)",
    "resposta_esperada": "sim_nao" | "lista" | "detalhada" | "especifica"
}}

TIPOS DE INTENÇÃO:
- "verificar_existencia": pergunta se existe/tem integração (ex: "Temos integração com X?", "Existe integração X?")
- "detalhes": pede informações gerais sobre a integração
- "funcionalidades": pergunta especificamente sobre funcionalidades
- "contato": pergunta sobre dados de contato/suporte
- "listar": pede para listar integrações/ERPs
- "outro": qualquer outra pergunta

TIPOS DE RESPOSTA:
- "sim_nao": deve começar com "Sim" ou "Não" (ex: "Temos integração?")
- "lista": deve listar itens
- "detalhada": resposta completa com todas as informações
- "especifica": resposta focada em um aspecto específico

EXEMPLOS:
Pergunta: "Temos integração com Notazz?"
JSON: {{"intencao": "verificar_existencia", "nome_erp": "Notazz", "query_busca": "Notazz", "resposta_esperada": "sim_nao"}}

Pergunta: "pode me passar os dados de contato da bling?"
JSON: {{"intencao": "contato", "nome_erp": "bling", "query_busca": "bling", "resposta_esperada": "especifica"}}

Pergunta: "Quais funcionalidades tem o Eccosys?"
JSON: {{"intencao": "funcionalidades", "nome_erp": "Eccosys", "query_busca": "Eccosys", "resposta_esperada": "especifica"}}

Pergunta: "listar integrações"
JSON: {{"intencao": "listar", "nome_erp": null, "query_busca": null, "resposta_esperada": "lista"}}

IMPORTANTE:
- Retorne APENAS o JSON, sem texto adicional
- O nome_erp deve ser o mais exato possível (exatamente como aparece em documentos)
- A query_busca deve ser limpa, apenas palavras significativas
- Se não mencionar nenhum ERP específico, use null para nome_erp e query_busca

JSON:"""

        # Gerar resposta com retry
        max_retries = 2
        retry_delay = 1
        
        response = None
        for tentativa in range(max_retries):
            try:
                response = model.generate_content(prompt)
                break  # Sucesso, sair do loop
            except Exception as e:
                if tentativa < max_retries - 1:
                    logger.warning(f"⚠️ Erro na tentativa {tentativa + 1}/{max_retries}: {e}. Tentando novamente...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ Falha após {max_retries} tentativas: {e}")
                    raise
        
        if not response:
            raise Exception("Falha ao gerar resposta do Gemini")
        
        # Extrair JSON da resposta (pode vir com ```json ... ``` ou texto extra)
        resposta_texto = response.text.strip()
        
        # Remover wrapper ```json ... ``` ou ``` ... ```
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', resposta_texto)
        if code_block_match:
            resposta_texto = code_block_match.group(1).strip()
        
        # Tentar extrair JSON (suporta objetos aninhados com múltiplos })
        json_match = re.search(r'\{[\s\S]*\}', resposta_texto)
        if json_match:
            resposta_texto = json_match.group(0)
        
        resultado = json.loads(resposta_texto)
        
        logger.info(f"✅ Intenção interpretada: {resultado.get('intencao')} | ERP: {resultado.get('nome_erp')}")
        
        return resultado
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erro ao decodificar JSON do Gemini: {e}")
        logger.error(f"   Resposta recebida: {resposta_texto[:200] if 'resposta_texto' in locals() else 'N/A'}")
        # Fallback: tentar extrair manualmente
        return {
            "intencao": "outro",
            "nome_erp": None,
            "query_busca": pergunta.lower().strip(),
            "resposta_esperada": "detalhada"
        }
    except Exception as e:
        logger.error(f"❌ Erro ao interpretar intenção: {e}")
        # Fallback
        return {
            "intencao": "outro",
            "nome_erp": None,
            "query_busca": pergunta.lower().strip(),
            "resposta_esperada": "detalhada"
        }

