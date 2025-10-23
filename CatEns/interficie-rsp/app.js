// app.js - mostra DretVot només per files tipus 'member'
(() => {
  // Columnes i colors (mateixes que script)
  const COLUMNS = [
    "Nom / Nivell", "Eliminar", "DretVot",
    "PersonesParticipInicial", "PersonesParticipActual",
    "PercentatgeParticipInicial", "PercentatgeParticip",
    "PersonesMembreInicial", "PersonesMembreActual",
    "PercentatgeInicial", "Percentatge",
    "PercentatgePersonaInicial", "PercentatgePersona",
    "CarrecInicial", "Carrec"
  ];

  const COLORS = [
    "#FFFFFF", "#FFFFFF", "#FFFFFF",
    "#D4EDDA", "#D4EDDA", "#D4EDDA", "#D4EDDA",
    "#D1ECF1", "#D1ECF1", "#D1ECF1", "#D1ECF1",
    "#E8E8FA", "#E8E8FA", "#E8E8FA", "#E8E8FA"
  ];

  // DOM elements
  const headerRowEl = document.getElementById('header-row');
  const rowsEl = document.getElementById('rows');
  const btnImport = document.getElementById('btn-import');
  const btnExport = document.getElementById('btn-export');
  const fileInput = document.getElementById('file-input');
  const btnLoadSample = document.getElementById('btn-load-sample');

  // Estructura d'arbre en memòria
  let nextId = 1;
  const items = {}; // id -> node {id, text, values, meta, parent, children, expanded, indent}
  let roots = [];

  let gridTemplateCols = '';

  // Utilitats
  function newId(){ return `n${nextId++}`; }
  function copy(o){ return JSON.parse(JSON.stringify(o)); }

  // Render header (grid columns)
  function renderHeader(){
    headerRowEl.innerHTML = '';
    const totalCols = COLUMNS.length + 1;
    const rest = COLUMNS.map(()=> '1fr').join(' ');
    gridTemplateCols = `28px ${rest}`;
    headerRowEl.style.gridTemplateColumns = gridTemplateCols;

    // toggle placeholder (col 0)
    const toggle = document.createElement('div');
    toggle.className = 'cell toggle-btn header';
    toggle.setAttribute('data-col', 'toggle');
    headerRowEl.appendChild(toggle);

    COLUMNS.forEach((col, i) => {
      const cell = document.createElement('div');
      cell.className = 'cell header col-' + i;
      cell.textContent = col;
      cell.style.background = COLORS[i] || '#fff';
      cell.setAttribute('data-col', String(i));
      headerRowEl.appendChild(cell);
    });
  }

  // Insert node
  function insertNode({parent=null, text='', values=[], node_type=null, metaNode={}}){
    const id = newId();
    const indent = parent ? (items[parent].indent + 1) : 0;
    const expected = COLUMNS.length - 1;
    const vals = values.slice(0, expected).concat(Array(Math.max(0, expected - values.length)).fill(''));
    const meta = Object.assign({}, metaNode);
    // ensure initial_values exists and has correct length
    meta.initial_values = Array.isArray(meta.initial_values) ? meta.initial_values.slice(0, expected).concat(Array(Math.max(0, expected - (meta.initial_values||[]).length)).fill('')) : vals.slice();
    meta.initial_text = meta.initial_text || text;
    // defaults for flags and booleans
    meta.eliminar = !!meta.eliminar;
    meta.dret_vot = !!meta.dret_vot;
    meta.dret_vot_parent = !!meta.dret_vot_parent;
    if (node_type) { meta.type = node_type; meta._locked_type = true; }
    const node = { id, text, values: vals, meta, parent, children: [], expanded: !!meta.expanded !== false ? true : false, indent };
    items[id] = node;
    if (parent){
      items[parent].children.push(id);
    } else {
      roots.push(id);
    }
    return id;
  }

  // Robust loadFromData: accepta la llista generada per dades_obertes.py
  function loadFromData(data, filterText = ''){
    clearAll();

    let nodesList = [];
    if (!data) { alert('No hi ha dades.'); return; }
    if (Array.isArray(data)) {
      nodesList = data;
    } else if (typeof data === 'object' && data !== null) {
      if (Array.isArray(data.children)) {
        nodesList = [data];
      } else {
        const vals = Object.values(data);
        const potentialRoots = vals.filter(n => !n.parent);
        if (potentialRoots.length) nodesList = potentialRoots;
        else nodesList = vals;
      }
    } else {
      alert('Format JSON no reconegut.');
      return;
    }

    const filtro = (filterText||'').trim().toLowerCase();
    if (filtro) {
      nodesList = nodesList.filter(n => (String(n.text||'')).toLowerCase().includes(filtro));
      if (!nodesList.length) { alert('No s\'ha trobat cap entitat amb el filtre.'); return; }
    }

    function recInsert(nodeObj, parentId = null){
      if (!nodeObj || typeof nodeObj !== 'object') return null;

      const nodeMeta = (nodeObj.meta && typeof nodeObj.meta === 'object') ? copy(nodeObj.meta) : {};
      if (Array.isArray(nodeObj.meta_initial_values) && !Array.isArray(nodeMeta.initial_values)) {
        nodeMeta.initial_values = nodeObj.meta_initial_values.slice();
      }
      if (nodeObj.meta_initial_text && !nodeMeta.initial_text) {
        nodeMeta.initial_text = nodeObj.meta_initial_text;
      }

      const nodeValues = Array.isArray(nodeObj.values) ? nodeObj.values.slice() : [];
      const nodeType = nodeMeta.type || null;

      const newId = insertNode({parent: parentId, text: nodeObj.text || '', values: nodeValues, node_type: nodeType, metaNode: nodeMeta});

      if (typeof nodeObj.expanded === 'boolean') items[newId].expanded = nodeObj.expanded;

      const childrenArr = Array.isArray(nodeObj.children) ? nodeObj.children : [];
      for (let ch of childrenArr) {
        recInsert(ch, newId);
      }
      return newId;
    }

    for (let rootNode of nodesList) {
      recInsert(rootNode, null);
    }

    recomputeAndRender();
  }

  function exportToJSON(){
    function nodeToDict(id){
      const it = items[id];
      return {
        text: it.text,
        values: it.values.slice(),
        meta: Object.assign({}, it.meta),
        meta_initial_values: (it.meta && it.meta.initial_values) ? it.meta.initial_values.slice() : [],
        meta_initial_text: (it.meta && it.meta.initial_text) ? it.meta.initial_text : it.text,
        parent: it.parent,
        expanded: !!it.expanded,
        children: it.children.map(nodeToDict)
      };
    }
    const arr = roots.map(nodeToDict);
    const blob = new Blob([JSON.stringify(arr, null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tree_export.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // Render whole list (no virtualization)
  function renderAll(){
    rowsEl.innerHTML = '';
    const order = [];
    function visit(id){
      order.push(id);
      if (items[id].expanded){
        items[id].children.forEach(visit);
      }
    }
    roots.forEach(visit);
    order.forEach(id => {
      const node = items[id];
      const row = document.createElement('div');
      row.className = 'row ' + (node.meta.type || '');
      row.dataset.id = id;
      row.style.display = 'grid';
      row.style.gridTemplateColumns = gridTemplateCols;

      // toggle cell (no indent here; indent applied to first column)
      const toggleCell = document.createElement('div');
      toggleCell.className = 'cell toggle-btn';
      toggleCell.setAttribute('data-col', 'toggle');
      const toggleSym = document.createElement('span');
      toggleSym.className = 'toggle-symbol';
      toggleSym.textContent = node.children.length ? (node.expanded ? '▼' : '▶') : '';
      toggleCell.appendChild(toggleSym);
      toggleCell.addEventListener('click', (e)=>{
        e.stopPropagation();
        toggleNode(id);
      });
      row.appendChild(toggleCell);

      // columns
      COLUMNS.forEach((col, i) => {
        const colCell = document.createElement('div');
        colCell.className = 'cell col-' + i + (i===0 ? ' first col-name' : '');
        colCell.setAttribute('data-col', String(i));
        colCell.style.background = COLORS[i] || '#fff';

        if (i === 0){
          // first column holds the text and the indent (not the toggle)
          colCell.style.paddingLeft = (node.indent * 16 + 6) + 'px';
          colCell.textContent = node.text || '';
          colCell.addEventListener('click', (e)=>{
            e.stopPropagation();
            selectRow(id);
          });
          colCell.addEventListener('dblclick', (e)=>{
            e.stopPropagation();
            onRowDoubleClick(id);
          });
        } else {
          const valIdx = i - 1;
          let display = node.values[valIdx] !== undefined ? node.values[valIdx] : '';
          if (col.toLowerCase().includes('eliminar')) {
            colCell.classList.add('center');
            colCell.textContent = (node.meta.eliminar) ? '☒' : (display || '☐');
            colCell.addEventListener('click', (e)=>{ e.stopPropagation(); toggleEliminar(id); });
          } else if (col.toLowerCase().includes('dretvot')) {
            // SHOW DRETVOT ONLY FOR 'member' NODES
            colCell.classList.add('center');
            if (node.meta && node.meta.type === 'member') {
              colCell.textContent = (node.meta.dret_vot) ? '☒' : (display || '☐');
              colCell.addEventListener('click', (e)=>{ e.stopPropagation(); toggleDretVot(id); });
            } else {
              // not a member -> empty cell (no interactive flag)
              colCell.textContent = '';
            }
          } else {
            colCell.textContent = display;
            if (col === 'Carrec'){
              colCell.addEventListener('dblclick', (e)=>{
                e.stopPropagation();
                if ((node.meta && node.meta.type) === 'person'){
                  startEditCarrec(id, valIdx, colCell);
                }
              });
            }
          }
        }
        row.appendChild(colCell);
      });

      row.addEventListener('click', ()=> selectRow(id));
      rowsEl.appendChild(row);
    });
    updateRowColorsAll();
  }

  function selectRow(id){
    document.querySelectorAll('.row').forEach(r => r.classList.remove('selected'));
    const el = document.querySelector(`.row[data-id="${id}"]`);
    if (el) el.classList.add('selected');
    window._selectedRow = id;
  }

  function toggleNode(id){
    items[id].expanded = !items[id].expanded;
    renderAll();
  }

  function onRowDoubleClick(id){
    const node = items[id];
    if (!node) return;
    const parentMeta = node.meta || {};
    const parentType = parentMeta.type;
    if (parentType === 'person') return;
    const hierarchy = { entity: 'tipus', tipus: 'particip', particip: 'member', member: 'person' };
    const childType = hierarchy[parentType] || null;
    if (!childType) return;
    const promptMap = {
      tipus: "Denominació del nou tipus:",
      particip: "Denominació del nou partícip:",
      member: "Denominació del nou membre:",
      person: "Nom de la nova persona:"
    };
    const name = prompt(promptMap[childType] || 'Denominació del nou element:');
    if (!name || !name.trim()) return;
    const numExtra = Math.max(0, COLUMNS.length - 3);
    const base_values = ['☐',''].concat(Array(numExtra).fill(''));
    if (childType === 'particip'){
      ['PersonesParticipInicial','PercentatgeParticipInicial'].forEach(colName=>{
        if (COLUMNS.includes(colName)){ const idx = COLUMNS.indexOf(colName)-1; if (idx>=0) base_values[idx] = '0.0%'; }
      });
    }
    if (childType === 'member'){
      ['PersonesMembreInicial','PercentatgeInicial'].forEach(colName=>{
        if (COLUMNS.includes(colName)){ const idx = COLUMNS.indexOf(colName)-1; if (idx>=0) base_values[idx] = '0.0%'; }
      });
      if (COLUMNS.includes('DretVot')){ const idx = COLUMNS.indexOf('DretVot')-1; if (idx>=0) base_values[idx] = '☐'; }
    }
    if (childType === 'person'){
      ['PercentatgePersonaInicial'].forEach(colName=>{
        if (COLUMNS.includes(colName)){ const idx = COLUMNS.indexOf(colName)-1; if (idx>=0) base_values[idx] = '0.0%'; }
      });
    }
    const newId = insertNode({parent:id, text:name.trim(), values: base_values, node_type: childType});
    const newMeta = items[newId].meta;
    newMeta.type = childType;
    newMeta.initial_values = newMeta.initial_values || base_values.slice();
    newMeta.initial_text = name.trim();
    newMeta.eliminar = false;
    if (childType === 'member') newMeta.dret_vot = false;
    if (childType === 'person') { newMeta.carrec = ''; newMeta.dret_vot_parent = !!(parentMeta && parentMeta.dret_vot); }
    recomputeAndRender();
  }

  // Editing Carrec
  function startEditCarrec(id, valIndex, cellEl){
    const node = items[id];
    if (!node) return;
    const prev = node.values[valIndex] || '';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'inline-input';
    input.value = prev;
    cellEl.innerHTML = '';
    cellEl.appendChild(input);
    input.focus();
    input.select();
    input.addEventListener('keydown', (e)=>{
      if (e.key === 'Enter'){
        commitEditCarrec(id, valIndex, input.value);
      } else if (e.key === 'Escape'){
        renderAll();
      }
    });
    input.addEventListener('blur', ()=>{
      commitEditCarrec(id, valIndex, input.value);
    });
  }
  function commitEditCarrec(id, valIndex, value){
    const node = items[id];
    if (!node) return;
    node.values[valIndex] = value;
    if ((node.meta && node.meta.type) === 'person'){
      node.meta.carrec = value;
    }
    recomputeAndRender();
  }

  // Toggle eliminar - if uncheck, restore descendants initial values
  function toggleEliminar(id){
    const node = items[id];
    if (!node) return;
    node.meta.eliminar = !node.meta.eliminar;
    if (!node.meta.eliminar){
      function restore(iid){
        const nd = items[iid];
        nd.meta.eliminar = false;
        const initial = nd.meta.initial_values || [];
        ['PercentatgePersona','Percentatge','PercentatgeParticip'].forEach(colName=>{
          if (COLUMNS.includes(colName)){
            const colIdx = COLUMNS.indexOf(colName)-1;
            if (colIdx >= 0 && initial[colIdx] !== undefined){
              nd.values[colIdx] = initial[colIdx];
            }
          }
        });
        nd.children.forEach(restore);
      }
      node.children.forEach(restore);
    }
    recomputeAndRender();
  }

  // Toggle dret_vot for members, propagate dret_vot_parent to person children
  function toggleDretVot(id){
    const node = items[id];
    if (!node) return;
    if ((node.meta && node.meta.type) !== 'member') return;
    node.meta.dret_vot = !node.meta.dret_vot;
    function propagate(iid){
      items[iid].children.forEach(ch=>{
        const chMeta = items[ch].meta || {};
        if (chMeta.type === 'person'){
          chMeta.dret_vot_parent = !!node.meta.dret_vot;
        }
        propagate(ch);
      });
    }
    propagate(id);
    recomputeAndRender();
  }

  // Count valid persons under a node (not eliminated and recursively)
  function countValidPersons(nodeId){
    let total = 0;
    items[nodeId].children.forEach(ch=>{
      const m = items[ch].meta || {};
      if (m.eliminar) return;
      if (m.type === 'person') total += 1;
      else total += countValidPersons(ch);
    });
    return total;
  }

  // Effective elimination check (ancestor elimination)
  function isEffectivelyEliminated(iid){
    let cur = iid;
    while(cur){
      if (items[cur].meta && items[cur].meta.eliminar) return true;
      cur = items[cur].parent;
    }
    return false;
  }

  // Count valid persons considering effective elimination
  function countValidPersonsEffective(parentId){
    let total = 0;
    items[parentId].children.forEach(ch=>{
      if (isEffectivelyEliminated(ch)) return;
      const meta = items[ch].meta || {};
      if (meta.type === 'person') total += 1;
      else total += countValidPersonsEffective(ch);
    });
    return total;
  }

  // refresh_tree_display_all portat a JS
  function refreshTreeDisplayAll(){
    const entityIds = Object.values(items).filter(it => (it.meta && it.meta.type) === 'entity' && !isEffectivelyEliminated(it.id)).map(it=>it.id);
    const entityTotals = {};
    entityIds.forEach(entId => {
      let total_entity = 0;
      const stack = [entId];
      while(stack.length){
        const nodeId = stack.pop();
        if (isEffectivelyEliminated(nodeId)) continue;
        const m = items[nodeId].meta || {};
        if (m.type === 'member' && m.dret_vot){
          total_entity += countValidPersonsEffective(nodeId);
        }
        items[nodeId].children.forEach(c=>stack.push(c));
      }
      entityTotals[entId] = total_entity;
    });

    Object.values(items).forEach(it => {
      const meta = it.meta || {};
      const t = meta.type;
      ['PersonesParticipActual','PersonesMembreActual','PercentatgeParticip','Percentatge','PercentatgePersona'].forEach(col=>{
        if (COLUMNS.includes(col)) setValue(it.id, col, '');
      });

      if (isEffectivelyEliminated(it.id)){
        if (t === 'person' && COLUMNS.includes('PercentatgePersona')) setValue(it.id, 'PercentatgePersona', '0.00');
        else if (t === 'member'){
          if (COLUMNS.includes('Percentatge')) setValue(it.id, 'Percentatge', '0.00');
          if (COLUMNS.includes('PersonesMembreActual')) setValue(it.id, 'PersonesMembreActual', '0');
        } else if (t === 'particip' || t === 'entity'){
          if (COLUMNS.includes('PercentatgeParticip')) setValue(it.id, 'PercentatgeParticip', '0.00');
          if (COLUMNS.includes('PersonesParticipActual')) setValue(it.id, 'PersonesParticipActual', '0');
        }
        return;
      }

      let entity_iid = it.id;
      while(entity_iid && !(items[entity_iid].meta && items[entity_iid].meta.type === 'entity')){
        entity_iid = items[entity_iid].parent;
      }
      const total_entity = entityTotals[entity_iid] || 0;

      if (t === 'person'){
        if (meta.dret_vot_parent && total_entity > 0){
          const pct = (1 / total_entity) * 100;
          setValue(it.id,'PercentatgePersona', pct.toFixed(2));
        } else {
          if (COLUMNS.includes('PercentatgePersona')) setValue(it.id,'PercentatgePersona','0.00');
        }
      } else if (t === 'member'){
        const cnt = countValidPersonsEffective(it.id);
        if (COLUMNS.includes('PersonesMembreActual')) setValue(it.id,'PersonesMembreActual', String(cnt));
        if (meta.dret_vot && total_entity > 0){
          const pct = (cnt / total_entity) * 100;
          setValue(it.id,'Percentatge', pct.toFixed(2));
        } else {
          if (COLUMNS.includes('Percentatge')) setValue(it.id,'Percentatge','0.00');
        }
      } else if (t === 'particip'){
        let total_persons = 0;
        const stack = [it.id];
        while(stack.length){
          const nid = stack.pop();
          if (isEffectivelyEliminated(nid)) continue;
          const metaN = items[nid].meta || {};
          if (metaN.type === 'member' && metaN.dret_vot) total_persons += countValidPersonsEffective(nid);
          items[nid].children.forEach(c=>stack.push(c));
        }
        if (COLUMNS.includes('PersonesParticipActual')) setValue(it.id, 'PersonesParticipActual', String(total_persons));
        if (total_entity > 0){
          const pct = (total_persons / total_entity) * 100;
          setValue(it.id, 'PercentatgeParticip', pct.toFixed(2));
        } else {
          if (COLUMNS.includes('PercentatgeParticip')) setValue(it.id,'PercentatgeParticip','0.00');
        }
      } else if (t === 'entity'){
        if (COLUMNS.includes('PercentatgeParticip')) setValue(it.id, 'PercentatgeParticip', (total_entity>0?100.00:0.00).toFixed(2));
      }
    });
  }

  function setValue(id, colName, value){
    const idx = COLUMNS.indexOf(colName);
    if (idx <= 0) return;
    const pos = idx - 1;
    const node = items[id];
    if (!node) return;
    node.values[pos] = value;
  }

  // update row colors for diffs Initial vs Actual
  function updateRowColorsAll(){
    document.querySelectorAll('.row').forEach(row => {
      const id = row.dataset.id;
      const node = items[id];
      if (!node) return;
      row.querySelectorAll('.cell').forEach(c => c.style.color = '#000');
      COLUMNS.forEach((col, colIndex) => {
        if (!col.endsWith('Inicial')) return;
        const baseCol = col.slice(0, -7);
        let actualColIndex = COLUMNS.indexOf(baseCol);
        if (actualColIndex === -1) actualColIndex = COLUMNS.indexOf(baseCol + 'Actual');
        if (actualColIndex === -1) return;
        const initPos = colIndex - 1;
        const actPos = actualColIndex - 1;
        const initVal = node.values[initPos] !== undefined ? String(node.values[initPos]).trim() : '';
        const actVal = node.values[actPos] !== undefined ? String(node.values[actPos]).trim() : '';
        const domInit = row.querySelector(`.cell[data-col="${colIndex}"]`);
        const domAct = row.querySelector(`.cell[data-col="${actualColIndex}"]`);
        if (!domInit || !domAct) return;
        if (initVal !== actVal){
          domInit.style.color = 'red';
          domAct.style.color = 'green';
        } else {
          domInit.style.color = '#000';
          domAct.style.color = '#000';
        }
      });
    });
  }

  function recomputeAndRender(){
    refreshTreeDisplayAll();
    renderAll();
  }

  function clearAll(){
    Object.keys(items).forEach(k=>delete items[k]);
    roots = [];
    nextId = 1;
    rowsEl.innerHTML = '';
  }

  // Import/export handlers
  btnImport.addEventListener('click', ()=> fileInput.click());
  fileInput.addEventListener('change', (e)=>{
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (ev)=>{
      try{
        const data = JSON.parse(ev.target.result);
        const filtered = prompt('Filtre d\'entitat (deixa en blanc per carregar totes):','');
        loadFromData(Array.isArray(data)?data:[data], filtered);
      }catch(err){
        alert('Error llegint JSON: ' + err);
      }
    };
    reader.readAsText(f, 'utf-8');
    fileInput.value = '';
  });

  btnExport.addEventListener('click', ()=> exportToJSON());
  btnLoadSample.addEventListener('click', ()=> {
    fetch('sample_data.json').then(r=>r.json()).then(data=>{
      loadFromData(Array.isArray(data)?data:[data], '');
    }).catch(err=> alert('No s\'ha pogut carregar sample_data.json: ' + err));
  });

  // initial render header
  renderHeader();

  // sample data embedded
  const SAMPLE = [
    {
      "text": "Entitat A",
      "values": [],
      "meta": {"type":"entity"},
      "children": [
        {
          "text":"Tipus X",
          "values":[],
          "meta":{"type":"tipus"},
          "children":[
            {
              "text":"Partícip 1",
              "values":["☐","0","0.00"],
              "meta":{"type":"particip"},
              "children":[
                {
                  "text":"Membre Alpha",
                  "values":["☐","1","50.00"],
                  "meta":{"type":"member","dret_vot":true},
                  "children":[
                    {"text":"Persona 1","values":["0.00","",""],"meta":{"type":"person","dret_vot_parent":true}}
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ];

  // Expose small API for debugging
  window._treeApp = {
    insertNode, items, roots, loadFromData, exportToJSON, recomputeAndRender
  };

  // load sample automatically on startup
  loadFromData(SAMPLE, '');
})();