import frappe


def before_uninstall() -> None:
	try:
		count = frappe.db.count("LMS Course", filters={"published": 1})
		if count:
			frappe.logger().warning(
				f"lms_lock_chapter: desinstalando com {count} curso(s) publicado(s). "
				"Alunos terão acesso irrestrito após a remoção."
			)
	except Exception:
		pass


def after_uninstall() -> None:
	try:
		frappe.cache().delete_keys("lms_lock:*")
	except Exception:
		pass
	frappe.logger().info("lms_lock_chapter desinstalado.")
