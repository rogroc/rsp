  var urlbase1 = "https://analisi.transparenciacatalunya.cat/resource/ub8p-uqwj.json?$query=";
  var urlbase2 = "https://analisi.transparenciacatalunya.cat/Legislaci-just-cia/Acords-del-Govern/ub8p-uqwj/explore/query/";
  
  var cosurl = "SELECT%0A%20%20%60codi%60%2C%0A%20%20%60departament%60%2C%0A%20%20%60titol%60%2C%0A%20%20%60any%60%2C%0A%20%20%60datasessio%60%2C%0A%20%20%60document1%60%2C%0A%20%20%60document2%60%2C%0A%20%20%60document3%60%2C%0A%20%20%60document4%60%2C%0A%20%20%60document5%60%2C%0A%20%20%60tipus_document%60%0AWHERE%0A%20%20caseless_contains(%60titol%60%2C%20%22ampliaci%C3%B3%20de%20capital%22)%0A%20%20%20%20OR%20(caseless_contains(%60titol%60%2C%20%22reducci%C3%B3%20de%20capital%22)%0A%20%20%20%20%20%20%20%20%20%20OR%20caseless_contains(%60titol%60%2C%20%22capital%20social%22))";

  var url = urlbase1+cosurl;

function carregarDadesEnviaCorreu() {
  // URL de les dades JSON

  // Realitza la sol·licitud HTTP
  var resposta = UrlFetchApp.fetch(url);
  
  // Converteix la resposta en un objecte JSON
  var dades = resposta.getContentText();
  var dadesJSON = JSON.parse(dades);

  // Obtenir la fulla de càlcul activa
  var fulla = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Obtenir les dades actuals a la fulla de càlcul
  var dadesActuals = fulla.getDataRange().getValues();

  // Crear una matriu per emmagatzemar les dades a afegir a la fulla, incloent els noms de les columnes
  var dadesPerAfegir = [];

  // Crear una variable per saber si s'han afegit dades noves
  var hiHaDadesNoves = false;

  // Obtenir la data actual
  var dataDescarrega = new Date();

  // Loop a través de les dades JSON i afegir-les a la matriu si no existeixen ja a les dades actuals
  for (var i = 0; i < dadesJSON.length; i++) {
    var filaJaExisteix = false;
    for (var j = 0; j < dadesActuals.length; j++) {
      if (dadesJSON[i].codi === dadesActuals[j][1]) { // Assumeixo que el camp "codi" és l'identificador únic
        filaJaExisteix = true;
        break;
      }
    }
    if (!filaJaExisteix) {
      var fila = [
        dataDescarrega,
        dadesJSON[i].codi,
        dadesJSON[i].departament,
        dadesJSON[i].titol,
        dadesJSON[i].any,
        dadesJSON[i].datasessio,
        dadesJSON[i].document1,
        dadesJSON[i].document2,
        dadesJSON[i].document3,
        dadesJSON[i].document4,
        dadesJSON[i].document5,
        dadesJSON[i].tipus_document
      ];
      dadesPerAfegir.push(fila);
      hiHaDadesNoves = true;
    }
  }

  // Afegir les noves dades a la fulla de càlcul
  if (hiHaDadesNoves) {
    fulla.getRange(fulla.getLastRow() + 1, 1, dadesPerAfegir.length, dadesPerAfegir[0].length).setValues(dadesPerAfegir);
    
    // Enviar correu electrònic si hi ha dades noves
    enviarCorreu(dataDescarrega, dadesPerAfegir, url);
  }
}

function enviarCorreu(dataDescarrega, dadesNoves, url) {
  // Lista de destinatarios separados por comas
  var destinataris = ["rogerrocavert@gencat.cat", "msalvatella@gencat.cat", "luisconesa@gencat.cat"];
  var assumpte = "Nou/s acord/s de govern (augments o reduccions de capital)";
  var cosMissatge = "Nou/s acord/s de govern amb referència a augments o reducions de capital\n\n";
  cosMissatge += "S'han afegit nous registres des de la següent URL:\n" + urlbase2 + cosurl + "\n\n";

  // Afegir les dades noves al cos del missatge
  cosMissatge += "Dades Noves:\n\n";
  for (var i = 0; i < dadesNoves.length; i++) {
    cosMissatge += "Data de Sessió: " + dadesNoves[i][5].replace("T00:00:00.000", "") + "\n"; // Index 5 correspon al camp "datasessio"
    cosMissatge += dadesNoves[i].slice(1).join(", ") + "\n";
    cosMissatge += "\n"; // Afegir una línia en blanc entre registres
  }

  // Enviar el correu electrònic a cada destinatario
  for (var j = 0; j < destinataris.length; j++) {
    var destinatari = destinataris[j];
    MailApp.sendEmail(destinatari, assumpte, cosMissatge);
  }
}
