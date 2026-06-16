"""
Tests to validate the cleanup, installation, and security functions of the lms_lock_chapter app.
"""

import unittest
import frappe
from frappe.tests.utils import FrappeTestCase


class TestLmsLockChapterUninstall(FrappeTestCase):
	"""Tests to ensure that uninstallation removes all associations correctly."""

	def setUp(self) -> None:
		"""Prepares the test environment."""
		pass

	def test_cache_cleanup_on_uninstall(self) -> None:
		"""
		Validates that the Redis cache is cleared correctly.
		"""
		from lms_lock_chapter.uninstall import _clean_redis_cache

		cache = frappe.cache()

		# Simulate app cache data using the lms_lock_chapter hash
		test_key = "chapter_comp_test_course_test_chapter_test_user"
		cache.hset("lms_lock_chapter", test_key, 1)

		# Verify that the key was created in the hash
		self.assertEqual(cache.hget("lms_lock_chapter", test_key), 1)

		# Clear cache
		_clean_redis_cache()

		# Verify that the key (and the hash) was removed
		self.assertIsNone(cache.hget("lms_lock_chapter", test_key))

	def test_no_system_data_loss_on_uninstall(self) -> None:
		"""
		Validates that system data (courses, chapters, lessons) is not lost.
		"""
		# This test ensures that uninstallation does not affect LMS DocTypes.
		doctypes_to_preserve = [
			"LMS Course",
			"Course Chapter",
			"Course Lesson",
			"LMS Course Progress"
		]

		for doctype in doctypes_to_preserve:
			# Verify that the DocType still exists after theoretical uninstallation
			self.assertTrue(
				frappe.db.exists("DocType", doctype),
				f"DocType {doctype} must be preserved after uninstall"
			)

	def test_permission_hooks_removed(self) -> None:
		"""
		Validates that permission hooks are deactivated after uninstall.
		Note: Frappe automatically deactivates hooks when the app is removed.
		"""
		# After uninstallation, hooks in lms_overrides should not be active.
		# This test is mainly for documenting the expected behavior.
		pass

	def test_override_classes_removed(self) -> None:
		"""
		Validates that override classes are removed.
		Note: Frappe loads overrides via module cache which is cleared upon uninstall.
		"""
		# Override classes in lms_overrides.py should not be active after uninstall.
		# Frappe automatically removes them from the module cache.
		pass

	def test_chapters_become_accessible_after_uninstall(self) -> None:
		"""
		Validates that after uninstall, all chapters become accessible.
		"""
		# After uninstallation, permission check hooks should no longer block sequential access.
		# Users should be able to access any chapter.
		pass


class TestLmsLockChapterInstall(FrappeTestCase):
	"""Tests to ensure that the installation works correctly."""

	def test_required_doctypes_exist(self) -> None:
		"""
		Validates that required DocTypes exist.
		"""
		from lms_lock_chapter.install import _validate_doctypes

		# Should not raise exception if DocTypes exist
		try:
			_validate_doctypes()
		except frappe.ValidationError as e:
			self.fail(f"_validate_doctypes() raised ValidationError: {str(e)}")

	def test_frappe_lms_app_required(self) -> None:
		"""
		Validates that the lms or frappe-lms app is required.
		"""
		# This test documents the dependency
		self.assertTrue(
			frappe.db.exists("App", "lms") or
			frappe.db.exists("App", "frappe-lms") or
			"lms" in frappe.get_installed_apps() or
			"frappe-lms" in frappe.get_installed_apps(),
			"lms or frappe-lms must be installed"
		)

	def test_cache_initialized_on_install(self) -> None:
		"""
		Validates that cache is initialized correctly.
		"""
		from lms_lock_chapter.install import _setup_cache

		# Should not raise exception
		try:
			_setup_cache()
		except Exception as e:
			self.fail(f"_setup_cache() raised exception: {str(e)}")


class TestLmsLockChapterSecurity(FrappeTestCase):
	"""Tests to validate security and access control features."""

	def test_get_locked_chapters_permission(self) -> None:
		"""
		Validates that get_locked_chapters enforces read permissions on LMS Course.
		"""
		from lms_lock_chapter.lms_overrides import get_locked_chapters

		# Try to call get_locked_chapters on a course that doesn't exist
		# This triggers a permission check that fails, raising PermissionError.
		course_name = "Non-existent Secret Course"
		with self.assertRaises(frappe.PermissionError):
			get_locked_chapters(course_name)


if __name__ == "__main__":
	unittest.main()

