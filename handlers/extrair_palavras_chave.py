#!/usr/bin/env python3
"""
Módulo para extrair palavras-chave de perguntas em linguagem natural
"""

import re

# Palavras comuns que devem ser ignoradas (stop words)
STOP_WORDS = {
    'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas',
    'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas',
    'por', 'para', 'com', 'sem', 'sob', 'sobre',
    'que', 'qual', 'quais', 'onde', 'quando', 'como', 'porque', 'porquê',
    'esse', 'essa', 'esses', 'essas', 'este', 'esta', 'estes', 'estas',
    'aquele', 'aquela', 'aqueles', 'aquelas',
    'seu', 'sua', 'seus', 'suas', 'meu', 'minha', 'meus', 'minhas',
    'e', 'ou', 'mas', 'porém', 'contudo', 'todavia',
    'é', 'são', 'está', 'estão', 'foi', 'foram', 'ser', 'estar',
    'tem', 'têm', 'ter', 'temos', 'tive', 'teve',
    'me', 'te', 'se', 'nos', 'vos', 'lhe', 'lhes',
    'oque', 'oq', 'q', 'pq', 'tbm', 'tb'
}

def extrair_palavras_chave(texto):
    """
    Extrai palavras-chave relevantes de uma pergunta em linguagem natural
    
    Args:
        texto (str): Pergunta ou texto em linguagem natural
        
    Returns:
        str: Texto com palavras-chave relevantes para busca
    """
    
    # Remover menções do bot
    texto = re.sub(r'<@[^>]+>', '', texto)
    texto = re.sub(r'@\w+\s+BOT', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'@\w+', '', texto)
    
    # Converter para minúsculas
    texto = texto.lower()
    
    # Remover caracteres especiais, manter apenas letras, números e espaços
    texto = re.sub(r'[^\w\s\-áéíóúàèìòùâêîôûãõç]', ' ', texto)
    
    # Separar em palavras
    palavras = texto.split()
    
    # Filtrar stop words e palavras muito curtas
    palavras_relevantes = [
        p for p in palavras 
        if len(p) > 2 and p not in STOP_WORDS
    ]
    
    # Se não sobrou nenhuma palavra relevante, retornar texto original limpo
    if not palavras_relevantes:
        return re.sub(r'\s+', ' ', texto).strip()
    
    # Retornar palavras-chave separadas por espaço
    return ' '.join(palavras_relevantes)

def melhorar_busca_confluence(texto):
    """
    Melhora o termo de busca para o Confluence, extraindo palavras-chave
    e criando uma query mais eficiente
    
    NOVA ESTRATÉGIA: Manter TODAS as palavras relevantes para busca mais abrangente
    
    Args:
        texto (str): Pergunta original
        
    Returns:
        str: Termo otimizado para busca (mantém todas palavras-chave)
    """
    
    # Extrair palavras-chave
    palavras_chave = extrair_palavras_chave(texto)
    
    # Separar em palavras
    palavras = palavras_chave.split()
    
    # Remover apenas palavras MUITO genéricas que não agregam
    palavras_genericas = ['doc', 'docs', 'alguma', 'alguns', 'temos', 'existe', 'fazer', 'faço']
    palavras_filtradas = [p for p in palavras if p not in palavras_genericas]
    
    # Se sobrou alguma palavra relevante, usar elas
    if palavras_filtradas:
        palavras = palavras_filtradas
    
    if len(palavras) == 0:
        # Se não sobrou nada, retornar texto original limpo
        return re.sub(r'\s+', ' ', texto.lower()).strip()
    else:
        # MUDANÇA IMPORTANTE: Retornar TODAS as palavras relevantes
        # Isso permite que a busca seja mais abrangente
        return ' '.join(palavras)

if __name__ == "__main__":
    # Testes
    exemplos = [
        "oque temos de integrações?",
        "como integrar magento?",
        "temos alguma doc de template?",
        "qual o processo para criar uma integração?",
        "onde encontro a documentação da API?",
        "como faço para configurar webhook?"
    ]
    
    print("🔍 Testando extração de palavras-chave:\n")
    for exemplo in exemplos:
        palavras = extrair_palavras_chave(exemplo)
        busca = melhorar_busca_confluence(exemplo)
        print(f"Original: {exemplo}")
        print(f"Palavras-chave: {palavras}")
        print(f"Busca otimizada: {busca}")
        print("-" * 80)

