"""
Handler para buscar integrações da planilha Google Sheets
"""

import os
import json
import logging
from dotenv import load_dotenv

# Configurar logger
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

def buscar_integracoes_google_sheets():
    """
    Busca todas as integrações da planilha Google Sheets
    Retorna uma string formatada para o Slack
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        logger.info("📊 Iniciando busca no Google Sheets...")
        
        # Obter configurações do .env
        sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        sheets_tab = os.getenv('GOOGLE_SHEETS_TAB', 'Sheet1')
        
        if not sheets_id:
            logger.error("❌ GOOGLE_SHEETS_ID não configurado no .env")
            return None
        
        # Carregar credenciais
        credentials = None
        
        # OPÇÃO 1: Tentar carregar de variável de ambiente (JSON como string)
        creds_json_str = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if creds_json_str:
            logger.info("🔑 Carregando credenciais da variável de ambiente")
            try:
                creds_dict = json.loads(creds_json_str)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erro ao parsear GOOGLE_SHEETS_CREDENTIALS: {e}")
                return None
        
        # OPÇÃO 2: Tentar carregar de arquivo JSON
        if not credentials:
            creds_file = 'google_sheets_credentials.json'
            if os.path.exists(creds_file):
                logger.info("🔑 Carregando credenciais do arquivo JSON")
                credentials = service_account.Credentials.from_service_account_file(
                    creds_file,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            else:
                logger.error("❌ Credenciais não encontradas (nem .env nem arquivo JSON)")
                return None
        
        # Conectar ao Google Sheets
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        logger.info(f"📋 Buscando dados da planilha: {sheets_id}, aba: {sheets_tab}")
        
        # Ler dados da planilha (assumindo que a primeira linha tem cabeçalhos)
        result = sheet.values().get(
            spreadsheetId=sheets_id,
            range=f'{sheets_tab}!A:Z'  # Ler todas as colunas
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.warning("⚠️ Planilha vazia ou sem dados")
            return "📊 A planilha de integrações está vazia no momento."
        
        # Primeira linha são os cabeçalhos
        headers = values[0]
        rows = values[1:]
        
        logger.info(f"✅ Encontradas {len(rows)} integrações na planilha")
        logger.info(f"📋 Colunas: {headers}")
        
        # Formatar resposta
        resposta = "📊 *Integrações Disponíveis (Google Sheets)*\n\n"
        
        # Identificar índices das colunas importantes
        col_nome = _find_column_index(headers, ['nome', 'integração', 'integracao', 'sistema'])
        col_status = _find_column_index(headers, ['status', 'ativo', 'disponível', 'disponivel'])
        col_complexidade = _find_column_index(headers, ['complexidade', 'nivel', 'dificuldade'])
        col_responsavel = _find_column_index(headers, ['responsável', 'responsavel', 'time', 'equipe'])
        col_link = _find_column_index(headers, ['link', 'url', 'documentação', 'documentacao'])
        
        # Processar cada linha
        for i, row in enumerate(rows, 1):
            if not row or (col_nome is not None and col_nome >= len(row)):
                continue  # Linha vazia
            
            nome = row[col_nome] if col_nome is not None and col_nome < len(row) else f"Integração {i}"
            status = row[col_status] if col_status is not None and col_status < len(row) else ""
            complexidade = row[col_complexidade] if col_complexidade is not None and col_complexidade < len(row) else ""
            responsavel = row[col_responsavel] if col_responsavel is not None and col_responsavel < len(row) else ""
            link = row[col_link] if col_link is not None and col_link < len(row) else ""
            
            # Formatar item
            resposta += f"*{i}. {nome}*\n"
            
            if status:
                emoji_status = "✅" if "ativ" in status.lower() or "sim" in status.lower() else "⚠️"
                resposta += f"   {emoji_status} Status: {status}\n"
            
            if complexidade:
                emoji_complex = {"baixa": "🟢", "média": "🟡", "alta": "🔴"}.get(complexidade.lower(), "⚪")
                resposta += f"   {emoji_complex} Complexidade: {complexidade}\n"
            
            if responsavel:
                resposta += f"   👤 Responsável: {responsavel}\n"
            
            if link:
                resposta += f"   🔗 {link}\n"
            
            resposta += "\n"
        
        resposta += f"\n📊 _Total: {len(rows)} integrações encontradas_"
        resposta += f"\n_Última atualização: consulte a planilha_"
        
        logger.info("✅ Resposta formatada com sucesso")
        return resposta
        
    except ImportError:
        logger.error("❌ Bibliotecas do Google não instaladas. Execute: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao buscar Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return None


def buscar_integracao_especifica_sheets(nome_integracao):
    """
    Busca informações de uma integração específica na planilha
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        logger.info(f"🔍 Buscando integração específica: {nome_integracao}")
        
        # Obter configurações
        sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        sheets_tab = os.getenv('GOOGLE_SHEETS_TAB', 'Sheet1')
        
        if not sheets_id:
            return None
        
        # Carregar credenciais (mesmo processo que função anterior)
        credentials = None
        creds_json_str = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        
        if creds_json_str:
            creds_dict = json.loads(creds_json_str)
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
        else:
            creds_file = 'google_sheets_credentials.json'
            if os.path.exists(creds_file):
                credentials = service_account.Credentials.from_service_account_file(
                    creds_file,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            else:
                return None
        
        # Conectar e buscar dados
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=sheets_id,
            range=f'{sheets_tab}!A:Z'
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return None
        
        headers = values[0]
        rows = values[1:]
        
        # Procurar pela integração
        col_nome = _find_column_index(headers, ['nome', 'integração', 'integracao', 'sistema'])
        
        if col_nome is None:
            return None
        
        for row in rows:
            if col_nome >= len(row):
                continue
            
            if nome_integracao.lower() in row[col_nome].lower():
                # Encontrou! Formatar resposta detalhada
                resposta = f"*📊 {row[col_nome]}*\n\n"
                
                for i, header in enumerate(headers):
                    if i < len(row) and row[i] and header.lower() != 'nome':
                        resposta += f"*{header}*: {row[i]}\n"
                
                logger.info(f"✅ Integração encontrada: {row[col_nome]}")
                return resposta
        
        logger.info(f"❌ Integração '{nome_integracao}' não encontrada na planilha")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar integração específica: {e}")
        return None


def _find_column_index(headers, possible_names):
    """
    Encontra o índice de uma coluna baseado em nomes possíveis
    """
    headers_lower = [h.lower().strip() for h in headers]
    
    for name in possible_names:
        if name.lower() in headers_lower:
            return headers_lower.index(name.lower())
    
    return None


if __name__ == "__main__":
    # Teste local
    logging.basicConfig(level=logging.INFO)
    
    print("=== Teste de busca no Google Sheets ===\n")
    
    resultado = buscar_integracoes_google_sheets()
    
    if resultado:
        print(resultado)
    else:
        print("❌ Falha ao buscar dados")

