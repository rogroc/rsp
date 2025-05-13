async function consultaNIF(nif) {
  const base = 'https://opendata.registradores.org/directorio';
  const params = new URLSearchParams({
    p_p_id: 'org_registradores_opendata_portlet_BuscadorSociedadesPortlet',
    p_p_lifecycle: '2',
    p_p_state: 'normal',
    p_p_mode: 'view',
    p_p_resource_id: '/opendata/sociedades',
    p_p_cacheability: 'cacheLevelPage',
    _org_registradores_opendata_portlet_BuscadorSociedadesPortlet_mvcRenderCommandName: '/sociedades',
    _org_registradores_opendata_portlet_BuscadorSociedadesPortlet_term: nif
  });
  const url = 'https://opendata.registradores.org/directorio?p_p_id=org_registradores_opendata_portlet_BuscadorSociedadesPortlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=%2Fopendata%2Fsociedades&p_p_cacheability=cacheLevelPage&_org_registradores_opendata_portlet_BuscadorSociedadesPortlet_mvcRenderCommandName=%2Fsociedades&_org_registradores_opendata_portlet_BuscadorSociedadesPortlet_term='+nif;

  // Envia la petició i espera 10 segons perquè el servei generi el JSON
  await new Promise(res => setTimeout(res, 3000));

  const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!resp.ok) throw new Error(`Resposta HTTP ${resp.status}`);

  const text = await resp.text();
  try {
    return JSON.parse(text);
  } catch (e) {
    throw new Error('La resposta no és un JSON vàlid.');
  }
}

document.getElementById('cerca').addEventListener('click', async () => {
  const nif = document.getElementById('nif').value.trim();
  const missatge = document.getElementById('missatge');
  const contenidor = document.getElementById('resultat');
  const tbody = document.querySelector('#taula-resultats tbody');

  // Netegem estat inicial
  missatge.textContent = 'Enviant petició...';
  contenidor.style.display = 'none';
  tbody.innerHTML = '';

  try {
    const data = await consultaNIF(nif);
    const empresa = data.data?.[0];
    if (!empresa) {
      missatge.textContent = 'No s\'ha trobat cap dada per aquest NIF.';
      return;
    }

    // Camps a mostrar
    const camps = [
      'nif',
      'denominacion',
      'denominacionNormalized',
      'estado',
      'domicilioSocial',
      'registro',
      'actividadEconomica',
      'euid',
      'irus'
    ];

    let irusVal = '';
    let denomNorm = '';

    // Omplim la taula
    camps.forEach(clau => {
      const tr = document.createElement('tr');
      const tdClau = document.createElement('td');
      tdClau.textContent = clau;
      const tdValor = document.createElement('td');
      let valor = empresa[clau];
      if (valor === undefined) valor = '';
      else if (typeof valor === 'object') valor = JSON.stringify(valor);
      tdValor.textContent = valor;
      tr.append(tdClau, tdValor);
      tbody.appendChild(tr);

      // Desa valors per URL de detall
      if (clau === 'irus') irusVal = valor;
      if (clau === 'denominacionNormalized') denomNorm = valor;
    });

    missatge.textContent = 'Dades obtingudes:';
    contenidor.style.display = 'block';

    // Obre URL detall en nova pestanya
    if (irusVal && denomNorm) {
      const detallURL = `https://opendata.registradores.org/directorio/-/sociedad/${irusVal}/${denomNorm}`;
      window.open(detallURL, '_blank');
    }
  } catch (err) {
    missatge.textContent = `Error: ${err.message}`;
  }
});
