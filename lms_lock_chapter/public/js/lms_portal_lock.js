(function () {
	"use strict";

	var LOCK_TITLE = "🔒 " + (typeof __ === "function" ? __("Chapter Locked") : "Chapter Locked");
	var LOCK_MSG =
		typeof __ === "function"
			? __("You need to complete the previous chapter before accessing this content.")
			: "You need to complete the previous chapter before accessing this content.";

	/* ------------------------------------------------------------------
	   Displays the message using Vue/frappe-ui's native $dialog
	   Fallback: Displays a fixed HTML banner at the top
	------------------------------------------------------------------ */
	function showBlockedMessage() {
		// Prevent duplicate message from showing consecutively
		if (window._lmsLockMsgShowing) return;
		window._lmsLockMsgShowing = true;
		setTimeout(function () {
			window._lmsLockMsgShowing = false;
		}, 3000);

		// Try to use the $dialog from the Vue app (frappe-ui)
		try {
			var appEl = document.querySelector("#app");
			var vueApp = appEl && appEl.__vue_app__;
			var $dialog = vueApp && vueApp.config && vueApp.config.globalProperties.$dialog;
			if (typeof $dialog === "function") {
				$dialog({ title: LOCK_TITLE, message: LOCK_MSG });
				return;
			}
		} catch (e) {}

		// Fallback: orange HTML banner at the top
		showBanner();
	}

	function showBanner() {
		if (document.getElementById("lms-lock-banner")) return;
		var banner = document.createElement("div");
		banner.id = "lms-lock-banner";
		banner.style.cssText = [
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
		banner.textContent = LOCK_TITLE + " — " + LOCK_MSG;
		banner.addEventListener("click", function () {
			banner.remove();
		});
		document.body.insertBefore(banner, document.body.firstChild);
		setTimeout(function () {
			if (banner.parentNode) banner.remove();
		}, 6000);
	}

	/* ------------------------------------------------------------------
	   Intercepts unhandled promise rejection errors
	   Vue/frappe-ui throws an error when Course Chapter returns 403.
	   This error is not caught by the SCORMChapter.vue component.
	------------------------------------------------------------------ */
	window.addEventListener("unhandledrejection", function (event) {
		var reason = event.reason;
		if (!reason) return;

		var msg =
			typeof reason === "string" ? reason : reason.message || reason.exc || JSON.stringify(reason);

		// Checks if it is a Course Chapter PermissionError
		if (
			msg.indexOf("Course Chapter") !== -1 &&
			(msg.indexOf("PermissionError") !== -1 || msg.indexOf("permission") !== -1)
		) {
			showBlockedMessage();
			event.preventDefault(); // Suppresses the console error
		}
	});

	/* ------------------------------------------------------------------
	   Intercepts global fetch to capture _server_messages from 403 responses
	   (Executed before the Vue module script if web_include_js is active)
	------------------------------------------------------------------ */
	if (window.fetch && !window._lmsLockFetchPatched) {
		window._lmsLockFetchPatched = true;
		var _origFetch = window.fetch;
		window.fetch = function () {
			return _origFetch.apply(this, arguments).then(function (response) {
				if (response.status === 403 || response.status === 417) {
					response
						.clone()
						.json()
						.then(function (data) {
							var msgs = data._server_messages || "";
							if (
								typeof msgs === "string" &&
								(msgs.indexOf("Locked") !== -1 ||
									msgs.indexOf("previous chapter") !== -1 ||
									msgs.indexOf("Bloqueado") !== -1 ||
									msgs.indexOf("anterior") !== -1)
							) {
								showBlockedMessage();
							}
						})
						.catch(function () {});
				}
				return response;
			});
		};
	}

	/* ------------------------------------------------------------------
	   Applies visual locks on links of blocked chapters
	------------------------------------------------------------------ */
	function getCourseFromPage() {
		var m = window.location.pathname.match(/\/(?:lms\/)?courses\/([^\/]+)/);
		return m ? decodeURIComponent(m[1]) : null;
	}

	function getChapterFromUrl(url) {
		if (!url) return null;
		var match = url.match(/\/chapter\/([^/]+)/);
		return match ? decodeURIComponent(match[1]) : null;
	}

	function applyLocks(lockedChapters) {
		if (!lockedChapters || !lockedChapters.length) return;

		document.querySelectorAll("a[href], [data-chapter]").forEach(function (el) {
			var href = el.getAttribute("href") || "";
			var chAttr = el.getAttribute("data-chapter") || "";
			var targetChapter = chAttr || getChapterFromUrl(href);

			if (!targetChapter) return;

			var isLocked = lockedChapters.some(function (ch) {
				return ch === targetChapter || encodeURIComponent(ch) === targetChapter;
			});

			if (!isLocked || el.hasAttribute("data-lms-locked")) return;

			el.setAttribute("data-lms-locked", "1");
			el.style.opacity = "0.5";
			el.style.cursor = "not-allowed";
			el.style.pointerEvents = "auto";

			el.addEventListener(
				"click",
				function (e) {
					e.preventDefault();
					e.stopImmediatePropagation();
					showBlockedMessage();
				},
				true
			);
		});
	}

	function loadAndApplyLocks() {
		var course = getCourseFromPage();
		if (!course) return;

		// Uses original fetch (not patched) to prevent infinite loops
		var origFetch = window._origFetch || window.fetch;
		origFetch(
			"/api/method/lms_lock_chapter.lms_overrides.get_locked_chapters?course=" +
				encodeURIComponent(course),
			{ credentials: "same-origin" }
		)
			.then(function (r) {
				return r.json();
			})
			.then(function (d) {
				var locked = d && d.message ? d.message : [];
				if (!locked.length) return;

				// Direct access to a blocked chapter via URL
				var path = window.location.pathname;
				var directAccess = false;
				var chapterMatch = path.match(/\/chapter\/([^/]+)/);
				if (chapterMatch) {
					var currentChapter = decodeURIComponent(chapterMatch[1]);
					directAccess = locked.some(function (ch) {
						return ch === currentChapter || encodeURIComponent(ch) === currentChapter;
					});
				}

				if (directAccess) {
					showBlockedMessage();
					var base = path.replace(/\/learn\/.*$/, "").replace(/\/chapter\/.*$/, "");
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
	   Initialization
	------------------------------------------------------------------ */
	// Keeps reference to original fetch before any patches
	window._origFetch = window._origFetch || window.fetch;

	var path = window.location.pathname;
	if (path.indexOf("/lms") === -1 && path.indexOf("/courses") === -1) return;

	function checkLessonAccessOnLoad() {
		var path = window.location.pathname;
		var course = getCourseFromPage();

		// For /learn/ paths, try to get lesson name from page
		if (path.includes("/learn/") && course) {
			var lessonName = document.querySelector("[data-name][data-doctype='Course Lesson']");
			if (lessonName) {
				lessonName = lessonName.getAttribute("data-name");
				// Call API to check access
				var origFetch = window._origFetch || window.fetch;
				origFetch("/api/method/lms_lock_chapter.lms_overrides.check_lesson_access?course=" +
					encodeURIComponent(course) + "&lesson=" + encodeURIComponent(lessonName),
					{ credentials: "same-origin" }
				)
					.then(function (r) { return r.json(); })
					.then(function (d) {
						if (d.message === false) {
							showBlockedMessage();
							setTimeout(function () {
								window.location.href = "/lms/courses/" + encodeURIComponent(course);
							}, 2500);
						}
					})
					.catch(function () {});
			}
		}
	}

	function init() {
		loadAndApplyLocks();
		checkLessonAccessOnLoad();

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

