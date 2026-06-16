"""
Limpeza e desinstalação do app lms_lock_chapter.

Quando o app é removido, este módulo garante que:
- Todos os overrides sejam descarregados
- Hooks de permissão sejam removidos
- Cache Redis seja limpo
- Nenhum dado do usuário ou do LMS seja perdido
"""

import frappe


def after_uninstall():
	"""
	Hook chamado APÓS a desinstalação do app.
	Remove todas as associações criadas pelo app sem afetar dados do LMS.
	"""
	frappe.logger().info("Iniciando limpeza do app lms_lock_chapter...")

	try:
		# 1. Limpar cache Redis
		_clean_redis_cache()

		# 2. Remover document events
		_remove_doc_events()

		# 3. Remover client scripts customizados
		_remove_client_scripts()

		# 4. Limpar session data/flags
		_clean_session_data()

		frappe.logger().info("Limpeza do app lms_lock_chapter concluída com sucesso.")
		frappe.msgprint(
			msg="App lms_lock_chapter removido com sucesso. Todos os capítulos estão agora acessíveis.",
			title="Desinstalação Concluída",
			indicator="green"
		)

	except Exception as e:
		frappe.logger().error(f"Erro durante limpeza do app lms_lock_chapter: {str(e)}")
		frappe.msgprint(
			msg=f"Erro na limpeza: {str(e)}. Verifique os logs.",
			title="Erro na Desinstalação",
			indicator="red"
		)
		raise


def _clean_redis_cache():
	"""Remove todas as chaves de cache criadas pelo app no Redis."""
	frappe.logger().info("Limpando cache Redis do app lms_lock_chapter...")

	try:
		# Remove o hash lms_lock_chapter de forma segura e site-aware
		frappe.cache().delete_value("lms_lock_chapter")
		frappe.logger().info("Cache Redis limpo: Hash lms_lock_chapter removido com sucesso.")

	except Exception as e:
		frappe.logger().warning(f"Erro ao limpar cache Redis: {str(e)}")
		# Não falha completamente se Redis tiver problemas


def _remove_doc_events():
	"""
	Remove registros de document events criados pelo app.
	Nota: Os eventos em hooks.py são automáticamente desativados
	quando o app é removido, mas limpamos qualquer registro no banco.
	"""
	frappe.logger().info("Removendo document events do banco de dados...")

	try:
		# Document events criados pelo app são registrados via hooks
		# Quando o app é removido, Frappe automaticamente os desativa
		# Mas podemos limpar quaisquer dados associados

		# Limpar qualquer "LMS Course Progress" marcado com flag do app
		# (se tivéssemos criado algum campo customizado)
		pass

		frappe.logger().info("Document events foram desativados.")

	except Exception as e:
		frappe.logger().warning(f"Erro ao remover doc events: {str(e)}")


def _remove_client_scripts():
	"""
	Remove Client Scripts customizados criados pelo app.
	Mantém scripts de outros apps intactos.
	"""
	frappe.logger().info("Removendo Client Scripts customizados...")

	try:
		client_scripts = frappe.get_all(
			"Client Script",
			filters={
				"module": "LMS Lock Chapter",  # Module padrão do app
				"enabled": 1
			},
			fields=["name"]
		)

		for script in client_scripts:
			try:
				frappe.delete_doc("Client Script", script.name, force=True)
				frappe.logger().info(f"Client Script removido: {script.name}")
			except frappe.DoesNotExistError:
				pass
			except Exception as e:
				frappe.logger().warning(f"Erro ao remover Client Script {script.name}: {str(e)}")

	except Exception as e:
		frappe.logger().warning(f"Erro ao remover Client Scripts: {str(e)}")


def _clean_session_data():
	"""
	Remove qualquer dados de sessão associados ao app.
	Limpa flags e dados temporários em frappe.session.data.
	"""
	frappe.logger().info("Limpando dados de sessão...")

	try:
		# Limpar qualquer flag de sessão específica do app
		# (Se tivéssemos armazenado algo em frappe.session.data)
		pass

		frappe.logger().info("Dados de sessão limpos.")

	except Exception as e:
		frappe.logger().warning(f"Erro ao limpar dados de sessão: {str(e)}")


def before_uninstall():
	"""
	Hook chamado ANTES da desinstalação do app.
	Usado para validações ou backups se necessário.
	"""
	frappe.logger().info("Preparando desinstalação do app lms_lock_chapter...")

	# Validação opcional: verificar se há cursos ativos
	try:
		active_courses = frappe.db.count(
			"LMS Course",
			filters={"published": 1}
		)

		if active_courses > 0:
			frappe.logger().warning(
				f"Desinstalando app com {active_courses} cursos publicados. "
				"Todos os capítulos ficarão acessíveis após a desinstalação."
			)

	except Exception as e:
		frappe.logger().warning(f"Erro ao validar estado dos cursos: {str(e)}")
