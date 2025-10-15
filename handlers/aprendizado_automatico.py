"""
Sistema de aprendizado automático para FAQs
Registra perguntas e automaticamente cria FAQs quando detecta padrões
"""

import json
import os
import logging
from datetime import datetime
from difflib import SequenceMatcher
from handlers.buscar_faq import adicionar_faq, normalizar_texto

# Configurar logger
logger = logging.getLogger(__name__)

# Caminhos dos arquivos
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'perguntas_log.json')
FAQ_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'faq_database.json')

# Configurações
MIN_REPETICOES = 3  # Quantas vezes a pergunta precisa aparecer
SIMILARIDADE_MINIMA = 0.75  # Similaridade para considerar perguntas iguais


def carregar_log():
    """Carrega o log de perguntas"""
    try:
        if not os.path.exists(LOG_FILE):
            return {"perguntas": [], "metadata": {"total_perguntas": 0, "faqs_auto_geradas": 0}}
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Erro ao carregar log: {e}")
        return {"perguntas": [], "metadata": {"total_perguntas": 0, "faqs_auto_geradas": 0}}


def salvar_log(data):
    """Salva o log de perguntas"""
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao salvar log: {e}")
        return False


def encontrar_pergunta_similar(pergunta, log_data):
    """
    Encontra se já existe uma pergunta similar no log
    Retorna o índice da pergunta ou None
    """
    pergunta_norm = normalizar_texto(pergunta)
    
    for i, item in enumerate(log_data['perguntas']):
        item_pergunta_norm = normalizar_texto(item['pergunta'])
        similaridade = SequenceMatcher(None, pergunta_norm, item_pergunta_norm).ratio()
        
        if similaridade >= SIMILARIDADE_MINIMA:
            return i
    
    return None


def registrar_pergunta(pergunta, resposta_encontrada=None, fonte=None):
    """
    Registra uma pergunta no log e verifica se deve criar FAQ
    
    Args:
        pergunta: Pergunta do usuário
        resposta_encontrada: Resposta que foi dada (se houver)
        fonte: De onde veio a resposta (confluence, zendesk, faq)
        
    Returns:
        dict com informações sobre se foi criada FAQ
    """
    try:
        logger.info(f"📝 Registrando pergunta: '{pergunta}' (fonte: {fonte})")
        
        # Carregar log
        log_data = carregar_log()
        
        # Verificar se já existe pergunta similar
        idx_similar = encontrar_pergunta_similar(pergunta, log_data)
        
        if idx_similar is not None:
            # Incrementar contador da pergunta existente
            log_data['perguntas'][idx_similar]['contador'] += 1
            log_data['perguntas'][idx_similar]['ultima_vez'] = datetime.now().isoformat()
            
            # Atualizar melhor resposta se foi fornecida
            if resposta_encontrada and fonte:
                # Priorizar Confluence > Zendesk
                fonte_atual = log_data['perguntas'][idx_similar].get('fonte')
                if not fonte_atual or (fonte == 'confluence' and fonte_atual != 'confluence'):
                    log_data['perguntas'][idx_similar]['melhor_resposta'] = resposta_encontrada
                    log_data['perguntas'][idx_similar]['fonte'] = fonte
            
            contador = log_data['perguntas'][idx_similar]['contador']
            logger.info(f"✅ Pergunta similar encontrada (apareceu {contador} vezes)")
            
            # Verificar se deve criar FAQ automaticamente
            if contador >= MIN_REPETICOES and not log_data['perguntas'][idx_similar].get('faq_criada'):
                logger.info(f"🤖 Pergunta atingiu {MIN_REPETICOES}+ aparições, criando FAQ automaticamente...")
                
                sucesso = criar_faq_automatica(log_data['perguntas'][idx_similar])
                
                if sucesso:
                    log_data['perguntas'][idx_similar]['faq_criada'] = True
                    log_data['perguntas'][idx_similar]['faq_criada_em'] = datetime.now().isoformat()
                    log_data['metadata']['faqs_auto_geradas'] = log_data['metadata'].get('faqs_auto_geradas', 0) + 1
                    
                    salvar_log(log_data)
                    
                    return {
                        'faq_criada': True,
                        'contador': contador,
                        'pergunta': log_data['perguntas'][idx_similar]['pergunta']
                    }
        else:
            # Adicionar nova pergunta ao log
            nova_pergunta = {
                'pergunta': pergunta,
                'contador': 1,
                'primeira_vez': datetime.now().isoformat(),
                'ultima_vez': datetime.now().isoformat(),
                'melhor_resposta': resposta_encontrada,
                'fonte': fonte,
                'faq_criada': False
            }
            
            log_data['perguntas'].append(nova_pergunta)
            log_data['metadata']['total_perguntas'] = len(log_data['perguntas'])
            
            logger.info(f"✅ Nova pergunta adicionada ao log")
        
        # Salvar log
        salvar_log(log_data)
        
        return {
            'faq_criada': False,
            'contador': 1 if idx_similar is None else log_data['perguntas'][idx_similar]['contador']
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar pergunta: {e}")
        import traceback
        traceback.print_exc()
        return {'faq_criada': False, 'contador': 0}


def criar_faq_automatica(pergunta_data):
    """
    Cria uma FAQ automaticamente baseada nos dados do log
    
    Args:
        pergunta_data: Dados da pergunta do log
        
    Returns:
        bool indicando sucesso
    """
    try:
        pergunta = pergunta_data['pergunta']
        resposta = pergunta_data.get('melhor_resposta', '')
        fonte = pergunta_data.get('fonte', 'desconhecida')
        
        if not resposta:
            logger.warning(f"⚠️ Não há resposta para criar FAQ: {pergunta}")
            return False
        
        # Extrair palavras-chave da pergunta
        palavras_chave = extrair_palavras_chave(pergunta)
        
        # Determinar categoria baseada na fonte
        categoria = 'geral'
        if 'integra' in pergunta.lower():
            categoria = 'integracao'
        elif 'api' in pergunta.lower() or 'webhook' in pergunta.lower():
            categoria = 'api'
        elif 'frete' in pergunta.lower():
            categoria = 'frete'
        
        # Formatar resposta
        resposta_formatada = f"**{pergunta}**\n\n{resposta}\n\n"
        resposta_formatada += f"_📊 FAQ gerada automaticamente após {pergunta_data['contador']} solicitações._"
        
        # Adicionar ao arquivo FAQ
        sucesso = adicionar_faq(
            pergunta=pergunta,
            palavras_chave=palavras_chave,
            resposta=resposta_formatada,
            link="",
            categoria=categoria,
            prioridade="media"
        )
        
        if sucesso:
            logger.info(f"✅ FAQ automática criada com sucesso: {pergunta}")
        else:
            logger.error(f"❌ Falha ao criar FAQ automática: {pergunta}")
        
        return sucesso
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar FAQ automática: {e}")
        return False


def extrair_palavras_chave(pergunta):
    """
    Extrai palavras-chave de uma pergunta
    Remove stop words e retorna termos relevantes
    """
    stop_words = {
        'como', 'qual', 'quais', 'onde', 'quando', 'porque', 'o', 'a', 'os', 'as',
        'um', 'uma', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas',
        'com', 'para', 'por', 'que', 'é', 'são', 'tem', 'temos', 'posso', 'pode',
        'fazer', 'funciona', 'sobre', 'me', 'meu', 'minha'
    }
    
    # Dividir em palavras e remover stop words
    palavras = pergunta.lower().split()
    palavras_filtradas = [p for p in palavras if p not in stop_words and len(p) > 2]
    
    return palavras_filtradas[:5]  # Máximo 5 palavras-chave


def obter_estatisticas():
    """
    Retorna estatísticas sobre as perguntas registradas
    """
    try:
        log_data = carregar_log()
        
        total_perguntas = len(log_data['perguntas'])
        total_repeticoes = sum(p['contador'] for p in log_data['perguntas'])
        faqs_criadas = sum(1 for p in log_data['perguntas'] if p.get('faq_criada'))
        
        # Top 10 perguntas mais frequentes
        top_perguntas = sorted(
            log_data['perguntas'],
            key=lambda x: x['contador'],
            reverse=True
        )[:10]
        
        return {
            'total_perguntas_unicas': total_perguntas,
            'total_perguntas_feitas': total_repeticoes,
            'faqs_auto_geradas': faqs_criadas,
            'top_perguntas': [
                {
                    'pergunta': p['pergunta'],
                    'contador': p['contador'],
                    'faq_criada': p.get('faq_criada', False)
                }
                for p in top_perguntas
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {e}")
        return None


if __name__ == "__main__":
    # Teste local
    logging.basicConfig(level=logging.INFO)
    
    print("=== Teste do sistema de aprendizado automático ===\n")
    
    # Simular algumas perguntas
    perguntas_teste = [
        ("como integrar magento?", "Veja a documentação...", "confluence"),
        ("como integrar com magento", "Veja a documentação...", "confluence"),
        ("magento integração", "Veja a documentação...", "confluence"),
        ("como integrar shopify?", "Shopify docs...", "zendesk"),
        ("integração shopify", "Shopify docs...", "zendesk"),
    ]
    
    for pergunta, resposta, fonte in perguntas_teste:
        print(f"\n📝 Registrando: {pergunta}")
        resultado = registrar_pergunta(pergunta, resposta, fonte)
        
        if resultado['faq_criada']:
            print(f"🎉 FAQ CRIADA! Pergunta apareceu {resultado['contador']} vezes")
        else:
            print(f"📊 Contador: {resultado['contador']}")
    
    print("\n\n=== Estatísticas ===")
    stats = obter_estatisticas()
    print(json.dumps(stats, indent=2, ensure_ascii=False))

