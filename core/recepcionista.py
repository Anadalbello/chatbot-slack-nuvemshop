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

# Configuração de classificação de query (estilo Nina)
CLASSIFICATION_CONFIG = {
    "help_center_keywords": [
        "how to", "como fazer", "como configurar", "tutorial", "ajuda com",
        "configurar", "configuração", "configura", "setup", "instalar",
        "problema", "erro", "não funciona", "não está funcionando",
        "troubleshooting", "resolver", "solução", "corrigir"
    ],
    "apps_keywords": [
        "app", "aplicativo", "aplicação", "plugin", "integração",
        "qual app", "qual aplicativo", "recomend", "sugestão",
        "app for", "app para", "melhor app", "best app"
    ],
    "default_type": "apps",  # Default to apps if unclear
    "enable_logging": True,  # Enable detailed classification logging
    "override_on_strong_signal": False,  # Enable strict mode to override AI classification
    "override_margin": 3  # Minimum margin to override AI classification
}

# Prompt da recepcionista (estilo Nina - melhorado)
PROMPT_RECEPCIONISTA = """
You are an assistant in a chatbot system whose **only goal** is to understand the user's context and query.  
You must analyze the user's message **in the context of the full conversation**. This means you must **consider previous messages in the thread** to fully understand the user's intent and all required points, and you must identify the **language** (user_detected_language), the **country** (query_detected_country), and the **query type** (query_type).

Your task is to analyze the user message and return **only** a JSON object with the following fields:

- **thoughts**  
  A concise internal reasoning of how you interpreted the message and filled the fields.

- **query_type**  
  Classify the query as either `"apps"` or `"help_center"` based on the user's intent:
  - Use `"apps"` if the user is asking about which applications/plugins to use, recommendations, or app availability.
  - Use `"help_center"` if the user is asking how to do something, needs tutorials, configuration help, troubleshooting, or general platform guidance.
  - If unclear, default to `"apps"`.

- **query_detected_country**  
  ISO country code (e.g. `AR`, `MX`, `CO`, `BR`, `PT`) that the user's inquiry refers to.
  **IMPORTANT**: 
  - If explicitly mentioned (e.g., "para Argentina", "para o brasil") → use that country
  - If language is `pt` or `pt_BR` → ALWAYS infer `BR` (Portuguese = Brazil, only Portuguese-speaking country)
  - If language has specific Spanish region (e.g., `es_AR`, `es_MX`, `es_CO`) → infer the country from the region
  - If language is generic Spanish (`es` without region) → leave `""` to trigger follow-up question
  Leave `""` only for generic Spanish without explicit country mention.  

- **user_detected_language**  
  Language and region tag in BCP-47 format (e.g. `pt_BR`, `es_AR`, `es_MX`). Leave `""` if undetectable.  

- **user_detailed_query**  
  If the user's message is a confirmation (like "sim", "isso mesmo", "correto", "yes", "that's right") or a short answer to a previous question, you MUST reconstruct the original question from the context using the information mentioned in the thread. For example:
  - If context mentions "Tray" and user says "isso mesmo", the query should be the original question about Tray.
  - If context mentions "ela tem etiquetas?" and user confirms, reconstruct: "Tray tem etiquetas?"
  - Otherwise, copy exactly the user's question without interpretation.

- **follow_up_message**  
  Write a polite clarifying question if query_detected_country is empty/unclear.
  Ask the user to specify which country they are asking about.
  Examples:
  - In Spanish: "¿Para qué país necesitas esta información? (Argentina, México, Colombia, Chile o Brasil)"
  - In Portuguese: "Para qual país você precisa dessa informação? (Brasil, Argentina, México, Colômbia ou Chile)"
  
  If country is clear, return `""`.

---

### Formatting Rules

- Return output **only as a JSON object**, no extra text.  
- Always write in the **same language as the user**.  
- **IMPORTANT**: 
  - Portuguese (`pt` or `pt_BR`) → ALWAYS infer `BR` (Brazil is the only Portuguese-speaking country)
  - Spanish with region (`es_AR`, `es_MX`, etc.) → infer country from region
  - Generic Spanish (`es`) without explicit mention → leave empty and ask
- Country inference priority: Explicit mention > Portuguese=BR > Language region code > Ask user.  
- For query_type classification:
  - Questions about "which app", "recommend app", "app for X" → `"apps"`
  - Questions about "how to", "configure", "tutorial", "help with" → `"help_center"`
  - When in doubt, use `"apps"`
- **CRITICAL:** If the user's message is a confirmation/answer to a previous question (detected by context), reconstruct the full question from context instead of using the short confirmation.

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
        Analisa a pergunta do usuário (estilo Nina - melhorado)
        
        Args:
            pergunta_slack: Pergunta original do Slack
            contexto_thread: Contexto das mensagens anteriores (opcional)
            
        Returns:
            dict com análise completa:
            - needs_clarification: bool
            - follow_up_message: str (mensagem de esclarecimento)
            - query_detected_country: str (código do país: BR, AR, MX, etc.)
            - user_detected_language: str (idioma em formato BCP-47: pt_BR, es_AR, etc.)
            - query_type: str ("apps" ou "help_center")
            - user_intent: str (intent interno: search_knowledge, list_integrations, etc.)
            - user_detailed_query: str (query processada)
            - thoughts: str (raciocínio da análise)
        """
        logger.info("=== RECEPCIONISTA: Analisando pergunta ===")
        logger.debug(f"Pergunta: {pergunta_slack[:100]}...")
        
        # Limpar menções ao bot
        pergunta_limpa = self._limpar_mencoes(pergunta_slack)
        
        # Montar prompt completo
        prompt_completo = self.prompt_template
        
        if contexto_thread:
            prompt_completo += f"\n\n**Contexto da conversa anterior:**\n{contexto_thread}\n"
            prompt_completo += "\n**IMPORTANTE:** Se a mensagem do usuário for uma confirmação (como 'sim', 'isso mesmo', 'correto') ou resposta curta, você DEVE reconstruir a pergunta original usando o contexto acima. Por exemplo:\n"
            prompt_completo += "- Se contexto menciona 'Tray' e usuário diz 'isso mesmo', reconstrua a pergunta sobre Tray.\n"
            prompt_completo += "- Se contexto mostra pergunta 'ela tem etiquetas?' e usuário confirma, reconstrua: 'Tray tem etiquetas?'\n"
        
        prompt_completo += f"\n**Mensagem do usuário:**\n{pergunta_slack}"
        
        try:
            # Chamar Gemini para análise
            logger.debug("Chamando Gemini para análise da recepcionista")
            response = get_gemini_response(prompt_completo)
            
            if not response:
                logger.warning("⚠️ Resposta vazia da recepcionista, usando fallback")
                return self._fallback_analysis(pergunta_limpa)
            
            # Verificar se a resposta é uma mensagem de erro
            # Verificação mais específica para evitar falsos positivos
            if response.startswith("Erro ao acessar Gemini"):
                # Detectar se é erro de quota para log mais conciso
                erro_detalhado = response.replace("Erro ao acessar Gemini: ", "")
                if "429" in erro_detalhado or "quota" in erro_detalhado.lower():
                    logger.debug("🔄 Gemini quota excedida na recepcionista, usando fallback")
                else:
                    logger.warning(f"⚠️ Erro do Gemini na recepcionista: {erro_detalhado[:80]}...")
                logger.info("🔄 Usando análise fallback")
                return self._fallback_analysis(pergunta_limpa)
            
            # Verificar se começa com "error" (case insensitive) - mais específico
            response_lower_start = response.strip()[:50].lower()
            if response_lower_start.startswith("error") and "erro ao acessar" not in response_lower_start:
                # Pode ser um JSON válido que começa com "error" em algum campo, verificar melhor
                if not response.strip().startswith("{") and not response.strip().startswith("```"):
                    logger.warning(f"⚠️ Resposta da recepcionista parece ser erro: {response[:100]}")
                    logger.info("🔄 Usando análise fallback")
                    return self._fallback_analysis(pergunta_limpa)
            
            # Processar resposta JSON
            try:
                analysis = self._parse_json_response(response, pergunta_limpa)
            except Exception as parse_error:
                logger.warning(f"⚠️ Erro ao parsear JSON da recepcionista: {parse_error}")
                logger.debug(f"Resposta recebida: {response[:200]}...")
                logger.info("🔄 Usando análise fallback")
                return self._fallback_analysis(pergunta_limpa)
            
            # Garantir que user_detailed_query não seja uma mensagem de erro
            user_query = analysis.get('user_detailed_query', '')
            if user_query.startswith("Erro ao acessar Gemini"):
                logger.warning("⚠️ user_detailed_query contém erro, usando pergunta original")
                analysis['user_detailed_query'] = pergunta_limpa
            
            # Inferir país baseado em idioma se não detectado
            analysis = self._infer_country_from_language(analysis)
            
            # Validar classificação de query usando keywords
            analysis['query_type'] = self._validate_query_classification(
                analysis.get('user_detailed_query', ''),
                analysis.get('query_type', 'apps')
            )
            
            # Determinar needs_clarification baseado em follow_up_message
            follow_up = analysis.get('follow_up_message', '')
            analysis['needs_clarification'] = bool(follow_up and follow_up.strip())
            analysis['clarification_message'] = follow_up  # Compatibilidade com código antigo
            
            logger.info(f"✅ Análise completa: query_type={analysis.get('query_type')}, country={analysis.get('query_detected_country')}, language={analysis.get('user_detected_language')}, intent={analysis.get('user_intent')}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Erro na recepcionista: {e}")
            return self._fallback_analysis(pergunta_limpa)
    
    def _limpar_mencoes(self, texto: str) -> str:
        """Remove menções ao bot do texto"""
        # Remover menções do tipo <@U...>
        texto_limpo = re.sub(r'<@[A-Z0-9]+>', '', texto).strip()
        return texto_limpo if texto_limpo else texto
    
    def _parse_json_response(self, response: str, pergunta_limpa: str = "") -> Dict:
        """Extrai e parseia JSON da resposta"""
        try:
            # Verificar se a resposta é uma mensagem de erro antes de processar
            if response.startswith("Erro ao acessar Gemini"):
                logger.warning("⚠️ Resposta contém erro do Gemini, não é JSON válido")
                raise json.JSONDecodeError("Resposta contém erro", response, 0)
            
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
            
            # Validar e preencher campos obrigatórios
            analysis['user_detailed_query'] = analysis.get('user_detailed_query', pergunta_limpa or '')
            analysis['query_detected_country'] = analysis.get('query_detected_country', '')
            analysis['user_detected_language'] = analysis.get('user_detected_language', 'pt')
            analysis['query_type'] = analysis.get('query_type', 'apps').strip().lower()
            analysis['follow_up_message'] = analysis.get('follow_up_message', '')
            analysis['thoughts'] = analysis.get('thoughts', '')
            
            # Validar query_type
            if analysis['query_type'] not in ['apps', 'help_center']:
                logger.warning(f"query_type inválido '{analysis['query_type']}', usando 'apps'")
                analysis['query_type'] = 'apps'
            
            # Mapear query_type para user_intent (compatibilidade)
            if analysis['query_type'] == 'help_center':
                analysis['user_intent'] = 'search_knowledge'
            else:
                # Detectar intent baseado em keywords
                query_lower = analysis['user_detailed_query'].lower()
                if any(word in query_lower for word in ['listar', 'quais', 'tem quais', 'quantas']):
                    analysis['user_intent'] = 'list_integrations'
                elif any(word in query_lower for word in ['oi', 'olá', 'hello', 'bom dia']):
                    analysis['user_intent'] = 'greeting'
                elif any(word in query_lower for word in ['menu', 'ajuda', 'help']):
                    analysis['user_intent'] = 'menu'
                else:
                    analysis['user_intent'] = 'search_knowledge'
            
            return analysis
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Erro ao parsear JSON da recepcionista: {e}. Usando fallback")
            return self._fallback_analysis(pergunta_limpa or response)
    
    def _validate_query_classification(self, user_query: str, ai_classification: str) -> str:
        """
        Valida classificação de query usando keywords (estilo Nina)
        
        Args:
            user_query: Query do usuário
            ai_classification: Classificação da IA ('apps' ou 'help_center')
            
        Returns:
            Classificação validada
        """
        if not CLASSIFICATION_CONFIG.get("enable_logging", True):
            return ai_classification
        
        query_lower = user_query.lower()
        
        # Contar matches de keywords
        help_center_matches = sum(1 for keyword in CLASSIFICATION_CONFIG["help_center_keywords"] 
                                  if keyword.lower() in query_lower)
        apps_matches = sum(1 for keyword in CLASSIFICATION_CONFIG["apps_keywords"] 
                           if keyword.lower() in query_lower)
        
        # Log análise de keywords
        if CLASSIFICATION_CONFIG.get("enable_logging", True):
            logger.debug(f"Keyword analysis - Help Center: {help_center_matches}, Apps: {apps_matches}")
        
        # Verificar se modo override está habilitado
        override_enabled = CLASSIFICATION_CONFIG.get("override_on_strong_signal", False)
        override_margin = CLASSIFICATION_CONFIG.get("override_margin", 3)
        
        # Se há sinal forte de keywords que contradiz IA, logar warning
        if help_center_matches > apps_matches + 2 and ai_classification == "apps":
            logger.warning(f"IA classificou como 'apps' mas sinal forte de 'help_center' detectado ({help_center_matches} matches)")
            
            # Override classificação da IA se habilitado e margem excedida
            if override_enabled and help_center_matches > apps_matches + override_margin:
                logger.info(f"Override: mudando classificação 'apps' para 'help_center' (margem: {help_center_matches - apps_matches})")
                return "help_center"
                
        elif apps_matches > help_center_matches + 2 and ai_classification == "help_center":
            logger.warning(f"IA classificou como 'help_center' mas sinal forte de 'apps' detectado ({apps_matches} matches)")
            
            # Override classificação da IA se habilitado e margem excedida
            if override_enabled and apps_matches > help_center_matches + override_margin:
                logger.info(f"Override: mudando classificação 'help_center' para 'apps' (margem: {apps_matches - help_center_matches})")
                return "apps"
        
        # Confiar na classificação da IA mas logar análise
        return ai_classification
    
    def _infer_country_from_language(self, analysis: Dict) -> Dict:
        """
        Infere país baseado no idioma detectado (estilo Nina)
        - pt/pt_BR → BR
        - es_AR → AR
        - es_MX → MX
        - es_CO → CO
        - es_CL → CL
        """
        detected_language = analysis.get('user_detected_language', '')
        detected_country = analysis.get('query_detected_country', '')
        
        # Se já tem país detectado, não inferir
        if detected_country:
            return analysis
        
        # Inferir baseado em idioma
        if not detected_language:
            return analysis
        
        lang_lower = detected_language.lower()
        
        # Português → Brasil
        if lang_lower in ['pt', 'pt_br']:
            analysis['query_detected_country'] = 'BR'
            logger.debug("País inferido: BR (português)")
        # Espanhol com região → país correspondente
        elif lang_lower.startswith('es_'):
            region = lang_lower.split('_')[1].upper()
            country_map = {
                'AR': 'AR', 'MX': 'MX', 'CO': 'CO', 
                'CL': 'CL', 'ES': 'ES', 'PE': 'PE'
            }
            if region in country_map:
                analysis['query_detected_country'] = country_map[region]
                logger.debug(f"País inferido: {country_map[region]} (espanhol {region})")
        
        return analysis
    
    def _fallback_analysis(self, pergunta: str) -> Dict:
        """Análise fallback quando Gemini falha"""
        logger.info("Usando análise fallback")
        
        pergunta_lower = pergunta.lower()
        
        # Detecção simples de query_type
        query_type = 'apps'  # default
        if any(word in pergunta_lower for word in ['como', 'how to', 'configurar', 'tutorial', 'ajuda com']):
            query_type = 'help_center'
        
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
        language = 'pt_BR'
        country = 'BR'  # Default para português
        if any(word in pergunta_lower for word in ['how', 'what', 'when', 'where']):
            language = 'en'
            country = ''  # Não inferir país para inglês
        elif any(word in pergunta_lower for word in ['cómo', 'qué', 'cuándo']):
            language = 'es'
            country = ''  # Espanhol genérico - precisa perguntar
        
        return {
            'needs_clarification': False,
            'clarification_message': '',
            'follow_up_message': '',
            'query_detected_country': country,
            'user_detected_language': language,
            'query_type': query_type,
            'user_intent': intent,
            'user_detailed_query': pergunta,
            'thoughts': 'Análise fallback - detecção simples'
        }


