import frappe


def before_install() -> None:
	installed_apps = frappe.get_installed_apps()
	if not ("lms" in installed_apps or "frappe-lms" in installed_apps):
		frappe.throw("The app 'lms' or 'frappe-lms' is required to use lms_lock_chapter.")


def after_install() -> None:
	try:
		cache = frappe.cache()
		cache.set_value("lms_lock_chapter_test", "ok", expires_in_sec=60)
		cache.get_value("lms_lock_chapter_test")
	except Exception as e:
		frappe.logger().warning(f"Redis cache error: {str(e)}")

	required_doctypes = ["LMS Course", "Course Chapter", "Course Lesson", "LMS Course Progress"]
	for doctype in required_doctypes:
		if not frappe.db.exists("DocType", doctype):
			frappe.throw(f"Required DocType '{doctype}' not found.")

