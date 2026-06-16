# Cleanup e Desinstalação - LMS Lock Chapter

Este documento descreve como o app **LMS Lock Chapter** é limpo quando removido, garantindo que nenhum dado do sistema seja perdido.

---

## 📋 Visão Geral

Quando o app `lms_lock_chapter` é desinstalado do ERPNext, um processo automático de cleanup é acionado para:

✅ **Remover todas as associações** criadas pelo app  
✅ **Preservar todos os dados** do LMS (cursos, capítulos, aulas, progresso)  
✅ **Limpar cache Redis** associado ao app  
✅ **Desativar hooks e overrides** de forma segura  

---

## 🔄 Processo de Desinstalação

### Hooks Registrados

O app registra dois hooks para o ciclo de desinstalação:

```python
# Em hooks.py
before_uninstall = "lms_lock_chapter.uninstall.before_uninstall"
after_uninstall = "lms_lock_chapter.uninstall.after_uninstall"
```

### Execução Sequencial

#### 1️⃣ `before_uninstall()` - Antes da Desinstalação

**Localização:** `lms_lock_chapter/uninstall.py:before_uninstall()`

**Ações:**
- Valida estado atual dos cursos publicados
- Registra warning no log se houver cursos ativos
- Permite que administradores vejam o impacto antes de continuar

**Saída de Log:**
```
INFO: Preparando desinstalação do app lms_lock_chapter...
WARNING: Desinstalando app com X cursos publicados. Todos os capítulos ficarão acessíveis após a desinstalação.
```

#### 2️⃣ `after_uninstall()` - Depois da Desinstalação

**Localização:** `lms_lock_chapter/uninstall.py:after_uninstall()`

**Ações Realizadas (em ordem):**

##### A. Limpeza de Cache Redis
```python
_clean_redis_cache()
```

- Remove todas as chaves de cache de conclusão de capítulos
- Padrão de chaves removidas: `chapter_comp_*`
- Usa SCAN para iterar sem bloquear Redis
- Também remove hash `lms_lock_chapter`

**Impacto:** 
- ✅ Nenhum dado persistente é perdido
- ✅ Cache é apenas uma otimização, dados estão no banco

##### B. Remoção de Document Events
```python
_remove_doc_events()
```

- Frappe automaticamente desativa eventos quando o app é removido
- Esta função apenas limpa registros associados

**Impacto:**
- ✅ Events do app deixam de ser acionados
- ✅ Outros apps' events não são afetados

##### C. Remoção de Client Scripts
```python
_remove_client_scripts()
```

- Remove Client Scripts customizados criados pelo app
- Filtra por module `"LMS Lock Chapter"`
- Mantém scripts de outros apps intactos

**Impacto:**
- ✅ Scripts específicos do app são removidos
- ✅ Scripts de outros apps continuam funcionando

##### D. Limpeza de Dados de Sessão
```python
_clean_session_data()
```

- Remove flags e dados temporários de sessão
- Limpa dados associados ao app

**Impacto:**
- ✅ Nenhum dado persistente é afetado
- ✅ Apenas cache de sessão é limpo

---

## 📊 O que Acontece Após Desinstalação

### ✅ Preservado (Não Afetado)

| Item | Status |
|------|--------|
| **LMS Courses** | ✅ Mantém todos os dados |
| **Course Chapters** | ✅ Não são deletados |
| **Course Lessons** | ✅ Permanecem intactos |
| **LMS Course Progress** | ✅ Histórico preservado |
| **Usuários** | ✅ Contas intactas |
| **Permissões Frappe** | ✅ Não afetadas |
| **Outros Apps** | ✅ Não impactados |

### ❌ Removido (Limpeza Realizada)

| Item | Ação |
|------|------|
| **Cache de Capítulos Bloqueados** | Limpado do Redis |
| **Overrides LMS Course** | Desativado |
| **Hooks de Permissão** | Desativados |
| **Client Scripts do App** | Removidos |
| **Document Events do App** | Desativados |

### 🔓 Mudança de Comportamento

Após desinstalação:

```
ANTES: Usuários devem completar capítulos sequencialmente ↓
Capítulo 1 (Acessível) → Capítulo 2 (Bloqueado) → Capítulo 3 (Bloqueado)

DEPOIS: Todos os capítulos ficam acessíveis ↓
Capítulo 1 (Acessível) → Capítulo 2 (Acessível) → Capítulo 3 (Acessível)
```

---

## 🛠️ Instalação vs. Desinstalação

### Instalação (`install.py`)

```python
before_install():
  - Valida que frappe-lms está instalado
  - Verifica DocTypes obrigatórios

after_install():
  - Configura cache Redis
  - Inicializa namespaces
  - Exibe mensagem de sucesso
```

### Desinstalação (`uninstall.py`)

```python
before_uninstall():
  - Registra estado atual no log
  - Avisa sobre cursos afetados

after_uninstall():
  - Limpa cache Redis
  - Remove document events
  - Remove client scripts
  - Limpa dados de sessão
```

---

## 🧪 Testes

Testes automatizados validam o processo:

**Arquivo:** `lms_lock_chapter/tests/test_uninstall.py`

### Testes de Desinstalação
- ✅ `test_cache_cleanup_on_uninstall()` - Valida limpeza de cache
- ✅ `test_no_system_data_loss_on_uninstall()` - Garante preservação de dados
- ✅ `test_permission_hooks_removed()` - Valida desativação de hooks
- ✅ `test_chapters_become_accessible_after_uninstall()` - Testa acessibilidade

### Testes de Instalação
- ✅ `test_required_doctypes_exist()` - Valida dependências
- ✅ `test_frappe_lms_app_required()` - Verifica app obrigatório
- ✅ `test_cache_initialized_on_install()` - Testa inicialização

---

## 🔍 Monitorando o Processo

### Logs da Desinstalação

Todos os passos são registrados em `frappe.log`:

```
INFO: Preparando desinstalação do app lms_lock_chapter...
INFO: Iniciando limpeza do app lms_lock_chapter...
INFO: Limpando cache Redis do app lms_lock_chapter...
INFO: Cache Redis limpo: XXX chaves removidas.
INFO: Removendo document events do banco de dados...
INFO: Document events foram desativados.
INFO: Removendo Client Scripts customizados...
INFO: Client Script removido: SCRIPT_NAME
INFO: Limpando dados de sessão...
INFO: Dados de sessão limpos.
INFO: Limpeza do app lms_lock_chapter concluída com sucesso.
```

### Verificar em Banco de Dados

```sql
-- Verificar cursos existentes
SELECT name, title, published FROM `tabLMS Course` LIMIT 10;

-- Verificar capítulos
SELECT name, course, title FROM `tabCourse Chapter` LIMIT 10;

-- Verificar progresso de alunos
SELECT course, member, chapter, status FROM `tabLMS Course Progress` LIMIT 10;
```

---

## ⚠️ Aviso Importante

### O Que NÃO Acontece

❌ **Não deleta cursos ou capítulos**  
❌ **Não remove progresso de alunos**  
❌ **Não afeta outros apps**  
❌ **Não remove documentos do LMS**  
❌ **Não limpa banco de dados**  

### Como Garantir Limpeza Total

Se precisar de limpeza total manual:

```sql
-- ⚠️ CUIDADO: Apenas se realmente necessário!
-- Remover todas as chaves de cache do app
DELETE FROM `tabCache` WHERE name LIKE 'chapter_comp_%';
DELETE FROM `tabCache` WHERE name = 'lms_lock_chapter';
```

---

## 📝 Checklist de Desinstalação

Antes de desinstalar, verifique:

- [ ] Todos os alunos completaram seus cursos (ou foram avisados)
- [ ] Backup do banco de dados foi feito
- [ ] Ninguém está acessando cursos no momento
- [ ] Você revisou o log de avisos
- [ ] Entendeu que capítulos ficarão acessíveis

Pós-desinstalação:

- [ ] Verificar que cursos ainda existem
- [ ] Testar acesso a capítulos (deve estar desbloqueado)
- [ ] Verificar que progresso de alunos foi preservado
- [ ] Limpar cache do navegador (Ctrl+Shift+Delete)

---

## 🚀 Re-instalação

Para re-instalar o app após desinstalação:

```bash
# No bench
bench get-app lms_lock_chapter https://github.com/glsoltec/lms_lock_chapter.git
bench install-app lms_lock_chapter
bench restart
```

O bloqueio sequencial de capítulos será re-ativado automaticamente.

---

## 📞 Suporte

Para problemas com desinstalação:

1. Verificar logs em `frappe.log`
2. Consultar `CLEANUP.md` (este documento)
3. Executar testes: `bench run-tests lms_lock_chapter.tests`
4. Contactar suporte da GL Soltec

---

**Última atualização:** 2026-06-15  
**App:** lms_lock_chapter v16  
**Frappe:** v16.x  
**ERPNext:** v16.x
