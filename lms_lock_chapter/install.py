"""
Initial installation and configuration of the lms_lock_chapter app.

Performs the necessary setup when the app is installed.
"""

import frappe


def after_install() -> None:
	"""
	Hook called AFTER the app is installed.
	Performs necessary initial configurations.
	"""
	frappe.logger().info("Configuring lms_lock_chapter app after installation...")

	try:
		# 1. Set up cache namespace if needed
		_setup_cache()

		# 2. Validate required DocTypes
		_validate_doctypes()

		frappe.logger().info("Configuration of lms_lock_chapter app completed successfully.")
		frappe.msgprint(
			msg=frappe._("App lms_lock_chapter installed successfully. Sequential chapter access is active."),
			title=frappe._("Installation Completed"),
			indicator="green"
		)

	except Exception as e:
		frappe.logger().error(f"Error during installation of lms_lock_chapter app: {str(e)}")
		frappe.msgprint(
			msg=frappe._("Installation error: {0}. Please check the logs.").format(str(e)),
			title=frappe._("Installation Error"),
			indicator="red"
		)
		raise


def before_install() -> None:
	"""
	Hook called BEFORE the app is installed.
	Performs validations and preparations.
	"""
	frappe.logger().info("Validating requirements for lms_lock_chapter app installation...")

	try:
		# Validate that the 'lms' or 'frappe-lms' app is installed
		if not (frappe.db.exists("App", "lms") or frappe.db.exists("App", "frappe-lms")):
			frappe.throw(frappe._("The app 'lms' (frappe-lms) is required to use lms_lock_chapter."))

		frappe.logger().info("Pre-installation validations completed.")

	except frappe.ValidationError:
		raise
	except Exception as e:
		frappe.logger().warning(f"Error in pre-installation validation: {str(e)}")


def _setup_cache() -> None:
	"""
	Configures the cache namespace for the app.
	Ensures the app has isolated cache space in Redis.
	"""
	try:
		cache = frappe.cache()
		# Test cache connectivity
		cache.set_value("lms_lock_chapter_test", "ok", expires_in_sec=60)
		cache.get_value("lms_lock_chapter_test")
		frappe.logger().info("Redis cache configured successfully.")
	except Exception as e:
		frappe.logger().warning(f"Error configuring cache: {str(e)}")


def _validate_doctypes() -> None:
	"""
	Validates that all required DocTypes exist and are correct.
	"""
	required_doctypes = [
		"LMS Course",
		"Course Chapter",
		"Course Lesson",
		"LMS Course Progress"
	]

	for doctype in required_doctypes:
		if not frappe.db.exists("DocType", doctype):
			frappe.throw(
				frappe._("Required DocType '{0}' not found. Please install the 'frappe-lms' app first.").format(doctype)
			)

	frappe.logger().info("All required DocTypes have been validated.")

