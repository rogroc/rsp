# main.py (versió establerta amb Importar + sense sqlite3)
# -*- coding: utf-8 -*-
"""
CanvasTree: widget d'arbre basat en Canvas+Frames amb:
 - Colors de capçalera i columnes configurables
 - Carrega i mostra valors inicials i actuals
 - Pinta en vermell (Inicial) i verd (Actual) quan hi ha canvis; negre si no
 - Doble clic per editar la columna "Carrec" (només files de persones)
 - Doble clic a la primera columna per afegir un fill (excepte al nivell 'person')
 - Sense fletxes d'expansió a files de persones
 - Plegat/desplegat correcte: els fills es recol·loquen just sota el pare (pack(after=...))
 - Botó "Importar" que llegeix la variable global `arrels` (o fitxer JSON com a fallback)
"""

import sys
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from typing import List, Optional
import json

# ───────────────────────────────
# Classe CanvasTree
# ───────────────────────────────
class CanvasTree(tk.Frame):
    def __init__(self, master, columns: List[str], column_colors: Optional[List[str]] = None,
                 row_height: int = 25, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.columns = columns
        self.column_colors = column_colors or ["#FFFFFF"] * len(columns)
        self.row_height = row_height

        # Índex de la columna "Carrec" (si existeix)
        self.carrec_col_index = self.columns.index("Carrec") if "Carrec" in self.columns else None

        # Estat
        self.items = {}         # iid → metadata (text, values, meta, etc.)
        self.children_map = {}  # parent → [child_iids]
        self.parent_map = {}    # child → parent
        self._next_iid = 0
        self._selection = None

        # Constants d'UI
        self._toggle_px = 28  # amplada en píxels de la "columna" de la fletxa

        # ───── Capçalera (amb columna toggle buida per alinear) ─────
        self.header = tk.Frame(self)
        self.header.pack(fill="x", side="top")

        # Placeholder per a la columna toggle
        toggle_hdr = tk.Label(self.header, text="", relief="raised")
        toggle_hdr.grid(row=0, column=0, sticky="nsew")

        # Labels de capçalera per a cada columna definida
        self._header_labels = []
        for j, (col, color) in enumerate(zip(self.columns, self.column_colors), start=1):
            lbl = tk.Label(self.header, text=col, bg=color, relief="raised")
            lbl.grid(row=0, column=j, sticky="nsew")
            self._header_labels.append(lbl)

        # Configuració de columnes de la capçalera
        self.header.grid_columnconfigure(0, minsize=self._toggle_px, weight=0)
        for j in range(1, len(self.columns) + 1):
            self.header.grid_columnconfigure(j, weight=1, uniform="cols")

        # ───── Canvas + Scrollbar ─────

        
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self._on_scrollbar)
        self.canvas.configure(yscrollcommand=self._on_canvas_yview)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Mapa d'IDs de finestra del canvas per fila visible
        self._window_ids = {}  # iid → canvas_window_id

        # Bindings per re-renderitzar i capturar scroll
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel()

    # ───────────────────────────────
    # Guardar / Carregar (JSON)
    # ───────────────────────────────
    def guardar_estat(self, filepath=None):
        """Guarda l'estat actual de l'arbre a un fitxer JSON en format recursiu 'children'."""
        try:
            if filepath is None:
                root = self.winfo_toplevel()
                filepath = filedialog.asksaveasfilename(
                    parent=root,
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")]
                )
            if not filepath:
                return

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

            roots = [iid for iid, _item in self.items.items() if self.parent_map.get(iid) is None]
            data = [node_to_dict(iid) for iid in roots]

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("Guardar estat", f"Arbre guardat correctament a {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"No s'ha pogut guardar l'estat: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"S'ha produït un error inesperat: {e}")

    def carregar_estat(self, filepath=None, filtre_text=None):
        """Carrega l'arbre d'un fitxer JSON (estructura recursiva 'children')."""
        try:
            if filepath is None:
                root = self.winfo_toplevel()
                filepath = filedialog.askopenfilename(
                    parent=root,
                    filetypes=[("JSON files", "*.json")]
                )
            if not filepath:
                return
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"No s'ha pogut carregar l'estat: {e}")
                return

            if isinstance(data, dict):
                data = [data]

            self._load_from_data(data, filtre_text=filtre_text)
        except Exception as e:
            messagebox.showerror("Error", f"S'ha produït un error en carregar l'estat: {e}")

    def importar(self, data=None, filtre_text=None):
        """
        Importa la variable 'arrels' si existeix en el namespace global, o prova dadesObertes(), 
        i com a darrer recurs demana un JSON. Manté la lògica original.
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
                        root = self.winfo_toplevel()
                        filepath = filedialog.askopenfilename(
                            parent=root,
                            title="Selecciona JSON d'import",
                            filetypes=[("JSON files", "*.json")]
                        )
                        if not filepath:
                            return
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except Exception as e:
                            messagebox.showerror("Error", f"No s'ha pogut llegir el JSON d'import: {e}")
                            return

            if isinstance(data, dict):
                data = [data]

            self._load_from_data(data, filtre_text=filtre_text)
        except Exception as e:
            messagebox.showerror("Error", f"S'ha produït un error en importar: {e}")

    # ───────────────────────────────
    # Helpers de càrrega
    # ───────────────────────────────
    def _netejar_values(self, node):
        """Idèntic a l'original: neteja/normalitza els values i percentatges."""
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
        """
        Inserta un node (i recursivament els seus fills) a l'arbre,
        deduint 'type' si manca. Manté el 'type' si ja està present o està bloquejat.
        """
        text = node.get("text", "") or ""
        values = self._netejar_values(node)
    
        # Si el node JSON porta meta.type, el passem directament a insert perquè quedi fixat
        node_meta = node.get("meta", {}) or {}
        node_type_to_pass = node_meta.get("type")
    
        iid = self.insert(parent_iid, text=text, values=values, node_type=node_type_to_pass)
    
        # Ara actualitzem el meta del item sense sobreescriure el type si ja hi és
        meta_existing = self.items[iid]["meta"]
        # Combinem/copiem les claus del node original a l'item
        for k, v in (node_meta.items()):
            # si ja existeix type i està bloquejat, no l'escrivim
            if k == "type" and meta_existing.get("_locked_type"):
                continue
            meta_existing[k] = v
    
        # Si no hi ha cap type encara, deduïm segons el pare (mapping incloent 'tipus')
        if "type" not in meta_existing or not meta_existing.get("type"):
            if parent_iid is None:
                ded_type = "entity"
            else:
                parent_type = self.items[parent_iid]["meta"].get("type")
                mapping = {"entity": "tipus", "tipus": "particip", "particip": "member", "member": "person"}
                ded_type = mapping.get(parent_type, "entity")
            meta_existing["type"] = ded_type
    
        # Assegurar valors inicials
        meta_existing.setdefault("initial_values", node.get("meta_initial_values", list(values)))
        meta_existing.setdefault("initial_text", node.get("meta_initial_text", text))
    
        self.items[iid]["meta"] = meta_existing
        self.items[iid]["expanded"] = bool(node.get("expanded", True))
    
        # Inserir fills recursivament
        for child in node.get("children", []):
            self._inserta_node(child, iid)
    
        return iid


    def _load_from_data(self, data, filtre_text=None):
        """Carrega arrels (amb filtre opcional) i reconstrueix la llista visible."""
        if not isinstance(data, list) or not data:
            messagebox.showwarning("Importar", "No hi ha dades a importar.")
            return

        if filtre_text is None:
            filtre_text = simpledialog.askstring(
                "Filtre d'entitat",
                "Introdueix el text de l'entitat a carregar:\n(Deixa en blanc per carregar totes les entitats)",
                parent=self
            )
        if filtre_text is None:
            messagebox.showinfo("Carregar estat", "Operació cancel·lada.")
            return

        filtre_text_norm = (filtre_text or "").lower().strip()
        if filtre_text_norm != "":
            data_filtrada = [node for node in data if filtre_text_norm in (node.get("text", "") or "").lower()]
            if not data_filtrada:
                messagebox.showwarning("Carregar estat", f"No s'ha trobat cap entitat amb el filtre: {filtre_text}")
                return
            data = data_filtrada

        # Esborrar UI/estat anterior
        for iid, win_id in list(self._window_ids.items()):
            try:
                self.canvas.delete(win_id)
            except Exception:
                pass
        self._window_ids.clear()

        for iid, item in list(self.items.items()):
            try:
                if item.get("frame") is not None:
                    item["frame"].destroy()
            except Exception:
                pass

        self.items.clear()
        self.children_map.clear()
        self.parent_map.clear()
        self._next_iid = 0

        # Inserir arrels (si falta meta.type a arrel, forcem entity)
        for root_node in data:
            root_node.setdefault("meta", {}).setdefault("type", "entity")
            self._inserta_node(root_node)

        # Recalcular índexs visibles i dibuixar
        self._recompute_visible_order()
        self._render_visible()

        # Colors de fons segons tipus (quan hi hagi files visibles)
        for iid in list(self.items.keys()):
            self._update_row_background(iid)

        refresh_tree_display_all(self)
        messagebox.showinfo("Carregar estat", "Arbre carregat correctament.")

    # ───────────────────────────────
    # Virtualització: ordre visible i renderitzat
    # ───────────────────────────────
    def _recompute_visible_order(self):
        """Assigna row_index seqüencial només als nodes visibles (ancestres expandits)."""
        # Neteja índexs
        for item in self.items.values():
            item["row_index"] = -1
    
        # Construir llista en profunditat respectant expanded
        def visit(iid, visible_list):
            item = self.items[iid]
            visible_list.append(iid)
            if item.get("expanded", True):
                for ch in self.get_children(iid):
                    visit(ch, visible_list)
    
        roots = [iid for iid, _item in self.items.items() if self.parent_map.get(iid) is None]
        ordered = []
        for r in roots:
            visit(r, ordered)
    
        # Assignar row_index
        for idx, iid in enumerate(ordered):
            self.items[iid]["row_index"] = idx
    
        # Destrueix files invisibles immediatament
        for iid, item in self.items.items():
            if item["row_index"] == -1:
                self._destroy_row_if_exists(iid)
    
        # Actualitzar scrollregion amb amplada real
        total_rows = max(1, len(ordered))
        w = max(1, self.canvas.winfo_width())
        self.canvas.configure(scrollregion=(0, 0, w, total_rows * self.row_height))
    
    
    def _render_visible(self):
        """Crea/destrueix només els frames dins la finestra visible del canvas."""
        if not self.items:
            return
    
        try:
            y0, y1 = self.canvas.yview()
            total_rows = max(1, sum(1 for it in self.items.values() if it["row_index"] >= 0))
            total_height = total_rows * self.row_height
    
            first_row = max(0, int((y0 * total_height) // self.row_height) - 2)
            last_row = int((y1 * total_height) // self.row_height) + 2
    
            first_row = max(0, min(first_row, total_rows - 1))
            last_row = max(0, min(last_row, total_rows - 1))
    
            canvas_width = max(1, self.canvas.winfo_width())
    
            for iid, item in self.items.items():
                row_idx = item["row_index"]
    
                if row_idx < 0 or row_idx < first_row or row_idx > last_row:
                    self._destroy_row_if_exists(iid)
                    continue
    
                node_type = item["meta"].get("type", "")
                bg_color_default = self._get_background_color_by_type(node_type)
    
                if item.get("frame") is None:
                    # Crear fila nova
                    row = tk.Frame(self.canvas, height=self.row_height)
                    item["frame"] = row
                    item["labels"] = []
                    item["toggle_btn"] = None
    
                    row.grid_columnconfigure(0, minsize=self._toggle_px, weight=0)
                    for j in range(1, len(self.columns) + 1):
                        row.grid_columnconfigure(j, weight=1, uniform="cols")
    
                    # Toggle
                    toggle_btn = tk.Label(row, text="", anchor="w", bg=bg_color_default)
                    toggle_btn.grid(row=0, column=0, sticky="nsew")
                    toggle_btn.bind("<Button-1>", lambda e, _iid=iid: self.toggle(_iid))
                    item["toggle_btn"] = toggle_btn
    
                    # Primera columna
                    lbl0 = tk.Label(row, text=("    " * item["indent"]) + item["text"],
                                    anchor="w", bg=bg_color_default)
                    lbl0.grid(row=0, column=1, sticky="nsew")
                    lbl0.bind("<Button-1>", lambda e, _iid=iid: self._on_click(_iid))
                    lbl0.bind("<Double-Button-1>", lambda e, _iid=iid: self._on_row_double_click(_iid))
                    item["labels"].append(lbl0)
    
                    # Resta de columnes
                    for col_idx in range(1, len(self.columns)):
                        val = item["values"][col_idx - 1] if (col_idx - 1) < len(item["values"]) else ""
                        lbl = tk.Label(row, text=val, anchor="w", bg=bg_color_default)
                        lbl.grid(row=0, column=col_idx + 1, sticky="nsew")
                        lbl.bind("<Button-1>", lambda e, _iid=iid, c=col_idx: self._on_cell_click(_iid, c))
    
                        # Només permet editar Carrec amb doble clic
                        if self.columns[col_idx] == "Carrec":
                            lbl.bind("<Double-Button-1>", lambda e, _iid=iid, c=col_idx: self._start_edit(_iid, c))
    
                        item["labels"].append(lbl)
    
                    # Afegir finestra al canvas
                    top = row_idx * self.row_height
                    try:
                        win_id = self.canvas.create_window((0, top), window=row, anchor="nw", width=canvas_width)
                        self._window_ids[iid] = win_id
                    except Exception as e:
                        print(f"Error creant window canvas per {iid}: {e}", file=sys.stderr)
                        continue
    
                    self._update_row_background(iid)
                    self._update_row_colors(iid)
                    self._update_toggle_symbol(iid)
                    self._highlight_selection()
                else:
                    # Actualitzar posició i amplada
                    win_id = self._window_ids.get(iid)
                    if win_id is not None and win_id in self.canvas.find_all():
                        try:
                            top = row_idx * self.row_height
                            self.canvas.coords(win_id, 0, top)
                            self.canvas.itemconfigure(win_id, width=canvas_width)
                            self._update_toggle_symbol(iid)
                        except Exception as e:
                            print(f"Error actualitzant coords de {iid}: {e}", file=sys.stderr)
    
        except Exception as e:
            print(f"Error general en _render_visible: {e}", file=sys.stderr)


    def _destroy_row_if_exists(self, iid):
        item = self.items.get(iid)
        if not item:
            return
        if item.get("frame") is not None:
            try:
                item["frame"].destroy()
            except Exception:
                pass
            item["frame"] = None
            item["labels"] = []
            item["toggle_btn"] = None
        win_id = self._window_ids.pop(iid, None)
        if win_id is not None:
            try:
                self.canvas.delete(win_id)
            except Exception:
                pass

    # ───────────────────────────────
    # Setters / Getters
    # ───────────────────────────────
    def insert(self, parent, index="end", text="", values=(), tags=(), node_type=None):
        """Inserció lògica (sense crear widgets). Accepta node_type opcional per forçar el tipus."""
        iid = f"node_{self._next_iid}"
        self._next_iid += 1
    
        indent = 0
        if parent:
            parent_item = self.items.get(parent)
            indent = parent_item["indent"] + 1 if parent_item else 1
    
        expected_vals = len(self.columns) - 1
        vals = list(values) if values is not None else []
        if len(vals) < expected_vals:
            vals.extend([""] * (expected_vals - len(vals)))
        elif len(vals) > expected_vals:
            vals = vals[:expected_vals]
    
        # Construir meta inicial; si s'ha passat node_type l'afegim explícitament
        meta = {"initial_values": list(vals), "initial_text": text}
        if node_type:
            meta["type"] = node_type
            # Marquem com a "bloquejat" per evitar sobreescriptures posteriors
            meta["_locked_type"] = True
    
        self.items[iid] = {
            "text": text,
            "values": vals,
            "labels": [],
            "indent": indent,
            "expanded": True,
            "visible": False,
            "meta": meta,
            "frame": None,
            "toggle_btn": None,
            "row_index": -1,
        }
    
        self.children_map.setdefault(parent, []).append(iid)
        self.parent_map[iid] = parent
        return iid


    def set(self, iid, column=None, value=None):
        if iid not in self.items:
            return
        item = self.items[iid]
        if column is None:
            return

        col_index = self.columns.index(column)
        if col_index == 0:
            # Primera columna (text)
            item["text"] = value
            if item["labels"]:
                try:
                    item["labels"][0].config(text=("    " * item["indent"]) + value)
                except Exception:
                    pass
            return

        col_name = self.columns[col_index]
        if "Inicial" in col_name:
            # Només etiqueta si està renderitzada
            if item["labels"] and col_index < len(item["labels"]):
                try:
                    item["labels"][col_index].config(text=value)
                except Exception:
                    pass
        else:
            needed = col_index - 1
            if needed >= len(item["values"]):
                item["values"].extend([""] * (needed - len(item["values"]) + 1))
            item["values"][col_index - 1] = value
            if item["labels"] and col_index < len(item["labels"]):
                try:
                    item["labels"][col_index].config(text=value)
                except Exception:
                    pass
        self._update_row_colors(iid)

    def item(self, iid, option=None):
        if iid not in self.items:
            return {}
        item = self.items[iid]
        if option is None:
            return {"text": item["text"], "values": item["values"], "meta": item["meta"]}
        return item.get(option)

    def get_children(self, iid=None):
        return self.children_map.get(iid, [])

    def parent(self, iid):
        return self.parent_map.get(iid)

    # ───────────────────────────────
    # Selecció
    # ───────────────────────────────
    def _on_click(self, iid):
        self.selection_set(iid)

    def selection(self):
        return (self._selection,) if self._selection else ()

    def selection_set(self, iid):
        self._selection = iid
        self._highlight_selection()

    def _highlight_selection(self):
        for iid, meta in self.items.items():
            node_type = meta["meta"].get("type")
            first_col_bg = self._get_background_color_by_type(node_type)

            # Primera columna i toggle (si renderitzats)
            if meta.get("labels"):
                try:
                    bg_first = "#ffffcc" if iid == self._selection else first_col_bg
                    meta["labels"][0].config(bg=bg_first)
                except Exception:
                    pass
                for col_idx in range(1, len(meta["labels"])):
                    original_bg = self.column_colors[col_idx] if col_idx < len(self.column_colors) else "#FFFFFF"
                    bg = "#ffffcc" if iid == self._selection else original_bg
                    try:
                        meta["labels"][col_idx].config(bg=bg)
                    except Exception:
                        pass

            if meta.get("toggle_btn") is not None:
                try:
                    meta["toggle_btn"].config(bg="#ffffcc" if iid == self._selection else first_col_bg)
                except Exception:
                    pass

    # ───────────────────────────────
    # Plegat / Desplegat
    # ───────────────────────────────
    def toggle(self, iid):
        item = self.items[iid]
        # No actuar si no hi ha fletxa (p. ex. persones sense fills)
        # La presència de fills determina la fletxa.
        item["expanded"] = not item["expanded"]
        self._update_toggle_symbol(iid)
        # Recalcular ordre visible i re-renderitzar
        self._recompute_visible_order()
        self._render_visible()

    def _update_toggle_symbol(self, iid):
        """Actualitza el text del botó toggle segons si té fills i l'estat 'expanded'."""
        item = self.items[iid]
        btn = item.get("toggle_btn")
        if btn is None:
            return
        children = self.get_children(iid)
        try:
            if children:
                btn.config(text="▼" if item.get("expanded", True) else "▶")
            else:
                btn.config(text="")  # sense fletxa si no hi ha fills
        except Exception:
            pass

    # ───────────────────────────────
    # Edició en línia (Carrec)
    # ───────────────────────────────
    def _start_edit(self, iid, col_idx):
        meta = self.items[iid]["meta"]
        if meta.get("type") != "person":
            return  # només persones
        if not self.items[iid]["labels"] or col_idx >= len(self.items[iid]["labels"]):
            return
        lbl = self.items[iid]["labels"][col_idx]
        current = lbl.cget("text")
        entry = tk.Entry(self.items[iid]["frame"])
        entry.insert(0, current)
        entry.select_range(0, tk.END)
        entry.focus_set()
        entry.bind("<Return>", lambda e, i=iid, c=col_idx: self._commit_edit(i, c, entry))
        entry.bind("<Escape>", lambda e, i=iid, c=col_idx, cur=current: self._cancel_edit(i, c, entry, cur))
        entry.place(in_=lbl, x=0, y=0, relwidth=1, relheight=1)

    def _commit_edit(self, iid, col_idx, entry):
        new_val = entry.get()
        entry.destroy()
        col_name = self.columns[col_idx]
        self.set(iid, col_name, new_val)
        if self.items[iid]["meta"].get("type") == "person":
            self.items[iid]["meta"]["carrec"] = new_val
        self._update_row_colors(iid)

    def _cancel_edit(self, iid, col_idx, entry, old_val):
        entry.destroy()

    # ───────────────────────────────
    # Colors segons tipus i diferències Inicial/Actual
    # ───────────────────────────────
    def _update_row_background(self, iid):
        item = self.items[iid]
        meta = item["meta"]
        node_type = meta.get("type")

        if node_type == "entity":
            target_column = "PercentatgeParticip"
        elif node_type == "particip":
            target_column = "PercentatgeParticip"
        elif node_type == "member":
            target_column = "Percentatge"
        elif node_type == "person":
            target_column = "PercentatgePersona"
        else:
            target_column = None

        if target_column and target_column in self.columns:
            col_index = self.columns.index(target_column)
            if col_index < len(self.column_colors):
                bg_color = self.column_colors[col_index]
            else:
                bg_color = "#FFFFFF"
        else:
            bg_color = "#FFFFFF"

        # Aplicar fons a la primera columna, si està renderitzada
        if item.get("labels"):
            try:
                item["labels"][0].config(bg=bg_color)
            except Exception:
                pass
        if item.get("toggle_btn") is not None:
            try:
                item["toggle_btn"].config(bg=bg_color)
            except Exception:
                pass
        # Restaurar fons original per a la resta
        if item.get("labels"):
            for col_idx in range(1, len(item["labels"])):
                original_bg = self.column_colors[col_idx] if col_idx < len(self.column_colors) else "#FFFFFF"
                try:
                    item["labels"][col_idx].config(bg=original_bg)
                except Exception:
                    pass

    def _get_background_color_by_type(self, node_type):
        """
        Retorna el color de fons segons el tipus de node.
        """
        default_colors = {
            "entity": "#FFFFFF",    # Blanc (nivell 0)
            "tipus": "#F5F5F5",     # Gris suau (nivell 1)
            "particip": "#D4EDDA",  # Verd clar (nivell 2)
            "member": "#D1ECF1",    # Blau clar (nivell 3)
            "person": "#E8E8FA"     # Lila suau (nivell 4)
        }
        return default_colors.get(node_type, "#FFFFFF")



    def _update_row_colors(self, iid):
        """Pinta en vermell/verd segons diferències Inicial vs Actual (si els labels existeixen)."""
        def normalize(s: str) -> str:
            return (s or "").strip()

        item = self.items[iid]
        if not item.get("labels"):
            return  # es pintarà quan es renderitzi

        for lbl in item["labels"]:
            try:
                lbl.config(fg="black")
            except Exception:
                pass

        init_to_actual = {}
        for j, col in enumerate(self.columns):
            if j == 0:
                continue
            if col.endswith("Inicial"):
                base = col[:-7]
                candidates = [base, base + "Actual"]
                found = None
                for cand in candidates:
                    if cand in self.columns:
                        found = self.columns.index(cand)
                        break
                if found is not None:
                    init_to_actual[j] = found

        for init_idx, actual_idx in init_to_actual.items():
            if init_idx >= len(item["labels"]) or actual_idx >= len(item["labels"]):
                continue
            init_lbl = item["labels"][init_idx]
            cur_lbl = item["labels"][actual_idx]
            init_val = normalize(init_lbl.cget("text"))
            cur_val = normalize(cur_lbl.cget("text"))
            if init_val != cur_val:
                try:
                    init_lbl.config(fg="red")
                except Exception:
                    pass
                try:
                    cur_lbl.config(fg="green")
                except Exception:
                    pass
            else:
                try:
                    init_lbl.config(fg="black")
                    cur_lbl.config(fg="black")
                except Exception:
                    pass

    # ───────────────────────────────
    # Gestió de clic a cel·la (Eliminar, DretVot)
    # ───────────────────────────────
    def _on_cell_click(self, iid, col_idx):
        meta = self.items[iid]["meta"]
        if col_idx == 1:  # "Eliminar"
            new_state = not meta.get("eliminar", False)
            meta["eliminar"] = new_state
            newval = "☒" if new_state else "☐"
            self.set(iid, self.columns[col_idx], newval)

            if not new_state:
                def restore_descendants(i):
                    for ch in self.get_children(i):
                        ch_meta = self.items[ch]["meta"]
                        ch_meta["eliminar"] = False
                        self.set(ch, self.columns[1], "☐")
                        initial_vals = ch_meta.get("initial_values", [])
                        for col_name in ["PercentatgePersona", "Percentatge", "PercentatgeParticip"]:
                            if col_name in self.columns:
                                col_index = self.columns.index(col_name)
                                if col_index - 1 < len(initial_vals):
                                    self.set(ch, col_name, initial_vals[col_index - 1])
                        restore_descendants(ch)
                restore_descendants(iid)

        elif col_idx == 2 and meta.get("type") == "member":  # "DretVot"
            new_state = not meta.get("dret_vot", False)
            meta["dret_vot"] = new_state
            newval = "☒" if new_state else "☐"
            self.set(iid, self.columns[col_idx], newval)
            for child in self.get_children(iid):
                child_meta = self.items[child]["meta"]
                if child_meta.get("type") == "person":
                    child_meta["dret_vot_parent"] = new_state

        refresh_tree_display_all(self)
        # Re-pintar visibles (per si hi ha canvis de percentatges)
        self._render_visible()

    # ───────────────────────────────
    # Afegir fills (doble clic a la fila)
    # ───────────────────────────────
    def _next_child_type(self, parent_type: Optional[str]) -> Optional[str]:
        mapping = {"entity": "particip", "particip": "member", "member": "person"}
        return mapping.get(parent_type)

    def _snapshot_initial_from_current(self, iid):
        """Emplena els valors 'initial' del node a partir dels actuals (com l'original)."""
        item = self.items.get(iid)
        if not item or not item.get("labels"):
            return

        labels = item["labels"]

        def is_empty_text(lbl):
            txt = lbl.cget("text") if lbl is not None else ""
            return not txt or not txt.strip()

        for idx, col in enumerate(self.columns):
            if idx == 0:
                continue
            if col.endswith("Inicial"):
                base_col = col[:-7]
                if base_col in self.columns:
                    init_idx = idx
                    base_idx = self.columns.index(base_col)
                    if init_idx < len(labels) and base_idx < len(labels):
                        init_lbl = labels[init_idx]
                        actual_lbl = labels[base_idx]
                        if is_empty_text(init_lbl) and not is_empty_text(actual_lbl):
                            init_lbl.config(text=actual_lbl.cget("text"))
                            valpos = init_idx - 1
                            if 0 <= valpos < len(item["values"]):
                                item["values"][valpos] = actual_lbl.cget("text")
                            item["meta"].setdefault("initial_values", [""] * (len(self.columns) - 1))
                            if 0 <= valpos < len(item["meta"]["initial_values"]):
                                item["meta"]["initial_values"][valpos] = actual_lbl.cget("text")

        if "CarrecInicial" in self.columns and "Carrec" in self.columns:
            idx_inicial = self.columns.index("CarrecInicial")
            idx_actual = self.columns.index("Carrec")
            if idx_inicial < len(labels) and idx_actual < len(labels):
                lbl_inicial = labels[idx_inicial]
                lbl_actual = labels[idx_actual]
                if (not lbl_actual.cget("text") or not lbl_actual.cget("text").strip()) and (lbl_inicial.cget("text") and lbl_inicial.cget("text").strip()):
                    lbl_actual.config(text=lbl_inicial.cget("text"))
                    pos_actual = idx_actual - 1
                    if 0 <= pos_actual < len(item["values"]):
                        item["values"][pos_actual] = lbl_inicial.cget("text")
                    item["meta"]["carrec"] = lbl_inicial.cget("text")

    def _on_row_double_click(self, iid):
        """Doble clic a la fila: afegeix un fill segons la jerarquia del node pare.
        Ara: entity -> particip, tipus -> particip, particip -> member, member -> person.
        """
        item = self.items.get(iid)
        if not item:
            return
    
        parent_meta = item.get("meta", {}) or {}
        parent_type = parent_meta.get("type")
        if parent_type == "person":
            return  # Les persones no tenen fills
    
        # Mapatge corregit: entity i tipus creen particip; després particip->member->person
        hierarchy_mapping = {
            "entity": "tipus",
            "tipus": "particip",
            "particip": "member",
            "member": "person"
        }
        child_type = hierarchy_mapping.get(parent_type)
        if not child_type:
            return
    
        prompt_map = {
            "tipus": "Denominació del nou tipus:",
            "particip": "Denominació del nou partícip:",
            "member": "Denominació del nou membre:",
            "person": "Nom de la nova persona:"
        }
        title = "Afegir fill"
        name = simpledialog.askstring(title, prompt_map.get(child_type, "Denominació del nou element:"),
                                      parent=self.winfo_toplevel())
        if not name or not name.strip():
            return
        name = name.strip()
    
        # Preparar valors base (protegir cas quan hi hagi menys de 3 columnes)
        num_extra = max(0, len(self.columns) - 3)
        base_values = ["☐", ""] + [""] * num_extra
    
        # Inicialitzar columnes específiques per tipus (especial atenció a 'particip')
        if child_type == "particip":
            for col_name in ["PersonesParticipInicial", "PercentatgeParticipInicial"]:
                if col_name in self.columns:
                    idx = self.columns.index(col_name) - 1
                    if 0 <= idx < len(base_values):
                        base_values[idx] = "0.0%"
        elif child_type == "member":
            for col_name in ["PersonesMembreInicial", "PercentatgeInicial"]:
                if col_name in self.columns:
                    idx = self.columns.index(col_name) - 1
                    if 0 <= idx < len(base_values):
                        base_values[idx] = "0.0%"
            if "DretVot" in self.columns:
                idx = self.columns.index("DretVot") - 1
                if 0 <= idx < len(base_values):
                    base_values[idx] = "☐"
        elif child_type == "person":
            for col_name in ["PercentatgePersonaInicial"]:
                if col_name in self.columns:
                    idx = self.columns.index(col_name) - 1
                    if 0 <= idx < len(base_values):
                        base_values[idx] = "0.0%"
    
        # Inserir el node forçant node_type si l'insert ho suporta; si no, posem el type després
        try:
            new_iid = self.insert(iid, index=0, text=name, values=base_values, node_type=child_type)
        except TypeError:
            # insert no accepta node_type; fem la inserció i forcem el type a meta
            new_iid = self.insert(iid, index=0, text=name, values=base_values)
            self.items[new_iid].setdefault("meta", {})["type"] = child_type
            # marquem que aquest type és fixat per evitar que altres rutines el dedueixin
            self.items[new_iid]["meta"]["_locked_type"] = True
        else:
            # si insert va acceptar node_type, marquem _locked_type per seguretat
            self.items[new_iid].setdefault("meta", {})["_locked_type"] = True
    
        # Assignar/garantir metadades essencials del nou node
        new_meta = self.items[new_iid].setdefault("meta", {})
        new_meta["type"] = child_type  # forcem novament per assegurar coherència
        new_meta.setdefault("initial_values", list(base_values))
        new_meta.setdefault("initial_text", name)
        new_meta.setdefault("eliminar", False)
    
        if child_type == "member":
            new_meta.setdefault("dret_vot", False)
        if child_type == "person":
            new_meta.setdefault("carrec", "")
            new_meta.setdefault("dret_vot_parent", bool(parent_meta.get("dret_vot")))
    
        # Inicialitzar valors visibles per a particip (opcional)
        if child_type == "particip":
            if "PersonesParticipActual" in self.columns:
                try:
                    self.set(new_iid, "PersonesParticipActual", "0")
                except Exception:
                    pass
            if "PercentatgeParticip" in self.columns:
                try:
                    self.set(new_iid, "PercentatgeParticip", "0.00")
                except Exception:
                    pass
    
        # Debug opcional (descomenta per a diagnosticar)
        # print(f"DEBUG: creat node {new_iid} amb meta: {self.items[new_iid]['meta']}")
    
        # Recalcular ordre visible i actualitzar UI i càlculs
        self._recompute_visible_order()
        self._render_visible()
        refresh_tree_display_all(self)
        self._snapshot_initial_from_current(new_iid)
        self._update_row_colors(new_iid)
        self._highlight_selection()


    # ───────────────────────────────
    # Scroll i redibuix
    # ───────────────────────────────
    def _on_canvas_configure(self, event):
        """Quan el canvas canvia mida, ajusta amplades i redibuixa visibles."""
        canvas_width = event.width
        for win_id in list(self._window_ids.values()):
            try:
                self.canvas.itemconfigure(win_id, width=canvas_width)
            except Exception:
                pass
        # Recalcular scrollregion amb amplada nova
        total_rows = sum(1 for it in self.items.values() if it["row_index"] >= 0)
        w = max(1, canvas_width)
        self.canvas.configure(scrollregion=(0, 0, w, total_rows * self.row_height))
        # Re-pintar visibles
        self._render_visible()


    def _on_canvas_yview(self, *args):
        # proxy del yscrollcommand: actualitza scrollbar i refà el render
        self.scrollbar.set(*args)
        self._render_visible()

    def _on_scrollbar(self, *args):
        # proxy del command de la scrollbar: mou el canvas i refà el render
        self.canvas.yview(*args)
        self._render_visible()

    def _bind_mousewheel(self):
        # Windows / MacOS
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux (X11)
        self.canvas.bind_all("<Button-4>", lambda e: self._on_linux_wheel(-1))
        self.canvas.bind_all("<Button-5>", lambda e: self._on_linux_wheel(1))

    def _on_mousewheel(self, event):
        # En Windows event.delta és múltiple de 120; en macOS pot ser diferent
        delta = event.delta
        if event.num == 5:  # per si arriba via num en algun backend
            delta = -120
        elif event.num == 4:
            delta = 120
        units = -1 if delta > 0 else 1
        try:
            self.canvas.yview_scroll(units, "units")
        except Exception:
            pass
        self._render_visible()

    def _on_linux_wheel(self, direction):
        # direction: -1 amunt, 1 avall
        try:
            self.canvas.yview_scroll(direction, "units")
        except Exception:
            pass
        self._render_visible()


# ───────────────────────────────
# Funcions de càlcul globals
# ───────────────────────────────
def count_valid_persons(tree, parent_iid):
    """Compta persones no eliminades sota un node."""
    total = 0
    for ch in tree.get_children(parent_iid):
        meta = tree.item(ch, "meta")
        if meta.get("eliminar"):
            continue
        if meta.get("type") == "person":
            total += 1
        else:
            total += count_valid_persons(tree, ch)
    return total

def refresh_tree_display_all(tree):
    """Recalcula percentatges i totals de persones tenint en compte eliminacions i dret de vot."""

    def is_effectively_eliminated(iid):
        cur = iid
        while cur is not None:
            meta = tree.items[cur]["meta"]
            if meta.get("eliminar"):
                return True
            cur = tree.parent_map.get(cur)
        return False

    def count_valid_persons_effective(parent_iid):
        total = 0
        for ch in tree.get_children(parent_iid):
            if is_effectively_eliminated(ch):
                continue
            meta_ch = tree.items[ch]["meta"]
            if meta_ch.get("type") == "person":
                total += 1
            else:
                total += count_valid_persons_effective(ch)
        return total

    # Trobar totes les entitats
    entities = []
    for iid, item in tree.items.items():
        if item["meta"].get("type") == "entity" and not is_effectively_eliminated(iid):
            entities.append(iid)

    # Per a cada entitat, calcular el total de persones amb dret de vot
    entity_totals = {}
    for entity_iid in entities:
        total_entity = 0
        # Recórrer tots els membres de l'entitat amb dret de vot
        stack = [entity_iid]
        while stack:
            node_iid = stack.pop()
            if is_effectively_eliminated(node_iid):
                continue
            meta = tree.items[node_iid]["meta"]
            if meta.get("type") == "member" and meta.get("dret_vot"):
                total_entity += count_valid_persons_effective(node_iid)
            # Afegir fills al stack
            for child in tree.get_children(node_iid):
                stack.append(child)
        entity_totals[entity_iid] = total_entity

    # Netejar i calcular columnes
    for iid, item in tree.items.items():
        meta = item["meta"]
        t = meta.get("type")

        # Inicialitzar columnes
        for col in ["PersonesParticipActual", "PersonesMembreActual", "PercentatgeParticip", "Percentatge", "PercentatgePersona"]:
            if col in tree.columns:
                tree.set(iid, col, "")

        if is_effectively_eliminated(iid):
            if t == "person" and "PercentatgePersona" in tree.columns:
                tree.set(iid, "PercentatgePersona", "0.00")
            elif t == "member":
                if "Percentatge" in tree.columns:
                    tree.set(iid, "Percentatge", "0.00")
                if "PersonesMembreActual" in tree.columns:
                    tree.set(iid, "PersonesMembreActual", "0")
            elif t in ("particip", "entity"):
                if "PercentatgeParticip" in tree.columns:
                    tree.set(iid, "PercentatgeParticip", "0.00")
                if "PersonesParticipActual" in tree.columns:
                    tree.set(iid, "PersonesParticipActual", "0")
            continue

        # Trobar l'entitat pare
        entity_iid = iid
        while entity_iid is not None and tree.items[entity_iid]["meta"].get("type") != "entity":
            entity_iid = tree.parent_map.get(entity_iid)
        
        total_entity = entity_totals.get(entity_iid, 0) if entity_iid is not None else 0

        # Persones
        if t == "person":
            if meta.get("dret_vot_parent") and total_entity > 0:
                pct = (1 / total_entity) * 100
                tree.set(iid, "PercentatgePersona", f"{pct:.2f}")
            else:
                if "PercentatgePersona" in tree.columns:
                    tree.set(iid, "PercentatgePersona", "0.00")

        # Membres
        elif t == "member":
            cnt = count_valid_persons_effective(iid)
            if "PersonesMembreActual" in tree.columns:
                tree.set(iid, "PersonesMembreActual", str(cnt))
            if meta.get("dret_vot") and total_entity > 0:
                pct = (cnt / total_entity) * 100
                tree.set(iid, "Percentatge", f"{pct:.2f}")
            else:
                if "Percentatge" in tree.columns:
                    tree.set(iid, "Percentatge", "0.00")

        # Partícips
        elif t == "particip":
            total_persons = 0
            # Recórrer tots els membres del partícip amb dret de vot
            stack = [iid]
            while stack:
                node_iid = stack.pop()
                if is_effectively_eliminated(node_iid):
                    continue
                meta_node = tree.items[node_iid]["meta"]
                if meta_node.get("type") == "member" and meta_node.get("dret_vot"):
                    total_persons += count_valid_persons_effective(node_iid)
                # Afegir fills al stack
                for child in tree.get_children(node_iid):
                    stack.append(child)
            
            if "PersonesParticipActual" in tree.columns:
                tree.set(iid, "PersonesParticipActual", str(total_persons))
            if total_entity > 0:
                pct = (total_persons / total_entity) * 100
                tree.set(iid, "PercentatgeParticip", f"{pct:.2f}")
            else:
                if "PercentatgeParticip" in tree.columns:
                    tree.set(iid, "PercentatgeParticip", "0.00")

        # Entitats
        elif t == "entity":
            if "PercentatgeParticip" in tree.columns:
                tree.set(iid, "PercentatgeParticip", f"{100.00 if total_entity > 0 else 0.00:.2f}")

    # Actualitzar colors finals segons diferències Inicial vs Actual
    for iid in tree.items:
        tree._update_row_colors(iid)


# ───────────────────────────────
# Execució principal
# ───────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Arbre amb CanvasTree")

    columns = [
        "Nom / Nivell", "Eliminar", "DretVot",
        "PersonesParticipInicial", "PersonesParticipActual",
        "PercentatgeParticipInicial", "PercentatgeParticip",
        "PersonesMembreInicial", "PersonesMembreActual",
        "PercentatgeInicial", "Percentatge",
        "PercentatgePersonaInicial", "PercentatgePersona",
        "CarrecInicial", "Carrec"
    ]
    colors = [
        "#FFFFFF", "#FFFFFF", "#FFFFFF",
        "#D4EDDA", "#D4EDDA", "#D4EDDA", "#D4EDDA",
        "#D1ECF1", "#D1ECF1", "#D1ECF1", "#D1ECF1",
        "#E8E8FA", "#E8E8FA", "#E8E8FA", "#E8E8FA"
    ]

    tree = CanvasTree(root, columns, colors)
    tree.pack(fill="both", expand=True)

    # ─── Frame amb botons ───
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill="x")
    tk.Button(btn_frame, text="Guardar estat", command=tree.guardar_estat).pack(side="left", padx=5, pady=2)
    tk.Button(btn_frame, text="Carregar estat", command=tree.carregar_estat).pack(side="left", padx=5, pady=2)
    tk.Button(btn_frame, text="Importar", command=tree.importar).pack(side="left", padx=5, pady=2)

    root.mainloop()