# 🔧 Como Configurar Google Sheets API

## 📝 Passo 1: Criar Projeto no Google Cloud

1. Acesse: https://console.cloud.google.com/
2. Clique em **"Selecionar projeto"** → **"Novo projeto"**
3. Nome: `Chatbot Nuvemshop` (ou qualquer nome)
4. Clique em **"Criar"**

## 🔌 Passo 2: Habilitar Google Sheets API

1. No menu lateral, vá em: **APIs e Serviços** → **Biblioteca**
2. Busque por: **"Google Sheets API"**
3. Clique e depois em **"Ativar"**

## 🔑 Passo 3: Criar Credenciais (Service Account)

### Opção A: Service Account (Recomendado para bots)

1. Vá em: **APIs e Serviços** → **Credenciais**
2. Clique em: **"Criar credenciais"** → **"Conta de serviço"**
3. Preencha:
   - **Nome**: `chatbot-sheets-reader`
   - **ID**: (gerado automaticamente)
   - **Descrição**: "Bot para ler planilha de integrações"
4. Clique em **"Criar e continuar"**
5. Em **"Papel"**: Selecione **"Visualizador"** (read-only)
6. Clique em **"Concluir"**

### Gerar chave JSON

1. Na lista de contas de serviço, clique na que você criou
2. Vá na aba **"Chaves"**
3. Clique em **"Adicionar chave"** → **"Criar nova chave"**
4. Escolha formato: **JSON**
5. Clique em **"Criar"**
   - 📥 Um arquivo JSON será baixado automaticamente

### ⚠️ Importante: Compartilhar planilha com a Service Account

1. Abra o arquivo JSON baixado
2. Copie o valor do campo **"client_email"** (algo como `chatbot-sheets-reader@project-id.iam.gserviceaccount.com`)
3. Abra sua planilha no Google Sheets
4. Clique em **"Compartilhar"**
5. Cole o e-mail da service account
6. Escolha permissão: **"Leitor"**
7. Clique em **"Enviar"**

---

## 📂 Passo 4: Adicionar credenciais ao projeto

### Opção 1: Usar arquivo JSON diretamente

Salve o arquivo JSON baixado como:
```
/home/anabello/Área de trabalho/Codes/chatbot_gemini_completo_final/chatbot_gemini/google_sheets_credentials.json
```

**⚠️ IMPORTANTE**: Adicione ao `.gitignore` para não commitar credenciais!

```bash
echo "google_sheets_credentials.json" >> .gitignore
```

### Opção 2: Usar variável de ambiente (Recomendado para produção)

Copie TODO o conteúdo do arquivo JSON e adicione ao `.env`:

```bash
GOOGLE_SHEETS_CREDENTIALS='{"type": "service_account", "project_id": "...todo o JSON aqui..."}'
```

---

## 🔗 Passo 5: Configurar ID da planilha

Adicione ao `.env`:

```bash
# ID da planilha (pegar na URL)
GOOGLE_SHEETS_ID="1ABC123xyz"

# Nome da aba/sheet
GOOGLE_SHEETS_TAB="Sheet1"
```

---

## ✅ Verificação

Após seguir os passos, você terá:

- ✅ Google Sheets API habilitada
- ✅ Service Account criada
- ✅ Arquivo JSON de credenciais baixado
- ✅ Planilha compartilhada com a service account
- ✅ Credenciais configuradas no projeto (.env ou arquivo JSON)
- ✅ ID da planilha configurado

---

## 🚀 Próximo passo

Execute o teste de conexão:

```bash
python test_google_sheets.py
```

---

**Data**: 2025-10-15

