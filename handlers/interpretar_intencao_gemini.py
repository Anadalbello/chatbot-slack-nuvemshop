#!/usr/bin/env python3
"""
Módulo para usar Gemini para interpretar a intenção do usuário antes de buscar
"""

import os
import logging
import json
import re
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from handlers.buscar_integracoes_json import normalizar_typos_nome_integracao_na_query
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
    model_name="models/gemini-2.5-flash",  # Modelo estável e disponível na API
    generation_config={
        "temperature": 0.3,  # Menor temperatura para respostas mais precisas
        "top_p": 0.95,
        "top_k": 40,
        # Resposta JSON era truncada (~200 tok) e quebrava json.loads; precisa caber o objeto inteiro
        "max_output_tokens": 512,
    },
    safety_settings=safety_settings
)


def _extrair_intencao_json_parcial(texto: str) -> Optional[Dict[str, Any]]:
    """Se o Gemini truncar o JSON no meio, tenta extrair campos com regex."""
    if not texto or not texto.strip().startswith("{"):
        return None
    int_m = re.search(r'"intencao"\s*:\s*"([^"]*)"', texto)
    nome_m = re.search(r'"nome_erp"\s*:\s*"([^"]*)"', texto)
    nome_null = re.search(r'"nome_erp"\s*:\s*null', texto, re.I)
    qb_m = re.search(r'"query_busca"\s*:\s*"([^"]*)"', texto)
    resp_m = re.search(r'"resposta_esperada"\s*:\s*"([^"]*)"', texto)
    if not int_m and not nome_m and not nome_null and not qb_m:
        return None
    nome_val = None if nome_null else (nome_m.group(1) if nome_m else None)
    qb_val = qb_m.group(1) if qb_m else nome_val
    return {
        "intencao": int_m.group(1) if int_m else "funcionalidades",
        "nome_erp": nome_val,
        "query_busca": qb_val,
        "resposta_esperada": resp_m.group(1) if resp_m else "sim_nao",
    }


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
        pergunta = normalizar_typos_nome_integracao_na_query(pergunta)
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
- NÃO confunda integrações: "Jet", "jet." ou "Jet e-commerce" referem-se à integração oficial **jet.** (com ponto), NÃO a "Wake Commerce" nem outras plataformas.

EXEMPLO Jet:
Pergunta: "a jet. calcula frete com peso cubado?" ou "@Tina o Jet tem peso cubado?"
JSON: {{"intencao": "funcionalidades", "nome_erp": "jet.", "query_busca": "jet.", "resposta_esperada": "sim_nao"}}

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
        parcial = _extrair_intencao_json_parcial(resposta_texto) if "resposta_texto" in locals() else None
        if parcial:
            logger.info(f"✅ Intenção recuperada por regex (JSON truncado): {parcial}")
            return parcial
        # Fallback: heurística jet. se a pergunta citar jet
        pq = pergunta.lower()
        if re.search(r"\bjet\b|jet\.|jetcommerce", pq):
            return {
                "intencao": "funcionalidades",
                "nome_erp": "jet.",
                "query_busca": "jet.",
                "resposta_esperada": "sim_nao",
            }
        return {
            "intencao": "outro",
            "nome_erp": None,
            "query_busca": normalizar_typos_nome_integracao_na_query(pergunta.lower().strip()),
            "resposta_esperada": "detalhada"
        }
    except Exception as e:
        logger.error(f"❌ Erro ao interpretar intenção: {e}")
        # Fallback
        return {
            "intencao": "outro",
            "nome_erp": None,
            "query_busca": normalizar_typos_nome_integracao_na_query(pergunta.lower().strip()),
            "resposta_esperada": "detalhada"
        }

