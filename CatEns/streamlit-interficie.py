import streamlit as st
import json
import io

class CanvasTree:
    def __init__(self, columns, column_colors=None, row_height=25):
        self.columns = columns
        self.column_colors = column_colors or ["#FFFFFF"] * len(columns)
        self.row_height = row_height

        self.items = {}         # iid → metadata
        self.children_map = {}  # parent → [child_iids]
        self.parent_map = {}    # child → parent
        self._next_iid = 0
        self._selection = None

    # ───────────────────────────────
    # Guardar estat (JSON descarregable)
    # ───────────────────────────────
    def guardar_estat(self):
        """Genera un JSON descarregable amb l'estat actual de l'arbre."""

        def node_to_dict(iid):
            item = self.items[iid]
            return {
                "text": item["text"],
                "values": item["values"],
                "meta": item["meta"].copy(),
                "meta_initial_values": item["meta"].get("initial_values", []).copy(),
                "meta_initial_text": item["meta"].get("initial_text", item["text"]),
                "parent": self.parent_map.get(iid),
                "expanded": item.get("expanded", True),
                "children": [node_to_dict(child) for child in self.get_children(iid)]
            }

        roots = [iid for iid in self.items if self.parent_map.get(iid) is None]
        data = [node_to_dict(iid) for iid in roots]

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        buffer = io.BytesIO(json_str.encode("utf-8"))

        st.download_button(
            label="💾 Descarregar arbre en JSON",
            data=buffer,
            file_name="arbre.json",
            mime="application/json"
        )

    # ───────────────────────────────
    # Carregar estat (JSON pujat)
    # ───────────────────────────────
    def carregar_estat(self, filtre_text=None):
        """Carrega l'arbre des d’un fitxer JSON pujat amb Streamlit."""
        uploaded_file = st.file_uploader("📂 Carrega un fitxer JSON", type=["json"])
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                if isinstance(data, dict):
                    data = [data]
                self._load_from_data(data, filtre_text=filtre_text)
                st.success("Arbre carregat correctament ✅")
            except Exception as e:
                st.error(f"No s'ha pogut carregar l'estat: {e}")

    # ───────────────────────────────
    # Importar dades
    # ───────────────────────────────
    def importar(self, data=None, filtre_text=None):
        """
        Importa dades globals 'arrels', o bé dadesObertes(),
        o demana un JSON via Streamlit si no existeixen.
        """
        try:
            if data is None:
                gl = globals()
                potential = gl.get("arrels", None)
                if isinstance(potential, list):
                    data = potential
                else:
                    try:
                        globals()["arrels"] = dadesObertes()
                        data = globals()["arrels"]
                    except Exception:
                        uploaded_file = st.file_uploader("📂 Selecciona JSON d'import", type=["json"])
                        if uploaded_file is None:
                            return
                        try:
                            data = json.load(uploaded_file)
                        except Exception as e:
                            st.error(f"No s'ha pogut llegir el JSON d'import: {e}")
                            return

            if isinstance(data, dict):
                data = [data]

            self._load_from_data(data, filtre_text=filtre_text)
            st.success("Dades importades correctament ✅")
        except Exception as e:
            st.error(f"S'ha produït un error en importar: {e}")

    # ───────────────────────────────
    # Placeholder: funció que després implementarem
    # ───────────────────────────────
    def _load_from_data(self, data, filtre_text=None):
        """Carrega dades a l’arbre (funció pendent d’implementar)."""
        st.write("⚠️ Funció `_load_from_data` encara no implementada")
