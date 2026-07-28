(function(){
  const CSV_URL = './data/customer_support_tickets.csv';
  const PAGE_SIZE = 100;
  let data = [];
  let filtered = [];
  let sortKey = null;
  let sortDir = 1; // 1 asc, -1 desc
  let page = 1;

  const el = id => document.getElementById(id);

  function setStatus(txt){ const s = el('status'); if(s) s.textContent = txt; }

  function render(){
    const wrap = el('table-wrap');
    if(!wrap) return;
    wrap.innerHTML = '';
    if(filtered.length === 0){ wrap.innerHTML = '<div class="muted">No rows to display.</div>'; renderPager(); return; }

    const start = (page-1)*PAGE_SIZE;
    const pageRows = filtered.slice(start, start+PAGE_SIZE);

    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const tbody = document.createElement('tbody');

    const keys = Object.keys(filtered[0]);
    const trh = document.createElement('tr');
    keys.forEach(k=>{
      const th = document.createElement('th');
      th.textContent = k;
      th.style.whiteSpace = 'nowrap';
      th.onclick = ()=>{
        if(sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = 1; }
        applySort(); render();
      };
      trh.appendChild(th);
    });
    thead.appendChild(trh);

    pageRows.forEach(row=>{
      const tr = document.createElement('tr');
      keys.forEach(k=>{
        const td = document.createElement('td');
        td.textContent = row[k] || '';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    wrap.appendChild(table);
    renderPager();
  }

  function renderPager(){
    const pager = el('pager');
    pager.innerHTML = '';
    if(filtered.length === 0) return;
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    const info = document.createElement('div');
    info.textContent = `Showing page ${page} of ${totalPages} — ${filtered.length.toLocaleString()} rows`; info.className='muted';
    pager.appendChild(info);

    const prev = document.createElement('button'); prev.textContent='Prev'; prev.disabled = page<=1;
    prev.onclick = ()=>{ if(page>1) { page--; render(); window.scrollTo({top:0,behavior:'smooth'}); } };
    const next = document.createElement('button'); next.textContent='Next'; next.disabled = page>=totalPages;
    next.onclick = ()=>{ if(page<totalPages) { page++; render(); window.scrollTo({top:0,behavior:'smooth'}); } };
    pager.appendChild(prev); pager.appendChild(next);
  }

  function applySearch(q){
    if(!q) { filtered = data.slice(); page=1; applySort(); return; }
    const lower = q.toLowerCase();
    filtered = data.filter(row=>{
      for(const k in row){ if(row[k] && row[k].toString().toLowerCase().includes(lower)) return true; }
      return false;
    });
    page = 1;
    applySort();
  }

  function applySort(){
    if(!sortKey) return; 
    filtered.sort((a,b)=>{
      const A = (a[sortKey]||'').toString();
      const B = (b[sortKey]||'').toString();
      if(!isNaN(Date.parse(A)) && !isNaN(Date.parse(B))){ return (new Date(A) - new Date(B)) * sortDir; }
      if(!isNaN(parseFloat(A)) && !isNaN(parseFloat(B))){ return (parseFloat(A)-parseFloat(B)) * sortDir; }
      return A.localeCompare(B) * sortDir;
    });
  }

  function attachHandlers(){
    const search = el('search');
    search.addEventListener('input', e=>{ applySearch(e.target.value); render(); });
    search.addEventListener('keydown', e=>{ if(e.key==='Escape'){ e.target.value=''; applySearch(''); render(); } });
  }

  function load(){
    setStatus('Parsing CSV — this may take a moment...');
    Papa.parse(CSV_URL, {
      download: true,
      header: true,
      skipEmptyLines: true,
      worker: true,
      chunkSize: 1024*1024,
      complete: function(results){
        data = results.data || [];
        filtered = data.slice();
        setStatus(`Loaded ${data.length.toLocaleString()} rows`);
        attachHandlers();
        render();
      },
      error: function(err){ setStatus('Error parsing CSV: '+err.message); console.error(err); }
    });
  }

  // Start when DOM ready
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
