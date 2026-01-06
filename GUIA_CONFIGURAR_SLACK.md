# 📋 Guia: Configurar Eventos do Slack para Respostas em Threads

## 🎯 Objetivo

Habilitar o evento `message` para que o bot possa responder em threads sem precisar ser mencionado.

## 📍 Passo 1: Acessar Configurações do App

1. Acesse: https://api.slack.com/apps
2. Selecione seu app (ou crie um novo se necessário)
3. No menu lateral esquerdo, clique em **"Event Subscriptions"**

## 📍 Passo 2: Configurar Request URL (se ainda não estiver)

1. Em **"Enable Events"**, ative a opção (toggle ON)
2. Em **"Request URL"**, insira a URL do seu bot:
   - Se estiver no Render: `https://seu-app.onrender.com/slack/events`
   - Se estiver localmente com ngrok: `https://seu-subdomain.ngrok.io/slack/events`
3. O Slack vai testar a URL - deve mostrar ✅ "Verified"

## 📍 Passo 3: Adicionar Permissões (Scopes) do Bot

**IMPORTANTE:** Antes de adicionar eventos, configure as permissões necessárias!

1. No menu lateral esquerdo, clique em **"OAuth & Permissions"**
2. Role até **"Scopes"** → **"Bot Token Scopes"**
3. Adicione as seguintes permissões (clique em "Add an OAuth Scope"):

   **Permissões obrigatórias (já devem estar):**
   - ✅ `channels:history` - Ler histórico de canais públicos
   - ✅ `channels:read` - Ver canais públicos
   - ✅ `chat:write` - Enviar mensagens
   - ✅ `app_mentions:read` - Ler menções ao bot

   **Permissões para threads em canais privados:**
   - ➕ `groups:history` - Ler histórico de canais privados (grupos)
   - ➕ `groups:read` - Ver canais privados
   - ➕ `im:history` - Ler histórico de mensagens diretas (DM)
   - ➕ `mpim:history` - Ler histórico de grupos diretos

3. Após adicionar TODAS as permissões, **IMPORTANTE:** role até o topo da página e clique em **"Reinstall to Workspace"**
4. Autorize todas as permissões e confirme
5. **⚠️ CRÍTICO:** Após reinstalar, aguarde alguns segundos e verifique se as permissões aparecem como "Installed" (verde)

**💡 Dica:** Se você não reinstalar o app após adicionar permissões, elas não serão aplicadas! O erro `missing_scope` continuará aparecendo nos logs.

## 📍 Passo 4: Adicionar Eventos do Bot

1. Role a página até a seção **"Subscribe to bot events"**
2. Clique em **"Add Bot User Event"**
3. Digite ou selecione os seguintes eventos:

   **Eventos necessários:**
   - `app_mention` - Para quando o bot é mencionado (já deve estar)
   - `message` - Para mensagens em threads sem precisar mencionar

   **💡 Dica:** O evento `message` é genérico e funciona para todos os tipos de canais (públicos, privados, DMs) baseado nas permissões (scopes) que você configurou no Passo 3.

4. Após adicionar, clique em **"Save Changes"**

**⚠️ Nota:** Se você não encontrar `message` na lista, pode ser que apareça como "message" ou você precise digitar manualmente. O importante é que o evento seja apenas `message` (sem `.channels`, `.groups`, etc).

## 📍 Passo 5: Instalar/Reinstalar App (se necessário)

Se aparecer um banner amarelo pedindo para reinstalar o app:

1. Vá em **"Install App"** no menu lateral
2. Clique em **"Reinstall to Workspace"**
3. Autorize todas as permissões solicitadas
4. Confirme a instalação

## ✅ Verificação

Após configurar, você deve ver:

**Em OAuth & Permissions:**
- ✅ Bot Token Scopes inclui: `channels:history`, `groups:history`, `im:history`, `mpim:history`
- ✅ Status: **Installed** (verde)

**Em Event Subscriptions:**
- ✅ Enable Events: **On**
- ✅ Request URL: **Verified** (com ✅ verde)
- ✅ Bot Events: Deve incluir `app_mention` e `message`

## 🧪 Testar

1. Em um canal do Slack, mencione o bot: `@Tina oi`
2. O bot deve responder na thread
3. **Agora, sem mencionar**, responda na thread: `temos integração com Bling?`
4. O bot deve responder automaticamente! ✅

## ⚠️ Troubleshooting

### Bot não responde sem mention
- Verifique se o evento `message` (genérico) foi adicionado
- Verifique se as permissões (scopes) do Passo 3 foram adicionadas
- Verifique se o app foi reinstalado após adicionar eventos e permissões
- Verifique os logs do bot para ver se está recebendo os eventos
- O evento deve ser apenas `message` (não precisa dos específicos como `message.channels`)

### Erro "missing_scope" nos logs
- Adicione as permissões faltantes em "OAuth & Permissions" → "Bot Token Scopes"
- Permissões necessárias: `groups:history`, `groups:read`, `im:history`, `mpim:history`
- Após adicionar, **reinstale o app** no workspace
- Verifique se o erro desapareceu dos logs

### Event Subscriptions não salva
- Certifique-se de que a Request URL está verificada (✅ verde)
- Tente adicionar os eventos um por vez
- Verifique se tem permissões de admin no workspace

### URL não verifica
- Certifique-se de que o bot está rodando e acessível
- Verifique se o endpoint `/slack/events` está correto
- Verifique se o servidor está respondendo corretamente ao desafio do Slack

## 📚 Documentação Oficial

- [Slack Events API](https://api.slack.com/events-api)
- [Slack Event Types](https://api.slack.com/events/message)
- [Configurar Event Subscriptions](https://api.slack.com/events-api#subscriptions)

## 🎉 Pronto!

Com isso configurado, o bot pode:
- ✅ Responder quando mencionado (comportamento normal)
- ✅ Responder em threads onde já participou (sem precisar @)
- ✅ Manter contexto da conversa na thread
- ✅ Ignorar mensagens onde não deve responder (segurança)

