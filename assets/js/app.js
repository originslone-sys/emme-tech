/**
 * EMME Tech — WhatsApp AI Agent Manager
 * Main JS — lightweight, no dependencies
 */

(function () {
  'use strict';

  // ----------------------------------------------------------------
  // Auto-dismiss alerts
  // ----------------------------------------------------------------
  document.querySelectorAll('.alert').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity .5s';
      el.style.opacity    = '0';
      setTimeout(function () { el.remove(); }, 500);
    }, 5000);
  });

  // ----------------------------------------------------------------
  // Confirm delete buttons (extra safety)
  // ----------------------------------------------------------------
  document.querySelectorAll('form[onsubmit]').forEach(function (form) {
    // Already handled by inline onsubmit — just ensure they work
  });

  // ----------------------------------------------------------------
  // Auto-generate slug from name
  // ----------------------------------------------------------------
  var nameInput = document.querySelector('input[name="name"]');
  var slugInput = document.querySelector('input[name="slug"]');

  if (nameInput && slugInput && !slugInput.value) {
    nameInput.addEventListener('input', function () {
      slugInput.value = nameInput.value
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
    });
  }

  // ----------------------------------------------------------------
  // Mobile sidebar toggle
  // ----------------------------------------------------------------
  var sidebar = document.querySelector('.sidebar');
  var toggleBtn = document.createElement('button');
  toggleBtn.textContent = '☰';
  toggleBtn.style.cssText = [
    'position:fixed', 'top:12px', 'left:12px', 'z-index:200',
    'background:#111827', 'color:#fff', 'border:none',
    'padding:8px 12px', 'border-radius:6px', 'font-size:18px',
    'cursor:pointer', 'display:none',
  ].join(';');

  if (sidebar) {
    document.body.appendChild(toggleBtn);
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
  }

  function checkMobile() {
    if (window.innerWidth <= 768) {
      toggleBtn.style.display = 'block';
    } else {
      toggleBtn.style.display = 'none';
      if (sidebar) sidebar.classList.remove('open');
    }
  }

  window.addEventListener('resize', checkMobile);
  checkMobile();

  // ----------------------------------------------------------------
  // Schedule helper: show cron expression description
  // ----------------------------------------------------------------
  var scheduleInput = document.querySelector('input[name="schedule"]');
  if (scheduleInput) {
    var hint = document.createElement('small');
    hint.style.color = '#6b7280';
    hint.style.display = 'block';
    scheduleInput.parentNode.appendChild(hint);

    function describeSchedule(expr) {
      var presets = {
        '0 9 * * *':   'Todo dia às 9h',
        '0 9 * * 1':   'Toda segunda-feira às 9h',
        '0 18 * * 5':  'Toda sexta-feira às 18h',
        '*/30 * * * *':'A cada 30 minutos',
        '0 * * * *':   'A cada hora',
        '0 9 1 * *':   'Todo dia 1 do mês às 9h',
      };
      return presets[expr] || '';
    }

    scheduleInput.addEventListener('input', function () {
      hint.textContent = describeSchedule(this.value);
    });
    hint.textContent = describeSchedule(scheduleInput.value);
  }

  // ----------------------------------------------------------------
  // Threads page: scroll to bottom of message list
  // ----------------------------------------------------------------
  var threadMsgs = document.querySelector('.thread-messages');
  if (threadMsgs) {
    threadMsgs.scrollTop = threadMsgs.scrollHeight;
  }

  // ----------------------------------------------------------------
  // Table row click → navigate to link inside
  // ----------------------------------------------------------------
  document.querySelectorAll('tr[data-href]').forEach(function (row) {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function (e) {
      if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') return;
      window.location.href = row.dataset.href;
    });
  });

})();
