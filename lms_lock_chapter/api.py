"""
API pública (whitelisted) do lms_lock_chapter.
Mantida em arquivo separado para evitar falhas de importação do módulo LMS
que afetariam o registro das funções whitelisted no Frappe.
"""
import frappe


# --------------------------------------------------------------------------
# get_locked_chapters
# Compatibilidade com código existente e JavaScript legado
# --------------------------------------------------------------------------
@frappe.whitelist()
def get_locked_chapters(course: str) -> list:
	"""
	Retorna lista de nomes de capítulos bloqueados para o usuário atual.
	Usado pelo desk JS e por integrações legadas.
	"""
	if not course:
		return []

	from lms_lock_chapter.utils import (
		get_course_name_by_slug,
		get_locked_chapters_for_user,
		user_has_bypass,
	)

	course_name = get_course_name_by_slug(course)
	if not course_name:
		return []

	user = frappe.session.user
	if user == "Guest":
		return []
	if user_has_bypass(user):
		return []

	return get_locked_chapters_for_user(course_name, user)


# --------------------------------------------------------------------------
# get_locked_data
# Endpoint principal usado pelo portal JS
# Retorna capítulos E lições bloqueadas em uma única chamada
# --------------------------------------------------------------------------
@frappe.whitelist()
def get_locked_data(course: str) -> dict:
	"""
	Retorna dicionário com capítulos e lições bloqueados para o usuário atual.

	Formato de retorno:
	{
	    "locked_chapters": ["Chapter Name 1", ...],
	    "locked_lessons": ["Lesson Name 1", ...]
	}
	"""
	empty = {"locked_chapters": [], "locked_lessons": []}

	if not course:
		return empty

	from lms_lock_chapter.utils import (
		get_course_name_by_slug,
		get_locked_chapters_for_user,
		get_locked_lessons_for_user,
		user_has_bypass,
	)

	course_name = get_course_name_by_slug(course)
	if not course_name:
		return empty

	user = frappe.session.user
	if user == "Guest":
		return empty
	if user_has_bypass(user):
		return empty

	locked_chapters = get_locked_chapters_for_user(course_name, user)
	locked_lessons = get_locked_lessons_for_user(course_name, locked_chapters)

	return {
		"locked_chapters": locked_chapters,
		"locked_lessons": locked_lessons,
	}


# --------------------------------------------------------------------------
# check_lesson_access
# Permite verificar explicitamente se uma lição específica está acessível
# --------------------------------------------------------------------------
@frappe.whitelist()
def check_lesson_access(course: str, lesson: str) -> dict:
	"""
	Verifica se o usuário atual pode acessar uma lição específica.

	Retorna:
	{
	    "accessible": True/False,
	    "reason": "ok" | "not_enrolled" | "chapter_locked" | "guest"
	}
	"""
	if not course or not lesson:
		return {"accessible": False, "reason": "missing_params"}

	from lms_lock_chapter.utils import (
		get_course_for_lesson,
		get_course_name_by_slug,
		get_ordered_chapters,
		is_chapter_completed,
		user_has_bypass,
	)

	user = frappe.session.user
	if user == "Guest":
		return {"accessible": False, "reason": "guest"}

	course_name = get_course_name_by_slug(course)
	if not course_name:
		return {"accessible": False, "reason": "course_not_found"}

	if user_has_bypass(user):
		return {"accessible": True, "reason": "bypass_role"}

	course_resolved, chapter = get_course_for_lesson(lesson, course_name)
	if not course_resolved or not chapter:
		return {"accessible": True, "reason": "no_chapter_context"}

	chapters = get_ordered_chapters(course_resolved)
	if not chapters or chapter not in chapters:
		return {"accessible": True, "reason": "chapter_not_in_course"}

	idx = chapters.index(chapter)
	if idx == 0:
		return {"accessible": True, "reason": "first_chapter"}

	if not is_chapter_completed(course_resolved, chapters[idx - 1], user):
		return {"accessible": False, "reason": "chapter_locked"}

	return {"accessible": True, "reason": "ok"}
