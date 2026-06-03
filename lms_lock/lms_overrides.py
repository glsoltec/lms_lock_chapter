import frappe
from lms.lms.doctype.lms_course.lms_course import LMSCourse

BYPASS_ROLES = {"Administrator", "System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Instructor", "LMS Manager"}


def _get_course_for_chapter(chapter_name):
    """Busca o curso pai de um capítulo via Chapter Reference (child table de LMS Course)."""
    return frappe.db.get_value(
        "Chapter Reference",
        {"chapter": chapter_name, "parenttype": "LMS Course"},
        "parent"
    )


def _get_ordered_chapters(course_name):
    """Retorna lista ordenada de nomes de capítulos de um curso."""
    rows = frappe.get_all(
        "Chapter Reference",
        filters={"parent": course_name, "parenttype": "LMS Course"},
        fields=["chapter"],
        order_by="idx asc"
    )
    return [r.chapter for r in rows]


def _get_course_for_lesson(lesson_name):
    """Busca o curso e capítulo de uma aula via Lesson Reference → Chapter Reference."""
    chapter_name = frappe.db.get_value(
        "Lesson Reference",
        {"lesson": lesson_name, "parenttype": "Course Chapter"},
        "parent"
    )
    if not chapter_name:
        return None, None
    course_name = _get_course_for_chapter(chapter_name)
    return course_name, chapter_name


def get_doc_field(doc, field, default=None):
    if isinstance(doc, dict):
        return doc.get(field, default)
    return getattr(doc, field, default)


class LMSCourseLMSLock(LMSCourse):
    def check_permission(self, chapter):
        if not frappe.session.user or frappe.session.user == "Guest":
            return False

        user_roles = set(frappe.get_roles())
        if user_roles & BYPASS_ROLES:
            return True

        chapter_names = _get_ordered_chapters(self.name)

        if chapter not in chapter_names:
            return True  # Não pertence a este curso; libera

        current_idx = chapter_names.index(chapter)
        if current_idx == 0:
            return True

        previous_chapter = chapter_names[current_idx - 1]
        return is_chapter_completed(self.name, previous_chapter, frappe.session.user)


@frappe.whitelist()
def get_locked_chapters(course):
    """Retorna lista de capítulos bloqueados para o usuário atual."""
    if not course:
        return []

    chapter_names = _get_ordered_chapters(course)
    if not chapter_names:
        return []

    if not frappe.session.user or frappe.session.user == "Guest":
        return chapter_names[1:]

    user_roles = set(frappe.get_roles())
    if user_roles & BYPASS_ROLES:
        return []

    progress_records = frappe.get_all(
        "LMS Course Progress",
        filters={"course": course, "member": frappe.session.user, "status": "Complete"},
        fields=["chapter", "lesson"]
    )

    completed_chapters = {r.chapter for r in progress_records if r.chapter}
    completed_lessons = {r.lesson for r in progress_records if r.lesson}

    locked = []
    for i, chapter in enumerate(chapter_names):
        if i == 0:
            continue  # Primeiro capítulo nunca bloqueado
        previous_chapter = chapter_names[i - 1]
        if not check_completion_optimized(course, previous_chapter, completed_chapters, completed_lessons):
            locked.append(chapter)

    return locked


def check_completion_optimized(course, chapter, completed_chapters, completed_lessons):
    """Verifica conclusão usando dados pré-carregados."""
    chapter_doc = frappe.get_cached_value(
        "Course Chapter", chapter, ["is_scorm_package", "name"], as_dict=True
    )
    if not chapter_doc:
        return True

    if chapter_doc.is_scorm_package:
        return chapter in completed_chapters

    lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter}, pluck="lesson")
    if not lessons:
        return True

    return all(lesson in completed_lessons for lesson in lessons)


def is_chapter_completed(course: str, chapter: str, user: str) -> bool:
    """Verifica se um capítulo está concluído (com cache Redis por requisição)."""
    cache_key = f"chapter_comp_{course}_{chapter}_{user}"
    cached_status = frappe.cache().hget("lms_lock", cache_key)
    if cached_status is not None:
        return bool(cached_status)

    is_scorm = frappe.db.get_value("Course Chapter", chapter, "is_scorm_package")

    completed = False
    if is_scorm:
        completed = bool(frappe.db.exists("LMS Course Progress", {
            "course": course,
            "member": user,
            "chapter": chapter,
            "status": "Complete"
        }))
    else:
        lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter}, pluck="lesson")
        if not lessons:
            completed = True
        else:
            completed_count = frappe.db.count("LMS Course Progress", {
                "course": course,
                "member": user,
                "lesson": ["in", lessons],
                "status": "Complete"
            })
            completed = (completed_count == len(lessons))

    frappe.cache().hset("lms_lock", cache_key, 1 if completed else 0)
    return completed


def check_lesson_permission(doc, ptype="read", user=None):
    """
    Hook has_permission para Course Lesson.
    Retorna False se a aula pertence a um capítulo bloqueado.
    Retorna True se desbloqueada (garante acesso mesmo sem permissão de role).
    Retorna None apenas quando não conseguimos determinar o contexto.
    """
    try:
        if ptype != "read":
            return None

        # Chamada de nível de doctype (sem documento específico)
        if isinstance(doc, str):
            if doc == "Course Lesson":
                return None
            lesson_name = doc
            course_name, lesson_chapter = _get_course_for_lesson(lesson_name)
        else:
            lesson_name = get_doc_field(doc, "name")
            if not lesson_name:
                return None
            course_name = get_doc_field(doc, "course")
            lesson_chapter = get_doc_field(doc, "chapter")
            if not course_name or not lesson_chapter:
                course_name, lesson_chapter = _get_course_for_lesson(lesson_name)

        if not course_name or not lesson_chapter:
            return None

        user = user or frappe.session.user
        if not user or user == "Guest":
            return False

        user_roles = set(frappe.get_roles(user))
        if user_roles & BYPASS_ROLES:
            return True

        chapter_names = _get_ordered_chapters(course_name)
        if not chapter_names or lesson_chapter not in chapter_names:
            return None

        current_idx = chapter_names.index(lesson_chapter)

        # Primeiro capítulo: sempre liberado
        if current_idx == 0:
            return True

        previous_chapter = chapter_names[current_idx - 1]
        if not is_chapter_completed(course_name, previous_chapter, user):
            frappe.throw(
                msg=frappe._("Você precisa concluir o capítulo anterior antes de acessar este conteúdo."),
                exc=frappe.PermissionError,
                title=frappe._("Capítulo Bloqueado")
            )

        return True

    except frappe.PermissionError:
        raise
    except Exception:
        frappe.log_error(frappe.get_traceback(), "lms_lock: check_lesson_permission error")
        return None  # Em caso de erro, não bloqueia


def check_chapter_permission_hook(doc, ptype="read", user=None):
    """
    Hook has_permission para Course Chapter.
    Retorna False se o capítulo está bloqueado (anterior não concluído).
    Retorna True se desbloqueado (garante acesso mesmo sem permissão de role).
    Retorna None quando não conseguimos determinar o contexto.
    """
    try:
        if ptype != "read":
            return None

        # Chamada de nível de doctype (sem documento específico)
        if isinstance(doc, str):
            if doc == "Course Chapter":
                return None
            chapter_name = doc
            course_name = _get_course_for_chapter(chapter_name)
        else:
            chapter_name = get_doc_field(doc, "name")
            if not chapter_name:
                return None
            course_name = get_doc_field(doc, "course") or _get_course_for_chapter(chapter_name)

        if not course_name:
            return None  # Não conseguiu determinar o curso; não bloqueia

        user = user or frappe.session.user
        if not user or user == "Guest":
            return False

        user_roles = set(frappe.get_roles(user))
        if user_roles & BYPASS_ROLES:
            return True

        chapter_names = _get_ordered_chapters(course_name)
        if not chapter_names or chapter_name not in chapter_names:
            return None

        current_idx = chapter_names.index(chapter_name)

        # Primeiro capítulo: sempre liberado
        if current_idx == 0:
            return True

        previous_chapter = chapter_names[current_idx - 1]
        if not is_chapter_completed(course_name, previous_chapter, user):
            frappe.throw(
                msg=frappe._("Você precisa concluir o capítulo anterior antes de acessar este conteúdo."),
                exc=frappe.PermissionError,
                title=frappe._("Capítulo Bloqueado")
            )

        return True

    except frappe.PermissionError:
        raise
    except Exception:
        frappe.log_error(frappe.get_traceback(), "lms_lock: check_chapter_permission_hook error")
        return None  # Em caso de erro, não bloqueia
