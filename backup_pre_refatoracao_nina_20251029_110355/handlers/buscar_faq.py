"""
Handler para buscar perguntas frequentes (FAQ) em arquivo JSON
"""

import json
import os
import logging
from difflib import SequenceMatcher

# Configurar logger
logger = logging.getLogger(__name__)

# Caminho do arquivo FAQ
FAQ_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'faq_database.json')

def carregar_faqs():
    """
    Carrega as FAQs do arquivo JSON
    """
    try:
        if not os.path.exists(FAQ_FILE):
            logger.warning(f"⚠️ Arquivo FAQ não encontrado: {FAQ_FILE}")
            return []
        
        with open(FAQ_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            faqs = data.get('faqs', [])
            logger.info(f"✅ Carregadas {len(faqs)} FAQs do arquivo")
            return faqs
    except Exception as e:
        logger.error(f"❌ Erro ao carregar FAQs: {e}")
        return []


def calcular_similaridade(texto1, texto2):
    """
    Calcula a similaridade entre dois textos (0 a 1)
    Usa SequenceMatcher do Python
    """
    texto1 = texto1.lower().strip()
    texto2 = texto2.lower().strip()
    return SequenceMatcher(None, texto1, texto2).ratio()


def normalizar_texto(texto):
    """
    Normaliza o texto removendo acentos e caracteres especiais
    """
    # Remover acentos comuns
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
        'é': 'e', 'ê': 'e',
        'í': 'i',
        'ó': 'o', 'õ': 'o', 'ô': 'o',
        'ú': 'u',
        'ç': 'c'
    }
    
    texto = texto.lower()
    for old, new in replacements.items():
        texto = texto.replace(old, new)
    
    return texto


def buscar_faq(pergunta, threshold=0.6):
    """
    Busca uma FAQ que corresponda à pergunta
    
    Args:
        pergunta: Pergunta do usuário
        threshold: Confiança mínima (0-1) para considerar uma correspondência
        
    Returns:
        dict com a FAQ encontrada ou None
    """
    try:
        logger.info(f"🔍 Buscando FAQ para: '{pergunta}'")
        
        faqs = carregar_faqs()
        
        if not faqs:
            logger.warning("⚠️ Nenhuma FAQ disponível")
            return None
        
        pergunta_normalizada = normalizar_texto(pergunta)
        melhor_match = None
        melhor_score = 0
        
        for faq in faqs:
            # Pular FAQs inativas
            if not faq.get('ativo', True):
                continue
            
            # Calcular similaridade com a pergunta principal
            score_pergunta = calcular_similaridade(
                pergunta_normalizada,
                normalizar_texto(faq['pergunta'])
            )
            
            # Calcular similaridade com as palavras-chave
            palavras_chave = faq.get('palavras_chave', [])
            score_keywords = 0
            
            for keyword in palavras_chave:
                keyword_normalizado = normalizar_texto(keyword)
                
                # Se a palavra-chave está contida na pergunta, score alto
                if keyword_normalizado in pergunta_normalizada:
                    score_keywords = max(score_keywords, 0.9)
                else:
                    # Senão, calcular similaridade parcial
                    score_keywords = max(
                        score_keywords,
                        calcular_similaridade(pergunta_normalizada, keyword_normalizado)
                    )
            
            # Score final: média ponderada (70% keywords, 30% pergunta)
            score_final = (score_keywords * 0.7) + (score_pergunta * 0.3)
            
            logger.debug(f"  FAQ '{faq['id']}': score={score_final:.2f} (pergunta={score_pergunta:.2f}, keywords={score_keywords:.2f})")
            
            if score_final > melhor_score:
                melhor_score = score_final
                melhor_match = faq
        
        # Verificar se o melhor match é bom o suficiente
        if melhor_match and melhor_score >= threshold:
            logger.info(f"✅ FAQ encontrada: '{melhor_match['id']}' (confiança: {melhor_score:.0%})")
            return {
                'faq': melhor_match,
                'confianca': melhor_score
            }
        else:
            logger.info(f"❌ Nenhuma FAQ com confiança suficiente (melhor: {melhor_score:.0%})")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao buscar FAQ: {e}")
        import traceback
        traceback.print_exc()
        return None


def formatar_resposta_faq(resultado):
    """
    Formata a resposta da FAQ para enviar ao Slack
    
    Args:
        resultado: dict com 'faq' e 'confianca'
        
    Returns:
        string formatada para Slack (Markdown)
    """
    try:
        faq = resultado['faq']
        confianca = resultado['confianca']
        
        resposta = f"**{faq['pergunta']}**\n\n"
        resposta += faq['resposta']
        
        # Adicionar link se existir
        if faq.get('link'):
            resposta += f"\n\n🔗 **Saiba mais:** {faq['link']}"
        
        # Adicionar nota de confiança se for < 90%
        if confianca < 0.9:
            resposta += f"\n\n_💡 Essa resposta foi encontrada com {confianca:.0%} de confiança. Se não for o que procura, me pergunte de outra forma._"
        
        logger.info(f"✅ Resposta FAQ formatada: {len(resposta)} caracteres")
        return resposta
        
    except Exception as e:
        logger.error(f"❌ Erro ao formatar resposta FAQ: {e}")
        return None


def adicionar_faq(pergunta, palavras_chave, resposta, link="", categoria="geral", prioridade="media"):
    """
    Adiciona uma nova FAQ ao arquivo JSON
    
    Args:
        pergunta: Pergunta principal
        palavras_chave: Lista de palavras-chave
        resposta: Resposta formatada
        link: Link opcional para mais informações
        categoria: Categoria da FAQ (geral, api, integracao, etc)
        prioridade: Prioridade (alta, media, baixa)
        
    Returns:
        bool indicando sucesso
    """
    try:
        # Carregar FAQs existentes
        with open(FAQ_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        faqs = data.get('faqs', [])
        
        # Gerar ID único
        ultimo_id = max([int(faq['id'].split('_')[1]) for faq in faqs], default=0)
        novo_id = f"faq_{str(ultimo_id + 1).zfill(3)}"
        
        # Criar nova FAQ
        from datetime import datetime
        nova_faq = {
            "id": novo_id,
            "pergunta": pergunta,
            "palavras_chave": palavras_chave,
            "resposta": resposta,
            "link": link,
            "prioridade": prioridade,
            "categoria": categoria,
            "ativo": True,
            "criado_em": datetime.now().strftime("%Y-%m-%d"),
            "atualizado_em": datetime.now().strftime("%Y-%m-%d")
        }
        
        faqs.append(nova_faq)
        data['faqs'] = faqs
        data['metadata']['total_faqs'] = len(faqs)
        data['metadata']['ultima_atualizacao'] = datetime.now().isoformat()
        
        # Salvar de volta
        with open(FAQ_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Nova FAQ adicionada: {novo_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar FAQ: {e}")
        return False


if __name__ == "__main__":
    # Teste local
    logging.basicConfig(level=logging.INFO)
    
    print("=== Teste do sistema de FAQ ===\n")
    
    testes = [
        "como integrar magento?",
        "temos integração com tray",
        "calcular frete api",
        "quais integrações disponíveis",
        "webhook notificação",
        "como funciona o sistema?"  # Não deve encontrar
    ]
    
    for pergunta in testes:
        print(f"\n📝 Pergunta: {pergunta}")
        resultado = buscar_faq(pergunta)
        
        if resultado:
            print(f"✅ FAQ encontrada: {resultado['faq']['id']} ({resultado['confianca']:.0%})")
            print(f"Resposta:\n{formatar_resposta_faq(resultado)[:200]}...")
        else:
            print("❌ Nenhuma FAQ encontrada")

