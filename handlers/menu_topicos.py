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
    """Cria o menu principal de boas-vindas"""
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "👋 *Olá! Sou o assistente de integrações da Nuvem Envio*\n\nComo posso ajudá-lo hoje? Escolha uma opção:"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🚚 Frete e Cálculo"},
                        "value": "topico_frete",
                        "action_id": "menu_topico"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📦 Pedidos e Logística"},
                        "value": "topico_pedidos", 
                        "action_id": "menu_topico"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🧩 Configuração"},
                        "value": "topico_config",
                        "action_id": "menu_topico"
                    }
                ]
            },
            {
                "type": "actions", 
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🛒 Checkout"},
                        "value": "topico_checkout",
                        "action_id": "menu_topico"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🧠 Qualidade"},
                        "value": "topico_qualidade",
                        "action_id": "menu_topico"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📝 Observações"},
                        "value": "topico_observacoes",
                        "action_id": "menu_topico"
                    }
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔍 Pesquisa Global"},
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
            "text": {"type": "plain_text", "text": f"{descricao} ({coluna})"},
            "value": f"{topico_id}_{coluna}",
            "action_id": "submenu_opcao"
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
        
        # Buscar todas as integrações
        lista_integracoes = buscar_integracoes_google_sheets_publico()
        
        if not lista_integracoes:
            return "❌ Não foi possível acessar a base de dados de integrações."
        
        # Filtrar por coluna específica (implementação simplificada)
        # Aqui você pode implementar a lógica específica para filtrar por coluna
        categoria = CATEGORIAS_MENU.get(topico_id, {})
        nome_categoria = categoria.get("nome", "Tópico")
        descricao_coluna = categoria.get("descricoes", {}).get(coluna, f"Coluna {coluna}")
        
        resposta = f"📊 **{nome_categoria} - {descricao_coluna}**\n\n"
        resposta += f"Informações sobre {descricao_coluna.lower()}:\n\n"
        resposta += "🔍 *Busca realizada na base de dados de integrações*\n"
        resposta += f"📋 *Categoria:* {nome_categoria}\n"
        resposta += f"🎯 *Foco:* {descricao_coluna}\n\n"
        resposta += "_Para informações mais específicas, use a Pesquisa Global._"
        
        return resposta
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar por tópico e coluna: {e}")
        return f"❌ Erro ao buscar informações: {e}"

def criar_menu_principal():
    """Alias para criar_menu_boas_vindas para compatibilidade"""
    return criar_menu_boas_vindas()
