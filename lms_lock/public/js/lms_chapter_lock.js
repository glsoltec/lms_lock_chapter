frappe.ui.form.on('LMS Course', {
    refresh: function(frm) {
        if (frm.doc.__islocal) return;

        const applyChapterLock = () => {
            frappe.call({
                method: 'lms_lock.lms_overrides.get_locked_chapters',
                args: { course: frm.doc.name },
                callback: function(r) {
                    const locked = r.message || [];
                    if (!locked.length) return;

                    // Seleciona qualquer elemento que represente um capítulo na sidebar/conteúdo
                    const selectors = [
                        '[data-chapter]',
                        '.sidebar-item',
                        '.chapter-item',
                        '.lesson-container',
                        '.chapter-container'
                    ].join(', ');

                    $(selectors).each(function() {
                        const $el = $(this);

                        // Verifica pelo atributo data-chapter ou pelo texto do elemento
                        const dataChapter = $el.data('chapter') || $el.attr('data-chapter') || '';
                        const textContent = $el.text().trim();

                        const isLocked = locked.some(ch =>
                            (dataChapter && dataChapter === ch) || textContent.includes(ch)
                        );

                        if (!isLocked) return;

                        // Evita aplicar duas vezes
                        if ($el.hasClass('lms-locked-chapter')) return;

                        $el.addClass('lms-locked-chapter').css({
                            opacity: '0.5',
                            pointerEvents: 'none',
                            cursor: 'not-allowed'
                        });

                        if (!$el.find('.lms-lock-icon').length) {
                            $el.prepend('<i class="fa fa-lock mr-2 text-warning lms-lock-icon"></i>');
                        }

                        $el.on('click.lmslock', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            frappe.msgprint({
                                title: __('Capítulo Bloqueado'),
                                message: __('Complete o capítulo anterior para desbloquear este conteúdo.'),
                                indicator: 'orange'
                            });
                            return false;
                        });
                    });
                }
            });
        };

        applyChapterLock();

        // Re-aplica quando o DOM for modificado (LMS v16 é uma SPA)
        if (!window._lmsLockObserver) {
            const target = document.querySelector('.lms-container, .layout-main') || document.body;
            window._lmsLockObserver = new MutationObserver(() => {
                clearTimeout(window._lmsLockTimer);
                window._lmsLockTimer = setTimeout(applyChapterLock, 400);
            });
            window._lmsLockObserver.observe(target, { childList: true, subtree: true });
        }
    }
});
