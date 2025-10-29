"""
Sistema Recepcionista - Estilo Nina
Analisa a pergunta do usuário antes de processar
"""

import logging
from typing import Dict, Optional
from handlers.gemini_handler import get_gemini_response
import json
import re

logger = logging.getLogger(__name__)

# Prompt da recepcionista (estilo Nina)
PROMPT_RECEPCIONISTA = """
You are an assistant in a chatbot system whose **only goal** is to understand the user's context and query.  
You must analyze the user's message **in the context of the full conversation**. This means you must **consider previous messages in the thread** to fully understand the user's intent and all required points, and you must identify the **language** (user_detected_language) and the **main intent** (user_intent).  

Your task is to analyze the user message and return **only** a JSON object with the following fields:

- **thoughts**  
  A concise internal reasoning of how you interpreted the message and filled the fields.  

- **user_detected_language**  
  Language in format (e.g. `pt`, `es`, `en`). Leave `""` if undetectable.  

- **user_intent**  
  Main intent detected: "search_knowledge", "list_integrations", "specific_integration", "greeting", "menu", "other".  

- **user_detailed_query**  
  Must **copy exactly the user's question**, without interpretation or modification. Clean the text removing mentions and formatting.  

- **needs_clarification**  
  If any of the above fields are unclear or undetectable, set to `true` and write a short and polite clarifying question in the same language as the user. Otherwise, set to `false`.  

- **clarification_message**  
  If needs_clarification is true, provide a clarifying question. Otherwise, return `""`.  

---

### Formatting Rules

- Return output **only as a JSON object**, no extra text.  
- Never assume missing information. Ask if uncertain.  
- Always write in the **same language as the user**.  
- For "list_integrations", detect when user asks "quais", "listar", "tem quais", etc.
- For "specific_integration", detect when user asks about a specific integration name.

"""


class Recepcionista:
    """
    Sistema de análise de pergunta (estilo Nina)
    Analisa a pergunta antes de buscar em fontes
    """
    
    def __init__(self):
        self.prompt_template = PROMPT_RECEPCIONISTA
        logger.info("✅ Recepcionista inicializada")
    
    def analisar_pergunta(self, pergunta_slack: str, contexto_thread: Optional[str] = None) -> Dict:
        """
        Analisa a pergunta do usuário (estilo Nina)
        
        Args:
            pergunta_slack: Pergunta original do Slack
            contexto_thread: Contexto das mensagens anteriores (opcional)
            
        Returns:
            dict com análise completa:
            - needs_clarification: bool
            - clarification_message: str
            - user_detected_language: str
            - user_intent: str
            - user_detailed_query: str
            - thoughts: str
        """
        logger.info("=== RECEPCIONISTA: Analisando pergunta ===")
        logger.debug(f"Pergunta: {pergunta_slack[:100]}...")
        
        # Limpar menções ao bot
        pergunta_limpa = self._limpar_mencoes(pergunta_slack)
        
        # Montar prompt completo
        prompt_completo = self.prompt_template
        
        if contexto_thread:
            prompt_completo += f"\n\n**Contexto da conversa anterior:**\n{contexto_thread}\n"
        
        prompt_completo += f"\n**Mensagem do usuário:**\n{pergunta_slack}"
        
        try:
            # Chamar Gemini para análise
            logger.debug("Chamando Gemini para análise da recepcionista")
            response = get_gemini_response(prompt_completo)
            
            if not response:
                logger.warning("Resposta vazia da recepcionista, usando fallback")
                return self._fallback_analysis(pergunta_limpa)
            
            # Processar resposta JSON
            analysis = self._parse_json_response(response)
            
            logger.info(f"✅ Análise completa: intent={analysis.get('user_intent')}, language={analysis.get('user_detected_language')}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Erro na recepcionista: {e}")
            return self._fallback_analysis(pergunta_limpa)
    
    def _limpar_mencoes(self, texto: str) -> str:
        """Remove menções ao bot do texto"""
        # Remover menções do tipo <@U...>
        texto_limpo = re.sub(r'<@[A-Z0-9]+>', '', texto).strip()
        return texto_limpo if texto_limpo else texto
    
    def _parse_json_response(self, response: str) -> Dict:
        """Extrai e parseia JSON da resposta"""
        try:
            # Remover markdown code blocks se presente
            json_text = response.strip()
            
            if "```json" in json_text:
                start = json_text.find("```json") + 7
                end = json_text.find("```", start)
                json_text = json_text[start:end].strip() if end > start else json_text
            elif json_text.startswith("```") and json_text.endswith("```"):
                json_text = json_text[3:-3].strip()
            
            # Parsear JSON
            analysis = json.loads(json_text)
            
            # Validar campos obrigatórios
            required_fields = ['user_intent', 'user_detailed_query', 'needs_clarification']
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Campo '{field}' ausente na análise, usando padrão")
                    if field == 'needs_clarification':
                        analysis[field] = False
                    else:
                        analysis[field] = ""
            
            # Garantir tipos corretos
            analysis['needs_clarification'] = bool(analysis.get('needs_clarification', False))
            analysis['clarification_message'] = analysis.get('clarification_message', '')
            analysis['user_detected_language'] = analysis.get('user_detected_language', 'pt')
            analysis['user_intent'] = analysis.get('user_intent', 'search_knowledge')
            analysis['user_detailed_query'] = analysis.get('user_detailed_query', '')
            analysis['thoughts'] = analysis.get('thoughts', '')
            
            return analysis
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Erro ao parsear JSON da recepcionista: {e}. Usando fallback")
            return self._fallback_analysis(response)
    
    def _fallback_analysis(self, pergunta: str) -> Dict:
        """Análise fallback quando Gemini falha"""
        logger.info("Usando análise fallback")
        
        pergunta_lower = pergunta.lower()
        
        # Detecção simples de intent
        intent = 'search_knowledge'  # default
        if any(word in pergunta_lower for word in ['listar', 'quais', 'tem quais', 'quantas']):
            if any(word in pergunta_lower for word in ['integrac', 'parceir', 'sistem']):
                intent = 'list_integrations'
        elif any(word in pergunta_lower for word in ['oi', 'olá', 'hello', 'bom dia']):
            intent = 'greeting'
        elif any(word in pergunta_lower for word in ['menu', 'ajuda', 'help']):
            intent = 'menu'
        
        # Detecção simples de idioma
        language = 'pt'
        if any(word in pergunta_lower for word in ['how', 'what', 'when', 'where']):
            language = 'en'
        elif any(word in pergunta_lower for word in ['cómo', 'qué', 'cuándo']):
            language = 'es'
        
        return {
            'needs_clarification': False,
            'clarification_message': '',
            'user_detected_language': language,
            'user_intent': intent,
            'user_detailed_query': pergunta,
            'thoughts': 'Análise fallback - detecção simples'
        }

