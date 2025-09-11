import streamlit as st
import json
from typing import Optional

# ───────────────────────────────
# Classe principal
# ───────────────────────────────
class StreamlitTree:
    def __init__(self, columns):
        self.columns = columns
        self.items = {}
        self.children_map = {}
        self.parent_map = {}
        self._next_iid = 0

    # ────────── Inserció i jerarquia ──────────
    def insert(self, parent, text="", values=(), node_type=None):
        iid = f"node_{self._next_iid}"
        self._next_iid += 1

        indent = 0
        if parent:
            parent_item = self.items.get(parent)
            indent = parent_item["indent"] + 1 if parent_item else 1

        expected_vals = len(self.columns) - 1
        vals = list(values) if values else []
        if len(vals) < expected_vals:
            vals.extend([""] * (expected_vals - len(vals)))
        elif len(vals) > expected_vals:
            vals = vals[:expected_vals]

        meta = {"initial_values": list(vals), "initial_text": text}
        if node_type:
            meta["type"] = node_type
            meta["_locked_type"] = True

        self.items[iid] = {
            "text": text,
            "values": vals,
            "indent": indent,
            "expanded": True,
            "meta": meta
        }

        self.children_map.setdefault(parent, []).append(iid)
        self.parent_map[iid] = parent
        return iid

    def get_children(self, iid=None):
        return self.children_map.get(iid, [])

    def parent(self, iid):
        return self.parent_map.get(iid)

    # ────────── Carregar dades ──────────
    def _load_from_data(self, data):
        self.items.clear()
        self.children_map.clear()
        self.parent_map.clear()
        self._next_iid = 0

        def insert_node(node, parent=None):
            text = node.get("text", "")
            values = node.get("values", [])
            node_type = node.get("meta", {}).get("type")
            iid = self.insert(parent, text=text, values=values, node_type=node_type)
            for child in node.get("children", []):
                insert_node(child, iid)

        for node in data:
            insert_node(node)

    # ────────── Funcions percentatges ──────────
    def count_valid_persons(self, parent_iid):
        total = 0
        for ch in self.get_children(parent_iid):
            meta = self.items[ch]["meta"]
            if meta.get("eliminar"):
                continue
            if meta.get("type") == "person":
                total += 1
            else:
                total += self.count_valid_persons(ch)
        return total

    def refresh_tree_display_all(self):
        def is_effectively_eliminated(iid):
            cur = iid
            while cur:
                meta = self.items[cur]["meta"]
                if meta.get("eliminar"):
                    return True
                cur = self.parent_map.get(cur)
            return False

        for iid, item in self.items.items():
            meta = item["meta"]
            t = meta.get("type")
            # Inicialitzar columnes
            for col in ["PersonesParticipActual","PersonesMembreActual",
                        "PercentatgeParticip","Percentatge","PercentatgePersona"]:
                if col in self.columns:
                    idx = self.columns.index(col)
                    if idx-1 < len(item["values"]):
                        item["values"][idx-1] = "0.00" if "Percentatge" in col else "0"

            if is_effectively_eliminated(iid):
                continue

            # Persones
            if t == "person":
                parent_entity = iid
                while parent_entity and self.items[parent_entity]["meta"].get("type") != "entity":
                    parent_entity = self.parent_map.get(parent_entity)
                total_entity = self.count_valid_persons(parent_entity) if parent_entity else 0
                if total_entity > 0 and meta.get("dret_vot_parent"):
                    pct = 100/total_entity
                else:
                    pct = 0
                idx = self.columns.index("PercentatgePersona")-1
                if 0 <= idx < len(item["values"]):
                    item["values"][idx] = f"{pct:.2f}"

            # Membres
            elif t == "member":
                cnt = self.count_valid_persons(iid)
                idx_cnt = self.columns.index("PersonesMembreActual")-1
                if 0 <= idx_cnt < len(item["values"]):
                    item["values"][idx_cnt] = str(cnt)
                idx_pct = self.columns.index("Percentatge")-1
                parent_entity = iid
                while parent_entity and self.items[parent_entity]["meta"].get("type") != "entity":
                    parent_entity = self.parent_map.get(parent_entity)
                total_entity = self.count_valid_persons(parent_entity) if parent_entity else 0
                if 0 <= idx_pct < len(item["values"]):
                    pct = (cnt/total_entity*100 if total_entity>0 and meta.get("dret_vot") else 0)
                    item["values"][idx_pct] = f"{pct:.2f}"

            # Partícips
            elif t == "particip":
                total_persons = 0
                stack = [iid]
                while stack:
                    n = stack.pop()
                    nmeta = self.items[n]["meta"]
                    if nmeta.get("type")=="member" and nmeta.get("dret_vot"):
                        total_persons += self.count_valid_persons(n)
                    stack.extend(self.get_children(n))
                idx_cnt = self.columns.index("PersonesParticipActual")-1
                if 0 <= idx_cnt < len(item["values"]):
                    item["values"][idx_cnt] = str(total_persons)
                idx_pct = self.columns.index("PercentatgeParticip")-1
                parent_entity = iid
                while parent_entity and self.items[parent_entity]["meta"].get("type") != "entity":
                    parent_entity = self.parent_map.get(parent_entity)
                total_entity = self.count_valid_persons(parent_entity) if parent_entity else 0
                if 0 <= idx_pct < len(item["values"]):
                    pct = total_persons/total_entity*100 if total_entity>0 else 0
                    item["values"][idx_pct] = f"{pct:.2f}"

    # ────────── Render UI amb Streamlit ──────────
    def render_tree_ui(self):
        st.markdown("### Arbre jeràrquic")
        def render_node(iid, indent=0):
            item = self.items[iid]
            meta = item["meta"]
            t = meta.get("type")
            styles = {"entity":"#FFFFFF","tipus":"#F5F5F5",
                      "particip":"#D4EDDA","member":"#D1ECF1","person":"#E8E8FA"}
            row_style = f"background-color:{styles.get(t,'#FFFFFF')}; padding:3px;"

            cols = st.columns(len(self.columns))
            cols[0].markdown(f"<div style='{row_style}'>{'&nbsp;'*4*indent}{item['text']}</div>", unsafe_allow_html=True)
            eliminar = cols[1].checkbox("", value=meta.get("eliminar", False), key=f"eliminar_{iid}")
            meta["eliminar"] = eliminar
            dret_vot = cols[2].checkbox("", value=meta.get("dret_vot", False), key=f"dretvot_{iid}")
            meta["dret_vot"] = dret_vot
            for idx, col_name in enumerate(self.columns[3:], start=3):
                val = item["values"][idx-1] if idx-1 < len(item["values"]) else ""
                new_val = cols[idx].text_input(col_name, val, key=f"{col_name}_{iid}")
                if idx-1 < len(item["values"]):
                    item["values"][idx-1] = new_val

            for ch in self.get_children(iid):
                render_node(ch, indent+1)

        roots = [iid for iid, _ in self.items.items() if self.parent_map.get(iid) is None]
        for r in roots:
            render_node(r)

    # ────────── Botó importar dades obertes ──────────
    def importar_dades_obertes(self):
        try:
            data = dadesObertes()  # Aquesta funció l'has de definir
            self._load_from_data(data)
            self.refresh_tree_display_all()
            st.success("Dades obertes carregades correctament!")
        except Exception as e:
            st.error(f"No s'han pogut carregar dades obertes: {e}")


# ───────────────────────────────
# Execució Streamlit
# ───────────────────────────────
st.title("Arbre jeràrquic amb percentatges")

columns = [
    "Nom / Nivell", "Eliminar", "DretVot",
    "PersonesParticipInicial", "PersonesParticipActual",
    "PercentatgeParticipInicial", "PercentatgeParticip",
    "PersonesMembreInicial", "PersonesMembreActual",
    "PercentatgeInicial", "Percentatge",
    "PercentatgePersonaInicial", "PercentatgePersona",
    "CarrecInicial", "Carrec"
]

tree = StreamlitTree(columns)

# ─── Sidebar ───
st.sidebar.header("Gestió d'arbre")
uploaded_file = st.sidebar.file_uploader("Carregar estat JSON", type="json")
if uploaded_file:
    tree.load_from_file(uploaded_file)
st.sidebar.button("Importar dades obertes", on_click=tree.importar_dades_obertes)
st.sidebar.download_button("Descarregar estat JSON", tree.export_json(), file_name="arbre.json")

# ─── Render arbre ───
tree.render_tree_ui()
tree.refresh_tree_display_all()
