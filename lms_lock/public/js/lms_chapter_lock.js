frappe.ui.form.on('LMS Course', {
    refresh: function(frm) {
        if (frm.doc.__islocal) return;
        
        // Solicita os capítulos bloqueados ao servidor e aplica restrições na interface
        setTimeout(() => {
            frappe.call({
                method: 'lms_lock.lms_overrides.get_locked_chapters',
                args: {course: frm.doc.name},
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        r.message.forEach(chapter => {
                            // Busca o item correspondente ao capítulo na sidebar/menu lateral
                            let el = $(`.sidebar-item:contains('${chapter}')`);
                            if (el.length) {
                                el.addClass('disabled').css('opacity', '0.5');
                                el.find('a').prepend('<i class="fa fa-lock mr-2"></i>');
                                
                                // Remove ouvintes de clique anteriores para evitar múltiplas execuções
                                el.find('a').off('click').on('click', function(e) {
                                    e.preventDefault();
                                    frappe.msgprint(__('Complete o capítulo anterior para desbloquear'));
                                });
                            }
                        });
                    }
                }
            });
        }, 1000);
    }
});