(function () {
    "use strict";

    // Só executa em páginas do portal LMS
    var path = window.location.pathname;
    if (path.indexOf("/lms") === -1 && path.indexOf("/courses") === -1) return;

    var LOCK_MSG = "Você precisa concluir o capítulo anterior antes de acessar este conteúdo.";
    var LOCK_TITLE = "Capítulo Bloqueado";

    /* ------------------------------------------------------------------ */
    /* Extrai o nome do curso da URL ou do contexto da página              */
    /* ------------------------------------------------------------------ */
    function getCourseFromPage() {
        // Tenta via contexto Frappe (páginas Jinja/web)
        if (window.course) return window.course;
        if (window.doc && window.doc.name) return window.doc.name;

        // Tenta extrair da URL: /lms/courses/{course}/... ou /courses/{course}/...
        var match = path.match(/\/(?:lms\/)?courses\/([^\/]+)/);
        if (match) return decodeURIComponent(match[1]);

        // Tenta via elemento data-course no DOM
        var el = document.querySelector("[data-course]");
        if (el) return el.getAttribute("data-course");

        return null;
    }

    /* ------------------------------------------------------------------ */
    /* Mostra a mensagem de bloqueio                                        */
    /* ------------------------------------------------------------------ */
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

    /* ------------------------------------------------------------------ */
    /* Aplica bloqueio visual e intercepta cliques                         */
    /* ------------------------------------------------------------------ */
    function applyLocks(lockedChapters) {
        if (!lockedChapters || !lockedChapters.length) return;

        // Seleciona links e itens de capítulo/aula no portal
        var selectors = [
            "a[href]",
            "[data-chapter]",
            ".chapter-item",
            ".lesson-item",
            ".sidebar-item",
            ".chapter-card"
        ].join(", ");

        var items = document.querySelectorAll(selectors);

        items.forEach(function (el) {
            var chapterName = el.getAttribute("data-chapter") || "";
            var href = el.getAttribute("href") || "";
            var text = el.textContent.trim();

            var isLocked = lockedChapters.some(function (ch) {
                return (
                    (chapterName && chapterName === ch) ||
                    (href && href.indexOf(encodeURIComponent(ch)) !== -1) ||
                    (href && href.indexOf(ch) !== -1) ||
                    (text && text.indexOf(ch) !== -1)
                );
            });

            if (!isLocked || el.hasAttribute("data-lms-locked")) return;

            el.setAttribute("data-lms-locked", "1");
            el.style.opacity = "0.5";
            el.style.cursor = "not-allowed";
            el.style.pointerEvents = "none";

            // Adiciona ícone de cadeado se ainda não tiver
            if (!el.querySelector(".lms-lock-icon")) {
                var icon = document.createElement("i");
                icon.className = "fa fa-lock lms-lock-icon";
                icon.style.marginRight = "6px";
                icon.style.color = "#e67e22";
                el.insertBefore(icon, el.firstChild);
            }

            // Reativa pointer-events só para interceptar o clique e mostrar mensagem
            el.style.pointerEvents = "auto";
            el.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopPropagation();
                showBlockedMessage();
                return false;
            }, true);
        });
    }

    /* ------------------------------------------------------------------ */
    /* Verifica se a página atual é um capítulo bloqueado (acesso direto)  */
    /* ------------------------------------------------------------------ */
    function checkCurrentPageIsLocked(lockedChapters) {
        if (!lockedChapters || !lockedChapters.length) return false;
        return lockedChapters.some(function (ch) {
            return (
                path.indexOf(encodeURIComponent(ch)) !== -1 ||
                path.indexOf(ch) !== -1
            );
        });
    }

    /* ------------------------------------------------------------------ */
    /* Inicialização principal                                              */
    /* ------------------------------------------------------------------ */
    function init() {
        var course = getCourseFromPage();
        if (!course) return;

        frappe.call({
            method: "lms_lock.lms_overrides.get_locked_chapters",
            args: { course: course },
            callback: function (r) {
                var locked = (r && r.message) ? r.message : [];
                if (!locked.length) return;

                // Se a página atual é um capítulo bloqueado, mostra mensagem
                if (checkCurrentPageIsLocked(locked)) {
                    showBlockedMessage();
                    // Redireciona para a página do curso após 2.5s
                    setTimeout(function () {
                        var base = path.replace(/\/learn\/.*$/, "").replace(/\/chapter\/.*$/, "");
                        window.location.href = base || "/lms";
                    }, 2500);
                    return;
                }

                applyLocks(locked);
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /* Garante execução após o DOM estar pronto                            */
    /* ------------------------------------------------------------------ */
    if (typeof frappe !== "undefined") {
        frappe.ready(function () {
            init();

            // MutationObserver para SPAs que re-renderizam a sidebar
            if (!window._lmsPortalLockObserver) {
                var target = document.querySelector(".page-content, .lms-container, main") || document.body;
                window._lmsPortalLockObserver = new MutationObserver(function () {
                    clearTimeout(window._lmsPortalLockTimer);
                    window._lmsPortalLockTimer = setTimeout(function () {
                        var course = getCourseFromPage();
                        if (!course) return;
                        frappe.call({
                            method: "lms_lock.lms_overrides.get_locked_chapters",
                            args: { course: course },
                            callback: function (r) {
                                applyLocks((r && r.message) ? r.message : []);
                            }
                        });
                    }, 400);
                });
                window._lmsPortalLockObserver.observe(target, { childList: true, subtree: true });
            }
        });
    } else {
        // Fallback sem Frappe (carregamento mais antigo)
        document.addEventListener("DOMContentLoaded", init);
    }
})();
