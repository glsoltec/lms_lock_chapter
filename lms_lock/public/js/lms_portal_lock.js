(function () {
    "use strict";

    var LOCK_MSG   = "Você precisa concluir o capítulo anterior antes de acessar este conteúdo.";
    var LOCK_TITLE = "Capítulo Bloqueado";

    /* ------------------------------------------------------------------
       Exibe mensagem de bloqueio
       Tenta frappe.msgprint primeiro; cai em banner HTML se não disponível
    ------------------------------------------------------------------ */
    function showBlockedMessage() {
        // Evita duplicar mensagem
        if (document.getElementById("lms-lock-banner")) return;

        // Tenta frappe.msgprint (Frappe desk/portal)
        if (typeof frappe !== "undefined" && frappe.msgprint) {
            frappe.msgprint({
                title: LOCK_TITLE,
                message: LOCK_MSG,
                indicator: "orange"
            });
            return;
        }

        // Fallback: banner HTML visível no topo da página
        var banner = document.createElement("div");
        banner.id = "lms-lock-banner";
        banner.style.cssText = [
            "position:fixed", "top:0", "left:0", "right:0", "z-index:99999",
            "background:#e67e22", "color:#fff", "padding:14px 20px",
            "font-size:15px", "font-weight:600", "text-align:center",
            "box-shadow:0 2px 8px rgba(0,0,0,0.3)", "cursor:pointer"
        ].join(";");
        banner.innerHTML = "🔒 <strong>" + LOCK_TITLE + "</strong> — " + LOCK_MSG + " &nbsp;✕";
        banner.addEventListener("click", function () { banner.remove(); });
        document.body.insertBefore(banner, document.body.firstChild);
        setTimeout(function () { if (banner.parentNode) banner.remove(); }, 6000);
    }

    /* ------------------------------------------------------------------
       Intercepta fetch global — captura 403 e _server_messages
    ------------------------------------------------------------------ */
    function installFetchInterceptor() {
        if (!window.fetch || window._lmsLockFetchPatched) return;
        window._lmsLockFetchPatched = true;

        var _origFetch = window.fetch;
        window.fetch = function (input, init) {
            return _origFetch.apply(this, arguments).then(function (response) {
                var status = response.status;
                if (status === 403 || status === 417) {
                    response.clone().json().then(function (data) {
                        // Verifica _server_messages (frappe.msgprint registra aqui)
                        var msgs = data._server_messages || "";
                        if (typeof msgs === "string" && msgs.length) {
                            try {
                                var parsed = JSON.parse(msgs);
                                var arr = Array.isArray(parsed) ? parsed : [parsed];
                                arr.forEach(function (m) {
                                    var obj = (typeof m === "string") ? JSON.parse(m) : m;
                                    var title = obj.title || obj.message || "";
                                    if (title.indexOf("Bloqueado") !== -1 ||
                                        title.indexOf("anterior") !== -1 ||
                                        (obj.message || "").indexOf("anterior") !== -1) {
                                        showBlockedMessage();
                                    }
                                });
                            } catch (e) {}
                        }
                        // Fallback: verifica exception/exc
                        var exc = data.exc || data.exception || data._error_message || "";
                        if (typeof exc === "string" &&
                            (exc.indexOf("Bloqueado") !== -1 || exc.indexOf("anterior") !== -1)) {
                            showBlockedMessage();
                        }
                    }).catch(function () {});
                }
                return response;
            });
        };
    }

    /* ------------------------------------------------------------------
       Intercepta jQuery AJAX (fallback para chamadas legadas)
    ------------------------------------------------------------------ */
    function installJQueryInterceptor() {
        if (!window.jQuery) return;
        jQuery(document).ajaxComplete(function (event, xhr, settings) {
            var status = xhr.status;
            if (status !== 403 && status !== 417) return;
            try {
                var data = JSON.parse(xhr.responseText || "{}");
                var msgs = data._server_messages || "";
                if (typeof msgs === "string" && msgs.indexOf("Bloqueado") !== -1) {
                    showBlockedMessage();
                    return;
                }
                var exc = data.exc || data.exception || "";
                if (typeof exc === "string" &&
                    (exc.indexOf("Bloqueado") !== -1 || exc.indexOf("anterior") !== -1)) {
                    showBlockedMessage();
                }
            } catch (e) {}
        });
    }

    /* ------------------------------------------------------------------
       Detecta o nome do curso na URL ou contexto da página
    ------------------------------------------------------------------ */
    function getCourseFromPage() {
        // Contexto Frappe/LMS injetado na página
        if (window.course)                 return window.course;
        if (window.doc && window.doc.name) return window.doc.name;

        var el = document.querySelector("[data-course]");
        if (el) return el.getAttribute("data-course");

        // URLs: /lms/courses/{course}/... ou /courses/{course}/...
        var m = window.location.pathname.match(/\/(?:lms\/)?courses\/([^\/]+)/);
        if (m) return decodeURIComponent(m[1]);

        return null;
    }

    /* ------------------------------------------------------------------
       Aplica bloqueio visual e intercepta cliques
    ------------------------------------------------------------------ */
    function applyLocks(lockedChapters) {
        if (!lockedChapters || !lockedChapters.length) return;

        // Seletores comuns do LMS v16 portal
        var selectors = [
            "a[href]",
            "[data-chapter]",
            ".chapter-item a",
            ".chapter-item",
            ".lesson-item a",
            ".lesson-item",
            ".sidebar-item",
            ".chapter-card",
            ".chapter-link",
            ".lms-chapter"
        ].join(", ");

        document.querySelectorAll(selectors).forEach(function (el) {
            var chAttr = el.getAttribute("data-chapter") || "";
            var href   = (el.getAttribute("href") || el.getAttribute("data-href") || "");
            var text   = el.textContent.trim();

            var isLocked = lockedChapters.some(function (ch) {
                return (chAttr && chAttr === ch) ||
                       (href && (href.indexOf(encodeURIComponent(ch)) !== -1 ||
                                 href.indexOf(ch) !== -1)) ||
                       (text && text === ch);
            });

            if (!isLocked || el.hasAttribute("data-lms-locked")) return;

            el.setAttribute("data-lms-locked", "1");
            el.style.opacity       = "0.5";
            el.style.cursor        = "not-allowed";
            el.style.pointerEvents = "auto";

            // Ícone de cadeado
            if (!el.querySelector(".lms-lock-icon")) {
                var icon = document.createElement("i");
                icon.className = "fa fa-lock lms-lock-icon";
                icon.style.cssText = "margin-right:6px;color:#e67e22;";
                el.insertBefore(icon, el.firstChild);
            }

            // Clique: bloqueia navegação e mostra mensagem
            el.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopImmediatePropagation();
                showBlockedMessage();
            }, true);
        });
    }

    /* ------------------------------------------------------------------
       Verifica se a URL atual corresponde a um capítulo bloqueado
    ------------------------------------------------------------------ */
    function checkCurrentPageLocked(lockedChapters) {
        var p = window.location.pathname;
        return lockedChapters.some(function (ch) {
            return p.indexOf(encodeURIComponent(ch)) !== -1 || p.indexOf(ch) !== -1;
        });
    }

    /* ------------------------------------------------------------------
       Busca capítulos bloqueados via API e aplica proteções
    ------------------------------------------------------------------ */
    function loadAndApplyLocks() {
        var course = getCourseFromPage();
        if (!course) return;

        // Usa fetch direto (sem interceptor — evita loop)
        var url = "/api/method/lms_lock.lms_overrides.get_locked_chapters"
                + "?course=" + encodeURIComponent(course);

        var doApply = function (locked) {
            if (!locked || !locked.length) return;

            if (checkCurrentPageLocked(locked)) {
                showBlockedMessage();
                // Redireciona para a página do curso após 2,5 s
                var base = window.location.pathname
                    .replace(/\/learn\/.*$/, "")
                    .replace(/\/chapter\/.*$/, "");
                setTimeout(function () {
                    window.location.href = base || "/lms";
                }, 2500);
                return;
            }

            applyLocks(locked);
        };

        // Prefere frappe.call se disponível (já tem CSRF)
        if (typeof frappe !== "undefined" && frappe.call) {
            frappe.call({
                method: "lms_lock.lms_overrides.get_locked_chapters",
                args:   { course: course },
                callback: function (r) { doApply((r && r.message) ? r.message : []); }
            });
        } else {
            // Fallback puro fetch
            fetch(url, { credentials: "same-origin" })
                .then(function (r) { return r.json(); })
                .then(function (d) { doApply((d && d.message) ? d.message : []); })
                .catch(function () {});
        }
    }

    /* ------------------------------------------------------------------
       Inicialização
    ------------------------------------------------------------------ */
    installFetchInterceptor();
    installJQueryInterceptor();

    var path = window.location.pathname;
    var isLMSPage = path.indexOf("/lms") !== -1 || path.indexOf("/courses") !== -1;
    if (!isLMSPage) return;

    function init() {
        loadAndApplyLocks();

        // MutationObserver para SPAs que re-renderizam o DOM
        if (!window._lmsPortalLockObserver) {
            var target = document.querySelector(
                ".page-content, .lms-container, .course-details, main"
            ) || document.body;

            window._lmsPortalLockObserver = new MutationObserver(function () {
                clearTimeout(window._lmsPortalLockTimer);
                window._lmsPortalLockTimer = setTimeout(loadAndApplyLocks, 400);
            });
            window._lmsPortalLockObserver.observe(target, { childList: true, subtree: true });
        }
    }

    if (typeof frappe !== "undefined" && frappe.ready) {
        frappe.ready(init);
    } else {
        document.addEventListener("DOMContentLoaded", init);
    }
})();
