// Esperar a que es carregui completament el document
$(document).ready(function () {

    // Obtenir la finestra actual del navegador (context de l'extensió)
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {

        // Obté la pestanya activa
        const activeTab = tabs[0];

        // Executar un script de contingut a la pestanya activa per obtenir el contingut HTML
        chrome.tabs.executeScript(activeTab.id, { code: "document.documentElement.outerHTML" }, function (results) {

            // Verificar si s'ha obtingut correctament el contingut
            if (results && results[0]) {
                const htmlContent = results[0];

                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlContent, 'text/html');

                let tableData = [];
                let headersCount = {}; // Contador per a cada capçalera
                let allHeaders = new Set(); // Conjunt de totes les capçaleres

                // Trobar elements de la taula
                const trElements = doc.querySelectorAll('tr[name="tblDadesOrgans"]');

                // Processar les dades de la taula
                trElements.forEach((tr, rowIndex) => {
                    const trId = tr.id;
                    const rowData = {};


                    const tdElements = tr.querySelectorAll('td');
                    for (let colIndex = 0; colIndex < tdElements.length; colIndex += 2) {
                        const label = tdElements[colIndex].textContent.trim();
                        const value = tdElements[colIndex + 1].textContent.trim();

                        if (label !== '') {
                            rowData[label] = value;

                            // Incrementar el comptador per aquesta capçalera
                            headersCount[label] = (headersCount[label] || 0) + 1;

                            // Afegir la capçalera al conjunt si apareix en almenys un registre fins ara
                            if (headersCount[label] > 0 && !rowData["Data baixa:"]) {
                                allHeaders.add(label);
                            }
                        }
                    }

                    if (Object.keys(rowData).length > 0 && !rowData["Data baixa:"]) {
                        tableData.push(rowData);

chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
    chrome.tabs.executeScript(tabs[0].id, { code: `
console.log('${trId}');
var trId = '${trId}';
var allElements = document.querySelectorAll('*');

allElements.forEach(function(element) {
    // Comprova si l'ID de l'element coincideix amb trId
    if (element.id === trId) {
        element.style.display = '';
    }
});

    ` });
});
                    }


                });

                // Localitza el <td> següent al que contingui el text "Número d'Inscripció:"
                const numeroInscripcioTd = Array.from(doc.querySelectorAll('td')).find(td => td.textContent.includes("Número d'Inscripció:"));

                // Localitza el <td> següent al que contingui el text "Nom Oficial de l'Entitat:"
                const nomEntitatTd = Array.from(doc.querySelectorAll('td')).find(td => td.textContent.includes("Nom Oficial de l'Entitat:"));

                // Verifica si s'ha trobat l'element i extreu-ne el text
                let numeroInscripcioText = "";
                if (numeroInscripcioTd) {
                    numeroInscripcioText = numeroInscripcioTd.nextElementSibling.textContent.trim();
                    console.log(numeroInscripcioText);
                } else {
                    console.error("No s'ha trobat cap element amb el text 'Número d\'Inscripció:'.");
                }

                // Verifica si s'ha trobat l'element i extreu-ne el text
                let nomEntitatText = "";
                if (nomEntitatTd) {
                    nomEntitatText = nomEntitatTd.nextElementSibling.textContent.trim();
                    console.log(nomEntitatText);
                } else {
                    console.error("No s'ha trobat cap element amb el text 'Nom Oficial de l\'Entitat:'.");
                }

                // Obtenir la data actual en format yyyymmdd
                const currentDate = new Date();
                const year = currentDate.getFullYear();
                const month = String(currentDate.getMonth() + 1).padStart(2, '0');
                const day = String(currentDate.getDate()).padStart(2, '0');
                const formattedDate = `${year}${month}${day}`;

                // Configuració de DataTables amb botons d'exportació
                if (tableData.length > 0 && allHeaders.size > 0) {
                    // Assegura't que totes les capçaleres estiguin presents a cada fila
                    const columnsConfig = Array.from(allHeaders).map(key => ({ title: key.replace(':', ''), data: key }));
                    const rowsConfig = tableData.map(row => Object.fromEntries(Array.from(allHeaders).map(header => [header, row[header] || ''])));

                    $('#dataTable').DataTable({
                        data: rowsConfig,
                        columns: columnsConfig,
                        buttons: [
                            {
                                extend: 'excel',
                                text: 'Descarregar XLSX',
                                filename: `${formattedDate}_${numeroInscripcioText}_${nomEntitatText}`,
                                title: null,
                            }
                        ],
                        dom: 'Bfrtip',
                        lengthMenu: [
                            [ -1 ], // Mostra tot
                            ['Mostra tot']
                        ],

                    });
                } else {
                    console.error("No hi ha dades disponibles per a mostrar en la DataTable.");
                }
            } else {
                console.error("No s'ha rebut cap resposta amb el contingut de la pàgina.");
            }
        });
    });
});
