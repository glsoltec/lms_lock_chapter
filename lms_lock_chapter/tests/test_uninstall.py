import frappe
from frappe.tests.utils import FrappeTestCase


class TestLmsLockChapter(FrappeTestCase):

	def test_required_doctypes_exist(self) -> None:
		doctypes = ["LMS Course", "Course Chapter", "Course Lesson", "LMS Course Progress"]
		for doctype in doctypes:
			self.assertTrue(frappe.db.exists("DocType", doctype))

	def test_lms_app_required(self) -> None:
		installed_apps = frappe.get_installed_apps()
		self.assertTrue("lms" in installed_apps or "frappe-lms" in installed_apps)

	def test_get_locked_chapters_permission(self) -> None:
		from lms_lock_chapter.lms_overrides import get_locked_chapters
		with self.assertRaises(frappe.PermissionError):
			get_locked_chapters("Non-existent-Course")

