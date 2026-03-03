// ============================================================
// BORME Mail Generator – Main Application Logic
// Uses Gemini REST API directly via fetch (no npm required)
// ============================================================

const GEMINI_API_BASE = 'https://generativelanguage.googleapis.com/v1beta/models/';

// ---- DOM Elements ----
const apiKeyInput = document.getElementById('apiKey');
const entityNameInput = document.getElementById('entityName');
const modelSelect = document.getElementById('modelSelect');
const dropZone = document.getElementById('dropZone');
const pdfInput = document.getElementById('pdfInput');
const fileList = document.getElementById('fileList');
const generateBtn = document.getElementById('generateBtn');
const loadingState = document.getElementById('loadingState');
const emptyState = document.getElementById('emptyState');
const outputContent = document.getElementById('outputContent');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const copyBtn = document.getElementById('copyBtn');

// ---- State ----
let uploadedFiles = []; // Array of { file: File, base64: string, name: string }

// ---- Utility: convert File to base64 ----
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// ---- Utility: format file size ----
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ---- Update the generate button state ----
function updateGenerateBtn() {
    const hasKey = apiKeyInput.value.trim().length > 0;
    const hasEntity = entityNameInput.value.trim().length > 0;
    const hasFiles = uploadedFiles.length > 0;
    generateBtn.disabled = !(hasKey && hasEntity && hasFiles);
}

// ---- Render file list ----
function renderFileList() {
    fileList.innerHTML = '';
    uploadedFiles.forEach((f, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
      <div class="file-item-info">
        <svg class="file-item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        <span class="file-item-name" title="${f.name}">${f.name}</span>
        <span class="file-item-size">${formatSize(f.file.size)}</span>
      </div>
      <button class="file-item-remove" data-index="${index}" title="Eliminar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    `;
        fileList.appendChild(item);
    });

    // Bind remove buttons
    fileList.querySelectorAll('.file-item-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(btn.dataset.index);
            uploadedFiles.splice(idx, 1);
            renderFileList();
            updateGenerateBtn();
        });
    });

    updateGenerateBtn();
}

// ---- Handle file additions (from input or drag-drop) ----
async function handleFiles(files) {
    for (const file of files) {
        if (file.type !== 'application/pdf') continue;
        // Avoid duplicates
        if (uploadedFiles.some(f => f.name === file.name && f.file.size === file.size)) continue;
        const base64 = await fileToBase64(file);
        uploadedFiles.push({ file, base64, name: file.name });
    }
    renderFileList();
}

// ---- Drop Zone Events ----
dropZone.addEventListener('click', () => pdfInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
});

pdfInput.addEventListener('change', () => {
    handleFiles(pdfInput.files);
    pdfInput.value = '';
});

// ---- Input listeners ----
apiKeyInput.addEventListener('input', updateGenerateBtn);
entityNameInput.addEventListener('input', updateGenerateBtn);

// ---- Build the prompt for Gemini ----
function buildPrompt(entityName, fileNames) {
    const societyNames = fileNames.map(n => {
        // Remove .pdf extension and common BORME prefixes like dates to get society name
        return n.replace(/\.pdf$/i, '');
    });

    return `IDIOMA OBLIGATORI: Tot el text que generis ha de ser EXCLUSIVAMENT en català. No escriguis cap paraula en castellà ni en cap altre idioma.

CONCORDANÇA GRAMATICAL: Assegura't que totes les concordances gramaticals siguin correctes en català:
- Concordança de gènere i nombre entre substantius, adjectius i determinants.
- Ús correcte dels verbs en la persona i el temps adequats.
- Ús correcte de les preposicions, articles i pronoms en català.
- "Publicades" si el subjecte és femení plural (p.ex. ampliacions), "publicats" si és masculí plural (p.ex. augments).
- Quan hi hagi una única operació, usa el singular ("ampliació", "reducció", "publicada"); quan n'hi hagi diverses, usa el plural.

Ets un assistent especialitzat en analitzar documents del BORME (Butlletí Oficial del Registre Mercantil) espanyol.

T'adjunto ${fileNames.length} fitxer(s) PDF del BORME. Els noms dels fitxers són:
${fileNames.map(n => `- ${n}`).join('\n')}

L'entitat dels usuaris és: ${entityName}

TASCA: Llegeix atentament cada PDF del BORME adjunt i redacta un correu electrònic en CATALÀ seguint EXACTAMENT la plantilla següent, substituint la informació entre claudàtors per la informació real extreta dels BORMEs.

PLANTILLA DEL CORREU:

Benvolgut/da,

Rebeu el present correu en qualitat d'usuari/ària de ${entityName} i, per extensió, de les societats [LLISTA DE SOCIETATS EXTRETES DELS TÍTOLS DELS FITXERS DELS BORMES ADJUNTATS, però posant-les amb la forma exacta que apareixen dins el cos del BORME, separades per "i"] en l'aplicació del Registre del sector públic de la Generalitat de Catalunya.
Per tal d'actualitzar les dades de participació de les societats esmentades al Registre del sector públic, així com per a informar les dades de l'Inventari d'accions i participacions de la Generalitat de Catalunya, us demanem que ens trameteu les escriptures públiques que formalitzen els augments i/o reduccions de capital [INDICA SI SÓN AUGMENTS, REDUCCIONS O AMBDUES COSES, segons la informació dels BORMEs] següents, publicats al BORME, fins i tot en cas que ${entityName} no hagués participat en els augments:

[PER CADA SOCIETAT, CREA UNA LLISTA AMB VINYETES AMB EL FORMAT SEGÜENT:
• [Nom Societat]:
  o [Resum en UNA SOLA LÍNIA de tot el contingut del BORME per a aquesta societat: ampliacions de capital, reduccions de capital, modificació d'estatuts, canvis en accions o participacions, etc., amb els imports corresponents], publicades al BORME el [DATA DE PUBLICACIÓ DEL BORME. La data del BORME s'ha d'extreure de la seva capçalera, no de la línia d'inscripció.]
LA REFERÈNCIA A LA DATA DEL BORME HA D'ANAR SEMPRE AL FINAL DE TOT EL CONTINGUT DEL BORME CORRESPONENT]

Així mateix, en cas que s'haguessin realitzat operacions d'adquisició o alienació d'accions d'aquestes o altres entitats del sector públic de la Generalitat que en poguessin alterar la seva participació, us agrairem que ens feu arribar les escriptures públiques o altres instruments que les formalitzin.

Gràcies anticipades per la vostra col·laboració i quedem pendents de la vostra resposta.

Cordialment,

FI DE LA PLANTILLA.

INSTRUCCIONS IMPORTANTS:
1. Extreu TOTA la informació rellevant de cada BORME: augments de capital, reduccions de capital, modificació d'estatuts, canvis en accions o participacions, i qualsevol altra informació rellevant.
2. AGRUPA els continguts per SOCIETAT, no per fitxer BORME. Si una mateixa societat apareix en diversos BORMEs, agrupa tota la seva informació sota el seu nom en una llista de vinyetes amb una línia per cada BORME.
3. Resumeix el contingut de cada BORME en una sola línia per societat.
4. La referència a la data del BORME ha d'anar SEMPRE al final de tot el contingut del BORME corresponent.
5. NO INVENTIS CAP DADA. Només utilitza informació que aparegui LITERALMENT als PDFs adjunts.
6. El format del correu ha de ser text pla, sense markdown ni format HTML.
7. No afegeixis cap text abans ni després del correu.
8. Tot el text ha de ser en CATALÀ CORRECTE amb concordances gramaticals impecables.
9. Revisa el text final per assegurar-te que les concordances de gènere, nombre i persona són correctes.
10. SINGULAR/PLURAL PER SOCIETATS: Si només s'ha extret informació d'una única societat, redacta tot el correu en singular (ex: "de la societat", "de l'escriptura", "d'aquesta entitat"). Si n'hi ha més d'una, utilitza el plural (ex: "de les societats", "de les escriptures", "d'aquestes entitats").`;
}

// ---- Show/Hide UI States ----
function showState(state) {
    emptyState.style.display = 'none';
    loadingState.style.display = 'none';
    outputContent.style.display = 'none';
    errorState.style.display = 'none';
    copyBtn.style.display = 'none';

    switch (state) {
        case 'empty':
            emptyState.style.display = 'flex';
            break;
        case 'loading':
            loadingState.style.display = 'flex';
            break;
        case 'output':
            outputContent.style.display = 'block';
            copyBtn.style.display = 'flex';
            break;
        case 'error':
            errorState.style.display = 'flex';
            break;
    }
}

// ---- Call Gemini REST API ----
async function callGemini(apiKey, prompt, pdfParts) {
    // Build the request body with inline PDF data
    const parts = [];

    // Add each PDF as inline data
    for (const pdf of pdfParts) {
        parts.push({
            inlineData: {
                mimeType: 'application/pdf',
                data: pdf.base64
            }
        });
    }

    // Add the text prompt
    parts.push({ text: prompt });

    const requestBody = {
        contents: [{
            parts: parts
        }],
        generationConfig: {
            temperature: 0.1,
            maxOutputTokens: 8192
        }
    };

    const modelName = modelSelect.value;
    const url = `${GEMINI_API_BASE}${modelName}:generateContent?key=${apiKey}`;

    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const msg = errData?.error?.message || `Error HTTP ${response.status}`;
        throw new Error(msg);
    }

    const data = await response.json();

    if (!data.candidates || !data.candidates[0]?.content?.parts?.[0]?.text) {
        throw new Error('Resposta buida de Gemini. Comprova que els PDFs són vàlids.');
    }

    return data.candidates[0].content.parts[0].text;
}

// ---- Generate Email ----
generateBtn.addEventListener('click', async () => {
    const apiKey = apiKeyInput.value.trim();
    const entityName = entityNameInput.value.trim();

    if (!apiKey || !entityName || uploadedFiles.length === 0) return;

    showState('loading');
    generateBtn.disabled = true;

    try {
        const fileNames = uploadedFiles.map(f => f.name);
        const prompt = buildPrompt(entityName, fileNames);
        const pdfParts = uploadedFiles.map(f => ({ base64: f.base64 }));

        const result = await callGemini(apiKey, prompt, pdfParts);

        outputContent.textContent = result;
        showState('output');
    } catch (err) {
        errorMessage.textContent = err.message;
        showState('error');
    } finally {
        updateGenerateBtn();
    }
});

// ---- Copy to Clipboard ----
copyBtn.addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(outputContent.textContent);
        copyBtn.classList.add('copied');
        copyBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      Copiat!
    `;
        setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        Copiar
      `;
        }, 2000);
    } catch {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = outputContent.textContent;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
    }
});

// ---- Init ----
showState('empty');
