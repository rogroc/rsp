# arbre_streamlit.py
import streamlit as st
import json
from copy import deepcopy

# ───────────────────────────────
# Classe Tree emulant CanvasTree
# ───────────────────────────────
class StreamlitTree:
    def __init__(self, columns, colors):
        self.columns = columns
        self.column_colors = colors
        self.items = {}  # iid -> node info
        self.children_map = {}  # parent_iid -> [child_iid,...]
        self.parent_map = {}  # iid -> parent_iid
        self._next_iid = 0

        self._selection = None

    # ─── Inserció i accés ───
    def insert(self, parent, text="", values=(), node_type=None):
        iid = f"node_{self._next_iid}"
        self._next_iid += 1

        indent = 0
        if parent:
            indent = self.items[parent]["indent"] + 1

        expected_vals = len(self.columns) - 1
        vals = list(values)
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
            "meta": meta,
        }

        self.children_map.setdefault(parent, []).append(iid)
        self.parent_map[iid] = parent
        return iid

    def get_children(self, iid=None):
        return self.children_map.get(iid, [])

    def parent(self, iid):
        return self.parent_map.get(iid)

    def item(self, iid):
        return self.items.get(iid, {})

    def set(self, iid, column, value):
        item = self.items[iid]
        if column == self.columns[0]:
            item["text"] = value
        else:
            idx = self.columns.index(column) - 1
            item["values"][idx] = value

    # ─── Guardar i carregar ───
    def guardar_estat(self, filepath="tree_export.json"):
        def node_to_dict(iid):
            item = self.items[iid]
            return {
                "text": item["text"],
                "values": item["values"],
                "meta": item["meta"],
                "parent": self.parent_map.get(iid),
                "expanded": item.get("expanded", True),
                "children": [node_to_dict(ch) for ch in self.get_children(iid)],
            }
        roots = [iid for iid, _ in self.items.items() if self.parent_map.get(iid) is None]
        data = [node_to_dict(r) for r in roots]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success(f"Arbre guardat a {filepath}")

    def carregar_estat(self, filepath=None):
        if filepath is None:
            st.warning("Necessites passar un fitxer JSON.")
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.items.clear()
        self.children_map.clear()
        self.parent_map.clear()
        self._next_iid = 0
        def load_node(node, parent=None):
            iid = self.insert(parent, node.get("text", ""), node.get("values", []), node.get("meta", {}).get("type"))
            self.items[iid]["meta"].update(node.get("meta", {}))
            for child in node.get("children", []):
                load_node(child, iid)
        for r in data:
            load_node(r)
        st.success("Arbre carregat correctament.")

    # ─── Selecció ───
    def selection_set(self, iid):
        self._selection = iid

    def selection(self):
        return (self._selection,) if self._selection else ()

    # ─── Afegir fills ───
    def add_child(self, parent_iid, name):
        parent_meta = self.items[parent_iid]["meta"]
        hierarchy = {"entity": "tipus", "tipus": "particip", "particip": "member", "member": "person"}
        child_type = hierarchy.get(parent_meta.get("type"))
        if not child_type:
            return
        num_extra = max(0, len(self.columns) - 3)
        base_values = ["☐", ""] + [""] * num_extra
        new_iid = self.insert(parent_iid, text=name, values=base_values, node_type=child_type)
        new_meta = self.items[new_iid]["meta"]
        new_meta.setdefault("initial_values", list(base_values))
        new_meta.setdefault("initial_text", name)
        new_meta.setdefault("eliminar", False)
        if child_type == "member":
            new_meta.setdefault("dret_vot", False)
        if child_type == "person":
            new_meta.setdefault("carrec", "")
            new_meta.setdefault("dret_vot_parent", bool(parent_meta.get("dret_vot")))
        return new_iid

    # ─── Eliminació i dret de vot ───
    def toggle_eliminar(self, iid):
        meta = self.items[iid]["meta"]
        meta["eliminar"] = not meta.get("eliminar", False)

    def toggle_dret_vot(self, iid):
        meta = self.items[iid]["meta"]
        meta["dret_vot"] = not meta.get("dret_vot", False)

    # ─── Percentatges i càlcul ───
    def refresh_display(self):
        # Implementació simplificada: assigna percentatges segons dret de vot i eliminació
        entity_totals = {}
        def is_effectively_eliminated(iid):
            cur = iid
            while cur:
                if self.items[cur]["meta"].get("eliminar"):
                    return True
                cur = self.parent_map.get(cur)
            return False

        def count_valid_persons_effective(parent_iid):
            total = 0
            for ch in self.get_children(parent_iid):
                if is_effectively_eliminated(ch):
                    continue
                meta_ch = self.items[ch]["meta"]
                if meta_ch.get("type") == "person":
                    total += 1
                else:
                    total += count_valid_persons_effective(ch)
            return total

        for iid, item in self.items.items():
            meta = item["meta"]
            t = meta.get("type")
            if is_effectively_eliminated(iid):
                continue
            # Persones
            if t == "person":
                meta["PercentatgePersona"] = "0.0"
            elif t == "member":
                meta["Percentatge"] = "0.0"
            elif t == "particip":
                meta["PercentatgeParticip"] = "0.0"
            elif t == "entity":
                meta["PercentatgeParticip"] = "0.0"


# ───────────────────────────────
# Streamlit UI
# ───────────────────────────────
def render_tree_ui(tree):
    def render_node(iid):
        item = tree.items[iid]
        meta = item["meta"]
        t = meta.get("type")
        indent = item["indent"]

        st.markdown(f"<div style='padding-left:{indent*20}px;'>", unsafe_allow_html=True)

        cols = st.columns(len(tree.columns))
        # Primera columna: text amb input
        cols[0].text_input("Nom", value=item["text"], key=f"text_{iid}", on_change=tree.selection_set, args=(iid,))
        # Eliminar
        eliminar_val = meta.get("eliminar", False)
        cols[1].checkbox("Eliminar", value=eliminar_val, key=f"eliminar_{iid}", on_change=tree.toggle_eliminar, args=(iid,))
        # DretVot
        dret_val = meta.get("dret_vot", False)
        if t == "member":
            cols[2].checkbox("DretVot", value=dret_val, key=f"dret_{iid}", on_change=tree.toggle_dret_vot, args=(iid,))
        # Carrec
        if t == "person":
            idx_carrec = tree.columns.index("Carrec")
            cur_val = item["values"][idx_carrec-1]
            new_val = cols[idx_carrec].text_input("Carrec", value=cur_val, key=f"carrec_{iid}")
            tree.set(iid, "Carrec", new_val)

        # Botó afegir fill
        if t != "person":
            name = cols[0].text_input(f"Nom fill {iid}", key=f"childname_{iid}")
            if cols[0].button("Afegir fill", key=f"btn_child_{iid}"):
                if name.strip():
                    tree.add_child(iid, name.strip())

        st.markdown("</div>", unsafe_allow_html=True)

        # Fills
        for ch in tree.get_children(iid):
            render_node(ch)

    roots = [iid for iid, _ in tree.items.items() if tree.parent_map.get(iid) is None]
    for r in roots:
        render_node(r)

# ───────────────────────────────
# Execució Streamlit
# ───────────────────────────────
st.set_page_config(layout="wide")
st.title("Arbre jeràrquic amb Streamlit")

columns = [
    "Nom / Nivell", "Eliminar", "DretVot",
    "PersonesParticipInicial", "PersonesParticipActual",
    "PercentatgeParticipInicial", "PercentatgeParticip",
    "PersonesMembreInicial", "PersonesMembreActual",
    "PercentatgeInicial", "Percentatge",
    "PercentatgePersonaInicial", "PercentatgePersona",
    "CarrecInicial", "Carrec"
]
colors = ["#FFFFFF"]*len(columns)

tree = StreamlitTree(columns, colors)

# Sidebar: carregar / guardar
with st.sidebar:
    st.header("Opcions")
    uploaded_file = st.file_uploader("Carregar JSON", type="json")
    if uploaded_file:
        tree.carregar_estat(uploaded_file)

    if st.button("Guardar estat"):
        tree.guardar_estat("tree_export.json")

st.header("Arbre jeràrquic")
render_tree_ui(tree)
