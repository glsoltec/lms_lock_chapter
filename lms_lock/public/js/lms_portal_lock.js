(function () {
    "use strict";

    var LOCK_MSG   = "Você precisa concluir o capítulo anterior antes de acessar este conteúdo.";
    var LOCK_TITLE = "Capítulo Bloqueado";

    /* ------------------------------------------------------------------
       Interceptor global de erros de API
       Captura qualquer resposta HTTP 417 (ValidationError do Frappe) que
       contenha nossa mensagem de bloqueio e exibe o popup corretamente,
       mesmo que o LMS portal trate o erro de forma silenciosa.
    ------------------------------------------------------------------ */
    function installErrorInterceptor() {
        // Intercepta fetch (Frappe v14+)
        if (window.fetch) {
            var _origFetch = window.fetch;
            window.fetch = function () {
                return _origFetch.apply(this, arguments).then(function (response) {
                    if (response.status === 417) {
                        response.clone().json().then(function (data) {
                            var exc = (data.exc || data.exception || data._error_message || "");
                            if (exc.indexOf("Capítulo Bloqueado") !== -1 ||
                                exc.indexOf("capitulo anterior") !== -1 ||
                                exc.indexOf("cap") !== -1 && exc.indexOf("anterior") !== -1) {
                                showBlockedMessage();
                            }
                        }).catch(function () {});
                    }
                    return response;
                });
            };
        }

        // Intercepta jQuery AJAX (Frappe web clássico)
        if (window.jQuery) {
            jQuery(document).ajaxError(function (event, jqXHR) {
                if (jqXHR.status === 417) {
                    try {
                        var data = JSON.parse(jqXHR.responseText || "{}");
                        var exc = (data.exc || data.exception || data._error_message || "");
                        if (exc.indexOf("Capítulo Bloqueado") !== -1 ||
                            exc.indexOf("capitulo anterior") !== -1) {
                            showBlockedMessage();
                        }
                    } catch (e) {}
                }
            });
        }
    }

    /* ------------------------------------------------------------------
       Exibe a mensagem de bloqueio
    ------------------------------------------------------------------ */
    function showBlockedMessage() {
        if (typeof frappe !== "undefined" && frappe.msgprint) {
            frappe.msgprint({
                title: __(LOCK_TITLE),
                message: __(LOCK_MSG),
                indicator: "orange"
            });
        } else {
            alert(LOCK_TITLE + "\n\n" + LOCK_MSG);
        }
    }

    /* ------------------------------------------------------------------
       Extrai o nome do curso da URL ou do contexto da página
    ------------------------------------------------------------------ */
    function getCourseFromPage() {
        if (window.course)                          return window.course;
        if (window.doc && window.doc.name)          return window.doc.name;

        var el = document.querySelector("[data-course]");
        if (el) return el.getAttribute("data-course");

        // /lms/courses/{course}/... ou /courses/{course}/...
        var match = window.location.pathname.match(/\/(?:lms\/)?courses\/([^\/]+)/);
        if (match) return decodeURIComponent(match[1]);

        return null;
    }

    /* ------------------------------------------------------------------
       Aplica bloqueio visual e intercepta cliques nos itens bloqueados
    ------------------------------------------------------------------ */
    function applyLocks(lockedChapters) {
        if (!lockedChapters || !lockedChapters.length) return;

        var selectors = [
            "a[href]",
            "[data-chapter]",
            ".chapter-item",
            ".lesson-item",
            ".sidebar-item",
            ".chapter-card"
        ].join(", ");

        document.querySelectorAll(selectors).forEach(function (el) {
            var chapterAttr = el.getAttribute("data-chapter") || "";
            var href        = el.getAttribute("href") || "";
            var text        = el.textContent.trim();

            var isLocked = lockedChapters.some(function (ch) {
                return (chapterAttr && chapterAttr === ch) ||
                       (href && (href.indexOf(encodeURIComponent(ch)) !== -1 || href.indexOf(ch) !== -1)) ||
                       (text && text.indexOf(ch) !== -1);
            });

            if (!isLocked || el.hasAttribute("data-lms-locked")) return;

            el.setAttribute("data-lms-locked", "1");
            el.style.opacity      = "0.5";
            el.style.cursor       = "not-allowed";
            el.style.pointerEvents = "auto";

            if (!el.querySelector(".lms-lock-icon")) {
                var icon = document.createElement("i");
                icon.className = "fa fa-lock lms-lock-icon";
                icon.style.cssText = "margin-right:6px;color:#e67e22;";
                el.insertBefore(icon, el.firstChild);
            }

            el.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopPropagation();
                showBlockedMessage();
            }, true);
        });
    }

    /* ------------------------------------------------------------------
       Verifica se a página atual é um capítulo bloqueado (acesso direto)
    ------------------------------------------------------------------ */
    function checkCurrentPageLocked(lockedChapters) {
        var p = window.location.pathname;
        return lockedChapters.some(function (ch) {
            return p.indexOf(encodeURIComponent(ch)) !== -1 || p.indexOf(ch) !== -1;
        });
    }

    /* ------------------------------------------------------------------
       Busca capítulos bloqueados e aplica proteções
    ------------------------------------------------------------------ */
    function loadAndApplyLocks() {
        var course = getCourseFromPage();
        if (!course || typeof frappe === "undefined") return;

        frappe.call({
            method: "lms_lock.lms_overrides.get_locked_chapters",
            args:   { course: course },
            callback: function (r) {
                var locked = (r && r.message) ? r.message : [];
                if (!locked.length) return;

                if (checkCurrentPageLocked(locked)) {
                    showBlockedMessage();
                    var base = window.location.pathname
                        .replace(/\/learn\/.*$/, "")
                        .replace(/\/chapter\/.*$/, "");
                    setTimeout(function () {
                        window.location.href = base || "/lms";
                    }, 2500);
                    return;
                }

                applyLocks(locked);
            }
        });
    }

    /* ------------------------------------------------------------------
       Inicialização
    ------------------------------------------------------------------ */
    // O interceptor de erros deve ser instalado o mais cedo possível
    installErrorInterceptor();

    // Só aplica o bloqueio visual em páginas LMS
    var path = window.location.pathname;
    var isLMSPage = path.indexOf("/lms") !== -1 || path.indexOf("/courses") !== -1;
    if (!isLMSPage) return;

    function init() {
        loadAndApplyLocks();

        // MutationObserver para SPAs que re-renderizam o DOM
        if (!window._lmsPortalLockObserver) {
            var target = document.querySelector(".page-content, .lms-container, main") || document.body;
            window._lmsPortalLockObserver = new MutationObserver(function () {
                clearTimeout(window._lmsPortalLockTimer);
                window._lmsPortalLockTimer = setTimeout(loadAndApplyLocks, 400);
            });
            window._lmsPortalLockObserver.observe(target, { childList: true, subtree: true });
        }
    }

    if (typeof frappe !== "undefined") {
        frappe.ready(init);
    } else {
        document.addEventListener("DOMContentLoaded", init);
    }
})();
