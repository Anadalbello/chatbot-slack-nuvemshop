import os
import requests
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()

def obter_usuario_slack_info(user_id, slack_client):
    """Obtém informações do usuário do Slack"""
    try:
        user_info = slack_client.users_info(user=user_id)
        if user_info["ok"]:
            user = user_info["user"]
            return {
                "name": user.get("real_name", user.get("name", "Usuário")),
                "email": user.get("profile", {}).get("email", ""),
                "display_name": user.get("display_name", user.get("name", ""))
            }
    except Exception as e:
        logger.error(f"Erro ao buscar info do usuário Slack: {e}")
    
    return {"name": "Usuário Slack", "email": "", "display_name": ""}

def buscar_usuario_jira_por_email(email, base_url, headers, auth):
    """Busca usuário no Jira pelo email"""
    if not email:
        return None
        
    try:
        search_url = f"{base_url}/rest/api/3/user/search"
        params = {"query": email}
        response = requests.get(search_url, headers=headers, auth=auth, params=params, timeout=10)
        
        if response.status_code == 200:
            users = response.json()
            if users:
                return users[0]["accountId"]
    except Exception as e:
        logger.error(f"Erro ao buscar usuário no Jira: {e}")
    
    return None

def criar_chamado_jira(titulo, descricao, usuario_slack=None, slack_client=None):
    email = os.getenv("ATLASSIAN_EMAIL")
    token = os.getenv("ATLASSIAN_TOKEN")
    base_url = os.getenv("ATLASSIAN_BASE_URL")
    project_key = os.getenv("JIRA_PROJECT_KEY")

    if not all([email, token, base_url, project_key]):
        logger.error("Configurações do Jira não encontradas")
        return "❌ Erro: Configurações do Jira não encontradas"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (email, token)

    try:
        # Obter informações do usuário Slack se fornecido
        user_info = {"name": "Usuário Slack", "email": "", "display_name": ""}
        if usuario_slack and slack_client:
            user_info = obter_usuario_slack_info(usuario_slack, slack_client)
        
        # Buscar metadados do projeto
        meta_url = f"{base_url}/rest/api/3/issue/createmeta"
        params = {"projectKeys": project_key, "expand": "projects.issuetypes.fields"}
        
        logger.info(f"Buscando metadados do projeto {project_key}")
        response = requests.get(meta_url, headers=headers, auth=auth, params=params, timeout=15)
        
        if response.status_code != 200:
            return f"❌ Erro: Não foi possível acessar o projeto '{project_key}'"
        
        meta_data = response.json()
        project = meta_data["projects"][0]
        
        # Encontrar tipo "Dúvidas"
        issue_type = None
        for it in project["issuetypes"]:
            if it["name"].lower() in ["dúvidas", "duvidas"]:
                issue_type = it
                break
        
        if not issue_type:
            issue_type = project["issuetypes"][0]
        
        logger.info(f"Usando tipo de issue: {issue_type['name']}")
        
        # Criar descrição enriquecida com info do usuário
        descricao_completa = f"""**👤 SOLICITANTE**
📧 {user_info['email'] or 'Email não disponível'}
👤 {user_info['name']}
🆔 Slack ID: {usuario_slack or 'Não fornecido'}

**📝 DESCRIÇÃO**
{descricao}

---
_Chamado criado automaticamente pelo Chatbot Slack_"""

        # Criar payload base
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": titulo,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": descricao_completa
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"id": issue_type["id"]},
                # Usar valores corretos descobertos no diagnóstico
                "customfield_13643": {"id": "16472"},  # "Nova integração - Cliente novo" (temporário)
                "customfield_13719": {"id": "17119"}   # "Integrações" 
            }
        }
        
        # Tentar definir o reporter como o usuário real
        if user_info["email"]:
            jira_user_id = buscar_usuario_jira_por_email(user_info["email"], base_url, headers, auth)
            if jira_user_id:
                payload["fields"]["reporter"] = {"id": jira_user_id}
                logger.info(f"Reporter definido para: {user_info['email']}")
            else:
                logger.info(f"Usuário {user_info['email']} não encontrado no Jira")
        
        # Verificar se há campo customizado para "solicitante"
        fields = issue_type.get("fields", {})
        for field_key, field_info in fields.items():
            field_name = field_info.get("name", "").lower()
            if "solicitante" in field_name and field_info.get("schema", {}).get("type") == "string":
                payload["fields"][field_key] = user_info["name"]
                logger.info(f"Campo solicitante preenchido: {field_key}")
                break
        
        # Criar o chamado
        create_url = f"{base_url}/rest/api/3/issue"
        logger.info(f"Criando chamado para: {user_info['name']}")
        
        response = requests.post(create_url, json=payload, headers=headers, auth=auth, timeout=15)
        
        if response.status_code == 201:
            data = response.json()
            issue_key = data['key']
            issue_url = f"{base_url}/browse/{issue_key}"
            
            logger.info(f"✅ Chamado criado com sucesso: {issue_key}")
            return f"✅ **Chamado {issue_key}** criado com sucesso para **{user_info['name']}**!\n🔗 {issue_url}"
        
        else:
            logger.error(f"❌ Erro ao criar chamado: {response.status_code} - {response.text}")
            return f"❌ Erro ao criar chamado: HTTP {response.status_code}"
            
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return f"❌ Erro inesperado: {e}"
