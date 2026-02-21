/* ── Sidebar collapse behaviour ────────────────────────────────────
   Toggle:  click #sidebar-trigger  or  Ctrl+B / Cmd+B
   State:   stored in localStorage under 'tonewood-sidebar'
   Restore: handled by the inline <head> script in base.html (flash prevention)
   ──────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var STORAGE_KEY = 'tonewood-sidebar';
  var root        = document.documentElement;

  function toggle() {
    var next = root.dataset.sidebar === 'collapsed' ? 'expanded' : 'collapsed';
    root.dataset.sidebar = next;
    localStorage.setItem(STORAGE_KEY, next);
  }

  /* Trigger button */
  var btn = document.getElementById('sidebar-trigger');
  if (btn) btn.addEventListener('click', toggle);

  /* Keyboard shortcut: Ctrl+B / Cmd+B — matches shadcn SIDEBAR_KEYBOARD_SHORTCUT */
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault();
      toggle();
    }
  });

}());

/* ── Theme switcher ─────────────────────────────────────────────────
   Swaps data-theme on <html>. Persisted in localStorage under 'luthia-theme'.
   Flash prevention handled by inline <head> script in base.html.
   ──────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var THEME_KEY     = 'luthia-theme';
  var DEFAULT_THEME = 'amber';

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll('.theme-swatch').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.theme === theme);
    });
  }

  /* Set initial active state on swatches (theme already applied by head script) */
  var current = localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
  applyTheme(current);

  /* Swatch click handlers */
  document.querySelectorAll('.theme-swatch').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var theme = btn.dataset.theme;
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
    });
  });

}());