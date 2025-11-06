// ==================================
// 🌓 Dark Mode Toggle
// ==================================
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    if (localStorage.getItem('darkMode') === 'true') {
      document.body.classList.add('dark-mode');
      themeToggle.textContent = '☀️ Mode Siang';
    }
    themeToggle.addEventListener('click', () => {
      document.body.classList.toggle('dark-mode');
      const isDark = document.body.classList.contains('dark-mode');
      localStorage.setItem('darkMode', isDark);
      themeToggle.textContent = isDark ? '☀️ Mode Siang' : '🌙 Mode Malam';
    });
  }

  // Inisialisasi semua fitur
  initClimpactAutoFill();
  initClimpactFormHandler();
  initFileManager();
});

// ==================================
// 📤 Auto-Fill Metadata dari File Upload (ClimPACT)
// ==================================
function initClimpactAutoFill() {
  const fileInput = document.getElementById('stationFile');
  const stationNameInput = document.getElementById('stationName');
  const latInput = document.getElementById('latitude');
  const lonInput = document.getElementById('longitude');

  if (!fileInput || !stationNameInput || !latInput || !lonInput) return;

  fileInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (!file) {
      stationNameInput.value = '';
      latInput.value = '';
      lonInput.value = '';
      return;
    }

    stationNameInput.value = '';
    latInput.value = '';
    lonInput.value = '';

    const reader = new FileReader();
    reader.onload = function (event) {
      const text = event.target.result;
      try {
        const lines = text.split('\n').filter(line => line.trim() !== '');
        if (lines.length < 2) {
          alert('File harus berisi minimal header dan satu baris data.');
          return;
        }

        let separator = ',';
        const firstLine = lines[0];
        if (firstLine.includes(';')) separator = ';';
        else if (firstLine.includes('\t')) separator = '\t';

        const headers = firstLine.split(separator).map(h => h.trim());
        const firstDataRow = lines[1].split(separator).map(v => v.trim());

        const required = ['NAME', 'CURRENT_LATITUDE', 'CURRENT_LONGITUDE'];
        const missing = required.filter(col => !headers.includes(col));
        if (missing.length > 0) {
          alert(`File tidak memiliki kolom wajib: ${missing.join(', ')}`);
          return;
        }

        const nameIndex = headers.indexOf('NAME');
        const latIndex = headers.indexOf('CURRENT_LATITUDE');
        const lonIndex = headers.indexOf('CURRENT_LONGITUDE');

        if (nameIndex !== -1 && firstDataRow[nameIndex]) {
          stationNameInput.value = firstDataRow[nameIndex];
        }
        if (latIndex !== -1 && firstDataRow[latIndex]) {
          const lat = parseFloat(firstDataRow[latIndex]);
          if (!isNaN(lat)) latInput.value = lat;
        }
        if (lonIndex !== -1 && firstDataRow[lonIndex]) {
          const lon = parseFloat(firstDataRow[lonIndex]);
          if (!isNaN(lon)) lonInput.value = lon;
        }

      } catch (err) {
        console.error('Gagal membaca file:', err);
        alert('Gagal membaca file. Pastikan format file benar (CSV/TXT dengan delimiter ;).');
      }
    };

    reader.readAsText(file, 'UTF-8');
  });
}

// ==================================
// 📤 Handler Form Climpact
// ==================================
function initClimpactFormHandler() {
  const form = document.getElementById('climpactForm');
  if (!form) return;

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(form);

    try {
      const res = await fetch('/climpact/preview', {
        method: 'POST',
        body: formData
      });

      if (res.headers.get('content-type')?.includes('application/json')) {
        const data = await res.json();
        if (!res.ok) {
          alert('Error: ' + (data.error || 'Gagal memproses file.'));
          return;
        }
      }

      if (res.ok) {
        const html = await res.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        if (doc.querySelector('title')?.textContent?.includes('Preview')) {
          document.open();
          document.write(html);
          document.close();
        } else {
          const errorMsg = doc.querySelector('.alert')?.textContent || 'Terjadi kesalahan.';
          alert(errorMsg);
        }
      } else {
        const text = await res.text();
        alert('Gagal: ' + (text || 'Server error.'));
      }

    } catch (err) {
      alert('Gagal mengunggah file: ' + err.message);
    }
  });
}

// ==================================
// 🔀 SORT ITEMS — GLOBAL FUNCTION (WAJIB DI LUAR initFileManager)
// ==================================
function sortItems(order) {
  const list = document.getElementById('file-list');
  if (!list) return;

  const backLink = list.querySelector('.back-link-item');
  const items = Array.from(list.querySelectorAll('li:not(.back-link-item)'));

  items.sort((a, b) => {
    const nameA = a.querySelector('.item-name')?.textContent.trim().toLowerCase() || '';
    const nameB = b.querySelector('.item-name')?.textContent.trim().toLowerCase() || '';

    if (order === 'name-asc') return nameA.localeCompare(nameB);
    if (order === 'name-desc') return nameB.localeCompare(nameA);
    return 0;
  });

  // Reset list
  while (list.lastChild) list.removeChild(list.lastChild);
  if (backLink) list.appendChild(backLink);
  items.forEach(item => list.appendChild(item));

  // Reset dropdown
  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) sortSelect.value = '';
}

// ==================================
// 📁 File Manager: Multi-select, Aksi, Folder, Sorting
// ==================================
function initFileManager() {
  const checkboxes = document.querySelectorAll('input[name="selected"]');
  const downloadBtn = document.getElementById('download-selected');
  const deleteBtn = document.getElementById('delete-selected');
  const createBtn = document.getElementById('create-folder-btn');
  const searchInput = document.getElementById('search-input');
  const fileInput = document.getElementById('file-input');
  const uploadForm = document.getElementById('upload-form');

  // Update status tombol berdasarkan checkbox yang terlihat
  function updateButtons() {
    const checked = Array.from(checkboxes).some(cb =>
      cb.checked && cb.closest('li')?.style.display !== 'none'
    );
    if (downloadBtn) downloadBtn.disabled = !checked;
    if (deleteBtn) deleteBtn.disabled = !checked;
  }

  if (checkboxes.length > 0) {
    checkboxes.forEach(cb => cb.addEventListener('change', updateButtons));
    updateButtons();
  }

  // Upload
  if (uploadForm && fileInput) {
    fileInput.addEventListener('change', async (e) => {
      const files = Array.from(e.target.files);
      if (files.length === 0) return;

      const fd = new FormData(uploadForm);
      try {
        const res = await fetch('/upload', {
          method: 'POST',
          body: fd
        });

        if (res.ok && (await res.text()) === 'OK') {
          alert('✅ File berhasil diunggah!');
          window.location.reload();
        } else {
          const errMsg = await res.text();
          alert('❌ Gagal upload:\n' + errMsg);
        }
      } catch (err) {
        alert('❌ Error jaringan: ' + err.message);
      } finally {
        fileInput.value = '';
      }
    });
  }

  // Download selected
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const selected = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
      if (!selected.length) return;
      const p = new URLSearchParams();
      selected.forEach(f => p.append('files', f));
      p.set('path', window.CURRENT_PATH || '');
      window.location.href = `/download-selected?${p.toString()}`;
    });
  }

  // Delete selected
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      const selected = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
      if (!selected.length || !confirm('Yakin hapus item terpilih?')) return;
      const fd = new FormData();
      fd.append('path', window.CURRENT_PATH || '');
      selected.forEach(n => fd.append('items', n));
      try {
        const res = await fetch('/delete', { method: 'POST', body: fd });
        if (res.ok) location.reload();
        else alert('Gagal: ' + (await res.text()));
      } catch (err) {
        alert('Error: ' + err.message);
      }
    });
  }

  // Create folder modal
  const modal = document.getElementById('mkdir-modal');
  const form = document.getElementById('mkdir-form');

  if (createBtn && modal && form) {
    createBtn.addEventListener('click', () => {
      document.getElementById('folder-name').value = '';
      modal.style.display = 'block';
    });

    window.closeMkdirModal = () => {
      modal.style.display = 'none';
    };

    window.addEventListener('click', (e) => {
      if (e.target === modal) closeMkdirModal();
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('folder-name').value.trim();
      const path = document.getElementById('mkdir-path')?.value || '';

      if (!name) return;

      const fd = new FormData();
      fd.append('path', path);
      fd.append('name', name);

      try {
        const res = await fetch('/mkdir', { method: 'POST', body: fd });
        const text = await res.text();

        if (res.ok && text === 'OK') {
          alert('✅ Folder berhasil dibuat!');
          closeMkdirModal();
          window.location.reload();
        } else {
          alert('❌ Gagal membuat folder:\n' + text);
        }
      } catch (err) {
        alert('❌ Error jaringan: ' + err.message);
      }
    });
  }

  // Search — ✅ DIPERBAIKI: gunakan .item-name
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const term = searchInput.value.toLowerCase();
      document.querySelectorAll('#file-list li:not(.back-link-item)').forEach(li => {
        const name = li.querySelector('.item-name')?.textContent.toLowerCase() || '';
        li.style.display = name.includes(term) ? '' : 'none';
      });
      updateButtons();
    });
  }
}

// ==================================// ⏰ Tampilkan Tanggal dan Waktu Lokal serta UTC
// ==================================

  function updateDateTime() {
    const now = new Date();
    const local = new Intl.DateTimeFormat('id-ID', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: 'Asia/Jakarta'
    }).format(now);
    
    const utc = new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: 'UTC'
    }).format(now);

    document.getElementById('day-time').textContent = 
      local.split('pukul ')[0];
    let clean = utc.replace(/ PM$/, '');
    document.getElementById('utc-time').textContent = "STANDAR WAKTU INDONESIA " +local.split('pukul ')[1] + "  /  " +  clean + '  UTC';
  }

  setInterval(updateDateTime, 1000);
  updateDateTime();