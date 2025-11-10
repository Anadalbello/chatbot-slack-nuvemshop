# 🤖 Documentação do Chatbot de Integrações - Nuvemshop

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Tecnologias e Ferramentas](#tecnologias-e-ferramentas)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Processo de Criação](#processo-de-criação)
5. [Funcionalidades Principais](#funcionalidades-principais)
6. [Estrutura do Projeto](#estrutura-do-projeto)
7. [Fluxo de Funcionamento](#fluxo-de-funcionamento)
8. [Deploy e Configuração](#deploy-e-configuração)

---

## 🎯 Visão Geral

O **Chatbot de Integrações** é um assistente virtual desenvolvido para a Nuvemshop que ajuda usuários a encontrar informações sobre integrações disponíveis na plataforma. O bot opera dentro do Slack e utiliza inteligência artificial (IA) para interpretar perguntas, buscar informações em múltiplas fontes de conhecimento e fornecer respostas precisas e contextualizadas.

### Objetivos Principais

- ✅ Fornecer informações rápidas sobre integrações disponíveis
- ✅ Responder perguntas sobre funcionalidades, configurações e suporte
- ✅ Facilitar o acesso à base de conhecimento da empresa
- ✅ Reduzir o tempo de resposta para dúvidas comuns
- ✅ Melhorar a experiência do usuário no suporte

---

## 🛠️ Tecnologias e Ferramentas

### Linguagens de Programação

- **Python 3.11.9** - Linguagem principal do projeto
  - Escolhida pela facilidade de integração com APIs
  - Bibliotecas robustas para processamento de texto e IA
  - Excelente suporte para desenvolvimento de bots

### Frameworks e Bibliotecas Principais

#### Backend e API
- **Flask 3.1.1** - Framework web para criar a API REST
  - Recebe eventos do Slack via webhooks
  - Gerencia rotas e requisições HTTP
  - Leve e eficiente para aplicações de bot

- **Gunicorn 23.0.0** - Servidor WSGI para produção
  - Usado no deploy para servir a aplicação Flask
  - Suporta múltiplos workers para melhor performance

#### Integração com Slack
- **slack_sdk 3.36.0** - SDK oficial do Slack
  - WebClient para enviar mensagens e interagir com o Slack
  - SignatureVerifier para validar requisições do Slack
  - Suporte completo à API do Slack (mensagens, threads, botões)

#### Inteligência Artificial
- **google-generativeai 0.8.5** - Biblioteca para Google Gemini AI
  - Modelo utilizado: `gemini-2.0-flash`
  - Interpretação de intenções do usuário
  - Geração de respostas contextualizadas
  - Resumo de conteúdo de múltiplas fontes

#### Processamento de Dados
- **requests 2.32.4** - Cliente HTTP para APIs externas
  - Integração com Confluence, Zendesk, Google Sheets
  - Busca em múltiplas fontes de conhecimento

- **beautifulsoup4 4.13.4** - Parsing de HTML
  - Extração de conteúdo de páginas web
  - Limpeza e formatação de texto

#### Autenticação e Segurança
- **google-auth 2.40.3** - Autenticação Google
- **google-auth-oauthlib 1.2.2** - OAuth2 para Google APIs
- **google-auth-httplib2 0.2.0** - HTTP client para autenticação
- **google-api-python-client 2.177.0** - Cliente para Google APIs

#### Utilitários
- **python-dotenv 1.1.1** - Gerenciamento de variáveis de ambiente
- **fake-useragent 2.2.0** - Geração de user agents para web scraping

### Ferramentas e Serviços Externos

#### Plataformas de Conhecimento
- **Confluence (Atlassian)** - Base de conhecimento corporativa
  - Busca de artigos e documentação
  - Integração via API REST

- **Zendesk Help Center** - Centro de ajuda
  - Busca de artigos de suporte
  - API para consulta de conteúdo

- **Google Sheets** - Planilha de integrações
  - Fonte de dados sobre integrações disponíveis
  - Sincronização para JSON local

#### Plataforma de Deploy
- **Render** - Hospedagem em nuvem
  - Deploy automático via Git
  - Configuração via `render.yaml`
  - Ambiente Python gerenciado

#### Plataforma de Comunicação
- **Slack** - Canal de comunicação
  - Bot integrado via Slack App
  - Suporte a threads e mensagens diretas
  - Botões interativos e menus

---

## 🏗️ Arquitetura do Sistema

### Arquitetura Geral

O sistema segue uma arquitetura modular e extensível, inspirada no padrão "Nina" (sistema de conhecimento inteligente). A arquitetura é dividida em camadas:

```
┌─────────────────────────────────────────┐
│         Slack (Interface)               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Flask App (app.py)                 │
│  - Recebe eventos do Slack              │
│  - Roteia intenções                     │
│  - Gerencia fluxo de conversação        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Core (Núcleo do Sistema)          │
│  - Recepcionista: Análise de intenções  │
│  - KnowledgeManager: Gerenciamento de    │
│    múltiplas fontes                     │
│  - FonteValidator: Validação de fontes  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Handlers (Processadores)           │
│  - Busca em JSON, Sheets, Confluence   │
│  - Cache de respostas                   │
│  - Interpretação com Gemini             │
│  - Resumo de conteúdo                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Fontes de Conhecimento             │
│  - integracoes.json (JSON estático)     │
│  - Google Sheets                        │
│  - Confluence                           │
│  - Zendesk                              │
└─────────────────────────────────────────┘
```

### Componentes Principais

#### 1. **Recepcionista** (`core/recepcionista.py`)
- **Função**: Analisa a pergunta do usuário antes de processar
- **Tecnologia**: Google Gemini AI
- **Responsabilidades**:
  - Detectar idioma do usuário
  - Identificar intenção (buscar integração, listar, detalhes, etc.)
  - Reconstruir contexto de conversas anteriores
  - Solicitar esclarecimentos quando necessário

#### 2. **KnowledgeManager** (`core/knowledge_manager.py`)
- **Função**: Gerencia múltiplas fontes de conhecimento de forma unificada
- **Características**:
  - Sistema de prioridades para fontes
  - Busca paralela em múltiplas fontes
  - Agregação e validação de resultados
  - Configuração via JSON (`sources_config.json`)

#### 3. **FonteValidator** (`core/fonte_validator.py`)
- **Função**: Valida e filtra resultados das fontes
- **Responsabilidades**:
  - Verificar relevância dos resultados
  - Filtrar conteúdo duplicado
  - Garantir qualidade das respostas

#### 4. **Handlers** (`handlers/`)
Módulos especializados para diferentes funcionalidades:

- **`buscar_integracoes_json.py`**: Busca em arquivo JSON local
- **`gemini_handler.py`**: Interface com Google Gemini
- **`cache_respostas.py`**: Sistema de cache para melhorar performance
- **`contexto_thread.py`**: Análise de histórico de conversas
- **`interpretar_intencao_gemini.py`**: Interpretação avançada de intenções
- **`resumir_conteudo_gemini.py`**: Resumo inteligente de conteúdo
- **`menu_topicos.py`**: Menu interativo de tópicos
- **`tracking_perguntas.py`**: Rastreamento de perguntas sem resposta

---

## 🚀 Processo de Criação

### Fase 1: Planejamento e Análise (Inicial)

1. **Definição de Requisitos**
   - Identificação das necessidades dos usuários
   - Análise das fontes de conhecimento disponíveis
   - Definição de casos de uso principais

2. **Escolha de Tecnologias**
   - Avaliação de opções de IA (Gemini, OpenAI, etc.)
   - Seleção da plataforma de comunicação (Slack)
   - Definição da arquitetura base

### Fase 2: Desenvolvimento Inicial

1. **Setup do Projeto**
   - Criação da estrutura de diretórios
   - Configuração do ambiente Python
   - Integração básica com Slack

2. **Implementação Core**
   - Desenvolvimento do handler principal (`app.py`)
   - Integração com Google Gemini
   - Sistema básico de busca em fontes

### Fase 3: Evolução e Refatoração

1. **Implementação do Sistema "Nina"**
   - Criação do módulo `core/` com arquitetura modular
   - Implementação do `KnowledgeManager` para múltiplas fontes
   - Desenvolvimento do `Recepcionista` para análise de intenções

2. **Otimizações**
   - Sistema de cache para respostas frequentes
   - Melhoria na busca de integrações (JSON estático)
   - Implementação de contexto de threads

3. **Funcionalidades Avançadas**
   - Menu interativo de tópicos
   - Busca por tipo de integração
   - Botões interativos para informações completas
   - Sistema anti-duplicação de eventos

### Fase 4: Melhorias Contínuas

1. **Refinamento da Busca**
   - Normalização de nomes de integrações
   - Busca por tipo (tabela de frete, API, rastreio)
   - Melhoria na detecção de intenções

2. **Experiência do Usuário**
   - Formatação melhorada de respostas
   - Botões para ver informações completas
   - Suporte a threads do Slack

3. **Manutenção e Correções**
   - Correção de bugs identificados
   - Melhoria no tratamento de erros
   - Adição de logs detalhados

---

## ⚙️ Funcionalidades Principais

### 1. Busca de Integrações

O bot pode buscar informações sobre integrações de três formas:

#### a) Busca Específica
- Usuário pergunta sobre uma integração específica (ex: "Tray tem etiquetas?")
- Bot identifica a integração e retorna informações detalhadas

#### b) Listagem de Integrações
- Usuário solicita lista de todas as integrações
- Bot retorna lista formatada com categorias e informações básicas

#### c) Busca por Tipo
- Usuário pergunta por tipo de integração (ex: "quais integrações via tabela de frete")
- Bot filtra e retorna apenas integrações do tipo solicitado

### 2. Interpretação Inteligente de Intenções

O sistema utiliza Google Gemini para:
- Detectar o idioma do usuário
- Identificar a intenção principal
- Reconstruir contexto de conversas anteriores
- Solicitar esclarecimentos quando necessário

### 3. Múltiplas Fontes de Conhecimento

O bot busca informações em:
1. **JSON Estático** (`knowledge/integracoes.json`) - Prioridade 1
   - Dados locais, rápidos e confiáveis
   - Sincronizado periodicamente do Google Sheets

2. **Google Sheets** - Prioridade 2 (opcional)
   - Fonte dinâmica de dados
   - Pode ser desabilitada em produção

3. **Confluence** - Prioridade 3 (opcional)
   - Base de conhecimento corporativa
   - Busca em artigos e documentação

4. **Zendesk** - Prioridade 4 (opcional)
   - Centro de ajuda
   - Artigos de suporte

### 4. Sistema de Cache

- Armazena respostas frequentes
- Reduz chamadas à API do Gemini
- Melhora tempo de resposta
- Estatísticas de uso do cache

### 5. Contexto de Threads

- Analisa histórico de mensagens na thread
- Mantém contexto da conversa
- Permite respostas mais precisas a perguntas de acompanhamento

### 6. Menu Interativo

- Menu de boas-vindas ao iniciar conversa
- Navegação hierárquica por categorias
- Botões interativos para facilitar uso

### 7. Botões de Ação

- Botão "Ver Informações Completas" para integrações específicas
- Acesso rápido a detalhes completos
- Melhora experiência do usuário

### 8. Sistema Anti-Duplicação

- Previne processamento duplicado de eventos
- Múltiplas chaves de detecção
- Cache de eventos processados

---

## 📁 Estrutura do Projeto

```
chatbot_gemini/
├── app.py                          # Aplicação principal Flask
├── app_emergency.py                # Bot de emergência (fallback)
├── app_simple.py                   # Versão simplificada para testes
├── requirements.txt                # Dependências Python
├── runtime.txt                     # Versão do Python
├── render.yaml                     # Configuração de deploy no Render
│
├── core/                           # Módulos principais (Núcleo)
│   ├── __init__.py
│   ├── knowledge_manager.py        # Gerenciador de fontes de conhecimento
│   ├── recepcionista.py            # Analisador de intenções
│   └── fonte_validator.py          # Validador de fontes
│
├── handlers/                       # Processadores especializados
│   ├── buscar_integracoes_json.py  # Busca em JSON local
│   ├── buscar_integracoes_sheets.py # Busca em Google Sheets
│   ├── gemini_handler.py           # Interface com Gemini
│   ├── cache_respostas.py          # Sistema de cache
│   ├── contexto_thread.py          # Análise de contexto
│   ├── interpretar_intencao_gemini.py # Interpretação de intenções
│   ├── resumir_conteudo_gemini.py  # Resumo de conteúdo
│   ├── menu_topicos.py             # Menu interativo
│   ├── tracking_perguntas.py       # Rastreamento de perguntas
│   ├── jira.py                     # Integração com Jira
│   ├── zendesk_api.py              # Integração com Zendesk
│   └── ...                         # Outros handlers
│
├── knowledge/                      # Base de conhecimento
│   ├── integracoes.json            # Dados de integrações (JSON)
│   ├── sources_config.json         # Configuração de fontes
│   └── context_rules.json          # Regras de contexto
│
├── scripts/                        # Scripts utilitários
│   └── sincronizar_sheets_para_json.py # Sincronização Sheets → JSON
│
└── backup_*/                       # Backups de versões anteriores
```

---

## 🔄 Fluxo de Funcionamento

### Fluxo Principal de uma Pergunta

```
1. Usuário envia mensagem no Slack
   │
   ▼
2. Slack envia evento para /slack/events (webhook)
   │
   ▼
3. Flask valida assinatura e processa evento
   │
   ▼
4. Sistema anti-duplicação verifica se já foi processado
   │
   ▼
5. Recepcionista analisa a pergunta:
   - Detecta idioma
   - Identifica intenção
   - Reconstroi contexto se necessário
   │
   ▼
6. Roteamento baseado na intenção:
   - list_integrations → Lista todas
   - specific_integration → Busca específica
   - search_knowledge → Busca geral
   │
   ▼
7. KnowledgeManager busca em fontes (por prioridade):
   - JSON estático (prioridade 1)
   - Google Sheets (prioridade 2, se habilitado)
   - Confluence (prioridade 3, se habilitado)
   - Zendesk (prioridade 4, se habilitado)
   │
   ▼
8. FonteValidator valida e filtra resultados
   │
   ▼
9. Sistema formata resposta:
   - Usa cache se disponível
   - Gera resumo com Gemini se necessário
   - Formata com emojis e estrutura
   │
   ▼
10. Bot envia resposta no Slack:
    - Mensagem formatada
    - Botões interativos (se aplicável)
    - Thread para manter contexto
```

### Exemplo de Fluxo: "Tray tem etiquetas?"

```
1. Usuário: "Tray tem etiquetas?"
   │
   ▼
2. Recepcionista detecta:
   - Idioma: pt
   - Intenção: specific_integration
   - Query: "Tray tem etiquetas?"
   │
   ▼
3. Sistema busca "Tray" no JSON
   │
   ▼
4. Encontra integração "Tray"
   │
   ▼
5. Verifica campo "Funcionalidades" ou "Outras_Informacoes"
   │
   ▼
6. Formata resposta:
   "✅ Sim! A integração Tray possui suporte a etiquetas.
   
   📋 Funcionalidades:
   - Geração de etiquetas de envio
   - Impressão de etiquetas
   ..."
   │
   ▼
7. Adiciona botão "Ver Informações Completas"
   │
   ▼
8. Envia resposta no Slack
```

---

## 🚀 Deploy e Configuração

### Plataforma de Deploy

O bot é hospedado no **Render**, uma plataforma de nuvem que oferece:
- Deploy automático via Git
- Ambiente Python gerenciado
- Configuração via arquivo YAML

### Arquivo de Configuração (`render.yaml`)

```yaml
services:
  - type: web
    name: chatbot-slack
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: PORT
        generateValue: true
      - key: PYTHON_VERSION
        value: 3.11.9
```

### Variáveis de Ambiente Necessárias

#### Obrigatórias:
- `SLACK_BOT_TOKEN` - Token do bot do Slack
- `SLACK_SIGNING_SECRET` - Secret para validar requisições
- `GEMINI_API_KEY` - Chave da API do Google Gemini

#### Opcionais (dependendo das fontes habilitadas):
- `ATLASSIAN_EMAIL` - Email para Confluence
- `ATLASSIAN_TOKEN` - Token do Atlassian
- `ATLASSIAN_BASE_URL` - URL base do Atlassian
- `ZENDESK_EMAIL` - Email do Zendesk
- `ZENDESK_API_TOKEN` - Token do Zendesk
- `ZENDESK_SUBDOMAIN` - Subdomínio do Zendesk
- `GOOGLE_SHEETS_CREDENTIALS` - Credenciais do Google Sheets

### Processo de Deploy

1. **Preparação**
   ```bash
   git add .
   git commit -m "feat: nova funcionalidade"
   git push origin main
   ```

2. **Deploy Automático**
   - Render detecta push no repositório
   - Executa `buildCommand` (instala dependências)
   - Inicia aplicação com `startCommand` (gunicorn)

3. **Configuração no Render**
   - Adicionar variáveis de ambiente no dashboard
   - Configurar webhook do Slack apontando para URL do Render

### Sincronização de Dados

O arquivo `knowledge/integracoes.json` é sincronizado periodicamente do Google Sheets usando o script:

```bash
python scripts/sincronizar_sheets_para_json.py
```

Este script:
- Conecta ao Google Sheets
- Baixa dados atualizados
- Converte para formato JSON
- Salva em `knowledge/integracoes.json`

---

## 📊 Estatísticas e Monitoramento

### Logs

O sistema gera logs detalhados para:
- Eventos recebidos do Slack
- Intenções detectadas
- Buscas realizadas
- Erros e exceções
- Performance de cache

### Métricas Disponíveis

- Estatísticas de cache (hits, misses)
- Perguntas sem resposta (tracking)
- Tempo de resposta
- Taxa de sucesso nas buscas

---

## 🔒 Segurança

### Validação de Requisições

- **Signature Verification**: Todas as requisições do Slack são validadas usando `SignatureVerifier`
- Previne requisições maliciosas ou falsificadas

### Gerenciamento de Secrets

- Variáveis de ambiente para credenciais
- Nunca commitadas no código
- Gerenciadas via dashboard do Render

### Sistema Anti-Duplicação

- Previne processamento duplicado de eventos
- Cache de eventos processados
- Limpeza automática de cache antigo

---

## 🎓 Conclusão

O **Chatbot de Integrações** é uma solução completa e robusta que combina:

- ✅ **Inteligência Artificial** (Google Gemini) para interpretação natural
- ✅ **Múltiplas Fontes de Conhecimento** para informações abrangentes
- ✅ **Arquitetura Modular** para fácil manutenção e extensão
- ✅ **Performance Otimizada** com cache e busca eficiente
- ✅ **Experiência do Usuário** com interface interativa no Slack

O sistema foi desenvolvido com foco em:
- **Confiabilidade**: Sistema anti-duplicação, tratamento de erros robusto
- **Performance**: Cache, busca otimizada, JSON estático
- **Extensibilidade**: Arquitetura modular, fácil adicionar novas fontes
- **Usabilidade**: Interface intuitiva, respostas claras, contexto mantido

---

## 📝 Notas Finais

Este documento foi criado para fornecer uma visão completa do sistema. Para questões específicas sobre implementação, consulte os comentários no código ou a documentação inline dos módulos.

**Última atualização**: Janeiro 2025  
**Versão do Sistema**: 2.0 (Estilo Nina)  
**Python**: 3.11.9  
**Status**: Em produção

