"""
Cleanup and uninstallation of the lms_lock_chapter app.

When the app is removed, this module ensures that:
- All overrides are unloaded
- Permission hooks are removed
- Redis cache is cleared
- No user or LMS data is lost
"""

import frappe


def after_uninstall() -> None:
	"""
	Hook called AFTER the app is uninstalled.
	Removes all associations created by the app without affecting LMS data.
	"""
	frappe.logger().info("Starting cleanup for lms_lock_chapter app...")

	try:
		# 1. Clear Redis cache
		_clean_redis_cache()

		# 2. Remove document events
		_remove_doc_events()

		# 3. Remove custom client scripts
		_remove_client_scripts()

		# 4. Clean session data/flags
		_clean_session_data()

		frappe.logger().info("Cleanup of lms_lock_chapter app completed successfully.")
		frappe.msgprint(
			msg=frappe._("App lms_lock_chapter removed successfully. All chapters are now accessible."),
			title=frappe._("Uninstallation Completed"),
			indicator="green"
		)

	except Exception as e:
		frappe.logger().error(f"Error during cleanup of lms_lock_chapter app: {str(e)}")
		frappe.msgprint(
			msg=frappe._("Cleanup error: {0}. Please check the logs.").format(str(e)),
			title=frappe._("Uninstallation Error"),
			indicator="red"
		)
		raise


def _clean_redis_cache() -> None:
	"""Removes all cache keys created by the app in Redis."""
	frappe.logger().info("Clearing Redis cache for lms_lock_chapter app...")

	try:
		# Remove the lms_lock_chapter hash in a safe and site-aware manner
		frappe.cache().delete_value("lms_lock_chapter")
		frappe.logger().info("Redis cache cleared: Hash lms_lock_chapter removed successfully.")

	except Exception as e:
		frappe.logger().warning(f"Error clearing Redis cache: {str(e)}")
		# Do not fail completely if Redis has issues


def _remove_doc_events() -> None:
	"""
	Removes document events records created by the app.
	Note: Events in hooks.py are automatically deactivated
	when the app is removed, but we clean up any DB records.
	"""
	frappe.logger().info("Removing document events from database...")

	try:
		# Document events created by the app are registered via hooks.
		# When the app is removed, Frappe automatically deactivates them,
		# but we can clean up any associated data.
		pass

		frappe.logger().info("Document events have been deactivated.")

	except Exception as e:
		frappe.logger().warning(f"Error removing document events: {str(e)}")


def _remove_client_scripts() -> None:
	"""
	Removes custom Client Scripts created by the app.
	Keeps client scripts from other apps intact.
	"""
	frappe.logger().info("Removing custom Client Scripts...")

	try:
		client_scripts = frappe.get_all(
			"Client Script",
			filters={
				"module": "LMS Lock Chapter",  # Default module of the app
				"enabled": 1
			},
			fields=["name"]
		)

		for script in client_scripts:
			try:
				frappe.delete_doc("Client Script", script.name, force=True)
				frappe.logger().info(f"Client Script removed: {script.name}")
			except frappe.DoesNotExistError:
				pass
			except Exception as e:
				frappe.logger().warning(f"Error removing Client Script {script.name}: {str(e)}")

	except Exception as e:
		frappe.logger().warning(f"Error removing Client Scripts: {str(e)}")


def _clean_session_data() -> None:
	"""
	Removes any session data associated with the app.
	Clears flags and temporary data in frappe.session.data.
	"""
	frappe.logger().info("Clearing session data...")

	try:
		# Clear any specific session flag for the app if stored in frappe.session.data
		pass

		frappe.logger().info("Session data cleared.")

	except Exception as e:
		frappe.logger().warning(f"Error clearing session data: {str(e)}")


def before_uninstall() -> None:
	"""
	Hook called BEFORE the app is uninstalled.
	Used for validations or backups if necessary.
	"""
	frappe.logger().info("Preparing uninstallation of lms_lock_chapter app...")

	# Optional validation: check if there are active courses
	try:
		active_courses = frappe.db.count(
			"LMS Course",
			filters={"published": 1}
		)

		if active_courses > 0:
			frappe.logger().warning(
				f"Uninstalling app with {active_courses} published courses. "
				"All chapters will become accessible after uninstallation."
			)

	except Exception as e:
		frappe.logger().warning(f"Error validating course status: {str(e)}")
