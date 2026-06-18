import frappe


def before_install() -> None:
	"""Verifica pré-requisitos antes de instalar o app."""
	installed = frappe.get_installed_apps()
	if "lms" not in installed and "frappe-lms" not in installed:
		frappe.throw(
			"O app 'lms' (Frappe LMS) precisa estar instalado antes do lms_lock_chapter."
		)


def after_install() -> None:
	"""Validações e log após instalação."""
	required = [
		"LMS Course",
		"Course Chapter",
		"Course Lesson",
		"LMS Course Progress",
		"Chapter Reference",
		"Lesson Reference",
	]
	missing = [dt for dt in required if not frappe.db.exists("DocType", dt)]
	if missing:
		frappe.throw(
			f"DocTypes necessários não encontrados: {', '.join(missing)}. "
			"Verifique se o app LMS está instalado e migrado corretamente."
		)

	frappe.logger().info("lms_lock_chapter instalado com sucesso.")
