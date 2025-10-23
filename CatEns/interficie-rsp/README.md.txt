```markdown
# Web port de CatEns / CanvasTree

Aquesta carpeta `web/` conté una versió client-side (HTML + CSS + JS) de l'script `CatEns/interficie-rsp.py`.

Com s'executa
1. Obre `web/index.html` en un navegador modern (Chrome, Firefox, Edge).
2. Utilitza els botons a la barra superior:
   - "Importar JSON": carregar una estructura d'arbre des d'un fitxer `.json` (mateix format recursiu 'children').
   - "Exportar JSON": descarregar l'estat actual com a `.json`.
   - "Carregar exemple": carrega un `sample_data.json` de prova.
3. Interaccions:
   - Click a la primera columna selecciona la fila.
   - Doble click a la primera columna afegeix un fill (segons jerarquia).
   - Doble click a la columna "Carrec" (només per person) permet editar en línia.
   - Click a la columna "Eliminar" canvia l'estat (☐ / ☒) i propaga restauracions.
   - Click a la columna "DretVot" (només per member) canvia l'estat i afecta càlculs.
   - Les columnes "Inicial" vs "Actual" es pinten en vermell/verd quan difereixen.

Limitacions i decisions de disseny
- La versió web no fa virtualització (renderitza totes les files). Si tens arbres molt grans, convé implementar virtualització.
- Es tracta d'una implementació client-only sense servidor.
- L'UI i l'usabilitat estan optimitzades per a navegadors d'escriptori.
- Mantenim la major part de la lògica de càlcul des del script original (count_valid_persons, refresh_tree_display_all).

Què es pot fer ara
- Afegir persistència (localStorage o backend).
- Afegir validacions més estrictes dels percentatges.
- Millorar l'accessibilitat i suport mòbil.
```