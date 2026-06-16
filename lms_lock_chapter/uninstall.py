import frappe


def before_uninstall() -> None:
	try:
		active_courses = frappe.db.count("LMS Course", filters={"published": 1})
		if active_courses > 0:
			frappe.logger().warning(f"Uninstalling with {active_courses} published courses.")
	except Exception:
		pass


def after_uninstall() -> None:
	try:
		frappe.cache().delete_value("lms_lock_chapter")

		client_scripts = frappe.get_all(
			"Client Script",
			filters={"module": "LMS Lock Chapter", "enabled": 1},
			fields=["name"]
		)
		for script in client_scripts:
			try:
				frappe.delete_doc("Client Script", script.name, force=True)
			except Exception:
				pass
	except Exception as e:
		frappe.logger().warning(f"Cleanup error: {str(e)}")
