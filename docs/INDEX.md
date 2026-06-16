# Documentação - LMS Lock Chapter

Índice completo da documentação do app lms_lock_chapter v16.

---

## 📚 Documentação Principal

### 1. [README.md](../README.md)
**Para:** Usuários e instaladores  
**Conteúdo:**
- Visão geral do app
- Instruções de instalação
- Configuração de pré-commit
- Informações de licença

**Ler quando:** Instalando o app pela primeira vez

---

### 2. [CLEANUP.md](../CLEANUP.md)
**Para:** Administradores ERPNext  
**Conteúdo:**
- Processo de desinstalação automático
- O que é preservado vs. removido
- Fluxo de hooks (before/after)
- Checklist de desinstalação
- Monitoramento via logs
- Re-instalação

**Ler quando:** 
- Planejando remover o app
- Precisando entender o que acontece na desinstalação
- Supervisionando um administrador desinstalar

**Tamanho:** 300 linhas

---

### 3. [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
**Para:** Administradores e desenvolvedores  
**Conteúdo:**
- Problemas na desinstalação (permissões, cache, bloqueios)
- Problemas na instalação (dependências, DocTypes)
- Problemas em execução (performance, capítulos não bloqueados)
- Debugging e logs
- Contatos de suporte

**Ler quando:**
- Algo deu errado durante instalação/desinstalação
- App não está funcionando como esperado
- Precisando de troubleshooting

**Tamanho:** 384 linhas

---

### 4. [docs/ARCHITECTURE.md](./ARCHITECTURE.md)
**Para:** Desenvolvedores e arquitetos  
**Conteúdo:**
- Visão geral da arquitetura
- Pontos de integração com Frappe
- Componentes principais (install.py, uninstall.py)
- Estrutura de armazenamento (Redis, Database)
- Mecanismo de cleanup seguro
- Testes
- Diagrama de estados
- Ciclo de vida completo
- Casos extremos
- Performance considerations

**Ler quando:**
- Entendendo como o app funciona internamente
- Contribuindo com código
- Fazendo troubleshooting avançado
- Planejando alterações no sistema

**Tamanho:** 510 linhas

---

## 🔧 Código-Fonte

### Python

#### `lms_lock_chapter/install.py`
**Funções:**
- `before_install()` - Validações pré-instalação
- `after_install()` - Setup pós-instalação
- `_setup_cache()` - Configura Redis
- `_validate_doctypes()` - Valida DocTypes obrigatórios

**Quando Executado:** 
- `before_install()` → Antes da instalação
- `after_install()` → Depois da instalação

---

#### `lms_lock_chapter/uninstall.py`
**Funções:**
- `before_uninstall()` - Log de estado pré-desinstalação
- `after_uninstall()` - Cleanup pós-desinstalação
- `_clean_redis_cache()` - Remove chaves de cache
- `_remove_doc_events()` - Limpa document events
- `_remove_client_scripts()` - Remove Client Scripts
- `_clean_session_data()` - Limpa dados de sessão

**Quando Executado:**
- `before_uninstall()` → Antes da desinstalação
- `after_uninstall()` → Depois da desinstalação

---

#### `lms_lock_chapter/hooks.py`
**Mudanças:**
- Adicionado `before_install`
- Adicionado `after_install`
- Adicionado `before_uninstall`
- Adicionado `after_uninstall`

**Outras Funcionalidades:** (já existentes)
- Override de LMS Course
- Has permission hooks
- Doc events
- Web include JS

---

### Testes

#### `lms_lock_chapter/tests/test_uninstall.py`
**Classes:**
- `TestLmsLockChapterUninstall` - Testes de desinstalação
- `TestLmsLockChapterInstall` - Testes de instalação

**Testes:**
- `test_cache_cleanup_on_uninstall()` - Valida limpeza de cache
- `test_no_system_data_loss_on_uninstall()` - Preservação de dados
- `test_permission_hooks_removed()` - Desativação de hooks
- `test_chapters_become_accessible_after_uninstall()` - Acessibilidade
- `test_required_doctypes_exist()` - Validação de dependências
- `test_frappe_lms_app_required()` - App obrigatório
- `test_cache_initialized_on_install()` - Inicialização de cache

**Executar:**
```bash
bench run-tests lms_lock_chapter.tests.test_uninstall
```

---

### Patches

#### `lms_lock_chapter/patches/v0_0_1_initial_setup.py`
**Função:** `execute()`
**Propósito:** Setup inicial na instalação/upgrade para v0.0.1
**Quando Executado:** Automaticamente durante instalação

---

## 📖 Fluxos Principais

### Fluxo de Instalação

```
bench install-app lms_lock_chapter
    ↓
1. before_install()
   ├─ Valida frappe-lms instalado
   └─ Valida DocTypes obrigatórios
    ↓
2. Frappe registra hooks
   ├─ Override classes carregadas
   └─ Hooks ativados
    ↓
3. after_install()
   ├─ _setup_cache() → testa Redis
   └─ _validate_doctypes() → revalida
    ↓
✅ App instalado e operacional
   ├─ Bloqueio sequencial ativo
   ├─ Cache Redis em uso
   └─ Hooks registrados
```

---

### Fluxo de Desinstalação

```
bench uninstall-app lms_lock_chapter
    ↓
1. before_uninstall()
   └─ Log estado dos cursos publicados
    ↓
2. Frappe descarrega hooks e overrides
    ↓
3. after_uninstall()
   ├─ _clean_redis_cache()
   │  ├─ SCAN para chaves "chapter_comp_*"
   │  └─ DEL cada chave + hash
   ├─ _remove_doc_events()
   ├─ _remove_client_scripts()
   └─ _clean_session_data()
    ↓
✅ App desinstalado e limpo
   ├─ Capítulos acessíveis
   ├─ Cache limpo
   ├─ Hooks removidos
   └─ Dados do LMS preservados
```

---

## 🎯 Caso de Uso: Removendo o App

**Cenário:** Você quer remover o bloqueio sequencial de capítulos

**Passo a Passo:**

1. **Ler documentação** → [CLEANUP.md](../CLEANUP.md)
   - Entender o que vai ser removido

2. **Fazer backup** (opcional)
   ```bash
   mysqldump -u frappe -p frappe_db_name > backup.sql
   ```

3. **Desinstalar app**
   ```bash
   bench uninstall-app lms_lock_chapter
   ```

4. **Verificar resultado**
   - Logs em `frappe.log`
   - Tentar acessar capítulo (deve estar desbloqueado)
   - Verificar que cursos ainda existem

5. **Se houver problema** → [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)

---

## 🆘 Guia de Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| Cache Redis não limpo | Ver [TROUBLESHOOTING.md](../TROUBLESHOOTING.md#problema-cache-redis-não-limpa) |
| Capítulos ainda bloqueados | Ver [TROUBLESHOOTING.md](../TROUBLESHOOTING.md#problema-capítulos-ainda-bloqueados-após-desinstalação) |
| "frappe-lms não encontrado" | Ver [TROUBLESHOOTING.md](../TROUBLESHOOTING.md#problema-frappe-lms-não-encontrado) |
| Performance lenta | Ver [TROUBLESHOOTING.md](../TROUBLESHOOTING.md#problema-performance-lenta-em-cursos-grandes) |
| Preciso entender como funciona | Ver [ARCHITECTURE.md](./ARCHITECTURE.md) |

---

## 📊 Estrutura de Diretórios

```
lms_lock_chapter/
├── __init__.py
├── config/
├── hooks.py                    ← Configuração principal
├── install.py                  ← ✨ Novo: Instalação
├── uninstall.py                ← ✨ Novo: Desinstalação
├── lms_overrides.py            ← Overrides de permissão
├── modules.txt
├── patches/
│   ├── __init__.py
│   └── v0_0_1_initial_setup.py ← ✨ Novo: Patch inicial
├── public/
│   └── js/
│       ├── lms_chapter_lock.js
│       └── lms_portal_lock.js
├── templates/
│   └── pages/
└── tests/                      ← ✨ Novo: Testes
    ├── __init__.py
    └── test_uninstall.py       ← ✨ Novo: Testes de cleanup

docs/
├── INDEX.md                    ← ✨ Este arquivo
├── ARCHITECTURE.md             ← ✨ Novo: Arquitetura técnica
├── CLEANUP.md                  ← ✨ Novo: Processo de cleanup
└── TROUBLESHOOTING.md          ← ✨ Novo: Troubleshooting
```

---

## ✨ O Que Foi Adicionado Nesta Release

- ✅ `install.py` - Sistema de instalação com validações
- ✅ `uninstall.py` - Sistema de limpeza seguro
- ✅ `docs/ARCHITECTURE.md` - Documentação técnica
- ✅ `docs/CLEANUP.md` - Guia de desinstalação
- ✅ `TROUBLESHOOTING.md` - Guia de problemas
- ✅ `lms_lock_chapter/tests/test_uninstall.py` - Testes automatizados
- ✅ `lms_lock_chapter/patches/v0_0_1_initial_setup.py` - Sistema de patches
- ✅ Hooks de instalação/desinstalação em `hooks.py`

---

## 🚀 Próximas Leituras

**Para administradores:**
1. [CLEANUP.md](../CLEANUP.md) - Entender desinstalação
2. [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Resolver problemas

**Para desenvolvedores:**
1. [ARCHITECTURE.md](./ARCHITECTURE.md) - Entender internals
2. Código-fonte: `install.py`, `uninstall.py`
3. Testes: `tests/test_uninstall.py`

**Para arquitetos/gestores:**
1. [CLEANUP.md](../CLEANUP.md) - Impacto da desinstalação
2. [ARCHITECTURE.md](./ARCHITECTURE.md) - Como funciona
3. [README.md](../README.md) - Overview geral

---

## 📞 Suporte

**Email:** suporte@glsoltec.com.br  
**GitHub:** https://github.com/glsoltec/lms_lock_chapter  
**Frappe Forum:** https://discuss.erpnext.com

---

**Versão:** v16  
**Última atualização:** 2026-06-15  
**Autor:** GL Soltec  
**Desenvolvedor:** Claude Haiku 4.5
