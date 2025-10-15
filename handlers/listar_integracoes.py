#!/usr/bin/env python3
"""
Handler para listar integrações e parceiros disponíveis
Como a API do Confluence não suporta bem databases, mantemos uma lista aqui
que pode ser atualizada periodicamente
"""

# Lista de integrações conhecidas (atualizar conforme necessário)
INTEGRACOES_DISPONIVEIS = [
    {
        "nome": "Wake OMS",
        "descricao": "Plataforma de gestão de pedidos (OMS)",
        "complexidade": "Média",
        "responsavel": "Equipe Integrações",
        "tipo": "ERP/OMS"
    },
    {
        "nome": "Mandaê",
        "descricao": "Sistema de envios e logística (parte do grupo)",
        "complexidade": "Baixa",
        "responsavel": "Equipe Nuvem Envio",
        "tipo": "Logística"
    },
    {
        "nome": "Magento",
        "descricao": "Plataforma de e-commerce",
        "complexidade": "Alta",
        "responsavel": "Parceiro",
        "tipo": "E-commerce"
    },
    {
        "nome": "SAP Business One",
        "descricao": "ERP empresarial",
        "complexidade": "Alta",
        "responsavel": "Parceiro",
        "tipo": "ERP"
    },
    {
        "nome": "Ativa",
        "descricao": "Sistema de gestão",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "Gestão"
    },
    {
        "nome": "D2D On Platform",
        "descricao": "Plataforma de integração",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "Plataforma"
    }
]


def listar_todas_integracoes():
    """Retorna lista formatada de todas as integrações"""
    resultado = "📋 **Integrações Disponíveis:**\n\n"
    
    for integracao in INTEGRACOES_DISPONIVEIS:
        resultado += f"• **{integracao['nome']}**\n"
        resultado += f"  └ {integracao['descricao']}\n"
        resultado += f"  └ Tipo: {integracao['tipo']}\n"
        resultado += f"  └ Complexidade: {integracao['complexidade']}\n\n"
    
    return resultado


def buscar_integracao(nome_busca):
    """Busca uma integração específica pelo nome"""
    nome_busca_lower = nome_busca.lower()
    
    for integracao in INTEGRACOES_DISPONIVEIS:
        if nome_busca_lower in integracao['nome'].lower():
            resultado = f"📦 **{integracao['nome']}**\n\n"
            resultado += f"**Descrição:** {integracao['descricao']}\n"
            resultado += f"**Tipo:** {integracao['tipo']}\n"
            resultado += f"**Complexidade:** {integracao['complexidade']}\n"
            resultado += f"**Responsável:** {integracao['responsavel']}\n"
            return resultado
    
    return None


def listar_por_tipo(tipo):
    """Lista integrações de um tipo específico"""
    tipo_lower = tipo.lower()
    integracoes_filtradas = [
        i for i in INTEGRACOES_DISPONIVEIS 
        if tipo_lower in i['tipo'].lower()
    ]
    
    if not integracoes_filtradas:
        return None
    
    resultado = f"📋 **Integrações do tipo {tipo}:**\n\n"
    for integracao in integracoes_filtradas:
        resultado += f"• **{integracao['nome']}** - {integracao['descricao']}\n"
    
    return resultado


def listar_parceiros():
    """Lista apenas parceiros (exclui sistemas internos)"""
    parceiros = [
        i for i in INTEGRACOES_DISPONIVEIS 
        if i['responsavel'] == 'Parceiro'
    ]
    
    resultado = "🤝 **Parceiros Integrados:**\n\n"
    for parceiro in parceiros:
        resultado += f"• **{parceiro['nome']}** ({parceiro['tipo']})\n"
        resultado += f"  └ {parceiro['descricao']}\n\n"
    
    return resultado


if __name__ == "__main__":
    print("=== TESTE: Listar todas ===")
    print(listar_todas_integracoes())
    
    print("\n=== TESTE: Buscar Magento ===")
    print(buscar_integracao("magento"))
    
    print("\n=== TESTE: Listar parceiros ===")
    print(listar_parceiros())
    
    print("\n=== TESTE: Por tipo ERP ===")
    print(listar_por_tipo("ERP"))

