/**
 * Ortak dinamik rapor sayfası script'i.
 *
 * `<main data-report-id="...">` içeren sayfalarda çalışır:
 *  - /api/reports/{id} endpoint'inden veriyi çekip stat kartlarını,
 *    filtre çubuğunu ve tabloyu çizer,
 *  - chatbot'un bıraktığı bekleyen filtreyi (sessionStorage "asis-pending-filter")
 *    İLK istekte uygular (filtresiz veri parlaması olmaz),
 *  - açık sayfada chatbot'tan gelen "asis:apply-filters" olayını dinleyip
 *    tabloyu sayfa yenilenmeden günceller.
 */
(function () {
  "use strict";

  const main = document.querySelector("[data-report-id]");
  if (!main) return;

  const reportId = main.dataset.reportId;
  const PENDING_KEY = "asis-pending-filter";

  const filterBarEl = document.getElementById("asis-filter-bar");
  const statGridEl = document.querySelector(".stat-grid");
  const tableEl = document.querySelector(".table-wrap table");
  const periodEl = document.getElementById("asis-report-period");

  let filterBarBuilt = false;

  // ---------- Bekleyen filtre (chatbot ile el sıkışma) ----------
  // Widget, kullanıcı başka sayfadayken toplanan filtreyi bu anahtara yazar;
  // hedef sayfa açılışta senkron okuyup siler.
  function readPendingFilters() {
    try {
      const raw = sessionStorage.getItem(PENDING_KEY);
      if (!raw) return null;
      const pending = JSON.parse(raw);
      if (pending && pending.report_id === reportId) {
        sessionStorage.removeItem(PENDING_KEY);
        return pending.filters || null;
      }
    } catch (e) {
      /* bozuk storage: filtresiz devam */
    }
    return null;
  }

  // ---------- Veri çekme ----------
  function buildQuery(filters) {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (value && key !== "label") params.set(key, value);
    });
    return params.toString();
  }

  async function fetchReport(filters) {
    try {
      const qs = buildQuery(filters);
      const res = await fetch("/api/reports/" + reportId + (qs ? "?" + qs : ""));
      if (!res.ok) throw new Error("HTTP " + res.status);
      render(await res.json());
    } catch (err) {
      renderError();
    }
  }

  // ---------- Çizim ----------
  function render(data) {
    renderStats(data.stats);
    renderFilterBar(data);
    renderTable(data.columns, data.rows, data.total_rows);
    if (periodEl) {
      periodEl.textContent = data.subtitle + " — " + data.period.label;
    }
  }

  function renderStats(stats) {
    if (!statGridEl) return;
    statGridEl.innerHTML = "";
    stats.forEach(({ label, value }) => {
      const div = document.createElement("div");
      div.className = "stat";
      const l = document.createElement("div");
      l.className = "label";
      l.textContent = label;
      const v = document.createElement("div");
      v.className = "value";
      v.textContent = value;
      div.append(l, v);
      statGridEl.appendChild(div);
    });
  }

  function renderTable(columns, rows, totalRows) {
    if (!tableEl) return;
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    columns.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.label;
      if (col.num) th.className = "num";
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);

    const tbody = document.createElement("tbody");
    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = columns.length;
      td.className = "empty-cell";
      td.textContent = "Bu filtrelerle kayıt bulunamadı.";
      tr.appendChild(td);
      tbody.appendChild(tr);
    }
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      columns.forEach((col) => {
        const td = document.createElement("td");
        if (col.num) td.className = "num";
        const value = row[col.key];
        if (col.badge) {
          const span = document.createElement("span");
          // Ödendi/Aktif yeşil, Bekliyor/Pasif gri rozet
          const olumlu = value === "Ödendi" || value === "Aktif";
          span.className = "badge " + (olumlu ? "aktif" : "pasif");
          span.textContent = value;
          td.appendChild(span);
        } else {
          td.textContent = value;
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tableEl.replaceChildren(thead, tbody);

    const wrap = tableEl.closest(".table-wrap");
    let note = wrap.querySelector(".table-note");
    if (totalRows > rows.length) {
      if (!note) {
        note = document.createElement("p");
        note.className = "table-note";
        wrap.appendChild(note);
      }
      note.textContent =
        "Son " + rows.length + " işlem gösteriliyor (toplam " + totalRows + ").";
    } else if (note) {
      note.remove();
    }
  }

  function renderError() {
    if (!tableEl) return;
    const tbody = tableEl.querySelector("tbody") || tableEl;
    tbody.innerHTML =
      '<tr><td colspan="9" class="empty-cell">Veri yüklenemedi. ' +
      "Lütfen sayfayı yenileyin.</td></tr>";
  }

  // ---------- Filtre çubuğu ----------
  // İlk yanıtta kurulur (seçenekler available_filters'tan gelir — tek doğruluk
  // kaynağı backend kayıt defteri); sonraki yanıtlarda yalnız değerler senkronlanır
  // ki chatbot'un uyguladığı filtre arayüzde de görünsün.
  function renderFilterBar(data) {
    if (!filterBarEl) return;
    if (!filterBarBuilt) {
      buildFilterBar(data.available_filters);
      filterBarBuilt = true;
    }
    filterBarEl.querySelector('[name="start"]').value = data.period.start || "";
    filterBarEl.querySelector('[name="end"]').value = data.period.end || "";
    Object.keys(data.available_filters).forEach((key) => {
      filterBarEl.querySelector('[name="' + key + '"]').value =
        data.applied_filters[key] || "";
    });
  }

  function buildFilterBar(availableFilters) {
    function field(labelText, inputEl) {
      const wrap = document.createElement("div");
      wrap.className = "filter-field";
      const label = document.createElement("label");
      label.textContent = labelText;
      wrap.append(label, inputEl);
      return wrap;
    }

    const startInput = document.createElement("input");
    startInput.type = "date";
    startInput.name = "start";
    const endInput = document.createElement("input");
    endInput.type = "date";
    endInput.name = "end";
    filterBarEl.append(
      field("Başlangıç", startInput),
      field("Bitiş", endInput)
    );

    Object.entries(availableFilters).forEach(([key, def]) => {
      const select = document.createElement("select");
      select.name = key;
      const hepsi = document.createElement("option");
      hepsi.value = "";
      hepsi.textContent = "Tümü";
      select.appendChild(hepsi);
      def.values.forEach((value) => {
        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = value;
        select.appendChild(opt);
      });
      filterBarEl.appendChild(field(def.label, select));
    });

    const applyBtn = document.createElement("button");
    applyBtn.type = "button";
    applyBtn.className = "btn btn-sm";
    applyBtn.textContent = "Filtrele";
    applyBtn.addEventListener("click", () => fetchReport(collectFilters()));

    const clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "btn btn-sm btn-ghost";
    clearBtn.textContent = "Temizle";
    clearBtn.addEventListener("click", () => fetchReport({}));

    const actions = document.createElement("div");
    actions.className = "filter-actions";
    actions.append(applyBtn, clearBtn);
    filterBarEl.appendChild(actions);
  }

  function collectFilters() {
    const filters = {};
    filterBarEl.querySelectorAll("input, select").forEach((el) => {
      if (el.value) filters[el.name] = el.value;
    });
    return filters;
  }

  // ---------- Chatbot canlı filtre olayı ----------
  // Sohbetten gelen filtre, sayfada o an uygulanmış olanların ÜZERİNE biner:
  // "sadece metro" dedikten sonra "geçen hafta" diyen kullanıcı mod seçimini
  // kaybetmez. (Filtre çubuğu her yanıtta senkronlandığı için mevcut durumu
  // çubuktan okumak yeterli.)
  document.addEventListener("asis:apply-filters", (e) => {
    if (e.detail && e.detail.report_id === reportId) {
      fetchReport(Object.assign(collectFilters(), e.detail.filters || {}));
    }
  });

  // Debug / manuel kullanım kancası
  window.AsisReportPage = { reportId, applyFilters: fetchReport };

  // ---------- İlk yükleme ----------
  fetchReport(readPendingFilters() || {});
})();
