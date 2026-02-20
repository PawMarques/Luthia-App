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
