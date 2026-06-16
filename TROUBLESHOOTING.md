# Troubleshooting - LMS Lock Chapter

Guia de resolução de problemas para instalação, execução e desinstalação do app.

---

## 🔴 Problemas na Desinstalação

### Problema: "Permission Error" ao desinstalar

**Sintoma:**
```
PermissionError: cannot delete file 'lms_lock_chapter/...': Permission denied
```

**Causa:** Processo Frappe sem permissão no diretório

**Solução:**
```bash
# Verificar permissões
ls -la apps/lms_lock_chapter/

# Se necessário, ajustar permissões
sudo chown -R frappe:frappe apps/lms_lock_chapter/
sudo chmod -R 755 apps/lms_lock_chapter/

# Tentar desinstalação novamente
bench uninstall-app lms_lock_chapter
```

---

### Problema: Cache Redis não limpa

**Sintoma:**
```
WARNING: Erro ao limpar cache Redis: Connection refused
```

**Causa:** Redis não está rodando ou inacessível

**Solução:**
```bash
# Verificar status do Redis
redis-cli ping

# Se não responder, reiniciar Redis
sudo systemctl restart redis-server

# Limpar cache manualmente
redis-cli KEYS "chapter_comp_*" | xargs redis-cli DEL
redis-cli DEL lms_lock_chapter

# Tentar desinstalação novamente
```

---

### Problema: Capítulos ainda bloqueados após desinstalação

**Sintoma:**
```
Capítulos continuam bloqueados mesmo após desinstalar o app
```

**Causa:** Cache do navegador ou override ainda ativo

**Solução:**

1. **Limpar cache do navegador:**
   ```
   Ctrl+Shift+Delete (ou Cmd+Shift+Delete no Mac)
   ```

2. **Limpar cache Frappe:**
   ```bash
   bench clear-cache
   ```

3. **Restart completo:**
   ```bash
   bench restart
   ```

4. **Verificar em outro navegador:**
   ```
   Abrir incógnita/private window
   Testar acesso a capítulo
   ```

---

### Problema: Client Scripts não removidos

**Sintoma:**
```
Scripts do app continuam executando após desinstalação
```

**Causa:** Client Scripts não foram encontrados ou deletados incorretamente

**Solução:**

```bash
# Conectar ao banco ERPNext
bench console

# Verificar scripts existentes
from frappe.client import get_list
scripts = get_list("Client Script", filters={"module": "LMS Lock Chapter"})
print(scripts)

# Deletar manualmente se necessário
from frappe.client import delete
for script in scripts:
    delete("Client Script", script["name"])

# Limpar cache
frappe.cache().clear()
```

---

## 🟡 Problemas na Instalação

### Problema: "frappe-lms não encontrado"

**Sintoma:**
```
ValidationError: O app 'frappe-lms' é obrigatório para usar lms_lock_chapter.
```

**Causa:** App frappe-lms não está instalado

**Solução:**
```bash
# Instalar frappe-lms primeiro
bench get-app frappe-lms https://github.com/frappe-school/frappe-lms.git
bench install-app frappe-lms

# Depois instalar lms_lock_chapter
bench install-app lms_lock_chapter
```

---

### Problema: DocType não encontrado

**Sintoma:**
```
ValidationError: DocType obrigatório 'LMS Course' não encontrado.
```

**Causa:** Dados do LMS não estão disponíveis

**Solução:**

1. **Verificar instalação do frappe-lms:**
   ```bash
   bench list-apps | grep lms
   ```

2. **Se não aparecer, instalar:**
   ```bash
   bench get-app frappe-lms
   bench install-app frappe-lms
   ```

3. **Migrar banco se necessário:**
   ```bash
   bench migrate
   ```

4. **Tentar instalar novamente:**
   ```bash
   bench install-app lms_lock_chapter
   ```

---

### Problema: Erro de cache Redis na instalação

**Sintoma:**
```
WARNING: Erro ao configurar cache: Cannot connect to Redis
```

**Causa:** Redis não está rodando

**Solução:**
```bash
# Iniciar Redis
redis-server

# Ou se usar systemd
sudo systemctl start redis-server

# Verificar status
redis-cli ping
# Resposta esperada: PONG

# Tentar instalação novamente
bench install-app lms_lock_chapter
```

---

## 🔵 Problemas em Execução

### Problema: Capítulos não bloqueiam

**Sintoma:**
```
Usuários podem acessar todos os capítulos mesmo sem completar anteriores
```

**Causa Possível 1:** App não está instalado corretamente

**Solução 1:**
```bash
bench install-app lms_lock_chapter
```

**Causa Possível 2:** Cache não foi inicializado

**Solução 2:**
```bash
bench clear-cache
bench restart
```

**Causa Possível 3:** Usuário tem role que bypassa bloqueio

**Solução 3:**
```python
# Verificar roles do usuário em hooks.py
BYPASS_ROLES = {"Administrator", "System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Instructor", "LMS Manager"}

# Roles em BYPASS_ROLES não têm capítulos bloqueados
# Remover role se necessário ou criar novo usuário
```

---

### Problema: Mensagem de bloqueio não aparece

**Sintoma:**
```
Usuário clica em capítulo bloqueado mas nada acontece
```

**Causa Possível 1:** JavaScript não carregado

**Solução 1:**
```bash
bench build
bench restart
```

**Causa Possível 2:** Evento web_include_js não ativado

**Solução 2:**
```python
# Verificar em hooks.py:
web_include_js = ["/assets/lms_lock_chapter/js/lms_portal_lock.js"]

# Se não estiver, ativar manualmente em Site Settings
```

---

### Problema: Performance lenta em cursos grandes

**Sintoma:**
```
Carregar página de curso leva muito tempo
```

**Causa:** Consultas SQL não otimizadas

**Solução:**
```bash
# Verificar índices no banco
SHOW INDEX FROM `tabChapter Reference`;
SHOW INDEX FROM `tabLesson Reference`;

# Se faltar índices, criar manualmente
ALTER TABLE `tabChapter Reference` 
ADD INDEX idx_parent_chapter (parent, chapter);

ALTER TABLE `tabLesson Reference` 
ADD INDEX idx_parent_lesson (parent, lesson);

# Limpar cache
bench clear-cache

# Testar novamente
```

---

## 🟢 Logs e Debugging

### Acessar logs

```bash
# Log principal do Frappe
tail -f ~/frappe-bench/logs/frappe.log

# Log de erro
tail -f ~/frappe-bench/logs/error.log

# Log de worker
tail -f ~/frappe-bench/logs/worker.log
```

### Habilitar debug mode

```python
# No console Frappe
frappe.logger().setLevel("DEBUG")

# Ou em settings
# development_mode = 1
```

### Inspecionar dados em banco

```bash
# Conectar ao banco MySQL/MariaDB
mysql -u frappe -p frappe_db_name

# Consultas úteis:
SELECT COUNT(*) FROM `tabLMS Course Progress` WHERE course = 'seu-curso';
SELECT DISTINCT member FROM `tabLMS Course Progress`;
SELECT name FROM `tabCourse Chapter` WHERE parent = 'seu-curso' ORDER BY idx;
```

---

## 🆘 Quando Pedir Ajuda

Se o problema persistir, forneça:

1. **Versão do ERPNext/Frappe:**
   ```bash
   bench --version
   ```

2. **Log completo de erro:**
   ```bash
   grep -A 20 "lms_lock_chapter" ~/frappe-bench/logs/frappe.log
   ```

3. **Status da instalação:**
   ```bash
   bench list-apps | grep lms
   ```

4. **Versão do Python:**
   ```bash
   python --version
   ```

5. **Status do Redis:**
   ```bash
   redis-cli INFO
   ```

---

## 📞 Contactos de Suporte

**GL Soltec**
- Email: suporte@glsoltec.com.br
- GitHub: https://github.com/glsoltec/lms_lock_chapter

**Frappe Community**
- Forum: https://discuss.erpnext.com
- GitHub: https://github.com/frappe/frappe

---

**Última atualização:** 2026-06-15
