import frappe
from lms.lms.doctype.lms_course.lms_course import LMSCourse

BYPASS_ROLES = {"Administrator", "System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Instructor", "LMS Manager"}


def _get_course_for_chapter(chapter_name):
    """Busca o curso pai de um capítulo via Chapter Reference."""
    return frappe.db.get_value("Chapter Reference", {"chapter": chapter_name}, "parent")


def _get_course_for_lesson(lesson_name):
    """Busca o curso e capítulo de uma aula via Lesson Reference → Chapter Reference."""
    chapter_name = frappe.db.get_value("Lesson Reference", {"lesson": lesson_name}, "parent")
    if not chapter_name:
        return None, None
    course_name = _get_course_for_chapter(chapter_name)
    return course_name, chapter_name


def _is_first_chapter(course_name, chapter_name):
    """Retorna True se o capítulo for o primeiro do curso (idx=0)."""
    first = frappe.db.get_value(
        "Chapter Reference",
        {"parent": course_name},
        "chapter",
        order_by="idx asc"
    )
    return first == chapter_name


class LMSCourseLMSLock(LMSCourse):
    def check_permission(self, chapter):
        if not frappe.session.user or frappe.session.user == "Guest":
            return False

        user_roles = set(frappe.get_roles())
        if user_roles & BYPASS_ROLES:
            return True

        chapters = frappe.get_all(
            "Chapter Reference",
            filters={"parent": self.name},
            fields=["chapter"],
            order_by="idx"
        )

        chapter_names = [c.chapter for c in chapters]

        # Capítulo não pertence a este curso: libera (não é nossa responsabilidade bloquear)
        if chapter not in chapter_names:
            return True

        current_idx = chapter_names.index(chapter)

        # O primeiro capítulo sempre é acessível
        if current_idx == 0:
            return True

        previous_chapter = chapter_names[current_idx - 1]
        return is_chapter_completed(self.name, previous_chapter, frappe.session.user)


@frappe.whitelist()
def get_locked_chapters(course):
    """Retorna lista de capítulos bloqueados para o usuário atual."""
    if not course:
        return []

    chapters = frappe.get_all(
        "Chapter Reference",
        filters={"parent": course},
        fields=["chapter"],
        order_by="idx"
    )

    chapter_names = [c.chapter for c in chapters]

    if not frappe.session.user or frappe.session.user == "Guest":
        # Para guests, bloqueia tudo exceto o primeiro
        return chapter_names[1:] if len(chapter_names) > 1 else []

    user_roles = set(frappe.get_roles())
    if user_roles & BYPASS_ROLES:
        return []

    # Carrega todo o progresso do usuário de uma vez (evita N+1 queries)
    progress_records = frappe.get_all(
        "LMS Course Progress",
        filters={
            "course": course,
            "member": frappe.session.user,
            "status": "Complete"
        },
        fields=["chapter", "lesson"]
    )

    completed_chapters = {r.chapter for r in progress_records if r.chapter}
    completed_lessons = {r.lesson for r in progress_records if r.lesson}

    locked = []
    for i, chapter in enumerate(chapter_names):
        # O primeiro capítulo NUNCA é bloqueado
        if i == 0:
            continue

        previous_chapter = chapter_names[i - 1]
        if not check_completion_optimized(course, previous_chapter, completed_chapters, completed_lessons):
            locked.append(chapter)

    return locked


def check_completion_optimized(course, chapter, completed_chapters, completed_lessons):
    """Verifica conclusão usando dados pré-carregados (sem queries extras)."""
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


def get_doc_field(doc, field, default=None):
    if isinstance(doc, dict):
        return doc.get(field, default)
    return getattr(doc, field, default)


def check_lesson_permission(doc, ptype="read", user=None):
    if ptype != "read":
        return None

    # Chamada de nível de doctype (sem documento específico)
    if isinstance(doc, str):
        if doc == "Course Lesson":
            return None
        doc = frappe.get_cached_doc("Course Lesson", doc)

    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    user_roles = set(frappe.get_roles(user))
    if user_roles & BYPASS_ROLES:
        return None

    lesson_name = get_doc_field(doc, "name")
    if not lesson_name:
        return None

    # Tenta obter curso e capítulo do próprio documento
    course_name = get_doc_field(doc, "course")
    lesson_chapter = get_doc_field(doc, "chapter")

    # Se o doc não tiver os campos, busca via relações
    if not course_name or not lesson_chapter:
        course_name, lesson_chapter = _get_course_for_lesson(lesson_name)

    if not course_name or not lesson_chapter:
        return None

    # Primeiro capítulo: sempre liberado
    if _is_first_chapter(course_name, lesson_chapter):
        return None

    chapters = frappe.get_all(
        "Chapter Reference",
        filters={"parent": course_name},
        fields=["chapter"],
        order_by="idx"
    )
    chapter_names = [c.chapter for c in chapters]

    if lesson_chapter not in chapter_names:
        return None

    current_idx = chapter_names.index(lesson_chapter)
    if current_idx == 0:
        return None

    previous_chapter = chapter_names[current_idx - 1]
    if not is_chapter_completed(course_name, previous_chapter, user):
        return False

    return None


def check_chapter_permission_hook(doc, ptype="read", user=None):
    if ptype != "read":
        return None

    # Chamada de nível de doctype
    if isinstance(doc, str):
        if doc == "Course Chapter":
            return None
        doc = frappe.get_cached_doc("Course Chapter", doc)

    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    user_roles = set(frappe.get_roles(user))
    if user_roles & BYPASS_ROLES:
        return None

    chapter_name = get_doc_field(doc, "name")
    if not chapter_name:
        return None

    # Tenta obter curso do próprio documento; se não existir, busca via Chapter Reference
    course_name = get_doc_field(doc, "course") or _get_course_for_chapter(chapter_name)
    if not course_name:
        return None

    # Primeiro capítulo: sempre liberado
    if _is_first_chapter(course_name, chapter_name):
        return None

    chapters = frappe.get_all(
        "Chapter Reference",
        filters={"parent": course_name},
        fields=["chapter"],
        order_by="idx"
    )
    chapter_names = [c.chapter for c in chapters]

    if chapter_name not in chapter_names:
        return None

    current_idx = chapter_names.index(chapter_name)
    if current_idx == 0:
        return None

    previous_chapter = chapter_names[current_idx - 1]
    if not is_chapter_completed(course_name, previous_chapter, user):
        return False

    return None
