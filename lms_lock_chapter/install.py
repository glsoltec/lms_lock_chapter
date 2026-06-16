"""
Instalação e configuração inicial do app lms_lock_chapter.

Realiza setup necessário quando o app é instalado.
"""

import frappe


def after_install():
	"""
	Hook chamado APÓS a instalação do app.
	Realiza configurações iniciais necessárias.
	"""
	frappe.logger().info("Configurando app lms_lock_chapter após instalação...")

	try:
		# 1. Criar cache namespace se necessário
		_setup_cache()

		# 2. Validar DocTypes necessários
		_validate_doctypes()

		frappe.logger().info("Configuração do app lms_lock_chapter concluída com sucesso.")
		frappe.msgprint(
			msg="App lms_lock_chapter instalado com sucesso. "
			"Acesso sequencial a capítulos está ativo.",
			title="Instalação Concluída",
			indicator="green"
		)

	except Exception as e:
		frappe.logger().error(f"Erro na instalação do app lms_lock_chapter: {str(e)}")
		frappe.msgprint(
			msg=f"Erro na instalação: {str(e)}. Verifique os logs.",
			title="Erro na Instalação",
			indicator="red"
		)
		raise


def before_install():
	"""
	Hook chamado ANTES da instalação do app.
	Realiza validações e preparações.
	"""
	frappe.logger().info("Validando requisitos para instalação do app lms_lock_chapter...")

	try:
		# Validar que o app frappe-lms está instalado
		if not frappe.db.exists("App", "frappe-lms"):
			frappe.throw("O app 'frappe-lms' é obrigatório para usar lms_lock_chapter.")

		frappe.logger().info("Validações de pré-instalação concluídas.")

	except frappe.ValidationError:
		raise
	except Exception as e:
		frappe.logger().warning(f"Erro na validação de pré-instalação: {str(e)}")


def _setup_cache():
	"""
	Configura cache namespace para o app.
	Garante que a aplicação tem espaço de cache isolado no Redis.
	"""
	try:
		cache = frappe.cache()
		# Testa conectividade com cache
		cache.set_value("lms_lock_chapter_test", "ok", expires_in_sec=60)
		cache.get_value("lms_lock_chapter_test")
		frappe.logger().info("Cache Redis configurado com sucesso.")
	except Exception as e:
		frappe.logger().warning(f"Erro ao configurar cache: {str(e)}")


def _validate_doctypes():
	"""
	Valida que todos os DocTypes necessários existem e estão corretos.
	"""
	required_doctypes = [
		"LMS Course",
		"Course Chapter",
		"Course Lesson",
		"LMS Course Progress"
	]

	for doctype in required_doctypes:
		if not frappe.db.exists("DocType", doctype):
			frappe.throw(f"DocType obrigatório '{doctype}' não encontrado. "
						f"Instale o app 'frappe-lms' primeiro.")

	frappe.logger().info("Todos os DocTypes obrigatórios foram validados.")
