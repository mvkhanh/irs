// ======= Setup & helpers =======
var data = (window.__INITIAL_DATA__ || {});

const urlParams = new URLSearchParams(window.location.search);
const textquery = urlParams.get('query');
if (textquery) document.getElementById('text_query').value = decodeURIComponent(textquery);
const prev_query = urlParams.get('prev');
if (prev_query) document.getElementById('prev_query').value = decodeURIComponent(prev_query);
const nextquery = urlParams.get('next');
if (nextquery) document.getElementById('next_query').value = decodeURIComponent(nextquery);
const ocrQS = urlParams.get('ocr');
if (ocrQS) document.getElementById('ocr').value = decodeURIComponent(ocrQS);
const asrQS = urlParams.get('asr');
if (asrQS) document.getElementById('asr').value = decodeURIComponent(asrQS);

const ratings = new Map(); // id -> 'pos' | 'neg'
function nameFromPath(p) {
    const parts = (p || '').split(/[\\/]/).filter(Boolean);
    return parts.slice(-2).join('/'); // ví dụ: L30_V083/051.jpg
}

// ======= Populate object classes =======
async function loadObjects() {
    try {
        const r = await fetch(window.__ROUTES__.get_objects_list);
        const j = await r.json();
        const classes = j.classes || [];
        const dl = document.getElementById('objlist');
        dl.innerHTML = classes.map(c => `<option value="${c}">`).join('');
        window.__OBJECT_CLASSES__ = classes;
    } catch (err) {
        console.warn('Load objects failed, fallback demo');
        const fallback = [];
        document.getElementById('objlist').innerHTML = fallback.map(c => `<option value="${c}">`).join('');
        window.__OBJECT_CLASSES__ = fallback;
    }
}

// ======= Object filters: dynamic rows =======
function addObjRow(initial = { name: '', cmp: 'eq', count: '' }) {
    const wrap = document.getElementById('obj_filters');
    const row = document.createElement('div');
    row.className = 'obj-row';
    row.innerHTML = `
    <input type="text" class="obj-name" list="objlist" placeholder="object (vd: person)" value="${initial.name || ''}">
    <select class="obj-cmp">
      <option value="eq"  ${initial.cmp === 'eq' ? 'selected' : ''}>=</option>
      <option value="gte" ${initial.cmp === 'gte' ? 'selected' : ''}>&ge;</option>
      <option value="gt"  ${initial.cmp === 'gt' ? 'selected' : ''}>&gt;</option>
      <option value="lte" ${initial.cmp === 'lte' ? 'selected' : ''}>&le;</option>
      <option value="lt"  ${initial.cmp === 'lt' ? 'selected' : ''}>&lt;</option>
    </select>
    <input type="number" class="obj-count" min="0" step="1" placeholder="n" value="${(initial.count ?? '')}">
    <button type="button" class="custom-btn btn-13 del" title="Xoá">−</button>
  `;
    wrap.appendChild(row);
}

function readObjFilters() {
    const rows = Array.from(document.querySelectorAll('#obj_filters .obj-row'));
    const filters = [];
    rows.forEach(r => {
        const name = r.querySelector('.obj-name').value.trim();
        const cmp = r.querySelector('.obj-cmp').value;
        const cntS = r.querySelector('.obj-count').value;
        if (name && cntS !== '') {
            const count = Math.max(0, parseInt(cntS, 10) || 0);
            filters.push({ name, cmp, count });
        }
    });
    return filters;
}

// --- Parse include_ids (placeholder supports forms like: "L21_V009", "L21-009", "21/9", "L21", "21") ---
// Returns { group_nums: number[], video_nums: number[] }
function parseIncludeIds(raw) {
  const result = { group_nums: [], video_nums: [] };
  if (raw == null) return result;

  const tokens = String(raw).split(","); // chỉ tách theo dấu phẩy
  for (let t of tokens) {
    t = t.trim();
    if (!t) continue;

    if (t.includes("/")) {
      // dạng "21/9"
      const [gStr, vStr] = t.split("/");
      const g = parseInt((gStr || "").trim(), 10);
      const v = parseInt((vStr || "").trim(), 10);
      if (Number.isFinite(g) && Number.isFinite(v)) {
        result.group_nums.push(g);
        result.video_nums.push(v);
      }
      // else: bỏ qua token lỗi
    } else {
      // chỉ group: "21"
      const g = parseInt(t, 10);
      if (Number.isFinite(g)) {
        result.group_nums.push(g);
        result.video_nums.push(-1);
      }
    }
  }
  return result;
}

// --- Gom form -> payload JSON gửi POST ---
function buildSearchPayload(overrides = {}) {
    const prev = document.getElementById('prev_query').value || '';
    const query = document.getElementById('text_query').value || '';
    const next = document.getElementById('next_query').value || '';
    const ocr = document.getElementById('ocr').value || '';
    const asr = document.getElementById('asr').value || '';
    const includesRaw = document.getElementById('include_ids').value || '';

    const filters = readObjFilters(); // [{name,cmp,count}, ...]
    const gv = parseIncludeIds(includesRaw); // { group_nums:[], video_nums:[] }

    // page/size từ URL hiện tại (để giữ trạng thái)
    const curUrl = new URL(window.location.href);
    const page = parseInt(curUrl.searchParams.get('page') || '1', 10);
    const size = parseInt(curUrl.searchParams.get('size') || '100', 10);

    const payload = {
        // paging
        page: Number.isFinite(page) && page > 0 ? page : 1,
        size: Number.isFinite(size) && size > 0 ? size : 100,

        // unified params (optional)
        prev: prev || null,
        query: query || null,
        next: next || null,
        ocr: ocr || null,
        asr: asr || null,

        // object filters & id filters
        obj_filters: filters,
        group_nums: gv.group_nums,
        video_nums: gv.video_nums,
        exclude_ids: [],
    };

    Object.assign(payload, overrides);
    return payload;
}

// --- Gọi POST unified search và cập nhật 'data' + UI ---
async function doSearch(overrides = {}) {
    const payload = buildSearchPayload(overrides);
    try {
        const apiUrl = window.__ROUTES__.keyframe_unified_search_api; // /keyframe/search (POST)
        const res = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(await res.text());

        // cập nhật state data + UI
        data = await res.json();
        add_img();
        add_paging(payload.page);

        // Cập nhật URL hiện tại để giữ trạng thái (có thể share/refresh)
        const qs = new URLSearchParams();
        if (payload.prev) qs.set('prev', payload.prev);
        if (payload.query) qs.set('query', payload.query);
        if (payload.next) qs.set('next', payload.next);
        if (payload.ocr) qs.set('ocr', payload.ocr);
        if (payload.asr) qs.set('asr', payload.asr);
        if (payload.obj_filters?.length) {
            const packed = payload.obj_filters.map(f => `${f.name}:${f.cmp}:${f.count}`).join(',');
            qs.set('obj_filters', packed);
        }
        if (payload.include_ids?.length) {
            qs.set('include_ids', payload.include_ids.join(','));
        }
        qs.set('page', String(payload.page));
        qs.set('size', String(payload.size));
        history.replaceState(null, '', `${location.pathname}?${qs.toString()}`);
    } catch (err) {
        console.error(err);
        alert('Search thất bại!');
    }
}

// Add/remove row events
document.addEventListener('click', (e) => {
    if (e.target.id === 'btn-add-filter') {
        addObjRow();
    } else if (e.target.closest && e.target.closest('#obj_filters .del')) {
        const row = e.target.closest('.obj-row');
        if (row) row.remove();
    }
});

// ======= Paging =======
function add_paging(page) {
    let cur_index = page;
    if (Number.isNaN(cur_index)) cur_index = 1;

    const total = Number(data['total_page'] || 0);
    const container = document.getElementById("div_page");
    container.innerHTML = "";
    if (total <= 0) {
        document.getElementById("div_total_page").innerText = "Total: 0 page";
        return;
    }
    const WINDOW = 4;

    const start = Math.max(1, cur_index - WINDOW);
    const end = Math.min(total, cur_index + WINDOW);

    if (start > 1) container.appendChild(mkDots());

    for (let i = start; i <= end; i++) {
        const a = document.createElement('a');
        a.href = "javascript:void(0)";
        a.textContent = String(i);
        if (i === cur_index) a.classList.add('active');
        a.addEventListener('click', () => {
            doSearch({ page: i });
        });

        const wrap = document.createElement('div');
        wrap.className = 'page_num';
        wrap.appendChild(a);
        container.appendChild(wrap);
    }

    if (end < total) container.appendChild(mkDots());

    document.getElementById("div_total_page").innerText = "Total: " + total + " page";

    function mkDots() {
        const d = document.createElement('div');
        d.className = 'page_num';
        d.innerHTML = '...';
        return d;
    }
}

// ======= Render images =======
function add_img() {
    const grid = $("#div_img");
    grid.empty();

    const pagefile_list = data['results'] || [];
    pagefile_list.forEach((item) => {
        const id = item.id;
        const fname = nameFromPath(item.path) || String(id);
        grid.append(`
      <div class="container_img_btn" data-id="${id}" data-fname="${fname}">
        <img alt="${fname}" src="get_img?fpath=${encodeURIComponent(item.path)}" loading="lazy">
        <div class="actions">
          <div class="btnrow">
            <button class="icon-btn" data-action="ir" title="Image Search"><i class="fa fa-search"></i><span class="tooltip">IR</span></button>
            <button class="icon-btn like" data-action="pos" data-toggle title="Positive"><i class="fa fa-thumbs-up"></i></button>
            <button class="icon-btn dislike" data-action="neg" data-toggle title="Negative"><i class="fa fa-thumbs-down"></i></button>
            <button class="icon-btn" data-action="neighbors" title="Neighbors"><i class="fa fa-image"></i></button>
          </div>
        </div>
        <span class="filename-badge">${fname}</span>
      </div>
    `);
    });
}

// ======= Event delegation =======
// Mobile: tap card to toggle overlay
$('#div_img').on('click', '.container_img_btn', function (e) {
    if (window.matchMedia('(pointer:coarse)').matches) {
        if (!e.target.closest('.icon-btn')) {
            $(this).toggleClass('show');
        }
    }
});

// Click action icons
$('#div_img').on('click', '.icon-btn', async function (e) {
    e.stopPropagation();
    const $card = $(this).closest('.container_img_btn');
    const id = $card.data('id');
    const action = $(this).data('action');
    const imageSearchUrl = window.__ROUTES__.image_search;

    if (action === 'ir') {
        window.open(`${imageSearchUrl}?imgid=${id}`, '_blank');
        return;
    }

    if (action === 'pos' || action === 'neg') {
        ratings.set(id, action);
        $card.find('[data-toggle]').removeClass('active');
        $(this).addClass('active');
        return;
    }

    if (action === 'neighbors') {
        openNeighborsModal(id, $card.data('fname'));
        return;
    }
});

async function submitFeedback(id, label) {
    try {
        const res = await fetch('/feedback', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, label })
        });
        if (!res.ok) throw new Error(await res.text());
    } catch (err) { console.error(err); alert('Gửi feedback thất bại!'); }
}

// ======= Modal logic =======
const modal = document.getElementById('modal');
const strip = document.getElementById('thumb-strip');
const preview = document.getElementById('preview');
const modalTitle = document.getElementById('modal-title');

// State for neighbors navigation
let neiFrames = [];   // [{imgpath, id?}, ...]
let neiIndex = -1;   // current index in neiFrames

document.getElementById('modal-close').addEventListener('click', closeModal);

function onKeydownModal(e) {
    if (!modal.classList.contains('open')) return;
    if (e.key === 'Escape') { closeModal(); return; }
    if (e.key === 'ArrowLeft') { navigateNeighbors(-1); }
    if (e.key === 'ArrowRight') { navigateNeighbors(+1); }
}
document.addEventListener('keydown', onKeydownModal);

function openModal(title) {
    modalTitle.textContent = title;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
}
function closeModal() {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    strip.innerHTML = ''; preview.innerHTML = '';
    // reset neighbors state
    neiFrames = []; neiIndex = -1;
    strip.onclick = null;
}

async function openNeighborsModal(id, fname) {
    openModal(`Frames around: ${fname}`);
    // Load neighbors
    try {
        const k = 10
        const apiUrl = window.__ROUTES__.get_neighbors;
        const r = await fetch(`${apiUrl}?imgid=${id}&k=${k}`);
        const j = await r.json();
        const frames = j.frames || [];
        if (frames.length) {
            // cache frames & initial index
            neiFrames = frames.slice();
            neiIndex = Math.floor(frames.length / 2);

            // initial preview
            setPreviewByIndex(neiIndex);

            // build thumbnails
            strip.innerHTML = neiFrames.map((f, i) => `
        <img class="thumb ${i === neiIndex ? 'active' : ''}"
          data-src="${f.path}" data-name="${nameFromPath(f.path)}"
          src="get_img?fpath=${f.path}">
      `).join('');
            const active = strip.querySelector('.thumb.active');
            if (active) {
                active.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            }
            // attach click once (delegated), persistent
            strip.onclick = onThumbClick;
        }
    } catch (err) { console.error(err); }
}

function onThumbClick(e) {
    const t = e.target.closest('.thumb');
    if (!t) return;
    const thumbs = Array.from(strip.querySelectorAll('.thumb'));
    const idx = thumbs.indexOf(t);
    if (idx < 0) return;
    neiIndex = idx;
    setPreviewByIndex(neiIndex);
}

function navigateNeighbors(delta) {
    if (!neiFrames.length) return;
    const next = Math.min(neiFrames.length - 1, Math.max(0, neiIndex + delta));
    if (next === neiIndex) return;
    neiIndex = next;
    setPreviewByIndex(neiIndex);
}

function setPreviewByIndex(idx) {
    const f = neiFrames[idx];
    if (!f) return;
    setPreview(f.path, nameFromPath(f.path));
    // update thumb active class
    const thumbs = Array.from(strip.querySelectorAll('.thumb'));
    thumbs.forEach((el, i) => el.classList.toggle('active', i === idx));
    // ensure visible
    const el = thumbs[idx];
    if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
}
function setPreview(path, name) {
    const fname = name || nameFromPath(path);
    preview.innerHTML = `
    <div style="position:relative; width:100%; display:flex; align-items:center; justify-content:center;">
      <img src="get_img?fpath=${path}" alt="${fname}">
      <span class="filename-badge">${fname}</span>
    </div>
  `;
}

// ======= Init =======
function on_load() {
    // nếu backend trả thêm query_prev/next thì fill
    // if ("query" in data) document.getElementById("text_query").value = decodeURIComponent(data["query"]);
    // if ("query_prev" in data) document.getElementById("prev_query").value = decodeURIComponent(data["query_prev"]);
    // if ("query_next" in data) document.getElementById("next_query").value = decodeURIComponent(data["query_next"]);

    loadObjects();
    // Prefill object filters from URL (?obj_filters=person:gte:2,car:eq:1)
    const pf = urlParams.get('obj_filters');
    const wrap = document.getElementById('obj_filters');
    wrap.innerHTML = '';
    if (pf) {
        pf.split(',').forEach(tok => {
            const [name, cmp, count] = tok.split(':');
            addObjRow({ name: name || '', cmp: cmp || 'eq', count: count || '' });
        });
    } else {
        addObjRow(); // one empty row by default
    }
    add_paging(1);
    add_img();
}
window.on_load = on_load;

// Bind buttons & Enter events
document.getElementById('btn-search').addEventListener('click', () => {
    doSearch({ page: 1 }); // tìm mới -> quay về trang 1
});

document.getElementById('btn-reset').addEventListener('click', () => {
    ['prev_query', 'text_query', 'next_query', 'ocr', 'asr', 'include_ids'].forEach(id => {
        document.getElementById(id).value = '';
    });
    const wrap = document.getElementById('obj_filters');
    wrap.innerHTML = '';
    addObjRow(); // để lại 1 hàng trống
    doSearch({ page: 1 }); // reset rồi tìm lại
});

// Enter trong các ô input -> doSearch
['prev_query', 'text_query', 'next_query', 'ocr', 'asr', 'include_ids'].forEach(id => {
    document.getElementById(id).addEventListener('keydown', (e) => {
        if (e.key === 'Enter') doSearch({ page: 1 });
    });
});