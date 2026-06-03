frappe.ui.form.on('LMS Course', {
    refresh: function(frm) {
        if (frm.doc.__islocal) return;
        
        // Função para aplicar o bloqueio
        const applyChapterLock = () => {
            frappe.call({
                method: 'lms_lock.lms_overrides.get_locked_chapters',
                args: { course: frm.doc.name },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        r.message.forEach(chapter => {
                            // Tenta encontrar o link do capítulo pelo atributo data-name ou pelo texto exato
                            // O ERPNext LMS v16 costuma usar classes específicas para a sidebar
                            let $items = $('.sidebar-item, .lesson-container, .chapter-item');
                            
                            $items.each(function() {
                                let $this = $(this);
                                let itemText = $this.text().trim();
                                
                                // Verifica se o texto do item corresponde ao nome do capítulo bloqueado
                                if (itemText.includes(chapter)) {
                                    $this.addClass('locked-chapter').css({
                                        'opacity': '0.5',
                                        'pointer-events': 'none',
                                        'cursor': 'not-allowed',
                                        'position': 'relative'
                                    });

                                    // Adiciona ícone de cadeado se ainda não existir
                                    if ($this.find('.fa-lock').length === 0) {
                                        $this.prepend('<i class="fa fa-lock mr-2 text-warning"></i>');
                                    }

                                    // Intercepta cliques (mesmo com pointer-events none, por segurança)
                                    $this.on('click', function(e) {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        frappe.msgprint({
                                            title: __('Capítulo Bloqueado'),
                                            message: __('Complete o capítulo anterior para desbloquear este conteúdo.'),
                                            indicator: 'orange'
                                        });
                                        return false;
                                    });
                                }
                            });
                        });
                    }
                }
            });
        };

        // Executa imediatamente e também monitora mudanças na sidebar (LMS v16 é dinâmico)
        applyChapterLock();

        // MutationObserver para garantir que o bloqueio persista se a sidebar for re-renderizada
        if (!window.lmsLockObserver) {
            const targetNode = document.querySelector('.lms-container') || document.body;
            const config = { childList: true, subtree: true };
            
            const callback = function(mutationsList, observer) {
                for(let mutation of mutationsList) {
                    if (mutation.type === 'childList') {
                        // Debounce simples para não sobrecarregar
                        clearTimeout(window.lmsLockTimer);
                        window.lmsLockTimer = setTimeout(applyChapterLock, 500);
                        break;
                    }
                }
            };

            window.lmsLockObserver = new MutationObserver(callback);
            window.lmsLockObserver.observe(targetNode, config);
        }
    }
});
