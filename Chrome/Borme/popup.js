document.addEventListener('DOMContentLoaded', function () {
  // Aconsegueix l'element d'entrada de la data
  var dateInput = document.getElementById('dateInput');

  // Afegeix un esdeveniment d'escolta quan es faci clic al botó
  document.getElementById('openUrlButton').addEventListener('click', function () {
    // Obté el valor de l'entrada de la data
    var dataEnFormatAAAAMMDD = dateInput.value;

    // Ara pots fer el que vulguis amb la variable dataEnFormatAAAAMMDD
    console.log('Data en format AAAA-MM-DD:', dataEnFormatAAAAMMDD);

    // Per exemple, pots cridar una funció que faci alguna cosa amb la data
    // funcioQueUtilitzaLaData(dataEnFormatAAAAMMDD);

    async function webScraping() {

        const url = "https://www.boe.es/borme/dias/" + dataEnFormatAAAAMMDD + "/";

        const response = await fetch(url); // Obteniu el contingut de la pàgina web
        const html = await response.text(); // Converteix la resposta a text

        // Parseu el contingut HTML amb DOMParser
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Cerqueu el text "ÍNDICE ALFABÉTICO DE SOCIEDADES" dins dels elements p
        const p_elements = doc.querySelectorAll('p');
        let pdf_href = '';

        for (const p of p_elements) {
            if (p.textContent === "ÍNDICE ALFABÉTICO DE SOCIEDADES") {
                // Obteniu l'element "a" dins del "li" pare del "p"
                const li_element = p.closest('li');
                const a_element = li_element.querySelector('a');
                // Obteniu el valor de l'atribut "href"
                pdf_href = "https://boe.es" + a_element.getAttribute('href');
                console.log(pdf_href);
            }
        }

        if (pdf_href) {
            return pdf_href;

        } else {
            alert("No s'ha trobat BORME de la data indicada");
        }
    }

    async function obtenirIndexBORME() {
        try {
            // Espera que l'objecte JSON sigui creat
            const index = await webScraping();

            // Ara pots utilitzar jsonObject amb seguretat

            return index;

        } catch (error) {
            console.error('Hi ha hagut un error:', error);
        }
    }


    // CREAR JSON AMB LES DADES DEL BORME D'ÍNDEX ALFABÈTIC DE SOCIETATS

    async function getTextFromPDF() {
        const index2 = await obtenirIndexBORME();
        const pdfUrl = index2;
        console.log(pdfUrl);

        const pdfjsLib = window['pdfjs-dist/build/pdf'];
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'pdf.worker.min.js';

        const response = await fetch(pdfUrl);
        const arrayBuffer = await response.arrayBuffer();
        const pdfData = new Uint8Array(arrayBuffer);

        try {
            const pdf = await pdfjsLib.getDocument({
                data: pdfData
            }).promise;

            let allText = '';
            let currentParagraph = '';
            let lastY = null;
            const MIN_Y_DIFFERENCE = 10;

            for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
                const page = await pdf.getPage(pageNumber);
                const textContent = await page.getTextContent();

                let fullText = '';

                textContent.items.forEach(item => {
                    if (lastY === null || Math.abs(item.transform[5] - lastY) <= MIN_Y_DIFFERENCE) {
                        currentParagraph += item.str + ' ';
                    } else {
                        const trimmedParagraph = currentParagraph.trim();
                        if (trimmedParagraph !== '') {
                            fullText += trimmedParagraph + '\n';
                        }
                        currentParagraph = item.str + ' ';
                    }
                    lastY = item.transform[5];
                });

                const trimmedParagraph = currentParagraph.trim();
                if (trimmedParagraph !== '') {
                    fullText += trimmedParagraph + '\n';
                }

                allText += fullText;
                //allText = allText.replace(/\n\n/g, ' '); 

                currentParagraph = '';
                lastY = null;
            }

            const regex = /^(.*?) +(BORME-.*?) +\((\d+)\)\n/gm;
            // const regex = /(^\d+) - (.*)+\n((.*)+)\n/gm;
            const paragrafList = document.getElementById('paragrafList');

            let regexMatches;
            let jsonArray = [];

            while ((regexMatches = regex.exec(allText)) !== null) {
                const societat = regexMatches[1];
                const borme = regexMatches[2];
                const codi = regexMatches[3];

                const jsonObject = {
                    Societat: societat,
                    Borme: borme,
                    Codi: codi,
                };

                jsonArray.push(jsonObject);
            }

            const jsonString = JSON.stringify(jsonArray, null, 2);
            return jsonArray;

        } catch (error) {

            console.error("No s'ha trobat cap BORME d'aquesta data.", error);
            alert("No s'ha trobat cap BORME d'aquesta data.");
        }
    }


    // FUNCIÓ PER EXTREURE EL LLISTAT D'ENTITATS DEL RSP DE DADES OBERTES

    async function getEntitats() {
        const url = 'https://analisi.transparenciacatalunya.cat/resource/gr39-ik6u.json';

        try {
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();

                const entitats = [];
                for (const d of data) {
                    if (Object.keys(d).length > 0) {
                        entitats.push(d.denominaci);
                    }
                }

		// Afegir noms desactualitzats d'entitats

                const entitats2 = [
                    ['ICF Banc, Entitat de Crèdit, SAU'],
                    ['LoteriesdeCatalunyaSAU'],
                    ['LoteriesdeCatalunyaSA'],
                    ['CorporacióCatalanadeMitjansAudiovisualsSA'],
                    ['CorporacioCatalanadeMitjansAudiovisualsSA'],
                    ['TeatreNacionaldeCatalunyaSA'],
                    ['InfraestructuresdelaGeneralitatdeCatalunyaSAU'],
                    ['InfraestructuresdelaGeneralitatdeCatalunyaSA'],
                    ['EquacatSA'],
                    ['CentralsiInfraestructuresperalaMobilitatilesActivitatsLogístiquesSAU(CIMALSA)'],
                    ['CentralsiInfraestructuresperalaMobilitatilesActivitatsLogístiquesSA'],
                    ['CentralsiInfraestructuresperalaMobilitatilesActivitatsLogístiquesSAU'],
                    ['CentralsiInfraestructuresperalaMobilitatilesActivitatsLogistiquesSAU(CIMALSA)'],
                    ['CentralsiInfraestructuresperalaMobilitatilesActivitatsLogistiquesSA'],
                    ['CentralsiInfraestructuresperalaMobilitatilesActivitatsLogistiquesSAU'],
                    ["Promotorad'ExportacionsCatalanesSA"],
                    ['EmpresadePromocióiLocalitzacióIndustrialdeCatalunyaSA(AVANÇSA)'],
                    ['EmpresadePromocióiLocalitzacióIndustrialdeCatalunyaSA'],
                    ['EmpresadePromocioiLocalitzacióIndustrialdeCatalunyaSA(AVANÇSA)'],
                    ['EmpresadePromocioiLocalitzacióIndustrialdeCatalunyaSA'],
                    ['ForestalCatalanaSA'],
                    ["Sistemad'EmergènciesMèdiquesSA"],
                    ["Sistemad'EmergenciesMediquesSA"],
                    ['TVCMultimèdiaSL'],
                    ['TVCMultimediaSL'],
                    ['IntracatalòniaSA'],
                    ['IntracataloniaSA'],
                    ['InstitutCatalàdeFinancesCapitalSGEICSA'],
                    ['InstitutCataladeFinancesCapitalSGEICSA'],
                    ['InstitutCatalàdeFinancesCapitalSGECRSA'],
                    ['InstitutCataladeFinancesCapitalSGECRSA'],
                    ['CargometroRailTransportSA'],
                    ['CoordinacióLogísticaSanitàriaAIE'],
                    ['CoordinacioLogisticaSanitariaAIE'],
                    ['ComercialdelaForjaSA'],
                    ['Fira2000SA'],
                    ["TerminalIntermodaldel'EmpordaSL"],
                    ['SabadellGentGranCentredeServeisSA'],
                    ['VallterSA'],
                    ['LogaritmeServeisLogísticsAIE'],
                    ['LogaritmeServeisLogisticsAIE'],
                    ['ParcTecnològicdelVallèsSA'],
                    ['ParcTecnologicdelVallesSA'],
                    ['AeroportsPúblicsdeCatalunyaSL'],
                    ['AeroportsPublicsdeCatalunyaSL'],
                    ['BarcelonaSagreraAltaVelocitatSA'],
                    ['CircuitsdeCatalunyaSL'],
                    ['InstrumentsFinancersperaEmpresesInnovadoresSL(IFEM)'],
                    ['InstrumentsFinancersperaEmpresesInnovadoresSL'],
                    ["Societatd'EstibadelsPortsCatalansSA"],
                    ['AutometroSA'],
                    ['CircuitdeMotocròsdeCatalunyaSL'],
                    ['CircuitdeMotocrosdeCatalunyaSL'],
                    ['ArrendadoraFerroviàriaSA'],
                    ['ArrendadoraFerroviariaSA'],
                    ['BarnaclínicSA'],
                    ['BarnaclinicSA'],
                    ['LuxquantaTechnologiesSL'],
                    ['NuageTherapeuticsSL'],
                    ['ALLREADMACHINELEARNINGTECHNOLOGIESSL'],
                    ['INNOVATIVESOLUTIONSECOSYSTEMSA'],
                    ['LaSedadeBarcelonaSA'],
                    ['SabadellAsabysHealthInnovationInvestmentsSCRSA'],
                    ['InvereadyBiotechIIISCRSA'],
                    ['InvereadyFirstCapitalIIISCRSA'],
                    ['ActiusdeMuntanyaSA'],
                    ['DevicareSL'],
                    ['WatchitySL'],
                    ['AvalisdeCatalunyaSGR'],
                    ['BarcelonaEmprènSCRSA'],
                    ['BarcelonaEmprenSCRSA'],
                    ["BiomassadelesTerresdel'EbreSAenliquidació"],
                    ["BiomassadelesTerresdel'EbreSAenliquidacio"],
                    ["BiomassadelesTerresdel'EbreSA"],
                    ['CaixaCapitalTICSCRSA'],
                    ["Catalanad'IniciativesSA"],
                    ['CentrodeEnsayosInnovaciónyServiciosSL'],
                    ['CentrodeEnsayosInnovacionyServiciosSL'],
                    ['CombustiblesEcològicsCatalansSAenliquidació'],
                    ['CombustiblesEcològicsCatalansSA'],
                    ['CombustiblesEcologicsCatalansSAenliquidaco'],
                    ['CombustiblesEcologicsCatalansSA'],
                    ['CRCMarSA'],
                    ['CreapolisParcdelaCreativitatSA'],
                    ['EAPOsonaSudAltCongostSLP'],
                    ['EmpresadeTransformaciónAgrariaSASMEMP'],
                    ['EmpresadeTransformaciónAgrariaSA'],
                    ['EmpresadeTransformacionAgrariaSASMEMP'],
                    ['EmpresadeTransformacionAgrariaSA'],
                    ['EraBiotechSA'],
                    ['FinavesIVSA'],
                    ['HabitacSL'],
                    ['HealthequitySCRSA'],
                    ['IDIADAAutomotiveTechnologySA'],
                    ['ImatgeMèdicaIntercentresSL'],
                    ['ImatgeMedicaIntercentresSL'],
                    ['AirbusDSGeoSGSA'],
                    ['IngeniaCapitalSA'],
                    ['InvereadyInnvierteBiotechIISCRSA'],
                    ['InvereadyFirstCapitalSCRSA'],
                    ['InvereadyVentureFinanceISCR-PYMESA'],
                    ['InvereadyVentureFinanceISCR'],
                    ['LaboratorideReferènciadeCatalunyaSA'],
                    ['LaboratorideReferenciadeCatalunyaSA'],
                    ['LGAITechnologicalCenterSA'],
                    ['LlotjaAgropecuàriaMercolleidaSA'],
                    ['LlotjaAgropecuariaMercolleidaSA'],
                    ['MegaframAIEenliquidació'],
                    ['MegaframAIEenliquidacio'],
                    ['NautaTechInvestIISCRSA'],
                    ['NautaTechInvestIIISCRSA'],
                    ['ParcAudiovisualdeCatalunyaSL'],
                    ['ParcEòlicBaixEbreSA'],
                    ['ParcEolicBaixEbreSA'],
                    ['RencatAIE'],
                    ['SermetraSL'],
                    ["Serveid'IncineraciódelsResidusUrbansSA(SIRUSA)"],
                    ["Serveid'IncineraciódelsResidusUrbansSA"],
                    ["Serveid'IncineraciodelsResidusUrbansSA(SIRUSA)"],
                    ["Serveid'IncineraciodelsResidusUrbansSA"],
                    ['ServeisAuxiliarsalaSanitatAIE'],
                    ['SocietatAnónimadeValoritzacionsAgroramaderesenliquidació'],
                    ['SocietatAnónimadeValoritzacionsAgroramaderes'],
                    ['SocietatAnonimadeValoritzacionsAgroramaderesenliquidacio'],
                    ['SocietatAnonimadeValoritzacionsAgroramaderes'],
                    ['SocietatCatalanadePetrolisSA'],
                    ["SocietatEòlicadel'EnderrocadaSA"],
                    ["SocietatEolicadel'EnderrocadaSA"],
                    ['SpinnakerInvestSCRSA'],
                    ['SuceramEnergiaElèctricaAIE'],
                    ['SuceramEnergiaElectricaAIE'],
                    ['TorredeCollserolaSA'],
                    ['TramviaMetropolitàdelBesòsSA'],
                    ['TramviaMetropolitadelBesosSA'],
                    ['TramviaMetropolitàSA'],
                    ['TramviaMetropolitaSA'],
                    ['VenturcapIISCRSA'],
                    ['GestoradeRunesdelaConstruccióSA'],
                    ['GestoradeRunesdelaConstruccioSA'],
                    ['CatlabCentreAnalítiquesTerrassaAIE'],
                    ['CatlabCentreAnalitiquesTerrassaAIE'],
                    ["ConsorcideSalutid'AtencióSocialdeCatalunyaSA"],
                    ["ConsorcideSalutid'AtencioSocialdeCatalunyaSA"],
                    ['Interhospitalia-2AIE'],
                    ["PoligeneracióParcdel'AlbaST4SA"],
                    ["PoligeneracioParcdel'AlbaST4SA"],
                    ['CaixaCapitalBiomedSCRSA'],
                    ['CaixaInnvierteIndustriaSCRSA'],
                    ['AprovisionamentsSantaTeclaAIE'],
                    ['NetejaSantaTeclaAIE'],
                    ['CimneTecnologiaSA'],
                    ['CompassIngenieríaySistemasSA'],
                    ['ComputationalandInformationTechnologiesSA'],
                    ['FreshWaterNatureSL'],
                    ['BuildairIngenieriayArquitecturaSA'],
                    ['BuildairIngenieríayArquitecturaSA'],
                    ['LyncosTechnologiesSL'],
                    ['PortableMultimediaSolutionsSL'],
                    ['HealthappSL'],
                    ['FGCRAILSA'],
                    ['SocietatCatalanaperalaMobilitatSA'],
                    ['ForestBioengineeringSolutionsSAU'],
                    ['ForestBioengineeringSolutionsSA'],
                    ['RobSurgicalSystemsSL'],
                    ['BeedataAnalyticsSL'],
                    ['VirtualBodyworksSL'],
                    ['NostrumBioDiscoverySL'],
                    ['AelixTherapeuticsSL'],
                    ['PeptomycSL'],
                    ['EodyneSystemsSL'],
                    ['InnovexTherapeuticsSL'],
                    ['BraingazeSL'],
                    ['ScipediaSL'],
                    ['VisualTaggingServicesSL'],
                    ['FueliumSL'],
                    ['PaperdropDiagnosticsSL'],
                    ['GassoCimneInergySL'],
                    ['PneumaticStructuresTechnologiesSL'],
                    ['InlocRoboticsSL'],
                    ['ProcarelightSL'],
                    ['HemophotonicsSL'],
                    ['TransplantBiotechSL'],
                    ['SpecificPigSL'],
                    ['ChemotargetsSL'],
                    ['ManresanadeMicrobacteriologiaSL'],
                    ['SumaCapitalGrowthFundISCRSA'],
                    ['OrchestraScientificSL'],
                    ['MicroomicsSystemsSL'],
                    ['QuantitativeGenomicMedicineLaboratoriesSL'],
                    ['SeqeraLabsSL'],
                    ['EuronaWirelessTelecomSA'],
                    ['MercadosdeAbastecimientosdeBarcelonaSA'],
                    ['NeosSurgerySL'],
                    ['GEIEFORESPIR'],
                    ['QusideTechnologiesSL'],
                    ['AuricaIIIBSCRSA'],
                    ['TreellumTechnologiesSL'],
                    ['MarinadeBadalonaSA'],
                    ['OnaTherapeuticsSL'],
                    ['PentabilitiesSL'],
                    ['MiwendoSolutionsSL'],
                    ['InbrainNeuroelectronicsSL'],
                    ['OnechainImnunotherapeuticsSL'],
                    ['PulmobioticsSL'],
                    ['QurvTechnologiesSL'],
                    ['AheadTherapeuticsSL'],
                    ['NorthernMosaicLP'],
                    ['PaloBiofarmaSL'],
                    ['FGCMOBILITATSA'],
                    ['OmniScopeLimited'],
                    ['SixsensoTechnologiesSL'],
                    ['BaretekBarcelonaDetectorTechnologiesSL'],
                    ['DeepDetectionSL'],
                    ['OrikineBioSL'],
                    ['EnergiesRenovablesPubliquesDeCatalunyaSA'],
                    ['EnergiesRenovablesPubliquesDeCatalunyaSAU'],
                    ['EnergiesRenovablesPúbliquesDeCatalunyaSA'],
                    ['EnergiesRenovablesPúbliquesDeCatalunyaSAU']
                ]; // Afegeix les entitats de la llista entitats2

                const flat_list = entitats2.flat();
                const finalEntitats = entitats.concat(flat_list);

                const entitats3 = finalEntitats.map(processEntitat);

                // La variable 'entitats3' conté la llista processada

                // Elimina els signes de puntuació
                const entitatsSensePuntuacio = entitats3.map(eliminarPuntuacio);

                // La variable 'entitatsSensePuntuacio' conté les dades sense signes de puntuació
                return entitatsSensePuntuacio;
            } else {
                console.error('Error en la petició');
            }
        } catch (error) {
            console.error('Error en la petició', error);
        }
    }

    function processEntitat(entitat) {
        return eliminarAccents(entitat.split(" ").map(paraula => {
            return paraula.replace(/\([^)]*\)|\bSA?\b|\bSL?\b|\bAIE?\b|\bSAU?\b|\bSAL?\b/g, '').trim();
        }).join(" "));
    }

    function eliminarPuntuacio(text) {
        return text.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, '').trim();
    }


    // BUSCAR SOCIETATS DEL RSP A L'ÍNDEX DEL BORME

    // RETORNA LES COINCIDÈNCIES ENTRE LLISTA SOCIETATS RSP I L'ÍNDEX DEL BORME

function eliminarAccents(text) {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

    async function coincidencies() {
        try {
            // Espera que l'objecte JSON sigui creat
            const indexBORME = await getTextFromPDF();
            const entitats = await getEntitats();

            // Ara pots utilitzar jsonObject amb seguretat

            // console.log(entitats);
            // console.log(indexBORME);

            function mostrarRegistresCoincidents(entitats, indexBORME) {
                // Filtra els registres de "indexBORME" que coincideixen amb les entitats
                const registresCoincidents = indexBORME.filter(registre => {
                    const nomSocietat = registre.Societat.replace(/\([^)]*\)|\bSA?\b|\bSL?\b|\bAIE?\b|\bSAU?\b|\bSAL?\b/g, '').trim().toLowerCase().replace(/\s|\./g, '').replace("'", "").replace("d'", "").replace("l'", "");
                    return entitats.some(entitat => nomSocietat.startsWith(eliminarAccents(eliminarPuntuacio(entitat.toLowerCase().replace(/\s/g, '').replace("'", "").replace("d'", "").replace("l'", "")))));
                });

                return registresCoincidents;
            }

            const registresCoincidents = mostrarRegistresCoincidents(entitats, indexBORME);
            // console.log(registresCoincidents);

            return registresCoincidents;

        } catch (error) {
            console.error('Hi ha hagut un error:', error);
        }
    }



    // CREAR FUNCIÓ PER OBTENIR LES INSCRIPCIONS DELS BORMES SELECCIONATS I DESCARREGAR-LES EN FORMAT XLSX

// const dataEnFormatAAAAMMDD = "2023/11/10";

    async function extraccio() {
        try {
            // Espera que l'objecte JSON sigui creat
            const extreure = await coincidencies();

            // Construir URLs dels BORMEs a consultar i afegir-les a un nou camp del JSON

            extreure.forEach((registre) => {
                registre.URL = `https://www.boe.es/borme/dias/` + dataEnFormatAAAAMMDD + `/pdfs/${registre.Borme}.pdf`;
            });

            console.log(extreure);

            return extreure;

        } catch (error) {
            console.error('Hi ha hagut un error:', error);
        }
    }

async function matriuConsulta() {

  try {
    // Mostrar la imatge d'animació de càrrega
    document.getElementById('loadingImage').style.display = 'block';

    const dadesAmbURLs = await extraccio();
    const resultatsGlobals = []; // Variable per emmagatzemar tots els resultats

    for (const registre of dadesAmbURLs) {
      const codiUnicMap = new Map(); // Mapa per emmagatzemar codis únics
      if (!codiUnicMap.has(registre.URL)) {
        codiUnicMap.set(registre.URL, [registre.Codi]);
      } else {
        codiUnicMap.get(registre.URL).push(registre.Codi);
      }

      const url = registre.URL;
      const codis = codiUnicMap.get(url);

      try {
        const resultats = await extreureTextBorme(url, codis);
        if (resultats.length > 0) {
          // Imprimeix els resultats de cada PDF
          console.log('Resultats per a URL:', url);
          console.log(resultats);
          resultatsGlobals.push(...resultats); // Afegir els resultats a la variable global
        }
      } catch (pdfError) {
        console.error(`Hi ha hagut un error en processar el PDF de la URL ${url}: ${pdfError}`);
      }
      // Amagar la imatge d'animació de càrrega
      document.getElementById('loadingImage').style.display = 'none';
    }

    if (resultatsGlobals && resultatsGlobals.length > 0) {
      // Crear un full de càlcul amb tots els resultats
      const ws = XLSX.utils.json_to_sheet(resultatsGlobals);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Dades");

      // Descarregar l'arxiu XLSX
      XLSX.writeFile(wb, dataEnFormatAAAAMMDD.replaceAll("/", "") + " BORME cerca.xlsx");

setTimeout(function() {
  alert("XLSX DESCARREGAT");
}, 100); 
	    
    } else {

      document.getElementById('loadingImage').style.display = 'none';
setTimeout(function() {
  alert("No s'ha trobat cap entitat del RSP al BORME d'aquesta data");
}, 100); 
    }
  } catch (error) {
    document.getElementById('loadingImage').style.display = 'none';
    console.error('Hi ha hagut un error:', error);
    // Amagar la imatge d'animació de càrrega
    document.getElementById('loadingImage').style.display = 'none';
  }
}



    // Crida la funció per extreure la matriu de consulta
    matriuConsulta();

    async function extreureTextBorme(url, codis) {
        const pdfUrl = url;
        console.log(pdfUrl);

        const pdfjsLib = window['pdfjs-dist/build/pdf'];
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'pdf.worker.min.js';

        const response = await fetch(pdfUrl);
        const arrayBuffer = await response.arrayBuffer();
        const pdfData = new Uint8Array(arrayBuffer);

        try {
            const pdf = await pdfjsLib.getDocument({
                data: pdfData
            }).promise;

            let allText = '';
            let currentParagraph = '';
            let lastY = null;
            const MIN_Y_DIFFERENCE = 10;

            for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
                const page = await pdf.getPage(pageNumber);
                const textContent = await page.getTextContent();

                let fullText = '';

                textContent.items.forEach(item => {
                    if (lastY === null || Math.abs(item.transform[5] - lastY) <= MIN_Y_DIFFERENCE) {
                        currentParagraph += item.str + ' ';
                    } else {
                        const trimmedParagraph = currentParagraph.trim();
                        if (trimmedParagraph !== '') {
                            fullText += trimmedParagraph + '\n';
                        }
                        currentParagraph = item.str + ' ';
                    }
                    lastY = item.transform[5];
                });

                const trimmedParagraph = currentParagraph.trim();
                if (trimmedParagraph !== '') {
                    fullText += trimmedParagraph + '\n';
                }

                allText += fullText;
                allText = allText.replace(/\n\n/g, ' ');

                currentParagraph = '';
                lastY = null;
            }

            const regex = /(^\d+) - (.*)+\n((.*)+)\n/gm;
            const paragrafList = document.getElementById('paragrafList');

            let regexMatches;
            let jsonArray = [];

            while ((regexMatches = regex.exec(allText)) !== null) {
                const codi = regexMatches[1];
                const societat = regexMatches[2];
                const inscripcio = regexMatches[3];

                if (codis.includes(codi)) {
                    const jsonObject = {
                        Codi: codi,
                        URL: url,
                        Societat: societat,
                        Inscripció: inscripcio,
                    };
                    jsonArray.push(jsonObject);
                }
            }

            return jsonArray;

        } catch (error) {
            console.error('Hi ha hagut un error en processar el PDF:', error);
            alert('Hi ha hagut un error en processar el PDF.');
        }
    }
  });
});
