"""
Funções utilitárias compartilhadas para o lms_lock_chapter.
Sem importações de nível de módulo do app LMS para evitar falhas de import.
"""
import frappe

# Papéis que têm acesso irrestrito — nunca são bloqueados
BYPASS_ROLES: frozenset[str] = frozenset({
	"Administrator",
	"System Manager",
	"Moderator",
	"Course Creator",
	"Batch Evaluator",
	"Instructor",
	"LMS Manager",
})


# --------------------------------------------------------------------------
# Resolução de nomes
# --------------------------------------------------------------------------

def get_course_name_by_slug(slug: str) -> str | None:
	"""Resolve slug/rota de curso para o docname real do LMS Course."""
	try:
		if not slug or not isinstance(slug, str):
			return None
		# Tentativa direta pelo nome
		if frappe.db.exists("LMS Course", slug):
			return slug
		# Tentativa por rota
		for path in (slug, f"courses/{slug}", f"/courses/{slug}"):
			name = frappe.db.get_value("LMS Course", {"route": path}, "name")
			if name:
				return name
	except Exception:
		pass
	return None


def get_ordered_chapters(course_name: str) -> list[str]:
	"""Retorna os nomes dos capítulos do curso na ordem correta (idx asc)."""
	try:
		rows = frappe.get_all(
			"Chapter Reference",
			filters={"parent": course_name, "parenttype": "LMS Course"},
			fields=["chapter"],
			order_by="idx asc",
		)
		return [r.chapter for r in rows if r.chapter]
	except Exception:
		return []


def get_course_for_chapter(chapter_name: str) -> str | None:
	"""Retorna o nome do curso ao qual um capítulo pertence."""
	try:
		return frappe.db.get_value(
			"Chapter Reference",
			{"chapter": chapter_name, "parenttype": "LMS Course"},
			"parent",
		)
	except Exception:
		return None


def get_course_for_lesson(
	lesson_name: str, hint_course: str | None = None
) -> tuple[str | None, str | None]:
	"""
	Retorna (course_name, chapter_name) para uma lição.
	hint_course acelera a busca quando o curso já é conhecido.
	"""
	try:
		chapter_refs = frappe.get_all(
			"Lesson Reference",
			filters={"lesson": lesson_name, "parenttype": "Course Chapter"},
			fields=["parent"],
		)
		if not chapter_refs:
			return None, None

		if hint_course:
			for ref in chapter_refs:
				ch = ref.parent
				if frappe.db.exists(
					"Chapter Reference",
					{"chapter": ch, "parent": hint_course, "parenttype": "LMS Course"},
				):
					return hint_course, ch

		ch = chapter_refs[0].parent
		course = frappe.db.get_value(
			"Chapter Reference",
			{"chapter": ch, "parenttype": "LMS Course"},
			"parent",
		)
		return course, ch
	except Exception:
		return None, None


# --------------------------------------------------------------------------
# Verificação de conclusão
# --------------------------------------------------------------------------

def is_chapter_completed(course: str, chapter: str, user: str) -> bool:
	"""
	Retorna True se o aluno completou todos os conteúdos do capítulo.

	Capítulos SCORM: verificam registro de conclusão no nível do capítulo.
	Capítulos nativos: TODAS as lições devem ter status "Complete".
	Capítulos sem lições: considerados concluídos automaticamente.
	"""
	try:
		is_scorm = frappe.db.get_value("Course Chapter", chapter, "is_scorm_package")

		if is_scorm:
			return bool(
				frappe.db.exists(
					"LMS Course Progress",
					{"course": course, "member": user, "chapter": chapter, "status": "Complete"},
				)
			)

		# Capítulo nativo: checar todas as lições
		lessons = frappe.get_all(
			"Lesson Reference",
			filters={"parent": chapter, "parenttype": "Course Chapter"},
			pluck="lesson",
		)

		if not lessons:
			return True  # Capítulo vazio é considerado completo

		completed = frappe.db.count(
			"LMS Course Progress",
			{"course": course, "member": user, "lesson": ["in", lessons], "status": "Complete"},
		)
		return int(completed) >= len(lessons)

	except Exception:
		frappe.log_error(frappe.get_traceback(), "lms_lock_chapter: is_chapter_completed")
		return True  # Fail-open para não bloquear por erro técnico


# --------------------------------------------------------------------------
# Verificação de acesso por usuário
# --------------------------------------------------------------------------

def user_has_bypass(user: str) -> bool:
	"""Verifica se o usuário tem papel de bypass (acesso irrestrito)."""
	return bool(set(frappe.get_roles(user)) & BYPASS_ROLES)


def get_locked_chapters_for_user(course_name: str, user: str) -> list[str]:
	"""
	Retorna lista de nomes de capítulos bloqueados para o usuário.
	O primeiro capítulo nunca é bloqueado.
	Capítulos subsequentes são bloqueados se o anterior não foi concluído.
	"""
	chapters = get_ordered_chapters(course_name)
	if not chapters:
		return []

	locked = []
	for i, ch in enumerate(chapters):
		if i == 0:
			continue
		if not is_chapter_completed(course_name, chapters[i - 1], user):
			locked.append(ch)

	return locked


def get_locked_lessons_for_user(course_name: str, locked_chapters: list[str]) -> list[str]:
	"""
	Retorna lista de nomes de lições que estão dentro de capítulos bloqueados.
	Usado pelo JavaScript para bloquear visualmente os itens na barra lateral.
	"""
	locked_lessons: list[str] = []
	for ch in locked_chapters:
		lessons = frappe.get_all(
			"Lesson Reference",
			filters={"parent": ch, "parenttype": "Course Chapter"},
			pluck="lesson",
		)
		locked_lessons.extend(lessons)
	return locked_lessons
