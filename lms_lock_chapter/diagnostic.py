"""
Diagnostic script to check lms_lock_chapter functionality after LMS updates.
Run with: bench console
>>> exec(open("lms_lock_chapter/diagnostic.py").read())
"""

import frappe
from lms_lock_chapter.lms_overrides import (
    check_lesson_permission,
    check_chapter_permission_hook,
    _get_ordered_chapters,
    is_chapter_completed,
)


def diagnostic():
    print("\n" + "="*80)
    print("LMS LOCK CHAPTER - DIAGNOSTIC REPORT")
    print("="*80)

    # 1. Check if hooks are registered
    print("\n1. HOOKS REGISTRATION:")
    hooks_config = frappe.get_app_config("lms_lock_chapter")
    print(f"   - override_doctype_class: {hooks_config.get('override_doctype_class', {})}")
    print(f"   - has_permission: {hooks_config.get('has_permission', {})}")
    print(f"   - doc_events: {hooks_config.get('doc_events', {})}")

    # 2. Check LMS app version
    print("\n2. APP VERSIONS:")
    try:
        lms_version = frappe.get_value("App", "lms", "app_version") or \
                     frappe.get_value("App", "frappe-lms", "app_version")
        print(f"   - LMS Version: {lms_version}")
    except Exception as e:
        print(f"   - LMS Version: Error - {e}")

    erpnext_version = frappe.get_value("App", "erpnext", "app_version")
    print(f"   - ERPNext Version: {erpnext_version}")

    # 3. Test with a sample course
    print("\n3. SAMPLE COURSE TEST:")
    try:
        courses = frappe.get_all("LMS Course", limit=1)
        if courses:
            course = courses[0]
            print(f"   - Course: {course.name}")

            chapters = _get_ordered_chapters(course.name)
            print(f"   - Chapters found: {len(chapters)}")
            if chapters:
                print(f"   - First chapter: {chapters[0]}")
                print(f"   - All chapters: {chapters}")
        else:
            print("   - No courses found in system")
    except Exception as e:
        print(f"   - Error getting courses: {e}")

    # 4. Test permission functions
    print("\n4. PERMISSION FUNCTION TEST:")
    try:
        # Get a test lesson
        lesson = frappe.get_all("Course Lesson", limit=1)
        if lesson:
            lesson_name = lesson[0].name
            print(f"   - Test lesson: {lesson_name}")

            # Call check_lesson_permission
            result = check_lesson_permission(lesson_name)
            print(f"   - check_lesson_permission result: {result} (type: {type(result).__name__})")

            # Call with doc object
            lesson_doc = frappe.get_doc("Course Lesson", lesson_name)
            result = check_lesson_permission(lesson_doc)
            print(f"   - check_lesson_permission (doc obj) result: {result}")
        else:
            print("   - No lessons found in system")
    except Exception as e:
        print(f"   - Error testing permission: {e}")
        frappe.log_error(frappe.get_traceback(), "diagnostic: error testing permission")

    # 5. Test LMSCourseLMSLock class
    print("\n5. LMSCourseLMSLock CLASS TEST:")
    try:
        from lms_lock_chapter.lms_overrides import LMSCourseLMSLock
        print(f"   - Class imported successfully: {LMSCourseLMSLock}")
        print(f"   - MRO: {[c.__name__ for c in LMSCourseLMSLock.__mro__]}")

        # Check if method exists
        if hasattr(LMSCourseLMSLock, "check_permission"):
            print(f"   - check_permission method found")
        else:
            print(f"   - check_permission method NOT found")
    except Exception as e:
        print(f"   - Error loading class: {e}")

    # 6. Check cache
    print("\n6. CACHE TEST:")
    try:
        cache = frappe.cache()
        cache.set_value("lms_lock_diagnostic_test", "ok", expires_in_sec=60)
        result = cache.get_value("lms_lock_diagnostic_test")
        print(f"   - Redis cache working: {result == 'ok'}")
    except Exception as e:
        print(f"   - Cache error: {e}")

    print("\n" + "="*80)
    print("END OF DIAGNOSTIC REPORT")
    print("="*80 + "\n")


if __name__ == "__main__":
    diagnostic()
