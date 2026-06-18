/**
 * lms_portal_lock.js — Bloqueio sequencial de capítulos e lições no portal LMS
 *
 * Compatível com ERPNext LMS 2.55+ (Vue 3 SPA)
 * Suporta capítulos SCORM (/chapter/) e lições nativas (/learn/)
 */
(function () {
	"use strict";

	// Evita dupla inicialização (web_include_js + after_request podem injetar duas vezes)
	if (window._lmsLockInitialized) return;
	window._lmsLockInitialized = true;

	// Só rodar em páginas LMS
	var _path = window.location.pathname;
	if (_path.indexOf("/lms") === -1 && _path.indexOf("/courses") === -1) return;

	/* ======================================================================
	   Mensagens i18n
	   ====================================================================== */
	var T = {
		title: typeof __ === "function" ? __("Chapter Locked") : "Capítulo Bloqueado",
		msg:
			typeof __ === "function"
				? __("You need to complete the previous chapter before accessing this content.")
				: "Você precisa completar o capítulo anterior antes de acessar este conteúdo.",
	};

	/* ======================================================================
	   Exibição da mensagem de bloqueio
	   ====================================================================== */
	function showBlockedMessage() {
		if (window._lmsLockMsgShowing) return;
		window._lmsLockMsgShowing = true;
		setTimeout(function () {
			window._lmsLockMsgShowing = false;
		}, 3500);

		// Tenta usar o $dialog do Vue/frappe-ui
		try {
			var appEl = document.querySelector("#app");
			var vueApp = appEl && appEl.__vue_app__;
			var $dialog =
				vueApp && vueApp.config && vueApp.config.globalProperties.$dialog;
			if (typeof $dialog === "function") {
				$dialog({ title: T.title, message: T.msg });
				return;
			}
		} catch (e) {}

		// Fallback: banner laranja fixo no topo
		_showBanner(T.title + " — " + T.msg);
	}

	function _showBanner(text) {
		var old = document.getElementById("lms-lock-banner");
		if (old) old.remove();

		var el = document.createElement("div");
		el.id = "lms-lock-banner";
		el.style.cssText = [
			"position:fixed",
			"top:0",
			"left:0",
			"right:0",
			"z-index:99999",
			"background:#e67e22",
			"color:#fff",
			"padding:14px 20px",
			"font-size:15px",
			"font-weight:600",
			"text-align:center",
			"box-shadow:0 2px 8px rgba(0,0,0,.3)",
			"cursor:pointer",
		].join(";");
		el.textContent = text;
		el.addEventListener("click", function () {
			el.remove();
		});
		document.body.insertBefore(el, document.body.firstChild);
		setTimeout(function () {
			if (el.parentNode) el.remove();
		}, 7000);
	}

	/* ======================================================================
	   Utilitários de URL
	   ====================================================================== */
	function getCourseSlug() {
		var m = window.location.pathname.match(/\/(?:lms\/)?courses\/([^\/]+)/);
		return m ? decodeURIComponent(m[1]) : null;
	}

	function getChapterFromPath(path) {
		var m = (path || window.location.pathname).match(/\/chapter\/([^\/]+)/);
		return m ? decodeURIComponent(m[1]) : null;
	}

	function getLessonFromPath(path) {
		// Padrão: /lms/courses/{course}/learn/{lesson-slug}
		var m = (path || window.location.pathname).match(/\/learn\/([^\/]+)/);
		return m ? decodeURIComponent(m[1]) : null;
	}

	function redirectToCourse() {
		var course = getCourseSlug();
		setTimeout(function () {
			window.location.href = course
				? "/lms/courses/" + encodeURIComponent(course)
				: "/lms";
		}, 2500);
	}

	/* ======================================================================
	   Interceptação do fetch — captura respostas 403 do Frappe
	   ====================================================================== */
	window._origFetch = window._origFetch || window.fetch;

	if (!window._lmsLockFetchPatched) {
		window._lmsLockFetchPatched = true;
		window.fetch = function () {
			return window._origFetch.apply(this, arguments).then(function (response) {
				if (response.status === 403 || response.status === 417) {
					response
						.clone()
						.json()
						.then(function (data) {
							var msgs = data._server_messages || "";
							if (typeof msgs !== "string") return;

							var isLockMsg =
								msgs.indexOf("previous chapter") !== -1 ||
								msgs.indexOf("Chapter Locked") !== -1 ||
								msgs.indexOf("Bloqueado") !== -1 ||
								msgs.indexOf("capítulo anterior") !== -1 ||
								msgs.indexOf("anterior") !== -1;

							if (isLockMsg) {
								showBlockedMessage();
								redirectToCourse();
							}
						})
						.catch(function () {});
				}
				return response;
			});
		};
	}

	/* ======================================================================
	   Interceptação de erros Vue não tratados (unhandledrejection)
	   Quando Course Chapter ou Course Lesson retornam PermissionError
	   ====================================================================== */
	window.addEventListener("unhandledrejection", function (event) {
		var reason = event.reason;
		if (!reason) return;

		var msg =
			typeof reason === "string"
				? reason
				: reason.message || reason.exc || JSON.stringify(reason);

		var isLmsDoc =
			msg.indexOf("Course Chapter") !== -1 || msg.indexOf("Course Lesson") !== -1;
		var isPermError =
			msg.indexOf("PermissionError") !== -1 ||
			msg.indexOf("permission") !== -1 ||
			msg.indexOf("403") !== -1;

		if (isLmsDoc && isPermError) {
			showBlockedMessage();
			event.preventDefault();
			redirectToCourse();
		}
	});

	/* ======================================================================
	   Estado dos bloqueios (preenchido pela API)
	   ====================================================================== */
	var _state = {
		lockedChapters: [], // nomes de capítulos bloqueados
		lockedLessons: [],  // nomes de lições dentro de capítulos bloqueados
		loaded: false,
		loading: false,
		courseSlug: null,
	};

	/* ======================================================================
	   Aplicação de locks visuais
	   ====================================================================== */
	function _lockElement(el) {
		if (el.hasAttribute("data-lms-locked")) return;
		el.setAttribute("data-lms-locked", "1");
		el.style.opacity = "0.5";
		el.style.cursor = "not-allowed";
		el.style.pointerEvents = "auto";

		// Ícone de cadeado
		if (!el.querySelector(".lms-lock-icon")) {
			var ico = document.createElement("span");
			ico.className = "lms-lock-icon";
			ico.textContent = " 🔒"; // 🔒
			ico.style.fontSize = "0.8em";
			el.appendChild(ico);
		}

		// Impede clique
		el.addEventListener(
			"click",
			function (e) {
				e.preventDefault();
				e.stopImmediatePropagation();
				showBlockedMessage();
			},
			true
		);
	}

	function _isLockedChapter(value) {
		return _state.lockedChapters.some(function (ch) {
			return (
				ch === value ||
				encodeURIComponent(ch) === value ||
				ch === decodeURIComponent(value)
			);
		});
	}

	function _isLockedLesson(value) {
		return _state.lockedLessons.some(function (l) {
			return (
				l === value ||
				encodeURIComponent(l) === value ||
				l === decodeURIComponent(value)
			);
		});
	}

	function applyVisualLocks() {
		if (!_state.loaded) return;
		if (!_state.lockedChapters.length && !_state.lockedLessons.length) return;

		// ----- Capítulos: links com /chapter/ no href ou data-chapter -----
		document.querySelectorAll("a[href], [data-chapter]").forEach(function (el) {
			var href = el.getAttribute("href") || "";
			var dataChapter = el.getAttribute("data-chapter") || "";
			var target = dataChapter || getChapterFromPath(href);
			if (target && _isLockedChapter(target)) {
				_lockElement(el);
			}
		});

		// ----- Lições: elementos com data-doctype="Course Lesson" -----
		document
			.querySelectorAll("[data-doctype='Course Lesson'][data-name]")
			.forEach(function (el) {
				var lessonName = el.getAttribute("data-name");
				if (lessonName && _isLockedLesson(lessonName)) {
					_lockElement(el);
				}
			});

		// ----- Lições: links /learn/ na barra lateral -----
		document.querySelectorAll("a[href*='/learn/']").forEach(function (el) {
			var href = el.getAttribute("href") || "";
			var slug = getLessonFromPath(href);
			if (slug && _isLockedLesson(slug)) {
				_lockElement(el);
			}
		});

		// ----- Lições: qualquer link cujo texto corresponde a uma lição bloqueada -----
		// Estratégia de fallback para sidebars sem atributos estruturados
		if (_state.lockedLessons.length) {
			document.querySelectorAll(".lesson-item a, .sidebar-item a, li a").forEach(function (el) {
				if (el.hasAttribute("data-lms-locked")) return;
				var href = el.getAttribute("href") || "";
				// Verifica se o href contém o nome de alguma lição bloqueada
				var matchLesson = _state.lockedLessons.some(function (l) {
					return (
						href.indexOf(encodeURIComponent(l)) !== -1 ||
						href.indexOf(l) !== -1
					);
				});
				if (matchLesson) _lockElement(el);
			});
		}
	}

	/* ======================================================================
	   Verificação de acesso à página atual
	   ====================================================================== */
	function checkCurrentPage() {
		if (!_state.loaded) return;

		var path = window.location.pathname;

		// Capítulo SCORM: /chapter/{name}
		var currentChapter = getChapterFromPath(path);
		if (currentChapter && _isLockedChapter(currentChapter)) {
			showBlockedMessage();
			redirectToCourse();
			return;
		}

		// Lição nativa: /learn/{slug}
		var lessonSlug = getLessonFromPath(path);
		if (lessonSlug && _isLockedLesson(lessonSlug)) {
			showBlockedMessage();
			redirectToCourse();
			return;
		}

		// Lição ativa no DOM (identifica pelo data-name na sidebar)
		var activeLessonEl =
			document.querySelector(
				".lesson-active [data-doctype='Course Lesson'][data-name], " +
				"[data-doctype='Course Lesson'][data-name].active, " +
				".is-active [data-doctype='Course Lesson'][data-name]"
			);
		if (activeLessonEl && _state.lockedLessons.length) {
			var ln = activeLessonEl.getAttribute("data-name");
			if (ln && _isLockedLesson(ln)) {
				showBlockedMessage();
				redirectToCourse();
			}
		}
	}

	/* ======================================================================
	   Carregamento dos dados de bloqueio via API
	   ====================================================================== */
	function loadLocks(forceRefresh) {
		var course = getCourseSlug();
		if (!course) return;

		// Não recarregar desnecessariamente no mesmo curso
		if (!forceRefresh && _state.loaded && _state.courseSlug === course) {
			applyVisualLocks();
			checkCurrentPage();
			return;
		}

		if (_state.loading) return;
		_state.loading = true;
		_state.courseSlug = course;

		window._origFetch(
			"/api/method/lms_lock_chapter.api.get_locked_data?course=" +
				encodeURIComponent(course),
			{ credentials: "same-origin" }
		)
			.then(function (r) {
				return r.json();
			})
			.then(function (data) {
				_state.loading = false;
				_state.loaded = true;

				var msg = data && data.message;
				_state.lockedChapters = (msg && msg.locked_chapters) || [];
				_state.lockedLessons = (msg && msg.locked_lessons) || [];

				applyVisualLocks();
				checkCurrentPage();
			})
			.catch(function () {
				_state.loading = false;
				_state.loaded = true; // Evitar loop infinito em erro de rede
			});
	}

	/* ======================================================================
	   MutationObserver — detecta renderizações do Vue após navegação SPA
	   ====================================================================== */
	function startObserver() {
		if (window._lmsPortalLockObserver) return;

		var target =
			document.querySelector(".page-content, main, #app") || document.body;

		window._lmsPortalLockObserver = new MutationObserver(function () {
			clearTimeout(window._lmsPortalLockTimer);
			window._lmsPortalLockTimer = setTimeout(function () {
				applyVisualLocks();
				checkCurrentPage();
			}, 350);
		});

		window._lmsPortalLockObserver.observe(target, {
			childList: true,
			subtree: true,
		});
	}

	/* ======================================================================
	   Interceptação da navegação SPA (Vue Router usa history.pushState)
	   ====================================================================== */
	(function patchHistory() {
		function onNavigate() {
			var newCourse = getCourseSlug();
			var changed = newCourse !== _state.courseSlug;
			if (changed) {
				// Novo curso: resetar e recarregar
				_state.loaded = false;
				_state.loading = false;
				_state.lockedChapters = [];
				_state.lockedLessons = [];
				// Limpar locks visuais do DOM anterior
				document.querySelectorAll("[data-lms-locked]").forEach(function (el) {
					el.removeAttribute("data-lms-locked");
					var ico = el.querySelector(".lms-lock-icon");
					if (ico) ico.remove();
				});
			}
			setTimeout(function () {
				loadLocks(changed);
			}, 300);
		}

		var origPush = history.pushState;
		history.pushState = function () {
			origPush.apply(history, arguments);
			onNavigate();
		};

		var origReplace = history.replaceState;
		history.replaceState = function () {
			origReplace.apply(history, arguments);
			onNavigate();
		};

		window.addEventListener("popstate", onNavigate);
	})();

	/* ======================================================================
	   Inicialização
	   ====================================================================== */
	function init() {
		loadLocks(false);
		startObserver();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
