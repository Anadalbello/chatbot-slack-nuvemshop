#!/usr/bin/env python3
"""
Script para criar/atualizar uma página no Confluence com a lista de integrações
Como databases não são acessíveis via API REST, criamos uma página "espelho"

USO:
1. Mantenha este arquivo atualizado com as integrações
2. Execute: python sincronizar_integracoes_manual.py
3. O bot poderá ler a página normalmente
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ========================================
# CONFIGURE AQUI AS INTEGRAÇÕES
# ========================================
INTEGRACOES = [
    {
        "nome": "Wake OMS",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Equipe Integrações",
        "tipo": "ERP/OMS",
        "descricao": "Plataforma de gestão de pedidos"
    },
    {
        "nome": "Mandaê",
        "status": "Ativa",
        "complexidade": "Baixa",
        "responsavel": "Nuvem Envio",
        "tipo": "Logística",
        "descricao": "Sistema de envios (parte do grupo)"
    },
    {
        "nome": "Magento",
        "status": "Ativa",
        "complexidade": "Alta",
        "responsavel": "Parceiro",
        "tipo": "E-commerce",
        "descricao": "Plataforma de e-commerce"
    },
    {
        "nome": "SAP Business One",
        "status": "Ativa",
        "complexidade": "Alta",
        "responsavel": "Parceiro",
        "tipo": "ERP",
        "descricao": "ERP empresarial"
    },
    {
        "nome": "Bling",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "ERP",
        "descricao": "ERP para pequenas empresas"
    },
    {
        "nome": "Ativa",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "Gestão",
        "descricao": "Sistema de gestão"
    },
    {
        "nome": "D2D On Platform",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "Plataforma",
        "descricao": "Plataforma de integração"
    },
    {
        "nome": "KPL ONCLICK",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "ERP",
        "descricao": "ERP KPL"
    },
    {
        "nome": "Notazz",
        "status": "Ativa",
        "complexidade": "Baixa",
        "responsavel": "Parceiro",
        "tipo": "Notas Fiscais",
        "descricao": "Sistema de notas fiscais"
    },
    {
        "nome": "Convertr",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "Frete",
        "descricao": "Cálculo de frete e pedidos"
    },
    {
        "nome": "Vtrina",
        "status": "Ativa",
        "complexidade": "Baixa",
        "responsavel": "Parceiro",
        "tipo": "Marketplace",
        "descricao": "Marketplace"
    },
    {
        "nome": "Magis5",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "ERP",
        "descricao": "ERP Magis5"
    },
    {
        "nome": "WBUY",
        "status": "Ativa",
        "complexidade": "Média",
        "responsavel": "Parceiro",
        "tipo": "Frete",
        "descricao": "Sistema de frete e pedidos"
    },
    {
        "nome": "Intelipost",
        "status": "Ativa",
        "complexidade": "Alta",
        "responsavel": "Parceiro",
        "tipo": "Frete",
        "descricao": "Plataforma de frete"
    },
    # ADICIONE MAIS INTEGRAÇÕES AQUI
]


def gerar_html_tabela():
    """Gera HTML da tabela de integrações"""
    html = """
<h2>📋 Integrações Disponíveis</h2>
<p><em>Última atualização: {data}</em></p>

<table>
<thead>
<tr>
<th>Nome</th>
<th>Status</th>
<th>Tipo</th>
<th>Complexidade</th>
<th>Responsável</th>
<th>Descrição</th>
</tr>
</thead>
<tbody>
"""
    
    from datetime import datetime
    html = html.format(data=datetime.now().strftime("%d/%m/%Y %H:%M"))
    
    for integ in sorted(INTEGRACOES, key=lambda x: x['nome']):
        status_emoji = "✅" if integ['status'] == "Ativa" else "❌"
        
        html += f"""<tr>
<td><strong>{integ['nome']}</strong></td>
<td>{status_emoji} {integ['status']}</td>
<td>{integ['tipo']}</td>
<td>{integ['complexidade']}</td>
<td>{integ['responsavel']}</td>
<td>{integ['descricao']}</td>
</tr>
"""
    
    html += """</tbody>
</table>

<p><strong>Total:</strong> {total} integrações</p>
""".format(total=len(INTEGRACOES))
    
    return html


def criar_ou_atualizar_pagina():
    """Cria ou atualiza a página no Confluence"""
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    space = os.getenv("CONFLUENCE_SPACE", "BDGCI")
    
    if not all([email, token, base_url]):
        print("❌ Configurações do Confluence não encontradas no .env")
        return False
    
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    auth = (email, token)
    
    # Nome da página espelho
    page_title = "Lista de Integrações (Bot)"
    
    try:
        # 1. Verificar se a página já existe
        print(f"🔍 Buscando página '{page_title}'...")
        search_url = f"{base_url}/wiki/rest/api/content?title={page_title}&spaceKey={space}&expand=version"
        response = requests.get(search_url, headers=headers, auth=auth, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        html_content = gerar_html_tabela()
        
        if results:
            # Página existe - atualizar
            page = results[0]
            page_id = page["id"]
            current_version = page["version"]["number"]
            
            print(f"📝 Atualizando página existente (ID: {page_id}, versão: {current_version})...")
            
            update_data = {
                "version": {"number": current_version + 1},
                "title": page_title,
                "type": "page",
                "body": {
                    "storage": {
                        "value": html_content,
                        "representation": "storage"
                    }
                }
            }
            
            update_url = f"{base_url}/wiki/rest/api/content/{page_id}"
            response = requests.put(update_url, json=update_data, headers=headers, auth=auth, timeout=15)
            response.raise_for_status()
            
            print(f"✅ Página atualizada com sucesso!")
            print(f"🔗 {base_url}/wiki/spaces/{space}/pages/{page_id}")
            
        else:
            # Página não existe - criar
            print(f"📄 Criando nova página...")
            
            create_data = {
                "type": "page",
                "title": page_title,
                "space": {"key": space},
                "body": {
                    "storage": {
                        "value": html_content,
                        "representation": "storage"
                    }
                }
            }
            
            create_url = f"{base_url}/wiki/rest/api/content"
            response = requests.post(create_url, json=create_data, headers=headers, auth=auth, timeout=15)
            response.raise_for_status()
            
            page = response.json()
            page_id = page["id"]
            
            print(f"✅ Página criada com sucesso!")
            print(f"🔗 {base_url}/wiki/spaces/{space}/pages/{page_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 SINCRONIZADOR DE INTEGRAÇÕES")
    print("=" * 60)
    print(f"\n📊 Total de integrações configuradas: {len(INTEGRACOES)}\n")
    
    # Mostrar prévia
    print("Prévia das integrações:")
    for i, integ in enumerate(sorted(INTEGRACOES, key=lambda x: x['nome'])[:5], 1):
        print(f"{i}. {integ['nome']} - {integ['status']} ({integ['tipo']})")
    
    if len(INTEGRACOES) > 5:
        print(f"... e mais {len(INTEGRACOES) - 5} integrações\n")
    
    # Confirmar
    confirmar = input("\n▶️  Deseja criar/atualizar a página no Confluence? (s/n): ")
    
    if confirmar.lower() == 's':
        print("\n" + "=" * 60)
        if criar_ou_atualizar_pagina():
            print("\n✨ Sincronização concluída com sucesso!")
            print("💡 O bot agora pode ler esta página normalmente.")
        else:
            print("\n❌ Falha na sincronização.")
    else:
        print("\n❌ Operação cancelada.")


