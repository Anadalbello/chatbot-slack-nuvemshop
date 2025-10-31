"""
Script de teste para verificar conexão com Google Sheets
"""

import logging
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Adicionar handlers ao path
sys.path.append('.')

from handlers.buscar_integracoes_sheets import buscar_integracoes_google_sheets

def main():
    print("=" * 60)
    print("🧪 TESTE DE CONEXÃO COM GOOGLE SHEETS")
    print("=" * 60)
    print()
    
    print("📋 Verificando configuração...")
    print()
    
    resultado = buscar_integracoes_google_sheets()
    
    print()
    print("=" * 60)
    
    if resultado:
        print("✅ SUCESSO!")
        print("=" * 60)
        print()
        print(resultado)
    else:
        print("❌ FALHA!")
        print("=" * 60)
        print()
        print("Verifique:")
        print("1. GOOGLE_SHEETS_ID está configurado no .env")
        print("2. GOOGLE_SHEETS_CREDENTIALS ou google_sheets_credentials.json existe")
        print("3. A planilha foi compartilhada com a service account")
        print("4. As bibliotecas do Google foram instaladas:")
        print("   pip install -r requirements.txt")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()

