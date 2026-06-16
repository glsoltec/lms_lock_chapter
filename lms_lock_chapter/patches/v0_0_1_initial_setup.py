"""
Initial setup patch for lms_lock_chapter v0.0.1.

This patch is executed once after installation or upgrade to v0.0.1.
"""

import frappe


def execute() -> None:
	"""
	Executes initial setup for the app.
	Frappe calls this automatically when the app is installed or upgraded.
	"""
	frappe.logger().info("Executing initial setup patch for lms_lock_chapter...")

	try:
		# Initial setup is already handled in install.py.
		# This patch serves as documentation and fallback initialization.
		frappe.logger().info("Patch v0.0.1 completed successfully.")

	except Exception as e:
		frappe.logger().error(f"Error in patch v0.0.1: {str(e)}")
		raise

