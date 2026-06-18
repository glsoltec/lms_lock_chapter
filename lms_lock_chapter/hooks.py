app_name = "lms_lock_chapter"
app_title = "LMS Lock Chapter"
app_publisher = "GL Soltec"
app_description = "Controle de acesso sequencial a capítulos e lições em cursos LMS"
app_email = "suporte@glsoltec.com.br"
app_license = "mit"

# --------------------------------------------------------------------------
# Lifecycle hooks
# --------------------------------------------------------------------------
before_install = "lms_lock_chapter.install.before_install"
after_install = "lms_lock_chapter.install.after_install"
before_uninstall = "lms_lock_chapter.uninstall.before_uninstall"
after_uninstall = "lms_lock_chapter.uninstall.after_uninstall"

# --------------------------------------------------------------------------
# Portal: inject lock script into every LMS HTML page
# web_include_js garante carregamento; after_request é fallback para rotas
# que o Frappe não inclui automaticamente (ex.: /lms/courses/*)
# --------------------------------------------------------------------------
web_include_js = ["/assets/lms_lock_chapter/js/lms_portal_lock.js"]
after_request = ["lms_lock_chapter.lms_overrides.inject_portal_script"]

# --------------------------------------------------------------------------
# Permission hooks — bloqueio server-side por capítulo/lição
# --------------------------------------------------------------------------
has_permission = {
	"Course Lesson": "lms_lock_chapter.lms_overrides.check_lesson_permission",
	"Course Chapter": "lms_lock_chapter.lms_overrides.check_chapter_permission",
}

# --------------------------------------------------------------------------
# Desk: JS exibido dentro do form de LMS Course no backend
# --------------------------------------------------------------------------
doctype_js = {"LMS Course": "public/js/lms_chapter_lock.js"}

# --------------------------------------------------------------------------
# Invalidar cache de conclusão quando o progresso do aluno é gravado
# --------------------------------------------------------------------------
doc_events = {
	"LMS Course Progress": {
		"after_insert": "lms_lock_chapter.lms_overrides.on_progress_update",
		"on_update": "lms_lock_chapter.lms_overrides.on_progress_update",
	}
}
