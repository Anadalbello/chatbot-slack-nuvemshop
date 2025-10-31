#!/usr/bin/env python3
"""
Script para criar backup completo do chatbot atual
Antes de iniciar a refatoração para o padrão Nina
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

def criar_backup():
    """Cria backup completo do chatbot atual"""
    
    # Diretório do projeto
    projeto_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = projeto_dir / f"backup_pre_refatoracao_nina_{timestamp}"
    
    print(f"🔄 Criando backup em: {backup_dir}")
    
    # Arquivos e diretórios para incluir
    itens_para_backup = [
        # Arquivos principais
        "app.py",
        "app_emergency.py",
        "app_simple.py",
        
        # Configurações
        "requirements.txt",
        "runtime.txt",
        "render.yaml",
        ".env",  # Incluído conforme solicitado
        
        # Base de conhecimento
        "faq_database.json",
        "perguntas_log.json",
        
        # Handlers
        "handlers/",
        
        # Scripts de teste e utilitários
        "test_google_sheets.py",
        "testar_token_confluence.py",
        "teste_pre_deploy.py",
        "teste_zendesk_api.py",
        "diagnostico_confluence.py",
        "diagnostico.py",
        "config_zendesk.py",
        "configurar_env.py",
        "verificar_config_render.py",
        "sincronizar_integracoes_manual.py",
        "listar_espacos_confluence.py",
    ]
    
    # Criar diretório de backup
    backup_dir.mkdir(exist_ok=True)
    
    # Copiar arquivos
    arquivos_copiados = []
    diretorios_copiados = []
    erros = []
    
    for item in itens_para_backup:
        origem = projeto_dir / item
        
        if not origem.exists():
            print(f"⚠️  Não encontrado: {item}")
            continue
        
        destino = backup_dir / item
        
        try:
            if origem.is_file():
                # Criar diretório de destino se necessário
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, destino)
                arquivos_copiados.append(str(item))
                print(f"✅ Copiado: {item}")
            
            elif origem.is_dir():
                # Copiar diretório inteiro (exceto __pycache__)
                if destino.exists():
                    shutil.rmtree(destino)
                
                shutil.copytree(
                    origem,
                    destino,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '__pycache__'),
                    dirs_exist_ok=True
                )
                diretorios_copiados.append(str(item))
                print(f"✅ Copiado diretório: {item}")
        
        except Exception as e:
            erro_msg = f"Erro ao copiar {item}: {e}"
            erros.append(erro_msg)
            print(f"❌ {erro_msg}")
    
    # Copiar arquivos .md manualmente
    for md_file in projeto_dir.glob("*.md"):
        if "backup" not in md_file.name.lower():
            try:
                shutil.copy2(md_file, backup_dir / md_file.name)
                arquivos_copiados.append(md_file.name)
                print(f"✅ Copiado: {md_file.name}")
            except Exception as e:
                erro_msg = f"Erro ao copiar {md_file.name}: {e}"
                erros.append(erro_msg)
                print(f"❌ {erro_msg}")
    
    # Copiar arquivos .py da raiz (scripts adicionais)
    for py_file in projeto_dir.glob("*.py"):
        if py_file.name != "backup_chatbot.py" and py_file.name not in arquivos_copiados:
            try:
                shutil.copy2(py_file, backup_dir / py_file.name)
                arquivos_copiados.append(py_file.name)
                print(f"✅ Copiado: {py_file.name}")
            except Exception as e:
                erro_msg = f"Erro ao copiar {py_file.name}: {e}"
                erros.append(erro_msg)
    
    # Criar arquivo de metadados do backup
    metadata = {
        "timestamp": timestamp,
        "data_criacao": datetime.now().isoformat(),
        "motivo": "Backup antes da refatoração para padrão Nina",
        "arquivos": sorted(arquivos_copiados),
        "diretorios": sorted(diretorios_copiados),
        "python_version": os.sys.version,
        "erros": erros,
        "observacoes": [
            "Este backup contém o estado atual do chatbot funcional",
            ".env foi incluído conforme solicitado",
            "NÃO inclui venv (ambiente virtual - recrie com python -m venv venv)",
            "NÃO inclui __pycache__ (arquivos compilados)",
            "Para restaurar: copiar arquivos de volta para a raiz do projeto"
        ]
    }
    
    with open(backup_dir / "BACKUP_METADATA.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Criar README do backup
    readme_content = f"""# Backup do Chatbot - {timestamp}

## 📋 Informações do Backup

- **Data:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
- **Motivo:** Backup antes da refatoração para padrão Nina
- **Arquivos salvos:** {len(arquivos_copiados)} arquivos, {len(diretorios_copiados)} diretórios

## 📁 Conteúdo do Backup

### Arquivos principais:
{chr(10).join(f"- `{f}`" for f in arquivos_copiados[:30])}
{f"- ... e mais {len(arquivos_copiados) - 30} arquivos" if len(arquivos_copiados) > 30 else ""}

### Diretórios:
{chr(10).join(f"- `{d}/`" for d in diretorios_copiados)}

## 🔄 Como Restaurar

Se precisar voltar à versão antiga:

1. **Fazer backup da versão nova primeiro:**
   ```bash
   # Garantir que não perde nada da nova versão
   ```

2. **Restaurar arquivos:**
   ```bash
   # Da raiz do projeto, copiar arquivos do backup
   cp -r backup_pre_refatoracao_nina_{timestamp}/* .
   ```

3. **Ou restaurar seletivamente:**
   ```bash
   # Restaurar apenas app.py
   cp backup_pre_refatoracao_nina_{timestamp}/app.py .
   
   # Restaurar handlers
   cp -r backup_pre_refatoracao_nina_{timestamp}/handlers/* handlers/
   
   # Restaurar .env (cuidado!)
   cp backup_pre_refatoracao_nina_{timestamp}/.env .env
   ```

## ⚠️ Observações Importantes

- O arquivo `.env` **FOI incluído** no backup (conforme solicitado)
- O ambiente virtual `venv/` não foi incluído (recrie com `python -m venv venv`)
- Arquivos compilados `__pycache__` não foram incluídos

## 🚀 Próximos Passos

Após este backup, podemos iniciar a refatoração seguramente!

## 📊 Estatísticas

- **Total de arquivos:** {len(arquivos_copiados)}
- **Total de diretórios:** {len(diretorios_copiados)}
- **Erros durante cópia:** {len(erros)}
"""
    
    if erros:
        readme_content += f"\n## ⚠️ Erros Encontrados\n\n"
        readme_content += "\n".join(f"- {e}" for e in erros)
    
    with open(backup_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"\n{'='*60}")
    print(f"✅ BACKUP CONCLUÍDO!")
    print(f"📁 Localização: {backup_dir}")
    print(f"📊 Arquivos: {len(arquivos_copiados)}")
    print(f"📂 Diretórios: {len(diretorios_copiados)}")
    if erros:
        print(f"⚠️  Erros: {len(erros)}")
    print(f"{'='*60}\n")
    
    # Informações importantes
    print("✅ ARQUIVOS INCLUÍDOS:")
    print("   - .env (incluído conforme solicitado)")
    print("   - Todos os arquivos .py")
    print("   - Todos os handlers/")
    print("   - Arquivos de configuração")
    print("\n⚠️  EXCLUÍDOS (normal):")
    print("   - venv/ (ambiente virtual)")
    print("   - __pycache__ (arquivos compilados)")
    print(f"\n💾 Backup salvo em: {backup_dir.name}\n")
    
    return backup_dir

if __name__ == "__main__":
    try:
        backup_dir = criar_backup()
        print("✅ Pronto para iniciar a refatoração!")
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        import traceback
        traceback.print_exc()


