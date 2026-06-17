"""
Diagnostic script to investigate native (non-SCORM) chapter completion tracking.
Run with: bench console
>>> exec(open("lms_lock_chapter/diagnostic_native_chapters.py").read())
"""

import frappe


def diagnostic_native_chapters():
    print("\n" + "="*80)
    print("NATIVE CHAPTERS COMPLETION DIAGNOSTIC")
    print("="*80)

    # 1. Find a non-SCORM course
    print("\n1. FIND NON-SCORM COURSES:")
    courses = frappe.get_all("LMS Course", filters={"is_active": 1}, limit=5)
    if not courses:
        print("   - No active courses found")
        return

    for course in courses:
        print(f"\n   Course: {course.name}")

        # Get chapters for this course
        chapters = frappe.get_all("Chapter Reference", filters={"parent": course.name, "parenttype": "LMS Course"}, fields=["chapter"])
        print(f"   Total chapters: {len(chapters)}")

        if not chapters:
            continue

        for ch_ref in chapters[:2]:  # Check first 2 chapters
            ch_name = ch_ref.get("chapter")
            is_scorm = frappe.db.get_value("Course Chapter", ch_name, "is_scorm_package")
            print(f"\n   Chapter: {ch_name} (SCORM: {is_scorm})")

            # Get lessons in this chapter
            lessons = frappe.get_all("Lesson Reference", filters={"parent": ch_name, "parenttype": "Course Chapter"}, pluck="lesson")
            print(f"      Lessons in chapter: {len(lessons)}")
            if lessons:
                print(f"      Lesson names: {lessons[:3]}")  # Show first 3

            # Check LMS Course Progress for this chapter
            print(f"\n      LMS Course Progress records for chapter {ch_name}:")
            progress_records = frappe.get_all(
                "LMS Course Progress",
                filters={"course": course.name, "chapter": ch_name},
                fields=["name", "member", "lesson", "status", "is_current"],
                limit=10
            )
            if progress_records:
                print(f"         Total records: {len(progress_records)}")
                for rec in progress_records[:3]:  # Show first 3
                    print(f"         - Member: {rec.get('member')}, Lesson: {rec.get('lesson')}, Status: {rec.get('status')}, Current: {rec.get('is_current')}")
            else:
                print("         No progress records found for this chapter")

            # Check progress for lessons
            if lessons:
                print(f"\n      LMS Course Progress records for lessons in {ch_name}:")
                lesson_progress = frappe.get_all(
                    "LMS Course Progress",
                    filters={"course": course.name, "lesson": ["in", lessons]},
                    fields=["name", "member", "lesson", "status", "is_current"],
                    limit=10
                )
                if lesson_progress:
                    print(f"         Total lesson progress records: {len(lesson_progress)}")
                    for rec in lesson_progress[:3]:  # Show first 3
                        print(f"         - Member: {rec.get('member')}, Lesson: {rec.get('lesson')}, Status: {rec.get('status')}, Current: {rec.get('is_current')}")
                else:
                    print("         No lesson progress records found")

    # 2. Check what status values exist
    print("\n2. POSSIBLE STATUS VALUES IN LMS COURSE PROGRESS:")
    status_values = frappe.get_all(
        "LMS Course Progress",
        fields=["status"],
        distinct=True,
        limit=20
    )
    if status_values:
        statuses = [r.get("status") for r in status_values]
        print(f"   Found status values: {statuses}")
    else:
        print("   No LMS Course Progress records found")

    # 3. Check DocType fields
    print("\n3. LMS COURSE PROGRESS DOCTYPE FIELDS:")
    doc_meta = frappe.get_meta("LMS Course Progress")
    print(f"   Available fields:")
    for field in doc_meta.fields:
        if field.fieldname in ["status", "is_current", "chapter", "lesson", "member", "course", "progress"]:
            print(f"      - {field.fieldname} ({field.fieldtype}): {field.label}")

    print("\n" + "="*80)
    print("END OF DIAGNOSTIC")
    print("="*80 + "\n")


if __name__ == "__main__":
    diagnostic_native_chapters()
