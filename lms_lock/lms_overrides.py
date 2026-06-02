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
    chapters = frappe.get_all("Chapter Reference", 
        filters={"parent": course}, 
        fields=["chapter"], 
        order_by="idx")
    
    chapter_names = [c.chapter for c in chapters]
    
    if not frappe.session.user or frappe.session.user == "Guest":
        return chapter_names[1:]  # Bloqueia todos a partir do segundo para convidados
        
    user_roles = set(frappe.get_roles())
    if user_roles & BYPASS_ROLES:
        return []
        
    locked = []
    for i, chapter in enumerate(chapter_names):
        if i == 0:
            continue
            
        previous_chapter = chapter_names[i - 1]
        if not is_chapter_completed(course, previous_chapter, frappe.session.user):
            locked.append(chapter)
            
    return locked

def is_chapter_completed(course: str, chapter: str, user: str) -> bool:
    """Verifica se um capítulo está concluído para o usuário (suporta aulas normais e pacotes SCORM)."""
    # Verificar se o capítulo é um pacote SCORM
    is_scorm = frappe.db.get_value("Course Chapter", chapter, "is_scorm_package")
    
    if is_scorm:
        # Para capítulos SCORM, o progresso é registrado diretamente associado ao capítulo
        scorm_completed = frappe.db.exists("LMS Course Progress", {
            "course": course,
            "member": user,
            "chapter": chapter,
            "status": "Complete"
        })
        return bool(scorm_completed)
        
    # Para capítulos normais, verifica se todas as aulas associadas estão concluídas
    lessons = frappe.get_all("Lesson Reference",
        filters={"parent": chapter},
        pluck="lesson")
        
    if not lessons:
        return True
        
    # Contar quantas dessas aulas específicas o estudante concluiu no curso
    completed_count = frappe.db.count("LMS Course Progress", {
        "course": course,
        "member": user,
        "lesson": ["in", lessons],
        "status": "Complete"
    })
    
    return completed_count == len(lessons)


def check_lesson_permission(doc, ptype="read", user=None):
    """Gancho (hook) de segurança para impedir a leitura direta das aulas bloqueadas no backend."""
    if ptype != "read":
        return None  # Permite que as outras operações sigam a permissão padrão
        
    if not user:
        user = frappe.session.user
        
    if user == "Guest" or not user:
        return False
        
    user_roles = set(frappe.get_roles(user))
    if user_roles & BYPASS_ROLES:
        return None  # Administradores e gerentes seguem a permissão padrão
        
    course_name = doc.course
    lesson_chapter = doc.chapter
    
    if not course_name or not lesson_chapter:
        return None
        
    # Obter os capítulos do curso ordenados
    chapters = frappe.get_all("Chapter Reference", 
        filters={"parent": course_name}, 
        fields=["chapter"], 
        order_by="idx")
    
    chapter_names = [c.chapter for c in chapters]
    
    if lesson_chapter not in chapter_names:
        return None
        
    current_idx = chapter_names.index(lesson_chapter)
    
    # Primeiro capítulo sempre acessível
    if current_idx == 0:
        return None
        
    # Validar se o capítulo anterior foi 100% concluído
    previous_chapter = chapter_names[current_idx - 1]
    if not is_chapter_completed(course_name, previous_chapter, user):
        return False  # Bloqueia explicitamente a leitura no backend
        
    return None  # Se estiver desbloqueado, prossegue com as verificações normais (como matrícula)

def check_chapter_permission_hook(doc, ptype="read", user=None):
    """Gancho (hook) de segurança para impedir a leitura de capítulos bloqueados no backend."""
    if ptype != "read":
        return None
        
    if not user:
        user = frappe.session.user
        
    if user == "Guest" or not user:
        return False
        
    user_roles = set(frappe.get_roles(user))
    if user_roles & BYPASS_ROLES:
        return None
        
    course_name = doc.course
    if not course_name:
        return None
        
    # Obter os capítulos do curso ordenados
    chapters = frappe.get_all("Chapter Reference", 
        filters={"parent": course_name}, 
        fields=["chapter"], 
        order_by="idx")
    
    chapter_names = [c.chapter for c in chapters]
    
    if doc.name not in chapter_names:
        return None
        
    current_idx = chapter_names.index(doc.name)
    
    # Primeiro capítulo sempre acessível
    if current_idx == 0:
        return None
        
    # Validar se o capítulo anterior foi 100% concluído
    previous_chapter = chapter_names[current_idx - 1]
    if not is_chapter_completed(course_name, previous_chapter, user):
        return False  # Bloqueia explicitamente a leitura do capítulo no backend
        
    return None