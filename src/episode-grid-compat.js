// SPDX-License-Identifier: MIT
/* Local Jellyfin 1.12 episode-grid compatibility for Chromium without :has(). */
(function () {
    'use strict';
    if (window.__jmpEpisodeGridCompat ||
        (window.CSS && CSS.supports('selector(:has(*))'))) return;
    window.__jmpEpisodeGridCompat = true;

    function start() {
        const style = document.createElement('style');
        style.id = 'jmp-episode-grid-compat';
        style.textContent = `
            .layout-desktop .vertical-list.jmp-episode-grid {
                display: grid !important;
                grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--minEpisodeCardWidth, 260px)), 1fr)) !important;
                gap: var(--itemColumnGap, 20px) !important;
            }
            .layout-desktop .jmp-episode-grid > .listItem-largeImage {
                min-width: 0;
            }
            .layout-desktop .jmp-episode-grid .listItemImage-large {
                position: relative;
                box-sizing: border-box;
                width: 100% !important;
                height: 0 !important;
                min-height: 0 !important;
                padding-top: 56.25% !important;
                background-size: cover;
                background-position: center;
            }
            .layout-desktop .jmp-episode-grid .listItemImage-large .listItemImageButton {
                position: absolute !important;
                top: 50% !important;
                left: 50% !important;
                right: auto !important;
                bottom: auto !important;
                margin: 0 !important;
                transform: translate(-50%, -50%) !important;
            }
        `;
        document.head.appendChild(style);
        let queued = false;
        function update() {
            queued = false;
            document.querySelectorAll('.vertical-list').forEach(function (list) {
                const episodes = Array.from(list.children).some(function (child) {
                    return child.matches('.listItem-largeImage[data-type="Episode"]');
                });
                list.classList.toggle('jmp-episode-grid', episodes);
            });
        }
        const observer = new MutationObserver(function () {
            if (!queued) {
                queued = true;
                requestAnimationFrame(update);
            }
        });
        observer.observe(document.body, {childList: true, subtree: true});
        update();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
    else start();
})();
