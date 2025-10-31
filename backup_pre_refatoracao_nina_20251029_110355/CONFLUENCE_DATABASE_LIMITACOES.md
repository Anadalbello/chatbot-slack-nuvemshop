# 📋 Limitações da API do Confluence para Databases

## ❌ Problema Identificado

As **Confluence Databases** (bancos de dados modernos do Confluence) **NÃO possuem suporte completo via API REST** até o momento.

### O que funciona ✅
- **Criar** uma database vazia via API v2: `POST /wiki/api/v2/databases`
- **Listar** databases existentes
- **Obter metadados** de uma database (ID, título, espaço, etc): `GET /wiki/api/v2/databases/{id}`
- **Deletar** uma database

### O que NÃO funciona ❌
- **Ler linhas/itens** de uma database existente
- **Adicionar linhas** a uma database
- **Atualizar linhas** de uma database
- **Deletar linhas** de uma database

## 🔍 Investigação Realizada

### Endpoints testados (todos falharam)
```
❌ GET /wiki/api/v2/databases/{id}/rows
❌ GET /wiki/api/v2/databases/{id}/items
❌ GET /wiki/api/v2/databases/{id}/entries
❌ GET /wiki/api/v2/databases/{id}/content
❌ GET /wiki/api/v2/databases/{id}/records
❌ GET /wiki/rest/api/content/{id}/child/page
❌ GET /wiki/rest/api/content/{id}?expand=body.atlas_doc_format (retorna vazio)
❌ POST /wiki/graphql (endpoint não disponível publicamente)
```

### Tentativas de workaround
1. **Web scraping**: HTML carregado, mas dados são renderizados via JavaScript assíncrono
2. **Apollo GraphQL State**: Contém metadados mas não os itens da database
3. **Export/View**: Endpoint de export não funciona para databases

## 📚 Fontes Oficiais

- **Atlassian Developer Community**: [Discussão sobre Database API](https://community.developer.atlassian.com/t/confluence-rest-api-databases/76402)
  - Confirmação oficial: *"Currently, the API REST do Confluence not support inserting rows in an existing database. This functionality has not been implemented yet."*

- **Atlassian REST API v2 Documentation**: [Database API Group](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-database/)
  - Apenas operações CRUD no nível da database (container), não nos itens/linhas

## 🛠️ Soluções Alternativas

### 1. **Página Espelho Manual** (Recomendada)
Criar uma página Confluence tradicional com uma tabela HTML que você mantém sincronizada:

```python
# Atualizar via API quando houver mudanças
PUT /wiki/rest/api/content/{pageId}
Body: {
  "type": "page",
  "body": {
    "storage": {
      "value": "<table>...</table>",
      "representation": "storage"
    }
  }
}
```

### 2. **Lista Dinâmica via Busca CQL**
Buscar todas as páginas no espaço relacionadas a integrações (solução atual implementada):

```python
from handlers.buscar_integracoes_dinamico import buscar_todas_integracoes_confluence
```

### 3. **Arquivo de Configuração Local**
Manter um arquivo JSON/YAML no repositório com as integrações:

```json
{
  "integracoes": [
    {
      "nome": "Magento",
      "status": "Ativa",
      "complexidade": "Alta",
      "responsavel": "Time Tech"
    }
  ]
}
```

### 4. **Google Sheets + API**
Usar Google Sheets como database e ler via API do Google Sheets (mais fácil que Confluence):

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
```

### 5. **Airtable/Notion + API**
Usar plataformas que têm APIs robustas para databases estruturadas

## ⏰ Expectativa de Suporte

A Atlassian está gradualmente expandindo a API v2 do Confluence, mas **não há previsão oficial** para quando o suporte a itens de database será adicionado.

**Recomendação**: Monitorar o [Changelog da API do Confluence](https://developer.atlassian.com/cloud/confluence/changelog/) para atualizações.

## 💡 Decisão Recomendada

Para o chatbot atual, as melhores opções são (em ordem de preferência):

1. **Página Confluence tradicional com tabela HTML** que você atualiza manualmente ou via script
   - ✅ Fácil de manter
   - ✅ API bem documentada
   - ✅ Bot consegue ler facilmente

2. **Google Sheets**
   - ✅ API excelente
   - ✅ Interface familiar para equipe
   - ✅ Fácil de integrar

3. **Arquivo JSON no repositório Git**
   - ✅ Versionado
   - ✅ Rápido
   - ❌ Requer deploy para atualizar

---

**Data**: 2025-10-15
**Status**: API v2 de Databases não suporta leitura de linhas/itens

