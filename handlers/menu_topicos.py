#!/usr/bin/env python3
"""
Handler para o menu de tópicos e navegação hierárquica
"""

import logging
from handlers.buscar_integracoes_sheets_publico import buscar_integracoes_google_sheets_publico

logger = logging.getLogger(__name__)

# Mapeamento das categorias e suas colunas correspondentes
CATEGORIAS_MENU = {
    "topico_frete": {
        "nome": "🚚 Frete e Cálculo",
        "colunas": ["F", "K", "L", "N", "M"],
        "descricoes": {
            "F": "Cálculo de Frete",
            "K": "Seguro configurável no frete?", 
            "L": "Seguro configurável na criação de pedido?",
            "N": "Calcula peso cubado?",
            "M": "Manuais para integração/cálculo frete"
        }
    },
    "topico_pedidos": {
        "nome": "📦 Pedidos e Logística",
        "colunas": ["G", "H", "I", "O", "J", "O2"],
        "descricoes": {
            "G": "Importação de pedidos",
            "H": "Múltiplos Volumes (MV)",
            "I": "Etiqueta",
            "O": "Atualização de Status", 
            "J": "Devolução de Rastreio",
            "O2": "Multi CD"
        }
    },
    "topico_config": {
        "nome": "🧩 Configuração e Integração",
        "colunas": ["A", "B", "D", "E", "R", "P", "S"],
        "descricoes": {
            "A": "Nome",
            "B": "Tipo",
            "D": "Complexidade/prazo estimado da Integração (Setup)",
            "E": "Responsável pela Integração",
            "R": "Quem desenvolveu a integração?",
            "P": "Plataforma permite teste sem a presença do cliente?",
            "S": "Custos envolvidos"
        }
    },
    "topico_checkout": {
        "nome": "🛒 Checkout e Personalização",
        "colunas": ["J"],
        "descricoes": {
            "J": "Nome transportadora no checkout personalizável?"
        }
    },
    "topico_qualidade": {
        "nome": "🧠 Qualidade e Suporte",
        "colunas": ["T", "U", "V", "W"],
        "descricoes": {
            "T": "Qualidade percebida/deduzida da plataforma",
            "U": "Ausência de funcionalidades na plataforma",
            "V": "Volume de problemas abertos conosco",
            "W": "Suporte da empresa"
        }
    },
    "topico_observacoes": {
        "nome": "📝 Observações e Links",
        "colunas": ["C", "N2", "Y", "Z"],
        "descricoes": {
            "C": "Observação",
            "N2": "Observações",
            "Y": "Link da Plataforma",
            "Z": "Link da Plataforma"
        }
    }
}

def criar_menu_boas_vindas():
    """Cria o menu simplificado de boas-vindas (sem menu de tópicos)"""
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "👋 *Olá! Sou o assistente de integrações da Nuvem Envio*\n\nPosso ajudar você com:\n• Buscar informações sobre integrações\n• Listar integrações disponíveis\n• Responder perguntas sobre documentação\n\n*Como posso ajudá-lo hoje?*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔍 Fazer uma Pergunta"},
                        "value": "pesquisa_global",
                        "action_id": "pesquisa_global",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📋 Listar Integrações"},
                        "value": "listar_integracoes",
                        "action_id": "listar_integracoes"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_💡 Dica: Você pode fazer perguntas diretamente, como:_\n• Como integrar com Magento?\n• Temos integração com Tray?\n• Como calcular frete?\n\n_Eu busco automaticamente em Google Sheets, Confluence e Zendesk!_"
                }
            }
        ]
    }

def criar_submenu_topico(topico_id):
    """Cria o submenu para um tópico específico"""
    if topico_id not in CATEGORIAS_MENU:
        return None
    
    categoria = CATEGORIAS_MENU[topico_id]
    nome_categoria = categoria["nome"]
    descricoes = categoria["descricoes"]
    
    # Criar botões para cada coluna/opção
    botoes = []
    for coluna, descricao in descricoes.items():
        botoes.append({
            "type": "button",
            "text": {"type": "plain_text", "text": descricao},
            "value": f"{topico_id}_{coluna}",
            "action_id": f"submenu_opcao_{topico_id}_{coluna}"
        })
    
    # Dividir botões em grupos de 3 (limite do Slack)
    grupos_botoes = []
    for i in range(0, len(botoes), 3):
        grupos_botoes.append(botoes[i:i+3])
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📋 *{nome_categoria}*\n\nEscolha uma opção específica:"
            }
        }
    ]
    
    # Adicionar grupos de botões
    for grupo in grupos_botoes:
        blocks.append({
            "type": "actions",
            "elements": grupo
        })
    
    # Botão para voltar
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "⬅️ Voltar ao Menu Principal"},
                "value": "voltar_menu",
                "action_id": "voltar_menu"
            }
        ]
    })
    
    return {"blocks": blocks}

def buscar_por_topico_e_coluna(topico_id, coluna):
    """Busca informações específicas por tópico e coluna"""
    try:
        logger.info(f"🔍 Buscando informações para {topico_id} - coluna {coluna}")
        
        # Obter informações da categoria
        categoria = CATEGORIAS_MENU.get(topico_id, {})
        nome_categoria = categoria.get("nome", "Tópico")
        
        # Buscar a descrição correta da coluna
        descricoes = categoria.get("descricoes", {})
        descricao_coluna = descricoes.get(coluna)
        
        # Se não encontrar, tentar obter do mapeamento de fallback
        if not descricao_coluna:
            logger.warning(f"⚠️ Coluna {coluna} não encontrada para {topico_id}, usando descrição genérica")
            descricao_coluna = f"Opção {coluna}"
        
        # Buscar na tabela Google Sheets
        logger.info(f"📊 Buscando na tabela Google Sheets para coluna {coluna}")
        
        # Mostrar mensagem de busca para o usuário
        resposta = f"🔍 *Buscando em {descricao_coluna}...*\n\n"
        
        lista_integracoes = buscar_integracoes_google_sheets_publico()
        
        if lista_integracoes:
            logger.info("✅ Dados da tabela Google Sheets obtidos")
            # Continuar a resposta com as informações
        else:
            logger.warning("⚠️ Não foi possível acessar a tabela Google Sheets")
            # Continuar a resposta com informações estáticas
        
        # Adicionar informações específicas baseadas na coluna
        if coluna == "F":  # Cálculo de Frete
            resposta += "🚚 *Cálculo de Frete:*\n"
            resposta += "• APIs disponíveis para cálculo\n"
            resposta += "• Parâmetros necessários (peso, dimensões, CEP)\n"
            resposta += "• Integração com transportadoras\n\n"
        elif coluna == "G":  # Importação de pedidos
            resposta += "📦 *Importação de Pedidos:*\n"
            resposta += "• Webhooks para novos pedidos\n"
            resposta += "• Sincronização de status\n"
            resposta += "• Mapeamento de campos\n\n"
        elif coluna == "H":  # Múltiplos Volumes
            resposta += "📦 *Múltiplos Volumes (MV):*\n"
            resposta += "• Suporte a pedidos com múltiplos volumes\n"
            resposta += "• Cálculo de frete por volume\n"
            resposta += "• Rastreamento individual\n\n"
        elif coluna == "I":  # Etiqueta
            resposta += "🏷️ *Etiquetas:*\n"
            resposta += "• Geração automática de etiquetas\n"
            resposta += "• Formato padrão das transportadoras\n"
            resposta += "• Impressão e envio\n\n"
        elif coluna == "O":  # Atualização de Status
            resposta += "🔄 *Atualização de Status:*\n"
            resposta += "• Sincronização automática de status\n"
            resposta += "• Notificações em tempo real\n"
            resposta += "• Histórico de mudanças\n\n"
        elif coluna == "J":  # Devolução de Rastreio
            resposta += "↩️ *Devolução de Rastreio:*\n"
            resposta += "• Processo de devolução\n"
            resposta += "• Rastreamento de retorno\n"
            resposta += "• Gestão de produtos devolvidos\n\n"
        elif coluna == "O2":  # Multi CD
            resposta += "🏢 *Multi CD:*\n"
            resposta += "• Múltiplos centros de distribuição\n"
            resposta += "• Otimização de rotas\n"
            resposta += "• Gestão de estoque distribuído\n\n"
        elif coluna == "A":  # Nome
            resposta += "🏷️ *Nome da Integração:*\n"
            resposta += "• Identificação da plataforma\n"
            resposta += "• Nome oficial da integração\n\n"
        elif coluna == "B":  # Tipo
            resposta += "🔧 *Tipo de Integração:*\n"
            resposta += "• Plataforma de e-commerce\n"
            resposta += "• ERP/Sistema de gestão\n"
            resposta += "• Marketplace\n\n"
        elif coluna == "K":  # Seguro configurável no frete
            resposta += "🛡️ *Seguro Configurável no Frete:*\n"
            resposta += "• Opções de seguro disponíveis\n"
            resposta += "• Configuração por produto\n"
            resposta += "• Cálculo automático de valor\n\n"
        elif coluna == "L":  # Seguro configurável na criação de pedido
            resposta += "🛡️ *Seguro na Criação de Pedido:*\n"
            resposta += "• Seguro configurável no checkout\n"
            resposta += "• Opções para o cliente\n"
            resposta += "• Integração com cálculo de frete\n\n"
        elif coluna == "N":  # Calcula peso cubado
            resposta += "📏 *Cálculo de Peso Cubado:*\n"
            resposta += "• Consideração de dimensões\n"
            resposta += "• Peso volumétrico\n"
            resposta += "• Otimização de embalagem\n\n"
        elif coluna == "M":  # Manuais para integração/cálculo frete
            resposta += "📚 *Manuais de Integração:*\n"
            resposta += "• Documentação técnica completa\n"
            resposta += "• Guias de implementação\n"
            resposta += "• Exemplos de código\n\n"
        
        resposta += "💡 *Para mais informações específicas, use a Pesquisa Global ou entre em contato com o suporte.*"
        
        return resposta
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar por tópico e coluna: {e}")
        return f"❌ Erro ao buscar informações: {e}"

def criar_menu_principal():
    """Alias para criar_menu_boas_vindas para compatibilidade"""
    return criar_menu_boas_vindas()
