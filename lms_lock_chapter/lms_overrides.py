import frappe
import re
from urllib.parse import urlparse
from lms.lms.doctype.lms_course.lms_course import LMSCourse


def inject_portal_script(response) -> None:
	try:
		if "text/html" not in response.headers.get("Content-Type", ""):
			return
		path = getattr(frappe.local.request, "path", "") if hasattr(frappe.local, "request") else ""
		if not path.startswith("/lms"):
			return
		data = response.get_data()
		if b"</body>" not in data:
			return
		script_tag = b'\n<script src="/assets/lms_lock_chapter/js/lms_portal_lock.js"></script>'
		response.set_data(data.replace(b"</body>", script_tag + b"</body>", 1))
	except Exception:
		pass


BYPASS_ROLES = {"Administrator", "System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Instructor", "LMS Manager"}


def _add_blocked_message() -> None:
	msg = frappe._("You need to complete the previous chapter before accessing this content.")
	if hasattr(frappe.local, "message_log"):
		for log in frappe.local.message_log:
			if isinstance(log, dict) and log.get("message") == msg:
				return
			elif isinstance(log, str) and msg in log:
				return
	frappe.msgprint(msg=msg, title=frappe._("Chapter Locked"), indicator="orange", raise_exception=False)


def _get_course_name_by_slug(course_slug: str) -> str | None:
	try:
		if not course_slug or not isinstance(course_slug, str):
			return None
		if frappe.db.exists("LMS Course", course_slug):
			return course_slug
		for p in [course_slug, f"courses/{course_slug}", f"/courses/{course_slug}"]:
			name = frappe.db.get_value("LMS Course", {"route": p}, "name")
			if name:
				return name
	except Exception:
		pass
	return None


def _get_course_from_request() -> str | None:
	try:
		if not hasattr(frappe.local, "request") or not frappe.local.request:
			return None
		path = getattr(frappe.local.request, "path", "") or ""
		match = re.search(r"/(?:lms/)?courses/([^/]+)", path)
		if match:
			return _get_course_name_by_slug(match.group(1))
		referer = frappe.local.request.headers.get("Referer", "")
		if referer:
			match = re.search(r"/(?:lms/)?courses/([^/]+)", urlparse(referer).path)
			if match:
				return _get_course_name_by_slug(match.group(1))
	except Exception:
		pass
	return None


def _get_course_for_chapter(chapter_name: str) -> str | None:
	try:
		course = _get_course_from_request()
		if course and frappe.db.exists("Chapter Reference", {"chapter": chapter_name, "parent": course, "parenttype": "LMS Course"}):
			return course
		return frappe.db.get_value("Chapter Reference", {"chapter": chapter_name, "parenttype": "LMS Course"}, "parent")
	except Exception:
		return None


def _get_ordered_chapters(course_name: str) -> list[str]:
	try:
		rows = frappe.get_all("Chapter Reference", filters={"parent": course_name, "parenttype": "LMS Course"}, fields=["chapter"], order_by="idx asc")
		return [r.get("chapter") if isinstance(r, dict) else getattr(r, "chapter", None) for r in rows if (r.get("chapter") if isinstance(r, dict) else getattr(r, "chapter", None))]
	except Exception:
		return []


def _get_course_for_lesson(lesson_name: str) -> tuple[str | None, str | None]:
	try:
		chapters = frappe.get_all("Lesson Reference", filters={"lesson": lesson_name, "parenttype": "Course Chapter"}, fields=["parent"])
		if not chapters:
			return None, None
		course = _get_course_from_request()
		if course:
			for c in chapters:
				ch = c.get("parent") if isinstance(c, dict) else getattr(c, "parent", None)
				if frappe.db.exists("Chapter Reference", {"chapter": ch, "parent": course, "parenttype": "LMS Course"}):
					return course, ch
		return _get_course_for_chapter(chapters[0].get("parent") if isinstance(chapters[0], dict) else getattr(chapters[0], "parent", None)), chapters[0].get("parent") if isinstance(chapters[0], dict) else getattr(chapters[0], "parent", None)
	except Exception:
		return None, None


class LMSCourseLMSLock(LMSCourse):
	def check_permission(self, ptype_or_chapter=None, *args, **kwargs) -> bool:
		try:
			if ptype_or_chapter in {"read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "report", "import", "export", "set_user_permissions", "share"}:
				return super().check_permission(ptype_or_chapter, kwargs.get("permlevel") or (args[0] if args else None)) or True
			chapter = ptype_or_chapter
			if not chapter or not frappe.session.user or frappe.session.user == "Guest":
				return False if frappe.session.user == "Guest" and chapter else True
			if set(frappe.get_roles()) & BYPASS_ROLES:
				return True
			chapters = _get_ordered_chapters(self.name)
			if chapter not in chapters:
				return True
			idx = chapters.index(chapter)
			return True if idx == 0 else is_chapter_completed(self.name, chapters[idx - 1], frappe.session.user)
		except Exception:
			return True


@frappe.whitelist()
def get_locked_chapters(course: str) -> list[str]:
	if not course:
		return []
	course_name = _get_course_name_by_slug(course)
	if not course_name:
		return []
	if not frappe.has_permission("LMS Course", "read", course_name):
		frappe.throw("You do not have permission to access this course.", exc=frappe.PermissionError)
	chapters = _get_ordered_chapters(course_name)
	if not chapters or not frappe.session.user or frappe.session.user == "Guest":
		return chapters[1:] if chapters else []
	if set(frappe.get_roles()) & BYPASS_ROLES:
		return []
	locked = []
	for i, ch in enumerate(chapters):
		if i == 0:
			continue
		if not is_chapter_completed(course_name, chapters[i - 1], frappe.session.user):
			locked.append(ch)
	return locked


def is_chapter_completed(course: str, chapter: str, user: str) -> bool:
	try:
		is_scorm = frappe.db.get_value("Course Chapter", chapter, "is_scorm_package")
		if is_scorm:
			return bool(frappe.db.exists("LMS Course Progress", {"course": course, "member": user, "chapter": chapter, "status": "Complete"}))
		lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter}, pluck="lesson")
		if not lessons:
			return True
		completed = frappe.db.count("LMS Course Progress", {"course": course, "member": user, "lesson": ["in", lessons], "status": "Complete"})
		return completed == len(lessons)
	except Exception:
		return True


def invalidate_chapter_completion_cache(doc, method=None) -> None:
	if doc.get("status") == "Complete" and doc.get("course") and doc.get("member"):
		chapter = doc.get("chapter")
		if not chapter and doc.get("lesson"):
			chapter = frappe.db.get_value("Lesson Reference", {"lesson": doc.get("lesson"), "parenttype": "Course Chapter"}, "parent")
		if chapter:
			frappe.cache().delete_value(f"chapter_comp_{doc.course}_{chapter}_{doc.member}")


def check_lesson_permission(doc, ptype: str = "read", user: str | None = None) -> bool | None:
	try:
		if ptype != "read":
			return None
		if isinstance(doc, str):
			if doc == "Course Lesson":
				return None
			lesson_name = doc
			course_name, lesson_chapter = _get_course_for_lesson(lesson_name)
		else:
			lesson_name = doc.get("name") if isinstance(doc, dict) else getattr(doc, "name", None)
			if not lesson_name:
				return None
			course_name = doc.get("course") if isinstance(doc, dict) else getattr(doc, "course", None)
			lesson_chapter = doc.get("chapter") if isinstance(doc, dict) else getattr(doc, "chapter", None)
			if not course_name or not lesson_chapter:
				course_name, lesson_chapter = _get_course_for_lesson(lesson_name)
		if not course_name or not lesson_chapter:
			return None
		user = user or frappe.session.user
		if not user or user == "Guest":
			return False
		if set(frappe.get_roles(user)) & BYPASS_ROLES:
			return True
		chapters = _get_ordered_chapters(course_name)
		if not chapters or lesson_chapter not in chapters:
			return None
		idx = chapters.index(lesson_chapter)
		frappe.logger().debug(f"check_lesson_permission: {lesson_name} in course {course_name}, chapter idx {idx}")
		if idx == 0:
			return True
		if not is_chapter_completed(course_name, chapters[idx - 1], user):
			frappe.logger().info(f"Lesson blocked: {lesson_name} - previous chapter not completed")
			_add_blocked_message()
			return False
		return None
	except Exception:
		frappe.log_error(frappe.get_traceback(), "lms_lock_chapter: check_lesson_permission error")
		return None


def check_chapter_permission_hook(doc, ptype: str = "read", user: str | None = None) -> bool | None:
	try:
		if ptype != "read":
			return None
		if isinstance(doc, str):
			if doc == "Course Chapter":
				return None
			chapter_name = doc
			course_name = _get_course_for_chapter(chapter_name)
		else:
			chapter_name = doc.get("name") if isinstance(doc, dict) else getattr(doc, "name", None)
			if not chapter_name:
				return None
			course_name = (doc.get("course") if isinstance(doc, dict) else getattr(doc, "course", None)) or _get_course_for_chapter(chapter_name)
		if not course_name:
			return None
		user = user or frappe.session.user
		if not user or user == "Guest":
			return False
		if set(frappe.get_roles(user)) & BYPASS_ROLES:
			return True
		chapters = _get_ordered_chapters(course_name)
		if not chapters or chapter_name not in chapters:
			return None
		idx = chapters.index(chapter_name)
		frappe.logger().debug(f"check_chapter_permission_hook: {chapter_name} in course {course_name}, chapter idx {idx}")
		if idx == 0:
			return True
		if not is_chapter_completed(course_name, chapters[idx - 1], user):
			frappe.logger().info(f"Chapter blocked: {chapter_name} - previous chapter not completed")
			_add_blocked_message()
			return False
		return None
	except Exception:
		frappe.log_error(frappe.get_traceback(), "lms_lock_chapter: check_chapter_permission_hook error")
		return None
