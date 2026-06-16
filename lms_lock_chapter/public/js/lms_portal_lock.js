(function () {
    "use strict";

    var LOCK_TITLE = "🔒 Capítulo Bloqueado";
    var LOCK_MSG   = "Você precisa concluir o capítulo anterior antes de acessar este conteúdo.";

    /* ------------------------------------------------------------------
       Exibe a mensagem usando o $dialog nativo do Vue/frappe-ui
       Fallback: banner HTML fixo no topo
    ------------------------------------------------------------------ */
    function showBlockedMessage() {
        // Evita duplicar mensagem
        if (window._lmsLockMsgShowing) return;
        window._lmsLockMsgShowing = true;
        setTimeout(function () { window._lmsLockMsgShowing = false; }, 3000);

        // Tenta o $dialog do Vue app (frappe-ui)
        try {
            var appEl = document.querySelector("#app");
            var vueApp = appEl && appEl.__vue_app__;
            var $dialog = vueApp && vueApp.config && vueApp.config.globalProperties.$dialog;
            if (typeof $dialog === "function") {
                $dialog({ title: LOCK_TITLE, message: LOCK_MSG });
                return;
            }
        } catch (e) {}

        // Fallback: banner HTML laranja no topo
        showBanner();
    }

    function showBanner() {
        if (document.getElementById("lms-lock-banner")) return;
        var banner = document.createElement("div");
        banner.id = "lms-lock-banner";
        banner.style.cssText = [
            "position:fixed", "top:0", "left:0", "right:0", "z-index:99999",
            "background:#e67e22", "color:#fff", "padding:14px 20px",
            "font-size:15px", "font-weight:600", "text-align:center",
            "box-shadow:0 2px 8px rgba(0,0,0,.3)", "cursor:pointer"
        ].join(";");
        banner.textContent = LOCK_TITLE + " — " + LOCK_MSG;
        banner.addEventListener("click", function () { banner.remove(); });
        document.body.insertBefore(banner, document.body.firstChild);
        setTimeout(function () { if (banner.parentNode) banner.remove(); }, 6000);
    }

    /* ------------------------------------------------------------------
       Intercepta erros de promessa não capturados (unhandledrejection)
       O Vue/frappe-ui lança um erro quando Course Chapter retorna 403.
       Esse erro não é capturado pelo componente SCORMChapter.vue.
    ------------------------------------------------------------------ */
    window.addEventListener("unhandledrejection", function (event) {
        var reason = event.reason;
        if (!reason) return;

        var msg = (typeof reason === "string")
            ? reason
            : (reason.message || reason.exc || JSON.stringify(reason));

        // Verifica se é um PermissionError de Course Chapter
        if (msg.indexOf("Course Chapter") !== -1 &&
            (msg.indexOf("PermissionError") !== -1 || msg.indexOf("permission") !== -1)) {
            showBlockedMessage();
            event.preventDefault(); // Suprime erro no console
        }
    });

    /* ------------------------------------------------------------------
       Intercepta fetch global para capturar _server_messages da resposta 403
       (executado antes do Vue module script se web_include_js estiver ativo)
    ------------------------------------------------------------------ */
    if (window.fetch && !window._lmsLockFetchPatched) {
        window._lmsLockFetchPatched = true;
        var _origFetch = window.fetch;
        window.fetch = function () {
            return _origFetch.apply(this, arguments).then(function (response) {
                if (response.status === 403 || response.status === 417) {
                    response.clone().json().then(function (data) {
                        var msgs = data._server_messages || "";
                        if (typeof msgs === "string" &&
                            (msgs.indexOf("Bloqueado") !== -1 || msgs.indexOf("anterior") !== -1)) {
                            showBlockedMessage();
                        }
                    }).catch(function () {});
                }
                return response;
            });
        };
    }

    /* ------------------------------------------------------------------
       Aplica bloqueio visual nos links dos capítulos bloqueados
    ------------------------------------------------------------------ */
    function getCourseFromPage() {
        var m = window.location.pathname.match(/\/(?:lms\/)?courses\/([^\/]+)/);
        return m ? decodeURIComponent(m[1]) : null;
    }

    function applyLocks(lockedChapters) {
        if (!lockedChapters || !lockedChapters.length) return;

        document.querySelectorAll("a[href], [data-chapter]").forEach(function (el) {
            var href  = el.getAttribute("href") || "";
            var chAttr = el.getAttribute("data-chapter") || "";

            var isLocked = lockedChapters.some(function (ch) {
                return (chAttr && chAttr === ch) ||
                       (href && (href.indexOf(encodeURIComponent(ch)) !== -1 ||
                                 href.indexOf(ch) !== -1));
            });

            if (!isLocked || el.hasAttribute("data-lms-locked")) return;

            el.setAttribute("data-lms-locked", "1");
            el.style.opacity       = "0.5";
            el.style.cursor        = "not-allowed";
            el.style.pointerEvents = "auto";

            el.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopImmediatePropagation();
                showBlockedMessage();
            }, true);
        });
    }

    function loadAndApplyLocks() {
        var course = getCourseFromPage();
        if (!course) return;

        // Usa fetch nativo (não o patcheado) para evitar loop
        var origFetch = window._origFetch || window.fetch;
        origFetch("/api/method/lms_lock_chapter.lms_overrides.get_locked_chapters?course=" +
                  encodeURIComponent(course), { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                var locked = (d && d.message) ? d.message : [];
                if (!locked.length) return;

                // Acesso direto a capítulo bloqueado via URL
                var path = window.location.pathname;
                var directAccess = locked.some(function (ch) {
                    return path.indexOf(encodeURIComponent(ch)) !== -1 ||
                           path.indexOf(ch) !== -1;
                });

                if (directAccess) {
                    showBlockedMessage();
                    var base = path.replace(/\/learn\/.*$/, "")
                                   .replace(/\/chapter\/.*$/, "");
                    setTimeout(function () {
                        window.location.href = base || "/lms";
                    }, 2500);
                    return;
                }

                applyLocks(locked);
            })
            .catch(function () {});
    }

    /* ------------------------------------------------------------------
       Inicialização
    ------------------------------------------------------------------ */
    // Guarda referência ao fetch original antes de qualquer patch
    window._origFetch = window._origFetch || window.fetch;

    var path = window.location.pathname;
    if (path.indexOf("/lms") === -1 && path.indexOf("/courses") === -1) return;

    function init() {
        loadAndApplyLocks();

        if (!window._lmsPortalLockObserver) {
            var target = document.querySelector(".page-content, main, #app") || document.body;
            window._lmsPortalLockObserver = new MutationObserver(function () {
                clearTimeout(window._lmsPortalLockTimer);
                window._lmsPortalLockTimer = setTimeout(loadAndApplyLocks, 400);
            });
            window._lmsPortalLockObserver.observe(target, { childList: true, subtree: true });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
