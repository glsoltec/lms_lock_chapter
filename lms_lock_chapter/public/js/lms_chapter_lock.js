/**
 * lms_chapter_lock.js — JS do Desk para o formulário LMS Course
 * Exibe indicadores de bloqueio na visualização administrativa do curso.
 */
frappe.ui.form.on("LMS Course", {
	refresh: function (frm) {
		if (frm.doc.__islocal) return;

		frappe.call({
			method: "lms_lock_chapter.api.get_locked_chapters",
			args: { course: frm.doc.name },
			callback: function (r) {
				var locked = r.message || [];
				if (!locked.length) return;

				var selectors = [
					"[data-chapter]",
					".sidebar-item",
					".chapter-item",
					".lesson-container",
					".chapter-container",
				].join(", ");

				$(selectors).each(function () {
					var $el = $(this);
					var dataChapter = $el.data("chapter") || $el.attr("data-chapter") || "";
					var href = $el.attr("href") || "";
					var chapterFromUrl = "";
					var m = href.match(/\/chapter\/([^/]+)/);
					if (m) chapterFromUrl = decodeURIComponent(m[1]);

					var target = dataChapter || chapterFromUrl;
					var isLocked = locked.some(
						(ch) => target && (ch === target || encodeURIComponent(ch) === target)
					);

					if (!isLocked || $el.hasClass("lms-locked-chapter")) return;

					$el.addClass("lms-locked-chapter").css({
						opacity: "0.5",
						pointerEvents: "none",
						cursor: "not-allowed",
					});

					if (!$el.find(".lms-lock-icon").length) {
						$el.prepend('<i class="fa fa-lock mr-1 text-warning lms-lock-icon"></i>');
					}
				});
			},
		});
	},
});
