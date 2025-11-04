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

  // Inisialisasi fitur Climpact jika ada
  initClimpactAutoFill();
  initClimpactFormHandler();
  initFileManager();
});

// ==================================
// 📤 Auto-Fill Metadata dari File Upload (ClimPACT)
// Mendukung delimiter: ; (utama), tab, koma
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

        // Deteksi delimiter: utamakan ;, lalu \t, lalu ,
        let separator = ',';
        const firstLine = lines[0];
        if (firstLine.includes(';')) separator = ';';
        else if (firstLine.includes('\t')) separator = '\t';

        const headers = firstLine.split(separator).map(h => h.trim());
        const firstDataRow = lines[1].split(separator).map(v => v.trim());

        // Validasi kolom wajib
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
// 📤 Handler Form Climpact: Submit ke /climpact/preview
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
        // Jika sukses dan kembali ke HTML, biarkan redirect alami
        // Tapi ini tidak terjadi — preview mengembalikan HTML, bukan JSON
      }

      // Jika respons HTML (template), biarkan browser handle
      if (res.ok) {
        const html = await res.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        if (doc.querySelector('title')?.textContent?.includes('Preview')) {
          // Ganti seluruh halaman
          document.open();
          document.write(html);
          document.close();
        } else {
          // Ada error di backend → tampilkan pesan
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
// 📁 File Manager: Multi-select, Aksi, Folder, Sorting
// ==================================
function initFileManager() {
  const checkboxes = document.querySelectorAll('input[name="selected"]');
  const downloadBtn = document.getElementById('download-selected');
  const deleteBtn = document.getElementById('delete-selected');
  const createBtn = document.getElementById('create-folder-btn');
  const searchInput = document.getElementById('search-input');

  // Update button status
  function updateButtons() {
    const checked = Array.from(checkboxes).some(cb => cb.checked);
    if (downloadBtn) downloadBtn.disabled = !checked;
    if (deleteBtn) deleteBtn.disabled = !checked;
  }

  if (checkboxes.length > 0) {
    checkboxes.forEach(cb => cb.addEventListener('change', updateButtons));
    updateButtons();
  }

  // Download selected
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const selected = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
      if (!selected.length) return;
      const url = new URL(window.location);
      url.pathname = '/download-selected';
      const p = new URLSearchParams();
      selected.forEach(f => p.append('files', f));
      p.set('path', window.CURRENT_PATH || '');
      window.location.href = url;
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

  // Create folder
  if (createBtn) {
    createBtn.addEventListener('click', async () => {
      const name = prompt('Nama folder:');
      if (!name?.trim()) return;
      if (name.includes('/') || name.includes('\\') || name.includes('..')) {
        alert('Nama tidak valid.');
        return;
      }
      const fd = new FormData();
      fd.append('path', window.CURRENT_PATH || '');
      fd.append('name', name.trim());
      try {
        const res = await fetch('/mkdir', { method: 'POST', body: fd });
        if (res.ok) location.reload();
        else alert('Gagal: ' + (await res.text()));
      } catch (err) {
        alert('Error: ' + err.message);
      }
    });
  }

  // Search & sort (jika ada)
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const term = searchInput.value.toLowerCase();
      document.querySelectorAll('#file-list li:not(.back-link-item)').forEach(li => {
        const name = li.querySelector('.item-link')?.textContent.toLowerCase() || '';
        li.style.display = name.includes(term) ? '' : 'none';
      });
    });
  }
}

// Utility: Sorting (bisa dipanggil dari HTML onclick)
window.sortItems = function(method) {
  const list = document.getElementById('file-list');
  if (!list) return;
  const items = Array.from(list.children);
  const staticStart = document.querySelector('.back-link-item') ? 1 : 0;
  const static = items.slice(0, staticStart);
  const sortable = items.slice(staticStart);
  sortable.sort((a, b) => {
    const aName = a.querySelector('.item-link')?.textContent.trim().split('(')[0].trim() || '';
    const bName = b.querySelector('.item-link')?.textContent.trim().split('(')[0].trim() || '';
    const aIsDir = a.classList.contains('folder');
    const bIsDir = b.classList.contains('folder');
    if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
    return (method === 'name-desc' ? -1 : 1) * aName.localeCompare(bName, 'id');
  });
  list.innerHTML = '';
  static.concat(sortable).forEach(item => list.appendChild(item));
};