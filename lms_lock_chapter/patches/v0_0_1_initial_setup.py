"""
Initial setup patch for lms_lock_chapter v0.0.1

Este patch é executado uma vez após a instalação ou upgrade para v0.0.1.
"""

import frappe


def execute():
	"""
	Executa setup inicial do app.
	Frappe chama automaticamente quando app é instalado/upgraded.
	"""
	frappe.logger().info("Executando patch inicial de setup do lms_lock_chapter...")

	try:
		# Setup inicial já é feito em install.py
		# Este patch serve como documentação e backup de inicialização
		frappe.logger().info("Patch v0.0.1 concluído com sucesso.")

	except Exception as e:
		frappe.logger().error(f"Erro no patch v0.0.1: {str(e)}")
		raise
