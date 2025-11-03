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

## 📍 Passo 3: Adicionar Eventos do Bot

1. Role a página até a seção **"Subscribe to bot events"**
2. Clique em **"Add Bot User Event"**
3. Adicione os seguintes eventos (um por vez ou separados por vírgula):

   **Eventos obrigatórios:**
   - `app_mention` - Para quando o bot é mencionado (já deve estar)

   **Eventos para threads sem mention:**
   - `message.channels` - Mensagens em canais públicos
   - `message.groups` - Mensagens em canais privados
   - `message.im` - Mensagens diretas (DM)
   - `message.mpim` - Mensagens em grupos diretos

4. Após adicionar cada evento, clique em **"Save Changes"**

## 📍 Passo 4: Instalar/Reinstalar App (se necessário)

Se aparecer um banner amarelo pedindo para reinstalar o app:

1. Vá em **"Install App"** no menu lateral
2. Clique em **"Reinstall to Workspace"**
3. Autorize todas as permissões solicitadas
4. Confirme a instalação

## ✅ Verificação

Após configurar, você deve ver:

- ✅ Event Subscriptions: **On**
- ✅ Request URL: **Verified** (com ✅ verde)
- ✅ Bot Events: Lista com os eventos adicionados acima

## 🧪 Testar

1. Em um canal do Slack, mencione o bot: `@Perguntaê oi`
2. O bot deve responder na thread
3. **Agora, sem mencionar**, responda na thread: `temos integração com Bling?`
4. O bot deve responder automaticamente! ✅

## ⚠️ Troubleshooting

### Bot não responde sem mention
- Verifique se os eventos `message.*` foram adicionados
- Verifique se o app foi reinstalado após adicionar os eventos
- Verifique os logs do bot para ver se está recebendo os eventos

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

