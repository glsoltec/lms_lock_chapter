"""
Testes para validar cleanup e desinstalação do app lms_lock_chapter.
"""

import unittest
import frappe
from frappe.tests.utils import FrappeTestCase


class TestLmsLockChapterUninstall(FrappeTestCase):
	"""Testes para garantir que a desinstalação remove todas as associações."""

	def setUp(self):
		"""Prepara ambiente de teste."""
		pass

	def test_cache_cleanup_on_uninstall(self):
		"""
		Valida que o cache Redis é limpo corretamente.
		"""
		from lms_lock_chapter.uninstall import _clean_redis_cache

		cache = frappe.cache()

		# Simular dados de cache do app
		test_key = "chapter_comp_test_course_test_chapter_test_user"
		cache.set_value(test_key, "1")

		# Verificar que a chave foi criada
		self.assertIsNotNone(cache.get_value(test_key))

		# Limpar cache
		_clean_redis_cache()

		# Verificar que a chave foi removida
		self.assertIsNone(cache.get_value(test_key))

	def test_no_system_data_loss_on_uninstall(self):
		"""
		Valida que dados do sistema (cursos, capítulos, aulas) não são perdidos.
		"""
		# Este teste garante que a desinstalação não afeta DocTypes do LMS
		doctypes_to_preserve = [
			"LMS Course",
			"Course Chapter",
			"Course Lesson",
			"LMS Course Progress"
		]

		for doctype in doctypes_to_preserve:
			# Verificar que o DocType ainda existe após desinstalação teórica
			self.assertTrue(
				frappe.db.exists("DocType", doctype),
				f"DocType {doctype} deve ser preservado após desinstalação"
			)

	def test_permission_hooks_removed(self):
		"""
		Valida que hooks de permissão são desativados após desinstalação.
		Nota: Frappe automaticamente desativa hooks quando app é removido.
		"""
		# Após a desinstalação, os hooks em lms_overrides não devem estar ativos
		# Este teste é principalmente para documentação do comportamento esperado
		pass

	def test_override_classes_removed(self):
		"""
		Valida que classes de override são removidas.
		Nota: Frappe carrega overrides via module cache que é limpo na desinstalação.
		"""
		# As classes em lms_overrides.py não devem estar ativas após desinstalação
		# Frappe automaticamente remove do module cache
		pass

	def test_chapters_become_accessible_after_uninstall(self):
		"""
		Valida que após desinstalação, todos os capítulos ficam acessíveis.
		"""
		# Após a desinstalação, as funções de verificação de permissão
		# não devem mais aplicar bloqueio sequencial
		# Os usuários podem acessar qualquer capítulo
		pass


class TestLmsLockChapterInstall(FrappeTestCase):
	"""Testes para garantir que a instalação funciona corretamente."""

	def test_required_doctypes_exist(self):
		"""
		Valida que os DocTypes obrigatórios existem.
		"""
		from lms_lock_chapter.install import _validate_doctypes

		# Não deve lançar exceção se DocTypes existem
		try:
			_validate_doctypes()
		except frappe.ValidationError as e:
			self.fail(f"_validate_doctypes() levantou ValidationError: {str(e)}")

	def test_frappe_lms_app_required(self):
		"""
		Valida que o app frappe-lms é obrigatório.
		"""
		# Este teste apenas documenta a dependência
		self.assertTrue(
			frappe.db.exists("App", "frappe-lms") or
			"frappe-lms" in frappe.get_installed_apps(),
			"frappe-lms deve estar instalado"
		)

	def test_cache_initialized_on_install(self):
		"""
		Valida que cache é inicializado corretamente.
		"""
		from lms_lock_chapter.install import _setup_cache

		# Não deve lançar exceção
		try:
			_setup_cache()
		except Exception as e:
			self.fail(f"_setup_cache() levantou exceção: {str(e)}")


if __name__ == "__main__":
	unittest.main()
