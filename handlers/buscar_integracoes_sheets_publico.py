"""
Handler para buscar integrações da planilha Google Sheets PÚBLICA
(Não requer autenticação - usa API pública do Google Sheets)
"""

import os
import logging
import requests
from dotenv import load_dotenv

# Configurar logger
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

def buscar_integracoes_google_sheets_publico():
    """
    Busca todas as integrações da planilha Google Sheets PÚBLICA
    Usa a API pública (não requer autenticação)
    Retorna uma string formatada para o Slack
    """
    try:
        logger.info("📊 Iniciando busca no Google Sheets (público)...")
        
        # Obter configurações do .env
        sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        sheets_tab = os.getenv('GOOGLE_SHEETS_TAB', 'Integrações')
        
        if not sheets_id:
            logger.error("❌ GOOGLE_SHEETS_ID não configurado no .env")
            return None
        
        # URL da API pública do Google Sheets
        # Formato: https://docs.google.com/spreadsheets/d/{ID}/gviz/tq?tqx=out:csv&sheet={NOME_ABA}
        url = f"https://docs.google.com/spreadsheets/d/{sheets_id}/gviz/tq?tqx=out:csv&sheet={sheets_tab}"
        
        logger.info(f"📋 Buscando dados da planilha pública: {sheets_id}, aba: {sheets_tab}")
        
        # Fazer requisição
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"❌ Erro ao acessar planilha: {response.status_code}")
            logger.error("⚠️ Verifique se a planilha está pública (qualquer pessoa com o link)")
            return None
        
        # Parsear CSV
        import csv
        from io import StringIO
        
        csv_data = StringIO(response.text)
        reader = csv.reader(csv_data)
        rows = list(reader)
        
        if not rows or len(rows) < 2:
            logger.warning("⚠️ Planilha vazia ou sem dados")
            return "📊 A planilha de integrações está vazia no momento."
        
        # Primeira linha são os cabeçalhos
        headers = rows[0]
        data_rows = rows[1:]
        
        logger.info(f"✅ Encontradas {len(data_rows)} integrações na planilha")
        logger.info(f"📋 Colunas: {headers[:5]}...")  # Mostrar primeiras 5 colunas
        
        # Formatar resposta
        resposta = "📊 *Integrações Disponíveis*\n\n"
        
        # Identificar índices das colunas importantes
        # Na planilha: A=Nome, B=Tipo, C=Observação, D=Complexidade, E=Responsável
        col_nome = 0  # Coluna A (sempre é a primeira)
        col_tipo = _find_column_index(headers, ['tipo', 'categoria', 'plataforma'])
        col_complexidade = _find_column_index(headers, ['complexidade', 'prazo'])
        col_responsavel = _find_column_index(headers, ['responsável', 'responsavel', 'time', 'equipe'])
        col_status = _find_column_index(headers, ['status', 'ativo', 'disponível', 'disponivel', 'observação', 'observacao'])
        
        # Contar integrações válidas
        count = 0
        
        # Processar cada linha
        for i, row in enumerate(data_rows, 1):
            if not row or len(row) == 0:
                continue  # Linha vazia
            
            # Pegar o nome da integração
            nome = ""
            if col_nome is not None and col_nome < len(row):
                nome = row[col_nome].strip()
            
            # Se não tem nome, pular
            if not nome or nome == "":
                continue
            
            count += 1
            
            # Limitar a 50 integrações para não ultrapassar limite do Slack
            if count > 50:
                resposta += f"\n_... e mais {len(data_rows) - i + 1} integrações_\n"
                break
            
            tipo = row[col_tipo].strip() if col_tipo is not None and col_tipo < len(row) else ""
            complexidade = row[col_complexidade].strip() if col_complexidade is not None and col_complexidade < len(row) else ""
            responsavel = row[col_responsavel].strip() if col_responsavel is not None and col_responsavel < len(row) else ""
            status = row[col_status].strip() if col_status is not None and col_status < len(row) else ""
            
            # Formatar item (mais compacto)
            resposta += f"*{count}. {nome}*"
            
            if tipo:
                resposta += f" | _{tipo}_"
            
            if complexidade:
                emoji_complex = {
                    "simples": "🟢", "baixa": "🟢",
                    "média": "🟡", "medio": "🟡",
                    "alta": "🔴", "complexa": "🔴"
                }
                emoji = "⚪"
                for key, em in emoji_complex.items():
                    if key in complexidade.lower():
                        emoji = em
                        break
                resposta += f" {emoji}"
            
            resposta += "\n"
            
            # Adicionar detalhes em linha separada (mais compacto)
            detalhes = []
            if responsavel:
                detalhes.append(f"👤 {responsavel}")
            if status and status.lower() not in ["ativo", "ativa", "sim", "yes"]:
                detalhes.append(f"⚠️ {status}")
            
            if detalhes:
                resposta += f"   {' | '.join(detalhes)}\n"
            
            resposta += "\n"
        
        if count == 0:
            return "📊 Nenhuma integração encontrada na planilha."
        
        resposta += f"\n📊 *Total: {count} integrações*"
        resposta += f"\n🔗 [Ver planilha completa](https://docs.google.com/spreadsheets/d/{sheets_id})"
        
        logger.info(f"✅ Resposta formatada com sucesso ({count} integrações)")
        return resposta
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return None


def buscar_integracao_especifica_sheets_publico(nome_integracao):
    """
    Busca informações de uma integração específica na planilha pública
    """
    try:
        logger.info(f"🔍 Buscando integração específica: {nome_integracao}")
        
        # Obter configurações
        sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        sheets_tab = os.getenv('GOOGLE_SHEETS_TAB', 'Integrações')
        
        if not sheets_id:
            return None
        
        # URL da API pública
        url = f"https://docs.google.com/spreadsheets/d/{sheets_id}/gviz/tq?tqx=out:csv&sheet={sheets_tab}"
        
        # Fazer requisição
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        
        # Parsear CSV
        import csv
        from io import StringIO
        
        csv_data = StringIO(response.text)
        reader = csv.reader(csv_data)
        rows = list(reader)
        
        if not rows or len(rows) < 2:
            return None
        
        headers = rows[0]
        data_rows = rows[1:]
        
        # Procurar pela integração
        col_nome = _find_column_index(headers, ['nome', 'integração', 'integracao', 'sistema'])
        
        if col_nome is None:
            return None
        
        for row in data_rows:
            if col_nome >= len(row):
                continue
            
            if nome_integracao.lower() in row[col_nome].lower():
                # Encontrou! Formatar resposta detalhada
                resposta = f"*📊 {row[col_nome]}*\n\n"
                
                for i, header in enumerate(headers):
                    if i < len(row) and row[i] and row[i].strip() != "" and header.lower() != 'nome':
                        # Limitar tamanho dos campos muito longos
                        valor = row[i].strip()
                        if len(valor) > 200:
                            valor = valor[:200] + "..."
                        resposta += f"*{header}*: {valor}\n"
                
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
    
    # Busca parcial (se a coluna contém o nome)
    for name in possible_names:
        for i, header in enumerate(headers_lower):
            if name.lower() in header:
                return i
    
    return None


if __name__ == "__main__":
    # Teste local
    logging.basicConfig(level=logging.INFO)
    
    print("=== Teste de busca no Google Sheets (público) ===\n")
    
    resultado = buscar_integracoes_google_sheets_publico()
    
    if resultado:
        print(resultado)
    else:
        print("❌ Falha ao buscar dados")
        print("\n⚠️ Verifique:")
        print("1. A planilha está pública? (Compartilhar → Qualquer pessoa com o link)")
        print("2. GOOGLE_SHEETS_ID está correto no .env")
        print("3. GOOGLE_SHEETS_TAB está correto (nome da aba)")

