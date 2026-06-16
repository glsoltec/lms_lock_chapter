import frappe
from lms.lms.doctype.lms_course.lms_course import LMSCourse


def inject_portal_script(response) -> None:
	"""
	Hook after_request: Injects lms_portal_lock.js into all LMS HTML pages.
	Necessary because the LMS uses a custom Vue SPA template that does not process
	Frappe's web_include_js hook.
	"""
	try:
		content_type = response.headers.get("Content-Type", "")
		if "text/html" not in content_type:
			return

		path = ""
		try:
			path = frappe.request.path
		except Exception:
			return

		if not path.startswith("/lms"):
			return

		data = response.get_data()
		if b"</body>" not in data:
			return

		script_tag = (
			b'\n<script src="/assets/lms_lock_chapter/js/lms_portal_lock.js">'
			b"</script>"
		)
		response.set_data(data.replace(b"</body>", script_tag + b"</body>", 1))
	except Exception:
		pass


BYPASS_ROLES = {
	"Administrator",
	"System Manager",
	"Moderator",
	"Course Creator",
	"Batch Evaluator",
	"Instructor",
	"LMS Manager",
}


def _add_blocked_message() -> None:
	"""
	Registers the block warning in Frappe's message_log.
	The message_log is sent on ANY API response (including 403 error responses),
	and the Frappe frontend automatically displays it as a popup.
	Guards against adding duplicate messages within the same request lifecycle.
	"""
	msg = frappe._("You need to complete the previous chapter before accessing this content.")
	if hasattr(frappe.local, "message_log"):
		for log in frappe.local.message_log:
			if isinstance(log, dict) and log.get("message") == msg:
				return
			elif isinstance(log, str) and msg in log:
				return

	frappe.msgprint(
		msg=msg,
		title=frappe._("Chapter Locked"),
		indicator="orange",
		raise_exception=False,
	)


def _get_course_name_by_slug(course_slug: str) -> str | None:
	"""Resolves the actual LMS Course document name from a slug/route."""
	try:
		if not course_slug:
			return None
		if not isinstance(course_slug, str):
			course_slug = str(course_slug)

		# 1. Direct match by name
		if frappe.db.exists("LMS Course", course_slug):
			return course_slug

		# 2. Match by route field (try various patterns)
		patterns = [
			course_slug,
			f"courses/{course_slug}",
			f"/courses/{course_slug}",
			f"lms/courses/{course_slug}",
			f"/lms/courses/{course_slug}"
		]
		for p in patterns:
			course_name = frappe.db.get_value("LMS Course", {"route": p}, "name")
			if course_name:
				return course_name

		# 3. Case-insensitive name match (e.g., nr05 -> NR-05)
		cleaned = course_slug.lower().replace("-", "").replace("_", "")
		courses = frappe.get_all("LMS Course", fields=["name"]) or []
		for c in courses:
			c_name = c.get("name") if isinstance(c, dict) else getattr(c, "name", None)
			if c_name:
				c_clean = c_name.lower().replace("-", "").replace("_", "")
				if c_clean == cleaned:
					return c_name
	except Exception:
		pass

	return None


def _get_course_from_request() -> str | None:
	"""Attempts to extract the course name from the current request path or HTTP Referer."""
	try:
		if not hasattr(frappe.local, "request") or not frappe.local.request:
			return None

		import re
		from urllib.parse import urlparse

		course_slug = None

		# 1. Try to get course from path (for direct page requests)
		path = getattr(frappe.local.request, "path", "") or ""
		match = re.search(r"/(?:lms/)?courses/([^/]+)", path)
		if match:
			course_slug = match.group(1)

		# 2. Try to get course from Referer header (for API requests made by the frontend)
		if not course_slug:
			referer = frappe.local.request.headers.get("Referer", "")
			if referer:
				try:
					parsed_url = urlparse(referer)
					match = re.search(r"/(?:lms/)?courses/([^/]+)", parsed_url.path)
					if match:
						course_slug = match.group(1)
				except Exception:
					pass

		# 3. Try to get course from request parameters (e.g. GET/POST args)
		if not course_slug and hasattr(frappe, "form_dict") and frappe.form_dict:
			course_slug = frappe.form_dict.get("course")

		if course_slug:
			return _get_course_name_by_slug(course_slug)
	except Exception:
		pass

	return None


def _get_course_for_chapter(chapter_name: str) -> str | None:
	"""Fetches the parent course of a chapter, prioritizing the course from request context."""
	try:
		course_from_req = _get_course_from_request()
		if course_from_req:
			exists = frappe.db.exists("Chapter Reference", {
				"chapter": chapter_name,
				"parent": course_from_req,
				"parenttype": "LMS Course"
			})
			if exists:
				return course_from_req

		return frappe.db.get_value(
			"Chapter Reference",
			{"chapter": chapter_name, "parenttype": "LMS Course"},
			"parent"
		)
	except Exception:
		return None


def _get_ordered_chapters(course_name: str) -> list[str]:
	"""Returns an ordered list of published, existing, and non-empty chapter names for a course."""
	try:
		rows = frappe.get_all(
			"Chapter Reference",
			filters={"parent": course_name, "parenttype": "LMS Course"},
			fields=["chapter"],
			order_by="idx asc",
		)

		chapters = []
		meta = None
		try:
			meta = frappe.get_meta("Course Chapter")
		except Exception:
			pass

		has_published_field = meta and meta.has_field("published")
		has_scorm_field = meta and meta.has_field("is_scorm_package")

		lesson_meta = None
		try:
			lesson_meta = frappe.get_meta("Course Lesson")
		except Exception:
			pass
		has_lesson_published = lesson_meta and lesson_meta.has_field("published")

		for r in rows:
			chapter_val = r.get("chapter") if isinstance(r, dict) else getattr(r, "chapter", None)
			if not chapter_val:
				continue

			# Check if the Course Chapter document actually exists
			if not frappe.db.exists("Course Chapter", chapter_val):
				continue

			# Filter by published status if the field exists
			if has_published_field:
				is_published = frappe.db.get_value("Course Chapter", chapter_val, "published")
				if not is_published:
					continue

			# Filter out empty or draft-only chapters
			is_scorm = False
			if has_scorm_field:
				is_scorm = frappe.db.get_value("Course Chapter", chapter_val, "is_scorm_package")

			if not is_scorm:
				# It is a normal chapter: check if it has at least one published lesson
				lessons = frappe.get_all(
					"Lesson Reference",
					filters={"parent": chapter_val, "parenttype": "Course Chapter"},
					fields=["lesson"]
				)
				lesson_names = []
				for l in lessons:
					val = l.get("lesson") if isinstance(l, dict) else getattr(l, "lesson", None)
					if val:
						lesson_names.append(val)

				if not lesson_names:
					# No lessons at all: empty chapter, skip it
					continue

				if has_lesson_published:
					published_lessons_count = frappe.db.count(
						"Course Lesson",
						filters={"name": ["in", lesson_names], "published": 1}
					)
					if published_lessons_count == 0:
						# No published lessons in this chapter: skip it
						continue

			chapters.append(chapter_val)

		return chapters
	except Exception:
		return []


def _get_course_for_lesson(lesson_name: str) -> tuple[str | None, str | None]:
	"""Fetches the course and chapter of a lesson, prioritizing request context."""
	try:
		chapters = frappe.get_all(
			"Lesson Reference",
			filters={"lesson": lesson_name, "parenttype": "Course Chapter"},
			fields=["parent"]
		)
		if not chapters:
			return None, None

		chapter_names = []
		for c in chapters:
			parent_val = c.get("parent") if isinstance(c, dict) else getattr(c, "parent", None)
			if parent_val:
				chapter_names.append(parent_val)

		if not chapter_names:
			return None, None

		course_from_req = _get_course_from_request()
		if course_from_req:
			for ch in chapter_names:
				exists = frappe.db.exists("Chapter Reference", {
					"chapter": ch,
					"parent": course_from_req,
					"parenttype": "LMS Course"
				})
				if exists:
					return course_from_req, ch

		# Fallback
		first_chapter = chapter_names[0]
		course_name = _get_course_for_chapter(first_chapter)
		return course_name, first_chapter
	except Exception:
		return None, None


def get_doc_field(doc, field: str, default=None):
	if isinstance(doc, dict):
		return doc.get(field, default)
	return getattr(doc, field, default)


# Default permission types of a Frappe Document.
# When check_permission is called internally by Frappe, the first argument is one of these.
_FRAPPE_PTYPES = frozenset({
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"print",
	"email",
	"report",
	"import",
	"export",
	"set_user_permissions",
	"share",
})


class LMSCourseLMSLock(LMSCourse):
	def check_permission(self, ptype_or_chapter=None, *args, **kwargs) -> bool:
		try:
			# When Frappe calls check_permission("read") or similar,
			# delegate to the default behavior without interference.
			if ptype_or_chapter in _FRAPPE_PTYPES:
				permtype = ptype_or_chapter or "read"
				permlevel = kwargs.get("permlevel") or (args[0] if args else None)
				super().check_permission(permtype, permlevel)
				return True

			# When LMS calls check_permission(chapter_name) to verify access to a chapter,
			# apply the sequential lock logic.
			chapter = ptype_or_chapter
			if not chapter:
				return True

			if not frappe.session.user or frappe.session.user == "Guest":
				return False

			user_roles = set(frappe.get_roles())
			if user_roles & BYPASS_ROLES:
				return True

			chapter_names = _get_ordered_chapters(self.name)

			if chapter not in chapter_names:
				return True  # Does not belong to this course; allow access

			current_idx = chapter_names.index(chapter)
			if current_idx == 0:
				return True

			previous_chapter = chapter_names[current_idx - 1]
			return is_chapter_completed(self.name, previous_chapter, frappe.session.user)
		except Exception:
			# Safety fallback: if anything fails, allow access to prevent blocking out users
			return True


@frappe.whitelist()
def get_locked_chapters(course: str) -> list[str]:
	"""Returns the list of locked chapters for the current user in a course."""
	if not course:
		return []

	# Resolve course slug to actual document name
	course_name = _get_course_name_by_slug(course)
	if not course_name:
		return []

	# Security verification: Check if the user has read permission on the course
	if not frappe.has_permission("LMS Course", "read", course_name):
		frappe.throw(
			msg=frappe._("You do not have permission to access this course."),
			exc=frappe.PermissionError,
		)

	chapter_names = _get_ordered_chapters(course_name)
	if not chapter_names:
		return []

	if not frappe.session.user or frappe.session.user == "Guest":
		return chapter_names[1:]

	user_roles = set(frappe.get_roles())
	if user_roles & BYPASS_ROLES:
		return []

	progress_records = frappe.get_all(
		"LMS Course Progress",
		filters={"course": course_name, "member": frappe.session.user, "status": "Complete"},
		fields=["chapter", "lesson"],
	)

	completed_chapters = {r.chapter for r in progress_records if r.chapter}
	completed_lessons = {r.lesson for r in progress_records if r.lesson}

	locked = []
	for i, chapter in enumerate(chapter_names):
		if i == 0:
			continue  # First chapter is never locked
		previous_chapter = chapter_names[i - 1]
		if not check_completion_optimized(course_name, previous_chapter, completed_chapters, completed_lessons):
			locked.append(chapter)

	return locked


def check_completion_optimized(
	course: str, chapter: str, completed_chapters: set[str], completed_lessons: set[str]
) -> bool:
	"""Verifies completion of a chapter using pre-loaded data."""
	try:
		chapter_doc = frappe.get_cached_value(
			"Course Chapter", chapter, ["is_scorm_package", "name"], as_dict=True
		)
		if not chapter_doc:
			return True

		is_scorm = chapter_doc.get("is_scorm_package") if isinstance(chapter_doc, dict) else getattr(chapter_doc, "is_scorm_package", None)
		if is_scorm:
			return chapter in completed_chapters

		lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter}, pluck="lesson")
		if not lessons:
			return True

		return all(lesson in completed_lessons for lesson in lessons)
	except Exception:
		return True


def _chapter_cache_key(course: str, chapter: str, user: str) -> str:
	return f"chapter_comp_{course}_{chapter}_{user}"


def invalidate_chapter_completion_cache(doc, method=None) -> None:
	"""
	Called via doc_events on LMS Course Progress (after_insert / on_update).
	Invalidates the Redis cache when a chapter or lesson belonging to it is completed,
	ensuring the next access reads the database and unlocks the next chapter.
	"""
	if doc.get("status") == "Complete" and doc.get("course") and doc.get("member"):
		chapter = doc.get("chapter")
		if not chapter and doc.get("lesson"):
			# If it's a lesson progress update, find the parent chapter of the lesson
			chapter = frappe.db.get_value(
				"Lesson Reference",
				{"lesson": doc.get("lesson"), "parenttype": "Course Chapter"},
				"parent"
			)

		if chapter:
			cache_key = _chapter_cache_key(doc.course, chapter, doc.member)
			frappe.cache().hdel("lms_lock_chapter", cache_key)


def is_chapter_completed(course: str, chapter: str, user: str) -> bool:
	"""
	Verifies if a chapter is completed.
	Redis cache is used only for completed status (True).
	Incomplete status is never cached to prevent stale caches after progress is made.
	"""
	try:
		cache_key = _chapter_cache_key(course, chapter, user)

		# Only trust cache if value is 1 (completed)
		cached_status = frappe.cache().hget("lms_lock_chapter", cache_key)
		if cached_status == 1 or cached_status == b"1" or cached_status is True:
			return True

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

		# Cache only when completed; incomplete reads from the database
		if completed:
			frappe.cache().hset("lms_lock_chapter", cache_key, 1)

		return completed
	except Exception:
		return True


def check_lesson_permission(doc, ptype: str = "read", user: str | None = None) -> bool | None:
	"""
	has_permission hook for Course Lesson.
	Returns False if the lesson belongs to a locked chapter.
	Returns None if unlocked (delegates to standard Frappe/LMS permissions).
	"""
	try:
		if ptype != "read":
			return None

		# Doctype-level call (no specific document instance)
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
			return None

		chapter_names = _get_ordered_chapters(course_name)
		if not chapter_names or lesson_chapter not in chapter_names:
			return None

		current_idx = chapter_names.index(lesson_chapter)

		# First chapter: always accessible
		if current_idx == 0:
			return None

		previous_chapter = chapter_names[current_idx - 1]
		if not is_chapter_completed(course_name, previous_chapter, user):
			_add_blocked_message()
			return False

		return None

	except Exception:
		frappe.log_error(frappe.get_traceback(), "lms_lock_chapter: check_lesson_permission error")
		return None


def check_chapter_permission_hook(doc, ptype: str = "read", user: str | None = None) -> bool | None:
	"""
	has_permission hook for Course Chapter.
	Returns False if the chapter is locked (previous one not completed).
	Returns None if unlocked (delegates to standard Frappe/LMS permissions).
	"""
	try:
		if ptype != "read":
			return None

		# Doctype-level call (no specific document instance)
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
			return None  # Could not determine course; do not lock

		user = user or frappe.session.user
		if not user or user == "Guest":
			return False

		user_roles = set(frappe.get_roles(user))
		if user_roles & BYPASS_ROLES:
			return None

		chapter_names = _get_ordered_chapters(course_name)
		if not chapter_names or chapter_name not in chapter_names:
			return None

		current_idx = chapter_names.index(chapter_name)

		# First chapter: always accessible
		if current_idx == 0:
			return None

		previous_chapter = chapter_names[current_idx - 1]
		if not is_chapter_completed(course_name, previous_chapter, user):
			_add_blocked_message()
			return False

		return None

	except Exception:
		frappe.log_error(frappe.get_traceback(), "lms_lock_chapter: check_chapter_permission_hook error")
		return None

