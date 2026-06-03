import frappe
from lms.lms.doctype.lms_course.lms_course import LMSCourse

# Conjunto de funções/papéis administrativos que ignoram o bloqueio de capítulos
BYPASS_ROLES = {"Administrator", "System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Instructor", "LMS Manager"}

class LMSCourseLMSLock(LMSCourse):
    def check_permission(self, chapter):
        if not frappe.session.user or frappe.session.user == "Guest":
            return False
            
        user_roles = set(frappe.get_roles())
        if user_roles & BYPASS_ROLES:
            return True
            
        # Obter todos os capítulos ordenados do curso
        chapters = frappe.get_all("Chapter Reference", 
            filters={"parent": self.name}, 
            fields=["chapter"], 
            order_by="idx")
        
        chapter_names = [c.chapter for c in chapters]
        
        if chapter not in chapter_names:
            return False
            
        current_idx = chapter_names.index(chapter)
        
        # O primeiro capítulo sempre é acessível
        if current_idx == 0:
            return True
            
        # Verificar se o capítulo anterior foi 100% concluído
        previous_chapter = chapter_names[current_idx - 1]
        return is_chapter_completed(self.name, previous_chapter, frappe.session.user)

@frappe.whitelist()
def get_locked_chapters(course):
    """Retorna uma lista de capítulos que estão bloqueados para o usuário atual."""
    if not course:
        return []

    chapters = frappe.get_all("Chapter Reference", 
        filters={"parent": course}, 
        fields=["chapter"], 
        order_by="idx")
    
    chapter_names = [c.chapter for c in chapters]
    
    if not frappe.session.user or frappe.session.user == "Guest":
        return chapter_names[1:] if len(chapter_names) > 1 else []
        
    user_roles = set(frappe.get_roles())
    if user_roles & BYPASS_ROLES:
        return []
        
    # Otimização: Carregar todo o progresso do usuário para este curso de uma vez
    progress_records = frappe.get_all("LMS Course Progress",
        filters={
            "course": course,
            "member": frappe.session.user,
            "status": "Complete"
        },
        fields=["chapter", "lesson"])
    
    completed_chapters = {r.chapter for r in progress_records if r.chapter}
    completed_lessons = {r.lesson for r in progress_records if r.lesson}
    
    locked = []
    for i, chapter in enumerate(chapter_names):
        if i == 0:
            continue
            
        previous_chapter = chapter_names[i - 1]
        
        # Verificar conclusão do capítulo anterior de forma otimizada
        if not check_completion_optimized(course, previous_chapter, completed_chapters, completed_lessons):
            locked.append(chapter)
            
    return locked

def check_completion_optimized(course, chapter, completed_chapters, completed_lessons):
    """Versão otimizada da verificação de conclusão que usa dados pré-carregados."""
    chapter_doc = frappe.get_cached_value("Course Chapter", chapter, ["is_scorm_package", "name"], as_dict=True)
    if not chapter_doc:
        return True

    if chapter_doc.is_scorm_package:
        return chapter in completed_chapters
        
    # Para capítulos normais, verifica as aulas
    lessons = frappe.get_all("Lesson Reference",
        filters={"parent": chapter},
        pluck="lesson")
        
    if not lessons:
        return True
        
    # Todas as aulas do capítulo devem estar no conjunto de aulas concluídas
    return all(lesson in completed_lessons for lesson in lessons)

def is_chapter_completed(course: str, chapter: str, user: str) -> bool:
    """Verifica se um capítulo está concluído (usado para verificações individuais de permissão)."""
    # Usar cache para evitar múltiplas consultas em uma mesma requisição
    cache_key = f"chapter_comp_{course}_{chapter}_{user}"
    cached_status = frappe.cache().hget("lms_lock", cache_key)
    if cached_status is not None:
        return bool(cached_status)

    is_scorm = frappe.db.get_value("Course Chapter", chapter, "is_scorm_package")
    
    completed = False
    if is_scorm:
        completed = frappe.db.exists("LMS Course Progress", {
            "course": course,
            "member": user,
            "chapter": chapter,
            "status": "Complete"
        })
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
    return bool(completed)

def get_doc_field(doc, field, default=None):
    if isinstance(doc, dict):
        return doc.get(field, default)
    return getattr(doc, field, default)

def check_lesson_permission(doc, ptype="read", user=None):
    if ptype != "read":
        return None
        
    if isinstance(doc, str):
        if doc == "Course Lesson": return None
        doc = frappe.get_cached_doc("Course Lesson", doc)
            
    course_name = get_doc_field(doc, "course")
    if not course_name: return None
        
    user = user or frappe.session.user
    if user == "Guest" or not user: return False
        
    user_roles = set(frappe.get_roles(user))
    if user_roles & BYPASS_ROLES: return None
        
    lesson_chapter = get_doc_field(doc, "chapter")
    if not lesson_chapter: return None
        
    chapters = frappe.get_all("Chapter Reference", 
        filters={"parent": course_name}, 
        fields=["chapter"], 
        order_by="idx")
    
    chapter_names = [c.chapter for c in chapters]
    if lesson_chapter not in chapter_names: return None
        
    current_idx = chapter_names.index(lesson_chapter)
    if current_idx == 0: return None
        
    previous_chapter = chapter_names[current_idx - 1]
    if not is_chapter_completed(course_name, previous_chapter, user):
        return False
        
    return None

def check_chapter_permission_hook(doc, ptype="read", user=None):
    if ptype != "read":
        return None
        
    if isinstance(doc, str):
        if doc == "Course Chapter": return None
        doc = frappe.get_cached_doc("Course Chapter", doc)
            
    course_name = get_doc_field(doc, "course")
    if not course_name: return None
        
    user = user or frappe.session.user
    if user == "Guest" or not user: return False
        
    user_roles = set(frappe.get_roles(user))
    if user_roles & BYPASS_ROLES: return None
        
    chapters = frappe.get_all("Chapter Reference", 
        filters={"parent": course_name}, 
        fields=["chapter"], 
        order_by="idx")
    
    chapter_names = [c.chapter for c in chapters]
    doc_name = get_doc_field(doc, "name")
    
    if not doc_name or doc_name not in chapter_names: return None
        
    current_idx = chapter_names.index(doc_name)
    if current_idx == 0: return None
        
    previous_chapter = chapter_names[current_idx - 1]
    if not is_chapter_completed(course_name, previous_chapter, user):
        return False
        
    return None
