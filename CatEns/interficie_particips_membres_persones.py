import streamlit as st
import json

# ───────────────────────────────
# Estructures de l'arbre
# ───────────────────────────────
if "tree_items" not in st.session_state:
    st.session_state.tree_items = {}
if "parent_map" not in st.session_state:
    st.session_state.parent_map = {}

COLUMNS = [
    "Nom / Nivell", "Eliminar", "DretVot",
    "PersonesParticipInicial", "PersonesParticipActual",
    "PercentatgeParticipInicial", "PercentatgeParticip",
    "PersonesMembreInicial", "PersonesMembreActual",
    "PercentatgeInicial", "Percentatge",
    "PercentatgePersonaInicial", "PercentatgePersona",
    "CarrecInicial", "Carrec"
]

# ───────────────────────────────
# Funcions auxiliars
# ───────────────────────────────
def get_children(iid):
    return [child for child, parent in st.session_state.parent_map.items() if parent == iid]

def is_effectively_eliminated(iid):
    cur = iid
    while cur is not None:
        meta = st.session_state.tree_items[cur]["meta"]
        if meta.get("eliminar"):
            return True
        cur = st.session_state.parent_map.get(cur)
    return False

def count_valid_persons_effective(parent_iid):
    total = 0
    for ch in get_children(parent_iid):
        if is_effectively_eliminated(ch):
            continue
        meta_ch = st.session_state.tree_items[ch]["meta"]
        if meta_ch.get("type") == "person":
            total += 1
        else:
            total += count_valid_persons_effective(ch)
    return total

def refresh_tree_display_all():
    # Calcular percentatges i totals
    entity_totals = {}
    for iid, item in st.session_state.tree_items.items():
        if item["meta"].get("type") == "entity" and not is_effectively_eliminated(iid):
            total_entity = 0
            stack = [iid]
            while stack:
                node_iid = stack.pop()
                if is_effectively_eliminated(node_iid):
                    continue
                meta = st.session_state.tree_items[node_iid]["meta"]
                if meta.get("type") == "member" and meta.get("dret_vot"):
                    total_entity += count_valid_persons_effective(node_iid)
                for child in get_children(node_iid):
                    stack.append(child)
            entity_totals[iid] = total_entity

    for iid, item in st.session_state.tree_items.items():
        t = item["meta"]["type"]
        # Inicialitzar columnes
        for col in ["PersonesParticipActual", "PersonesMembreActual", "PercentatgeParticip", "Percentatge", "PercentatgePersona"]:
            item["values"][COLUMNS.index(col)] = ""
        if is_effectively_eliminated(iid):
            if t == "person":
                item["values"][COLUMNS.index("PercentatgePersona")] = "0.00"
            elif t == "member":
                item["values"][COLUMNS.index("Percentatge")] = "0.00"
                item["values"][COLUMNS.index("PersonesMembreActual")] = "0"
            elif t in ("particip", "entity"):
                item["values"][COLUMNS.index("PercentatgeParticip")] = "0.00"
                item["values"][COLUMNS.index("PersonesParticipActual")] = "0"
            continue

        # Trobar l'entitat pare
        entity_iid = iid
        while entity_iid is not None and st.session_state.tree_items[entity_iid]["meta"].get("type") != "entity":
            entity_iid = st.session_state.parent_map.get(entity_iid)
        total_entity = entity_totals.get(entity_iid, 0) if entity_iid is not None else 0

        if t == "person":
            if item["meta"].get("dret_vot_parent") and total_entity > 0:
                pct = (1 / total_entity) * 100
                item["values"][COLUMNS.index("PercentatgePersona")] = f"{pct:.2f}"
            else:
                item["values"][COLUMNS.index("PercentatgePersona")] = "0.00"
        elif t == "member":
            cnt = count_valid_persons_effective(iid)
            item["values"][COLUMNS.index("PersonesMembreActual")] = str(cnt)
            if item["meta"].get("dret_vot") and total_entity > 0:
                pct = (cnt / total_entity) * 100
                item["values"][COLUMNS.index("Percentatge")] = f"{pct:.2f}"
            else:
                item["values"][COLUMNS.index("Percentatge")] = "0.00"
        elif t == "particip":
            total_persons = 0
            stack = [iid]
            while stack:
                node_iid = stack.pop()
                if is_effectively_eliminated(node_iid):
                    continue
                meta_node = st.session_state.tree_items[node_iid]["meta"]
                if meta_node.get("type") == "member" and meta_node.get("dret_vot"):
                    total_persons += count_valid_persons_effective(node_iid)
                for child in get_children(node_iid):
                    stack.append(child)
            item["values"][COLUMNS.index("PersonesParticipActual")] = str(total_persons)
            item["values"][COLUMNS.index("PercentatgeParticip")] = f"{(total_persons / total_entity * 100) if total_entity else 0:.2f}"
        elif t == "entity":
            item["values"][COLUMNS.index("PercentatgeParticip")] = f"{(100 if total_entity else 0):.2f}"

# ───────────────────────────────
# Funcions d'UI Streamlit
# ───────────────────────────────
def render_node(iid, level=0):
    item = st.session_state.tree_items[iid]
    indent = " " * level
    with st.expander(f"{indent}{item['values'][0]}", expanded=True):
        cols = st.columns([1, 0.2, 0.2])
        with cols[0]:
            st.text_input("Carrec", key=f"Carrec_{iid}", value=item["values"][COLUMNS.index("Carrec")])
        with cols[1]:
            if st.checkbox("Eliminar", key=f"Eliminar_{iid}", value=item["meta"].get("eliminar", False)):
                item["meta"]["eliminar"] = True
            else:
                item["meta"]["eliminar"] = False
        with cols[2]:
            if st.checkbox("DretVot", key=f"DretVot_{iid}", value=item["meta"].get("dret_vot", False)):
                item["meta"]["dret_vot"] = True
            else:
                item["meta"]["dret_vot"] = False

    # Afegir botó de nou fill
    if st.button(f"Afegeix fill a {item['values'][0]}", key=f"AddChild_{iid}"):
        child_type_map = {"entity": "tipus", "tipus": "particip", "particip": "member", "member": "person"}
        parent_type = item["meta"]["type"]
        if parent_type == "person":
            st.warning("Les persones no poden tenir fills.")
        else:
            child_type = child_type_map.get(parent_type)
            name = st.text_input(f"Nom del nou {child_type}:", key=f"NewName_{iid}")
            if name:
                new_iid = max(st.session_state.tree_items.keys(), default=0) + 1
                num_extra = len(COLUMNS) - 3
                base_values = ["☐", ""] + [""] * num_extra
                st.session_state.tree_items[new_iid] = {
                    "values": [name] + base_values,
                    "meta": {"type": child_type, "eliminar": False}
                }
                st.session_state.parent_map[new_iid] = iid

    # Render descendents
    for child in get_children(iid):
        render_node(child, level + 1)

# ───────────────────────────────
# Botons globals
# ───────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Guardar estat"):
        with open("tree_state.json", "w") as f:
            json.dump({
                "items": st.session_state.tree_items,
                "parent_map": st.session_state.parent_map
            }, f)
        st.success("Estat guardat!")

with col2:
    if st.button("Carregar estat"):
        try:
            with open("tree_state.json", "r") as f:
                data = json.load(f)
                st.session_state.tree_items = data["items"]
                st.session_state.parent_map = data["parent_map"]
            st.success("Estat carregat!")
        except Exception as e:
            st.error(f"Error al carregar: {e}")

with col3:
    if st.button("Importar"):
        st.info("Funció d'importar no implementada en aquesta demo.")

# ───────────────────────────────
# Render arbre principal
# ───────────────────────────────
for iid, item in st.session_state.tree_items.items():
    if st.session_state.parent_map.get(iid) is None:
        render_node(iid)

# Recalcular percentatges després de modificacions
refresh_tree_display_all()
