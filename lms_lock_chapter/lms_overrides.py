"""
Hooks de permissão e injeção de script para o lms_lock_chapter.

Não realiza importações de nível de módulo do app LMS para evitar
falhas de carregamento caso a estrutura interna do LMS mude.
Todas as importações pesadas são lazy (dentro das funções).
"""
import frappe


# --------------------------------------------------------------------------
# Script injection
# --------------------------------------------------------------------------

def inject_portal_script(response) -> None:
	"""
	Injeta o script de bloqueio antes de </body> em páginas HTML do LMS.
	Funciona como fallback quando web_include_js não cobre a rota.
	"""
	try:
		content_type = response.headers.get("Content-Type", "")
		if "text/html" not in content_type:
			return

		path = (
			getattr(frappe.local.request, "path", "")
			if hasattr(frappe.local, "request")
			else ""
		)
		if not path.startswith("/lms"):
			return

		data = response.get_data()
		script_tag = b'<script src="/assets/lms_lock_chapter/js/lms_portal_lock.js"></script>'

		# Não reinjetar se já estiver presente
		if script_tag in data:
			return

		if b"</body>" not in data:
			return

		response.set_data(data.replace(b"</body>", b"\n" + script_tag + b"\n</body>", 1))
	except Exception:
		pass


# --------------------------------------------------------------------------
# Mensagem de bloqueio
# --------------------------------------------------------------------------

def _add_blocked_message() -> None:
	"""Adiciona mensagem de capítulo bloqueado ao log de mensagens Frappe."""
	msg = frappe._("You need to complete the previous chapter before accessing this content.")
	try:
		if hasattr(frappe.local, "message_log"):
			for log in frappe.local.message_log:
				entry = log.get("message", "") if isinstance(log, dict) else str(log)
				if msg in entry:
					return
	except Exception:
		pass
	frappe.msgprint(
		msg=msg,
		title=frappe._("Chapter Locked"),
		indicator="orange",
		raise_exception=False,
	)


# --------------------------------------------------------------------------
# Helpers de contexto de requisição
# --------------------------------------------------------------------------

def _get_course_from_request() -> str | None:
	"""Extrai e resolve o slug do curso a partir do path HTTP ou Referer."""
	try:
		import re
		from urllib.parse import urlparse

		if not hasattr(frappe.local, "request") or not frappe.local.request:
			return None

		from lms_lock_chapter.utils import get_course_name_by_slug

		path = getattr(frappe.local.request, "path", "") or ""
		m = re.search(r"/(?:lms/)?courses/([^/]+)", path)
		if m:
			return get_course_name_by_slug(m.group(1))

		referer = frappe.local.request.headers.get("Referer", "")
		if referer:
			m = re.search(r"/(?:lms/)?courses/([^/]+)", urlparse(referer).path)
			if m:
				return get_course_name_by_slug(m.group(1))
	except Exception:
		pass
	return None


# --------------------------------------------------------------------------
# has_permission: Course Lesson
# --------------------------------------------------------------------------

def check_lesson_permission(doc, ptype: str = "read", user: str | None = None):
	"""
	Hook has_permission para Course Lesson.

	Retorna:
	  False  → bloquear (capítulo anterior não concluído)
	  None   → delegar ao sistema padrão (permitir)
	"""
	try:
		if ptype != "read":
			return None

		# Chamada de listagem — não bloquear
		if isinstance(doc, str) and doc == "Course Lesson":
			return None

		# Obter nome da lição
		if isinstance(doc, str):
			lesson_name = doc
		elif isinstance(doc, dict):
			lesson_name = doc.get("name")
		else:
			lesson_name = getattr(doc, "name", None)

		if not lesson_name:
			return None

		user = user or frappe.session.user
		if not user or user == "Guest":
			return False

		from lms_lock_chapter.utils import (
			BYPASS_ROLES,
			get_course_for_lesson,
			get_ordered_chapters,
			is_chapter_completed,
		)

		if set(frappe.get_roles(user)) & BYPASS_ROLES:
			return None

		hint_course = _get_course_from_request()
		course_name, lesson_chapter = get_course_for_lesson(lesson_name, hint_course)

		if not course_name or not lesson_chapter:
			return None

		chapters = get_ordered_chapters(course_name)
		if not chapters or lesson_chapter not in chapters:
			return None

		idx = chapters.index(lesson_chapter)
		if idx == 0:
			return None  # Primeiro capítulo: sempre acessível

		if not is_chapter_completed(course_name, chapters[idx - 1], user):
			frappe.logger().info(
				f"lms_lock_chapter: lição {lesson_name} BLOQUEADA para {user} "
				f"(capítulo {chapters[idx - 1]} não concluído)"
			)
			_add_blocked_message()
			return False

		return None

	except Exception:
		frappe.log_error(frappe.get_traceback(), "lms_lock_chapter: check_lesson_permission")
		return None


# --------------------------------------------------------------------------
# has_permission: Course Chapter
# --------------------------------------------------------------------------

def check_chapter_permission(doc, ptype: str = "read", user: str | None = None):
	"""
	Hook has_permission para Course Chapter.

	Retorna:
	  False  → bloquear (capítulo anterior não concluído)
	  None   → delegar ao sistema padrão (permitir)
	"""
	try:
		if ptype != "read":
			return None

		# Chamada de listagem — não bloquear
		if isinstance(doc, str) and doc == "Course Chapter":
			return None

		# Obter nome do capítulo
		if isinstance(doc, str):
			chapter_name = doc
		elif isinstance(doc, dict):
			chapter_name = doc.get("name")
		else:
			chapter_name = getattr(doc, "name", None)

		if not chapter_name:
			return None

		user = user or frappe.session.user
		if not user or user == "Guest":
			return False

		from lms_lock_chapter.utils import (
			BYPASS_ROLES,
			get_course_for_chapter,
			get_ordered_chapters,
			is_chapter_completed,
		)

		if set(frappe.get_roles(user)) & BYPASS_ROLES:
			return None

		course_name = get_course_for_chapter(chapter_name)
		if not course_name:
			return None

		chapters = get_ordered_chapters(course_name)
		if not chapters or chapter_name not in chapters:
			return None

		idx = chapters.index(chapter_name)
		if idx == 0:
			return None  # Primeiro capítulo: sempre acessível

		if not is_chapter_completed(course_name, chapters[idx - 1], user):
			frappe.logger().info(
				f"lms_lock_chapter: capítulo {chapter_name} BLOQUEADO para {user} "
				f"(capítulo {chapters[idx - 1]} não concluído)"
			)
			_add_blocked_message()
			return False

		return None

	except Exception:
		frappe.log_error(frappe.get_traceback(), "lms_lock_chapter: check_chapter_permission")
		return None


# --------------------------------------------------------------------------
# doc_events: LMS Course Progress
# --------------------------------------------------------------------------

def on_progress_update(doc, method=None) -> None:
	"""
	Invalida cache de conclusão de capítulo quando o progresso é atualizado.
	Chamado em after_insert e on_update do LMS Course Progress.
	"""
	try:
		if not doc.get("course") or not doc.get("member"):
			return

		chapter = doc.get("chapter")
		if not chapter and doc.get("lesson"):
			chapter = frappe.db.get_value(
				"Lesson Reference",
				{"lesson": doc.get("lesson"), "parenttype": "Course Chapter"},
				"parent",
			)

		if chapter:
			cache_key = f"lms_lock:chap:{doc.course}:{chapter}:{doc.member}"
			frappe.cache().delete_value(cache_key)
	except Exception:
		pass
