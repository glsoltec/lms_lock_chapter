"""
Server Script Validator for Course Lesson Permissions
This script should be saved as a Server Script in Frappe
DocType: Server Script
Event: Before Insert / Before Submit / Validate

This provides an additional layer of permission checking for Course Lessons
when the standard has_permission hooks are bypassed.
"""

import frappe
from lms_lock_chapter.lms_overrides import is_chapter_completed, _get_course_for_lesson

def validate_lesson_permission():
    """
    Validate if current user has permission to access this lesson.
    Called via before_insert or validate event on Course Lesson.
    """
    # This script would be triggered on Course Lesson access
    # It's an alternative approach if hooks are not being called

    lesson_name = doc.name if hasattr(doc, 'name') else None
    if not lesson_name:
        return

    user = frappe.session.user
    if not user or user == "Guest":
        return

    # Check if user has bypass roles
    bypass_roles = {"Administrator", "System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Instructor", "LMS Manager"}
    if set(frappe.get_roles(user)) & bypass_roles:
        return  # Allow

    # Get course and chapter for this lesson
    course_name, lesson_chapter = _get_course_for_lesson(lesson_name)

    if not course_name or not lesson_chapter:
        return  # Can't determine context, allow

    # Get ordered chapters
    chapters = frappe.db.sql("""
        SELECT chapter FROM `tabChapter Reference`
        WHERE parent = %s AND parenttype = 'LMS Course'
        ORDER BY idx ASC
    """, course_name, as_dict=True)

    if not chapters:
        return  # No chapters defined

    chapter_names = [c.get('chapter') for c in chapters]

    if lesson_chapter not in chapter_names:
        return  # Lesson's chapter not in course

    idx = chapter_names.index(lesson_chapter)

    # First chapter is always allowed
    if idx == 0:
        return

    # Check if previous chapter is completed
    if not is_chapter_completed(course_name, chapter_names[idx - 1], user):
        frappe.throw(f"You must complete the previous chapter before accessing this lesson.", exc=frappe.PermissionError)
