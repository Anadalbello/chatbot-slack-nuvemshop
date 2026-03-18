# Reindexar Pinecone no Render

Depois de atualizar o JSON (por exemplo, adicionar "Outros nomes" como WordPress para Woocommerce), é preciso reindexar o Pinecone para a busca vetorial encontrar essas variações.

## Passos no Render

1. **Definir o secret**
   - No [Dashboard do Render](https://dashboard.render.com) → seu serviço **chatbot-slack** → **Environment**.
   - Adicione uma variável:
     - **Key:** `PINECONE_SYNC_SECRET`
     - **Value:** uma senha forte (ex.: gere uma em [random.org](https://www.random.org/strings/) e guarde).

2. **Fazer o deploy** (se ainda não fez) para que a nova rota e o novo código estejam no ar.

3. **Chamar a rota de sync** (uma vez após o deploy):
   - No navegador ou com `curl`:
   ```bash
   curl "https://SEU-APP.onrender.com/internal/sync-pinecone?secret=SEU_PINECONE_SYNC_SECRET"
   ```
   - Ou com header:
   ```bash
   curl -H "X-Sync-Secret: SEU_PINECONE_SYNC_SECRET" https://SEU-APP.onrender.com/internal/sync-pinecone
   ```

4. **Resposta esperada**
   - Sucesso: `{"status":"ok","message":"Pinecone reindexado com sucesso (namespace br)..."}`  
   - Erro de secret: `403` ou `503` (verifique `PINECONE_SYNC_SECRET` e a URL do app).

Substitua `SEU-APP` pela URL do seu serviço no Render e `SEU_PINECONE_SYNC_SECRET` pelo valor que você definiu no passo 1.
