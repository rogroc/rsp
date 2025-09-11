import streamlit as st
from typing import Optional

# ───────────────────────────────
# Estructura CanvasTree simplificada per Streamlit
# ───────────────────────────────
class CanvasTree:
    def __init__(self, columns, column_colors):
        self.columns = columns
        self.column_colors = column_colors
        self.items = {}
        self.children_map = {}
        self.parent_map = {}
        self._next_iid = 0
        self._selection = None

    # ────────────── Setters / Getters ──────────────
    def insert(self, parent, index="end", text="", values=(), node_type=None):
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

    def set(self, iid, column, value):
        if iid not in self.items:
            return
        item = self.items[iid]
        col_index = self.columns.index(column)
        if col_index == 0:
            item["text"] = value
        else:
            needed = col_index - 1
            if needed >= len(item["values"]):
                item["values"].extend([""] * (needed - len(item["values"]) + 1))
            item["values"][col_index - 1] = value

    def item(self, iid, option=None):
        if iid not in self.items:
            return {}
        return self.items[iid]

    # ────────────── Selecció ──────────────
    def selection_set(self, iid):
        self._selection = iid

    def selection(self):
        return (self._selection,) if self._selection else ()

    # ────────────── Snapshot ──────────────
    def _snapshot_initial_from_current(self, iid):
        item = self.items.get(iid)
        if not item:
            return
        item["meta"]["initial_values"] = list(item["values"])
        item["meta"]["initial_text"] = item["text"]

    # ────────────── Rendering per Streamlit ──────────────
    def render_tree(self):
        """Retorna llista de files jeràrquiques amb indentació i valors."""
        def visit(iid, rows):
            item = self.items[iid]
            text = ("    " * item["indent"]) + item["text"]
            row = [text] + item["values"]
            rows.append((iid, row))
            for ch in self.get_children(iid):
                visit(ch, rows)
        rows = []
        roots = [iid for iid in self.items if self.parent_map.get(iid) is None]
        for r in roots:
            visit(r, rows)
        return rows

# ───────────────────────────────
# Funcions globals de càlcul
# ───────────────────────────────
def count_valid_persons(tree, parent_iid):
    total = 0
    for ch in tree.get_children(parent_iid):
        meta = tree.item(ch)["meta"]
        if meta.get("eliminar"):
            continue
        if meta.get("type") == "person":
            total += 1
        else:
            total += count_valid_persons(tree, ch)
    return total

def refresh_tree_display_all(tree):
    # Exemple simplificat: només percentatges persona
    for iid in tree.items:
        item = tree.items[iid]
        meta = item["meta"]
        t = meta.get("type")
        if t == "person":
            tree.set(iid, "PercentatgePersona", "100.00")  # simplificat

# ───────────────────────────────
# Execució principal Streamlit
# ───────────────────────────────
def main():
    st.set_page_config(page_title="Arbre amb StreamlitTree", layout="wide")
    st.title("Arbre jeràrquic editable")

    columns = [
        "Nom / Nivell", "Eliminar", "DretVot",
        "PersonesParticipInicial", "PersonesParticipActual",
        "PercentatgeParticipInicial", "PercentatgeParticip",
        "PersonesMembreInicial", "PersonesMembreActual",
        "PercentatgeInicial", "Percentatge",
        "PercentatgePersonaInicial", "PercentatgePersona",
        "CarrecInicial", "Carrec"
    ]
    colors = ["#FFFFFF"] * len(columns)

    if "tree" not in st.session_state:
        st.session_state.tree = CanvasTree(columns, colors)
    tree = st.session_state.tree

    # Botons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Afegir entitat"):
            name = st.text_input("Nom de la nova entitat:", key="new_entity")
            if name:
                new_iid = tree.insert(None, text=name, node_type="entity")
                tree._snapshot_initial_from_current(new_iid)
    with col2:
        if st.button("Recalcul percentatges"):
            refresh_tree_display_all(tree)

    # Render arbre
    st.markdown("### Arbre")
    rows = tree.render_tree()
    for iid, row in rows:
        st.write(row)

if __name__ == "__main__":
    main()
