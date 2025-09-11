import streamlit as st
import json
from typing import List, Optional, Dict, Any
import pandas as pd
from streamlit_modal import Modal
import tempfile
import os

# ───────────────────────────────
# Classe TreeManager (gestió de l'estat de l'arbre)
# ───────────────────────────────
class TreeManager:
    def __init__(self):
        self.columns = [
            "Nom / Nivell", "Eliminar", "DretVot",
            "PersonesParticipInicial", "PersonesParticipActual",
            "PercentatgeParticipInicial", "PercentatgeParticip",
            "PersonesMembreInicial", "PersonesMembreActual",
            "PercentatgeInicial", "Percentatge",
            "PercentatgePersonaInicial", "PercentatgePersona",
            "CarrecInicial", "Carrec"
        ]
        
        self.column_colors = [
            "#FFFFFF", "#FFFFFF", "#FFFFFF",
            "#D4EDDA", "#D4EDDA", "#D4EDDA", "#D4EDDA",
            "#D1ECF1", "#D1ECF1", "#D1ECF1", "#D1ECF1",
            "#E8E8FA", "#E8E8FA", "#E8E8FA", "#E8E8FA"
        ]
        
        if 'tree_data' not in st.session_state:
            st.session_state.tree_data = {}
            st.session_state.children_map = {}
            st.session_state.parent_map = {}
            st.session_state.next_iid = 0
            st.session_state.expanded_state = {}
            st.session_state.selected_node = None
            st.session_state.editing_node = None
            st.session_state.editing_column = None
            
    def insert(self, parent, text="", values=(), node_type=None):
        iid = f"node_{st.session_state.next_iid}"
        st.session_state.next_iid += 1
        
        expected_vals = len(self.columns) - 1
        vals = list(values) if values is not None else []
        if len(vals) < expected_vals:
            vals.extend([""] * (expected_vals - len(vals)))
        elif len(vals) > expected_vals:
            vals = vals[:expected_vals]
        
        # Construir meta inicial
        meta = {"initial_values": list(vals), "initial_text": text}
        if node_type:
            meta["type"] = node_type
            meta["_locked_type"] = True
        
        st.session_state.tree_data[iid] = {
            "text": text,
            "values": vals,
            "meta": meta,
            "expanded": True,
        }
        
        if parent not in st.session_state.children_map:
            st.session_state.children_map[parent] = []
        st.session_state.children_map[parent].append(iid)
        st.session_state.parent_map[iid] = parent
        
        st.session_state.expanded_state[iid] = True
        return iid

    def get_children(self, iid=None):
        return st.session_state.children_map.get(iid, [])
    
    def parent(self, iid):
        return st.session_state.parent_map.get(iid)
    
    def item(self, iid, option=None):
        if iid not in st.session_state.tree_data:
            return {}
        item = st.session_state.tree_data[iid]
        if option is None:
            return {"text": item["text"], "values": item["values"], "meta": item["meta"]}
        return item.get(option)
    
    def set(self, iid, column=None, value=None):
        if iid not in st.session_state.tree_data:
            return
        
        item = st.session_state.tree_data[iid]
        if column is None:
            return
        
        col_index = self.columns.index(column)
        if col_index == 0:
            item["text"] = value
        else:
            needed = col_index - 1
            if needed >= len(item["values"]):
                item["values"].extend([""] * (needed - len(item["values"]) + 1))
            item["values"][col_index - 1] = value
            
            # Actualitzar meta si és necessari
            if column == "Carrec" and item["meta"].get("type") == "person":
                item["meta"]["carrec"] = value
    
    def toggle(self, iid):
        if iid in st.session_state.tree_data:
            st.session_state.tree_data[iid]["expanded"] = not st.session_state.tree_data[iid]["expanded"]
            st.session_state.expanded_state[iid] = st.session_state.tree_data[iid]["expanded"]
    
    def get_background_color_by_type(self, node_type):
        default_colors = {
            "entity": "#FFFFFF",    # Blanc (nivell 0)
            "tipus": "#F5F5F5",     # Gris suau (nivell 1)
            "particip": "#D4EDDA",  # Verd clar (nivell 2)
            "member": "#D1ECF1",    # Blau clar (nivell 3)
            "person": "#E8E8FA"     # Lila suau (nivell 4)
        }
        return default_colors.get(node_type, "#FFFFFF")
    
    def _netejar_values(self, node):
        """Neteja/normalitza els values i percentatges."""
        values = node.get("values", [""] * (len(self.columns) - 1))
        meta = node.get("meta", {}) or {}
        tipus_node = (meta.get("type") or "").lower()

        result = []

        carrec_inicial_val = ""
        if "CarrecInicial" in self.columns:
            carrec_inicial_idx = self.columns.index("CarrecInicial") - 1
            if 0 <= carrec_inicial_idx < len(values):
                carrec_inicial_val = values[carrec_inicial_idx] or meta.get("carrec", "")
                if not isinstance(carrec_inicial_val, str):
                    carrec_inicial_val = str(carrec_inicial_val)

        for idx, col in enumerate(self.columns[1:]):
            c_lower = col.lower().replace(" ", "").replace("_", "")

            if c_lower == "eliminar":
                result.append("☒" if meta.get("eliminar") else "☐")
            elif c_lower == "dretvot":
                if tipus_node == "member":
                    result.append("☒" if meta.get("dret_vot") else "☐")
                else:
                    result.append("")
            elif "inicial" in c_lower or "actual" in c_lower:
                base_col = col.replace("Inicial", "").replace("Actual", "")
                val = ""
                if base_col.lower() in meta:
                    val = meta.get(base_col.lower(), "")
                    if not isinstance(val, str):
                        val = str(val)
                else:
                    if idx < len(values):
                        val = values[idx] or ""
                        if not isinstance(val, str):
                            val = str(val)
                if base_col.lower() == "carrec" and (not val or not val.strip()) and carrec_inicial_val and carrec_inicial_val.strip():
                    val = carrec_inicial_val
                if "percentatge" in col.lower() and val:
                    try:
                        val_str = str(val).replace("%", "").replace(",", ".")
                        val_float = float(val_str)
                        val = f"{val_float:.2f}"
                    except ValueError:
                        val = "0.00"
                result.append(val)
            else:
                val = values[idx] if idx < len(values) else ""
                if not isinstance(val, str):
                    val = str(val)
                if col == "Carrec" and (not val or not val.strip()) and carrec_inicial_val and carrec_inicial_val.strip():
                    val = carrec_inicial_val
                if "percentatge" in col.lower() and val:
                    try:
                        val_str = str(val).replace("%", "").replace(",", ".")
                        val_float = float(val_str)
                        val = f"{val_float:.2f}"
                    except ValueError:
                        val = "0.00"
                result.append(val)

        expected = len(self.columns) - 1
        if len(result) < expected:
            result.extend([""] * (expected - len(result)))
        elif len(result) > expected:
            result = result[:expected]
        return result

    def _inserta_node(self, node, parent_iid=None):
        """Inserta un node (i recursivament els seus fills) a l'arbre."""
        text = node.get("text", "") or ""
        values = self._netejar_values(node)
    
        # Si el node JSON porta meta.type, el passem directament a insert
        node_meta = node.get("meta", {}) or {}
        node_type_to_pass = node_meta.get("type")
    
        iid = self.insert(parent_iid, text=text, values=values, node_type=node_type_to_pass)
    
        # Actualitzem el meta del item
        meta_existing = st.session_state.tree_data[iid]["meta"]
        for k, v in (node_meta.items()):
            if k == "type" and meta_existing.get("_locked_type"):
                continue
            meta_existing[k] = v
    
        # Si no hi ha cap type encara, deduïm segons el pare
        if "type" not in meta_existing or not meta_existing.get("type"):
            if parent_iid is None:
                ded_type = "entity"
            else:
                parent_type = st.session_state.tree_data[parent_iid]["meta"].get("type")
                mapping = {"entity": "tipus", "tipus": "particip", "particip": "member", "member": "person"}
                ded_type = mapping.get(parent_type, "entity")
            meta_existing["type"] = ded_type
    
        # Assegurar valors inicials
        meta_existing.setdefault("initial_values", node.get("meta_initial_values", list(values)))
        meta_existing.setdefault("initial_text", node.get("meta_initial_text", text))
    
        st.session_state.tree_data[iid]["meta"] = meta_existing
        st.session_state.tree_data[iid]["expanded"] = bool(node.get("expanded", True))
    
        # Inserir fills recursivament
        for child in node.get("children", []):
            self._inserta_node(child, iid)
    
        return iid

    def guardar_estat(self, filepath=None):
        """Guarda l'estat actual de l'arbre a un fitxer JSON."""
        try:
            def node_to_dict(iid):
                item = st.session_state.tree_data[iid]
                return {
                    "text": item["text"],
                    "values": item["values"],
                    "meta": item["meta"].copy(),
                    "meta_initial_values": item["meta"].get("initial_values", []).copy(),
                    "meta_initial_text": item["meta"].get("initial_text", item["text"]),
                    "parent": st.session_state.parent_map.get(iid),
                    "expanded": item.get("expanded", True),
                    "children": [node_to_dict(child) for child in self.get_children(iid)]
                }

            roots = [iid for iid, _item in st.session_state.tree_data.items() if st.session_state.parent_map.get(iid) is None]
            data = [node_to_dict(iid) for iid in roots]

            return json.dumps(data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            st.error(f"Error en guardar l'estat: {e}")
            return None

    def carregar_estat(self, data_str, filtre_text=None):
        """Carrega l'arbre d'una cadena JSON."""
        try:
            data = json.loads(data_str)
            if isinstance(data, dict):
                data = [data]

            if not isinstance(data, list) or not data:
                st.warning("No hi ha dades a importar.")
                return False

            # Esborrar estat anterior
            st.session_state.tree_data.clear()
            st.session_state.children_map.clear()
            st.session_state.parent_map.clear()
            st.session_state.next_iid = 0
            st.session_state.expanded_state.clear()
            st.session_state.selected_node = None
            st.session_state.editing_node = None
            st.session_state.editing_column = None

            # Inserir arrels
            for root_node in data:
                root_node.setdefault("meta", {}).setdefault("type", "entity")
                self._inserta_node(root_node)

            st.success("Arbre carregat correctament.")
            return True
            
        except Exception as e:
            st.error(f"Error en carregar l'estat: {e}")
            return False

    def importar_dades(self, data=None, filtre_text=None):
        """Importa dades des de JSON."""
        if data is None:
            return False
            
        if isinstance(data, dict):
            data = [data]

        # Netejar estat existent
        st.session_state.tree_data.clear()
        st.session_state.children_map.clear()
        st.session_state.parent_map.clear()
        st.session_state.next_iid = 0
        st.session_state.expanded_state.clear()
        st.session_state.selected_node = None

        # Insertar nous nodes
        for root_node in data:
            root_node.setdefault("meta", {}).setdefault("type", "entity")
            self._inserta_node(root_node)

        return True

# ───────────────────────────────
# Funcions d'ajuda per al càlcul
# ───────────────────────────────
def count_valid_persons(tree_manager, parent_iid):
    """Compta persones no eliminades sota un node."""
    total = 0
    for ch in tree_manager.get_children(parent_iid):
        meta = tree_manager.item(ch, "meta")
        if meta.get("eliminar"):
            continue
        if meta.get("type") == "person":
            total += 1
        else:
            total += count_valid_persons(tree_manager, ch)
    return total

def refresh_tree_display_all(tree_manager):
    """Recalcula percentatges i totals de persones."""
    # Aquesta funció és complexa i s'ha adaptat de l'original
    # Es necessitaria una implementació completa per a Streamlit
    pass

# ───────────────────────────────
# Funcions per a la visualització en Streamlit
# ───────────────────────────────
def render_node(tree_manager, iid, level=0):
    """Renderitza un node de l'arbre i els seus fills."""
    if iid not in st.session_state.tree_data:
        return
    
    node = st.session_state.tree_data[iid]
    meta = node["meta"]
    node_type = meta.get("type", "")
    children = tree_manager.get_children(iid)
    
    # Determinar si el node és expandible
    is_expandable = len(children) > 0 and node_type != "person"
    
    # Crear una fila amb les dades del node
    cols = st.columns([0.5] + [1] * (len(tree_manager.columns) - 1))
    
    # Columna de toggle/expansió
    with cols[0]:
        if is_expandable:
            expanded = st.session_state.expanded_state.get(iid, True)
            if st.button("▼" if expanded else "▶", key=f"toggle_{iid}"):
                tree_manager.toggle(iid)
                st.rerun()
        else:
            st.write("")
    
    # Columna del nom
    with cols[1]:
        bg_color = tree_manager.get_background_color_by_type(node_type)
        st.markdown(f"<div style='background-color:{bg_color}; padding:5px;'>{'    ' * level}{node['text']}</div>", 
                   unsafe_allow_html=True)
    
    # Resta de columnes
    for idx, col in enumerate(tree_manager.columns[1:], 2):
        with cols[idx]:
            if idx - 2 < len(node["values"]):
                value = node["values"][idx - 2]
                
                # Determinar color del text
                text_color = "black"
                if "Inicial" in col and idx - 2 < len(meta.get("initial_values", [])):
                    initial_val = meta["initial_values"][idx - 2]
                    if value != initial_val:
                        text_color = "red" if "Inicial" in col else "green"
                
                # Mostrar valor
                st.markdown(f"<div style='color:{text_color};'>{value}</div>", unsafe_allow_html=True)
    
    # Mostrar fills si està expandit
    if is_expandable and st.session_state.expanded_state.get(iid, True):
        for child in children:
            render_node(tree_manager, child, level + 1)

def render_tree(tree_manager):
    """Renderitza l'arbre complet."""
    st.header("Arbre de Participacions i Membres")
    
    # Capçaleres de columnes
    cols = st.columns([0.5] + [1] * (len(tree_manager.columns) - 1))
    for idx, col_name in enumerate(tree_manager.columns):
        with cols[idx]:
            st.markdown(f"**{col_name}**")
    
    # Arrels de l'arbre
    roots = [iid for iid in st.session_state.tree_data if st.session_state.parent_map.get(iid) is None]
    for root in roots:
        render_node(tree_manager, root)

# ───────────────────────────────
# Aplicació principal de Streamlit
# ───────────────────────────────
def main():
    st.set_page_config(page_title="Arbre de Participacions", layout="wide")
    
    # Inicialitzar gestor d'arbre
    tree_manager = TreeManager()
    
    st.title("CanvasTree en Streamlit")
    
    # Barra lateral per a operacions
    with st.sidebar:
        st.header("Operacions")
        
        # Pujar fitxer JSON
        uploaded_file = st.file_uploader("Puja un fitxer JSON", type="json")
        if uploaded_file is not None:
            data_str = uploaded_file.getvalue().decode("utf-8")
            if st.button("Carregar des de fitxer"):
                if tree_manager.carregar_estat(data_str):
                    st.rerun()
        
        # Guardar estat
        if st.button("Guardar estat"):
            json_data = tree_manager.guardar_estat()
            if json_data:
                st.download_button(
                    label="Descarrega JSON",
                    data=json_data,
                    file_name="arbre_estat.json",
                    mime="application/json"
                )
        
        # Importar dades d'exemple
        if st.button("Importar dades d'exemple"):
            # Crear dades d'exemple
            example_data = [
                {
                    "text": "Entitat Example",
                    "meta": {"type": "entity"},
                    "values": ["", "", "100", "100", "100.00", "100.00", "", "", "", "", "", "", "", ""],
                    "children": [
                        {
                            "text": "Particip Example",
                            "meta": {"type": "particip"},
                            "values": ["☐", "", "50", "50", "50.00", "50.00", "", "", "", "", "", "", "", ""],
                            "children": []
                        }
                    ]
                }
            ]
            if tree_manager.importar_dades(example_data):
                st.rerun()
    
    # Contingut principal
    render_tree(tree_manager)
    
    # Editor de nodes (simplificat)
    if st.session_state.selected_node:
        st.sidebar.header("Editar node")
        node_data = tree_manager.item(st.session_state.selected_node)
        new_text = st.sidebar.text_input("Nom", value=node_data["text"])
        
        if st.sidebar.button("Actualitzar"):
            tree_manager.set(st.session_state.selected_node, "Nom / Nivell", new_text)
            st.rerun()

if __name__ == "__main__":
    main()
