/* =========================================================
   BOLÃO DA COPA 2026 — JavaScript Principal
   ========================================================= */

// ── Toggle Sidebar ──────────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;

  if (window.innerWidth <= 768) {
    sidebar.classList.toggle('open');
  } else {
    document.body.classList.toggle('sidebar-collapsed');
    localStorage.setItem('sidebarCollapsed', document.body.classList.contains('sidebar-collapsed'));
  }
}

// Restaurar estado do sidebar
document.addEventListener('DOMContentLoaded', function () {
  if (localStorage.getItem('sidebarCollapsed') === 'true' && window.innerWidth > 768) {
    document.body.classList.add('sidebar-collapsed');
  }

  // Fechar sidebar mobile ao clicar fora
  document.addEventListener('click', function (e) {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.sidebar-toggle');
    if (
      window.innerWidth <= 768 &&
      sidebar &&
      sidebar.classList.contains('open') &&
      !sidebar.contains(e.target) &&
      toggle && !toggle.contains(e.target)
    ) {
      sidebar.classList.remove('open');
    }
  });

  // Auto fechar alerts após 5 segundos
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (el) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    });
  }, 5000);
});

// ── Toggle visibilidade da senha ────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const icon = btn.querySelector('i');
  if (input.type === 'password') {
    input.type = 'text';
    if (icon) { icon.classList.remove('bi-eye'); icon.classList.add('bi-eye-slash'); }
  } else {
    input.type = 'password';
    if (icon) { icon.classList.remove('bi-eye-slash'); icon.classList.add('bi-eye'); }
  }
}

// ── Confirmação com destaque ────────────────────────────────────
// (usado via onclick="return confirm()" inline — já funciona nativo)

// ── Animação de loading nos forms ──────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
      const btn = form.querySelector('button[type="submit"]');
      if (btn && !btn.dataset.noload) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aguarde...';
      }
    });
  });
});

// ── Tooltip Bootstrap ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });
});
