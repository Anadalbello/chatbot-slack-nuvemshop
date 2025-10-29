#!/usr/bin/env python3
"""
Script para sincronizar dados do Google Sheets para JSON
Estilo Nina - converte planilha em arquivo JSON estático
"""

import os
import json
import requests
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import sys

# Adicionar diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def baixar_dados_do_sheets():
    """Baixa dados do Google Sheets via API pública CSV"""
    sheets_id = os.getenv('GOOGLE_SHEETS_ID')
    sheets_tab = os.getenv('GOOGLE_SHEETS_TAB', 'Integrações')
    
    if not sheets_id:
        raise ValueError("GOOGLE_SHEETS_ID não configurado")
    
    url = f"https://docs.google.com/spreadsheets/d/{sheets_id}/gviz/tq?tqx=out:csv&sheet={sheets_tab}"
    
    logger.info(f"📥 Baixando dados do Google Sheets: {sheets_id}")
    response = requests.get(url, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Erro ao acessar planilha: {response.status_code}")
    
    import csv
    from io import StringIO
    
    csv_data = StringIO(response.text)
    reader = csv.reader(csv_data)
    rows = list(reader)
    
    if not rows or len(rows) < 2:
        raise Exception("Planilha vazia ou sem dados")
    
    # Procurar linha que parece ser cabeçalho (contém palavras como "nome", "tipo", etc.)
    # Geralmente está na linha 1 ou 2 (linha 0 pode ser instruções)
    header_row_idx = 0
    palavras_cabecalho = ['nome', 'integração', 'integracao', 'tipo', 'plataforma', 'complexidade']
    
    for i, row in enumerate(rows[:5]):  # Verificar primeiras 5 linhas
        row_lower = ' '.join(row).lower()
        if any(palavra in row_lower for palavra in palavras_cabecalho):
            header_row_idx = i
            logger.info(f"📋 Cabeçalho encontrado na linha {i + 1}")
            break
    
    # Se header não está na primeira linha, remover linhas antes dele
    if header_row_idx > 0:
        logger.info(f"⚠️ Removendo {header_row_idx} linha(s) antes do cabeçalho")
        rows = rows[header_row_idx:]
    
    logger.info(f"✅ Dados baixados: {len(rows)} linhas (incluindo cabeçalho)")
    return rows

def converter_para_json_formatado(rows):
    """Converte linhas CSV para formato JSON estilo Nina"""
    headers = rows[0]
    data_rows = rows[1:]
    
    logger.info(f"📋 Processando {len(data_rows)} integrações")
    logger.info(f"📊 Colunas encontradas: {len(headers)} colunas")
    
    # Mapear índices das colunas por nome
    col_map = {}
    for i, header in enumerate(headers):
        header_lower = header.lower().strip()
        col_map[header_lower] = i
        # Também mapear por letra da coluna (A, B, C, etc.)
        col_letter = chr(65 + i)  # A=0, B=1, C=2, etc.
        col_map[col_letter] = i
    
    # Função auxiliar para buscar valor
    def get_value(row, col_names, default=""):
        for name in col_names:
            name_lower = name.lower()
            if name_lower in col_map and col_map[name_lower] < len(row):
                val = row[col_map[name_lower]].strip()
                if val:
                    return val
        return default
    
    integracoes = []
    
    for row_idx, row in enumerate(data_rows, start=2):  # start=2 porque linha 1 é cabeçalho
        if not row or not row[0].strip():  # Linha vazia
            continue
        
        # Mapear campos principais
        # A planilha tem estrutura: Coluna A = Nome da integração (ex: "Bling", "Amazon")
        # Usar primeira coluna (A) como nome principal
        nome = row[0].strip() if len(row) > 0 else ""
        
        # Pular linhas vazias ou que são cabeçalhos
        if not nome:
            continue
        
        nome_lower = nome.lower()
        
        # Pular linhas que são cabeçalhos ou instruções
        palavras_cabecalho_exatas = ['nome', 'tipo', 'observação', 'complexidade/prazo', 'responsável']
        if nome_lower in [p.lower() for p in palavras_cabecalho_exatas]:
            continue
        
        # Pular se contém palavras de instrução
        if any(palavra in nome_lower for palavra in ['estimado', 'setup', 'simples:', 'média:', 'complexa :', 'prazo do parceiro']):
            continue
        
        # Pular se é tudo maiúsculas E tem mais de 5 letras (tipo "PLATAFORMAS")
        letras_alpha = [c for c in nome if c.isalpha()]
        if len(letras_alpha) > 5 and nome.upper() == nome:
            continue
        
        # Se passou todas as verificações, usar como nome válido
        
        # Mapear campos baseado na estrutura conhecida:
        # Coluna A = Nome, Coluna B = Tipo, Coluna C = Observação, Coluna D = Complexidade, Coluna E = Responsável
        tipo = row[1].strip() if len(row) > 1 else ""
        observacao = row[2].strip() if len(row) > 2 else ""
        complexidade = row[3].strip() if len(row) > 3 else ""
        responsavel = row[4].strip() if len(row) > 4 else ""
        
        integracao = {
            "nome": nome,
            "descricao_curta": observacao[:200] if observacao else "",  # Limitar tamanho
            "descricao_longa": observacao,
            "tipo": tipo,
            "complexidade": complexidade,
            "responsavel": responsavel,
            "status": "",  # Não há coluna de status na estrutura atual
        }
        
        # Adicionar campos funcionais (baseado nas colunas do menu_topicos)
        funcionalidades = []
        
        # Frete e Cálculo
        if get_value(row, ['f', 'calcula_frete', 'calculo_frete'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Cálculo de Frete")
        if get_value(row, ['k', 'seguro_frete'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Seguro configurável no frete")
        if get_value(row, ['l', 'seguro_pedido'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Seguro na criação de pedido")
        if get_value(row, ['n', 'peso_cubado'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Calcula peso cubado")
        
        # Pedidos e Logística
        if get_value(row, ['g', 'importacao_pedidos', 'importa_pedidos'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Importação de pedidos")
        if get_value(row, ['h', 'multiplos_volumes', 'mv'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Múltiplos Volumes")
        if get_value(row, ['i', 'etiqueta'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Etiqueta")
        if get_value(row, ['o', 'atualizacao_status', 'status'], "").strip().lower() in ['sim', 'yes', 's', 'y', '1', 'true']:
            funcionalidades.append("Atualização de Status")
        
        integracao["funcionalidades"] = funcionalidades
        
        # Adicionar todos os campos como metadata (para busca completa)
        integracao["metadata"] = {}
        for i, header in enumerate(headers):
            if i < len(row) and row[i].strip():
                header_clean = header.lower().strip().replace(" ", "_").replace("ç", "c").replace("ã", "a").replace("õ", "o")
                integracao["metadata"][header_clean] = row[i].strip()
        
        # Adicionar links se existirem
        link = get_value(row, ['link', 'url', 'y', 'z'], "")
        if link:
            integracao["link"] = link
        
        integracoes.append(integracao)
    
    logger.info(f"✅ {len(integracoes)} integrações convertidas com sucesso")
    return integracoes

def salvar_json(integracoes, output_file="knowledge/integracoes.json"):
    """Salva integrações em arquivo JSON"""
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)
    
    # Adicionar metadados
    dados_completos = {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "source": "Google Sheets",
        "total_integracoes": len(integracoes),
        "integracoes": integracoes
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dados_completos, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 JSON salvo em: {output_path}")
    logger.info(f"📊 Total: {len(integracoes)} integrações")
    logger.info(f"📁 Tamanho do arquivo: {output_path.stat().st_size / 1024:.2f} KB")

def main():
    """Função principal"""
    try:
        logger.info("=" * 60)
        logger.info("🔄 Iniciando sincronização Google Sheets → JSON")
        logger.info("=" * 60)
        
        # 1. Baixar dados
        logger.info("\n📥 Passo 1: Baixando dados do Google Sheets...")
        rows = baixar_dados_do_sheets()
        
        # 2. Converter para formato JSON
        logger.info("\n🔄 Passo 2: Convertendo para formato JSON...")
        integracoes = converter_para_json_formatado(rows)
        
        # 3. Salvar JSON
        logger.info("\n💾 Passo 3: Salvando arquivo JSON...")
        salvar_json(integracoes)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Sincronização concluída com sucesso!")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Erro na sincronização: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

