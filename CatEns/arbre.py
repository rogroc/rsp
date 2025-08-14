import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import sqlite3
import os
import sys
import tkinter.font as tkfont
from datetime import datetime  # Per data i hora de validació

DB_FILE = 'arbre.db'
if '--selftest' in sys.argv:
    DB_FILE = 'arbre_selftest.db'

# ------------------------ Utilitats BD ------------------------
def init_db():
    """Crea la base de dades i les taules si no existeixen."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS entitat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS particips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE,
            eliminat INTEGER DEFAULT 0,
            data_eliminacio TEXT
        )
    ''')
    try:
        cur.execute("ALTER TABLE particips ADD COLUMN eliminat INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE particips ADD COLUMN data_eliminacio TEXT")
    except sqlite3.OperationalError:
        pass

    cur.execute('''
        CREATE TABLE IF NOT EXISTS membres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            particip_id INTEGER,
            dret_vot INTEGER DEFAULT 0,
            eliminat INTEGER DEFAULT 0,
            data_eliminacio TEXT,
            UNIQUE(nom, particip_id),
            FOREIGN KEY(particip_id) REFERENCES particips(id) ON DELETE CASCADE
        )
    ''')
    try:
        cur.execute("ALTER TABLE membres ADD COLUMN dret_vot INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE membres ADD COLUMN eliminat INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE membres ADD COLUMN data_eliminacio TEXT")
    except sqlite3.OperationalError:
        pass

    cur.execute('''
        CREATE TABLE IF NOT EXISTS persones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            membre_id INTEGER,
            eliminat INTEGER DEFAULT 0,
            data_eliminacio TEXT,
            UNIQUE(nom, membre_id),
            FOREIGN KEY(membre_id) REFERENCES membres(id) ON DELETE CASCADE
        )
    ''')
    try:
        cur.execute("ALTER TABLE persones ADD COLUMN eliminat INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE persones ADD COLUMN data_eliminacio TEXT")
    except sqlite3.OperationalError:
        pass

    cur.execute('''
        CREATE TABLE IF NOT EXISTS validacions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datahora TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS percentatges_validacio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            validacio_id INTEGER NOT NULL,
            membre_id INTEGER NOT NULL,
            percentatge REAL NOT NULL,
            FOREIGN KEY(validacio_id) REFERENCES validacions(id) ON DELETE CASCADE,
            FOREIGN KEY(membre_id) REFERENCES membres(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM entitat')
    if cur.fetchone()[0] == 0:
        cur.execute('INSERT INTO entitat (nom) VALUES (?)', ('Entitat Principal',))
        conn.commit()
    conn.close()

class ChooseOrCreateDialog(simpledialog.Dialog):
    def __init__(self, parent, title, items):
        self.items = items
        self.result_value = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text='Trieu un element existent o creeu-ne un de nou:').grid(row=0, column=0, columnspan=2, pady=4)
        self.listbox = tk.Listbox(master, height=6)
        for it in self.items:
            self.listbox.insert(tk.END, it)
        self.listbox.grid(row=1, column=0, padx=4, pady=4)
        frame = ttk.Frame(master)
        frame.grid(row=1, column=1, padx=4, pady=4, sticky='n')
        ttk.Label(frame, text='Nou nom:').pack(anchor='w')
        self.new_entry = ttk.Entry(frame)
        self.new_entry.pack(fill='x')
        return self.new_entry

    def apply(self):
        sel = None
        try:
            sel = self.listbox.get(self.listbox.curselection())
        except Exception:
            sel = None
        newname = self.new_entry.get().strip()
        if sel and newname:
            self.result_value = (sel, False)
        elif sel:
            self.result_value = (sel, False)
        elif newname:
            self.result_value = (newname, True)
        else:
            self.result_value = None

class ArbreApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Arbre jeràrquic: Entitat > Partícips > Membres > Persones')
        self.geometry('1000x600')  # Ampliada per nova columna
        self.base_font = tkfont.nametofont('TkDefaultFont')
        self.overstrike_font = self.base_font.copy()
        self.overstrike_font.configure(overstrike=1)
        self.item_meta = {}
        self.total_persones_vot = 0
        init_db()

        top_frame = ttk.Frame(self)
        top_frame.pack(side='top', fill='x', padx=6, pady=6)
        ttk.Label(top_frame, text='Entitat:').pack(side='left')
        self.entitat_label = ttk.Label(top_frame, text=self.get_entitat_nom(), font=('TkDefaultFont', 10, 'bold'))
        self.entitat_label.pack(side='left', padx=(4,10))
        self.add_particip_btn = ttk.Button(top_frame, text='Afegir partícip', command=self.on_add_particip_entitat)
        self.add_particip_btn.pack(side='left')

        mode_frame = ttk.Frame(self)
        mode_frame.pack(side='top', fill='x', padx=6, pady=(4,6))
        ttk.Label(mode_frame, text='Mesura de participació:').pack(side='left')
        self.mesura_participacio_var = tk.StringVar(value="Drets de vot a l'OGS")
        self.mesura_participacio = ttk.Combobox(mode_frame, textvariable=self.mesura_participacio_var, state='readonly',
                                               values=["Drets de vot a l'OGS", 'Altres mesures de participació'])
        self.mesura_participacio.pack(side='left', padx=(4,10))

        central = ttk.Frame(self)
        central.pack(fill='both', expand=True, padx=6, pady=6)

        # MODIFICAT: Afegir columna 'PercentatgeInicial'
        self.tree = ttk.Treeview(central, columns=('Eliminar','DretVot','Persones','Percentatge','PercentatgeInicial'), show='tree headings')
        self.tree.heading('#0', text='Nom / Nivell')
        self.tree.column('#0', width=300)  # Reduït per nova columna
        self.tree.heading('Eliminar', text='Eliminar')
        self.tree.column('Eliminar', width=70, anchor='center')
        self.tree.heading('DretVot', text='Dret de vot')
        self.tree.column('DretVot', width=70, anchor='center')
        self.tree.heading('Persones', text='Persones membre')
        self.tree.column('Persones', width=90, anchor='center')
        self.tree.heading('Percentatge', text='Percentatge membre')
        self.tree.column('Percentatge', width=110, anchor='center')
        # NOVA COLUMNA
        self.tree.heading('PercentatgeInicial', text='Percentatge inicial')
        self.tree.column('PercentatgeInicial', width=110, anchor='center')
        self.tree.pack(side='left', fill='both', expand=True)
        self.tree.tag_configure('eliminat', font=self.overstrike_font, foreground='gray50')
        self.tree.tag_configure('no_vot', foreground='gray50')

        scrollbar = ttk.Scrollbar(central, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='left', fill='y')

        right_panel = ttk.Frame(central, width=220)
        right_panel.pack(side='left', fill='y', padx=8)
        ttk.Label(right_panel, text='Accions').pack(anchor='nw')
        self.context_add_btn = ttk.Button(right_panel, text='[Selecciona un element]', state='disabled', command=self.on_context_add)
        self.context_add_btn.pack(fill='x', pady=4)
        ttk.Button(right_panel, text='VALIDAR', command=self.on_validate).pack(fill='x', pady=20)
        ttk.Label(right_panel, text='Instruccions', font=('TkDefaultFont', 9, 'bold')).pack(anchor='nw', pady=(10,0))
        instr = (
            "1) Selecciona un element de l'arbre.\n"
            "2) Utilitza \"Accions\" per afegir fill.\n"
            "3) Marca \"Eliminar\" per marcar per a esborrar.\n"
            "4) Premi VALIDAR per eliminar definitivament."
        )
        ttk.Label(right_panel, text=instr, wraplength=200).pack(anchor='nw')

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-1>', self.on_double_click_cell)
        self.tree.bind('<Button-1>', self.on_single_click)
        self.load_from_db()

    def get_entitat_nom(self):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT nom FROM entitat LIMIT 1')
        r = cur.fetchone()
        conn.close()
        return r[0] if r else 'Entitat'

    # MODIFICAT: Recuperar percentatges inicials de la BD
    def get_last_validation_percentages(self):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        # Obtenir l'última validació
        cur.execute('SELECT MAX(id) FROM validacions')
        last_val_id = cur.fetchone()[0]
        percentages = {}
        if last_val_id:
            cur.execute('SELECT membre_id, percentatge FROM percentatges_validacio WHERE validacio_id = ?', (last_val_id,))
            for row in cur.fetchall():
                percentages[row[0]] = row[1]
        conn.close()
        return percentages

    # ------------------------ BD helpers ------------------------
    def load_from_db(self):
        self.tree.delete(*self.tree.get_children())
        self.item_meta.clear()
        entitat_nom = self.get_entitat_nom()
        entitat_item = self.tree.insert('', 'end', text=entitat_nom, open=True, tags=('entity',))
        self.item_meta[entitat_item] = {'type':'entity', 'db_id': None, 'eliminar':False, 'dret_vot':False}
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        
        # Recuperar percentatges inicials
        initial_percentages = self.get_last_validation_percentages()
        
        cur.execute('SELECT id, nom FROM particips WHERE eliminat IS NULL OR eliminat = 0 ORDER BY nom')
        parts = cur.fetchall()
        for pid, pname in parts:
            p_item = self.tree.insert(entitat_item, 'end', text=pname, open=True, tags=('particip',))
            self.item_meta[p_item] = {'type':'particip', 'db_id': pid, 'eliminar':False, 'dret_vot':False}
            cur.execute('SELECT id, nom, dret_vot FROM membres WHERE (eliminat IS NULL OR eliminat = 0) AND particip_id=? ORDER BY nom', (pid,))
            membres = cur.fetchall()
            for mid, mname, dret_vot in membres:
                # Recuperar percentatge inicial per aquest membre
                initial_pct = initial_percentages.get(mid)
                
                m_item = self.tree.insert(p_item, 'end', text=mname, open=True, tags=('member',))
                self.item_meta[m_item] = {
                    'type': 'member',
                    'db_id': mid,
                    'eliminar': False,
                    'dret_vot': bool(dret_vot),
                    'dret_vot_original': bool(dret_vot),
                    'percent_inicial': initial_pct  # Emmagatzemar percentatge inicial
                }
                cur.execute('SELECT id, nom FROM persones WHERE (eliminat IS NULL OR eliminat = 0) AND membre_id=? ORDER BY nom', (mid,))
                persones = cur.fetchall()
                for perid, pernom in persones:
                    per_item = self.tree.insert(m_item, 'end', text=pernom, open=True, tags=('person',))
                    self.item_meta[per_item] = {'type':'person', 'db_id': perid, 'eliminar':False, 'dret_vot':False}
        conn.close()
        self.refresh_tree_display_all()


    def on_tree_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self.context_add_btn.configure(text='[Selecciona un element]', state='disabled')
            return
        iid = sel[0]
        meta = self.item_meta.get(iid)
        if not meta:
            self.context_add_btn.configure(text='[Element desconegut]', state='disabled')
            return
        t = meta['type']
        if t == 'entity':
            self.context_add_btn.configure(text='Afegir partícip', state='normal', command=self.on_add_particip_entitat)
        elif t == 'particip':
            self.context_add_btn.configure(text='Afegir membre', state='normal', command=lambda: self.on_add_membre(iid))
        elif t == 'member':
            self.context_add_btn.configure(text='Afegir persona', state='normal', command=lambda: self.on_add_persona(iid))
        else:
            self.context_add_btn.configure(text='Cap acció disponible', state='disabled')

    def on_context_add(self):
        cmd = self.context_add_btn['command']
        if cmd:
            cmd()

    # -------------- MODIFICAT: on_add_particip_entitat ----------------
    def on_add_particip_entitat(self):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT nom FROM particips ORDER BY nom')
        parts = [r[0] for r in cur.fetchall()]
        conn.close()
        dlg = ChooseOrCreateDialog(self, 'Afegir partícip', parts)
        if dlg.result_value is None:
            return
        name, created = dlg.result_value
        pid = None
        # Comprovem si ja existeix a la UI
        entita_item = self.get_entitat_item()
        exists = False
        for child in self.tree.get_children(entita_item):
            meta = self.item_meta.get(child)
            if meta and meta['type'] == 'particip' and meta.get('nom') == name and not meta.get('eliminar', False):
                exists = True
                self.tree.see(child)
                break
        if exists:
            return
        item = self.tree.insert(entita_item, 'end', text=name, open=True, tags=('particip',))
        self.item_meta[item] = {
            'type': 'particip',
            'db_id': pid,
            'eliminar': False,
            'dret_vot': False,
            'nou': True,
            'nom': name
        }
        self.refresh_tree_display_all()

    # -------------- MODIFICAT: on_add_membre ----------------
    def on_add_membre(self, particip_item):
        meta = self.item_meta.get(particip_item)
        if not meta or meta['type'] != 'particip':
            return
        particip_id = meta['db_id']
        # Noms de membres existents
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT nom FROM membres ORDER BY nom')
        membres = [r[0] for r in cur.fetchall()]
        conn.close()
        dlg = ChooseOrCreateDialog(self, 'Afegir membre', membres)
        if dlg.result_value is None:
            return
        name, created = dlg.result_value
        mid = None  # Provisional
        # Comprovem si ja existeix a la UI
        exists = False
        for child in self.tree.get_children(particip_item):
            m = self.item_meta.get(child)
            if m and m['type'] == 'member' and m.get('nom') == name and not m.get('eliminar', False):
                exists = True
                self.tree.see(child)
                break
        if exists:
            return
        item = self.tree.insert(particip_item, 'end', text=name, open=True, tags=('member',))
        self.item_meta[item] = {
            'type': 'member',
            'db_id': mid,
            'eliminar': False,
            'dret_vot': False,
            'dret_vot_original': False,
            'nou': True,
            'nom': name,
            'particip_id': particip_id,
            'percent_inicial': None  # Nou membre sense percentatge inicial
        }
        self.refresh_tree_display_all()

    # ----------------- MODIFICAT: on_add_persona -----------------
    def on_add_persona(self, membre_item):
        meta = self.item_meta.get(membre_item)
        if not meta or meta['type'] != 'member':
            return
        membre_id = meta['db_id']
        # En comptes d'obtenir només persones de la BD, permet noms lliures a la UI
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT nom FROM persones WHERE (eliminat IS NULL OR eliminat = 0) ORDER BY nom')
        persones = [r[0] for r in cur.fetchall()]
        conn.close()
        dlg = ChooseOrCreateDialog(self, 'Afegir persona', persones)
        if dlg.result_value is None:
            return
        name, created = dlg.result_value

        # NO afegim a la BD encara, només a la UI
        pid = None  # No hi ha id de BD encara
        # Comprovem si ja existeix la persona a aquest membre (a la UI, no a la BD)
        exists = False
        for child in self.tree.get_children(membre_item):
            m = self.item_meta.get(child)
            if m and m['type'] == 'person' and m.get('nom') == name and not m.get('eliminar', False):
                exists = True
                self.tree.see(child)
                break
        if exists:
            return
        item = self.tree.insert(membre_item, 'end', text=name, open=True, tags=('person',))
        self.item_meta[item] = {
            'type': 'person',
            'db_id': pid,
            'eliminar': False,
            'dret_vot': False,
            'nou': True,
            'nom': name,
            'membre_id': membre_id
        }
        self.refresh_tree_display_all()

    def get_entitat_item(self):
        roots = self.tree.get_children('')
        return roots[0] if roots else None

    def on_double_click_cell(self, event):
        region = self.tree.identify('region', event.x, event.y)
        if region not in ('cell', 'tree'):
            return
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row:
            return
        if col == '#1':
            self.toggle_eliminar_recursive(row)
            self.refresh_tree_display_all()
            return "break"
        elif col == '#2':
            meta = self.item_meta.get(row)
            if meta and meta['type'] == 'member':
                meta['dret_vot'] = not meta.get('dret_vot', False)
                # Desa a la BD immediatament (opcional, pots treure si només vols guardar a validar)
                db_id = meta.get('db_id')
                if db_id is not None:
                    conn = sqlite3.connect(DB_FILE)
                    cur = conn.cursor()
                    cur.execute('UPDATE membres SET dret_vot=? WHERE id=?', (1 if meta['dret_vot'] else 0, db_id))
                    conn.commit()
                    conn.close()
                self.refresh_tree_display_item(row)
                self.refresh_subtree(row)
                self.refresh_tree_display_all()
            return "break"
        else:
            meta = self.item_meta.get(row)
            if not meta:
                return "break"
            t = meta.get('type')
            if t == 'entity':
                self.on_add_particip_entitat()
            elif t == 'particip':
                self.on_add_membre(row)
            elif t == 'member':
                self.on_add_persona(row)
            else:
                messagebox.showinfo('Info', 'Els elements de tipus "Persona" no poden tenir fills.')
            return "break"
    
    
    def on_single_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        if region not in ('cell', 'tree'):
            return
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row:
            return
        meta = self.item_meta.get(row)
        if not meta:
            return
        if col == '#1':
            self.toggle_eliminar_recursive(row)
            self.refresh_tree_display_all()
            return
        elif col == '#2':
            if meta.get('type') == 'member':
                meta['dret_vot'] = not meta.get('dret_vot', False)
                db_id = meta.get('db_id')
                if db_id is not None:
                    conn = sqlite3.connect(DB_FILE)
                    cur = conn.cursor()
                    cur.execute('UPDATE membres SET dret_vot=? WHERE id=?', (1 if meta['dret_vot'] else 0, db_id))
                    conn.commit()
                    conn.close()
                self.refresh_tree_display_item(row)
                self.refresh_subtree(row)
                self.refresh_tree_display_all()
            return

    def toggle_eliminar_recursive(self, item):
        meta = self.item_meta.get(item)
        if not meta:
            return
        currently = meta.get('eliminar', False)
        if not currently:
            def mark_descendants(iid):
                m = self.item_meta.get(iid)
                if m is None:
                    return
                m['eliminar'] = True
                self.refresh_tree_display_item(iid)
                curtags = list(self.tree.item(iid, 'tags'))
                if 'eliminat' not in curtags:
                    curtags.append('eliminat')
                    self.tree.item(iid, tags=tuple(curtags))
                for ch in self.tree.get_children(iid):
                    mark_descendants(ch)
            mark_descendants(item)
        else:
            def unmark_descendants(iid):
                m = self.item_meta.get(iid)
                if m is None:
                    return
                if m.get('eliminar'):
                    m['eliminar'] = False
                    self.refresh_tree_display_item(iid)
                    curtags = list(self.tree.item(iid, 'tags'))
                    if 'eliminat' in curtags:
                        curtags = [t for t in curtags if t != 'eliminat']
                        self.tree.item(iid, tags=tuple(curtags))
                for ch in self.tree.get_children(iid):
                    unmark_descendants(ch)
            unmark_descendants(item)
            parent = self.tree.parent(item)
            while parent:
                pmeta = self.item_meta.get(parent)
                if pmeta and pmeta.get('eliminar'):
                    pmeta['eliminar'] = False
                    self.refresh_tree_display_item(parent)
                    curtags = list(self.tree.item(parent, 'tags'))
                    if 'eliminat' in curtags:
                        curtags = [t for t in curtags if t != 'eliminat']
                        self.tree.item(parent, tags=tuple(curtags))
                    parent = self.tree.parent(parent)
                else:
                    break
        self.refresh_tree_display_all()

    # MODIFICAT: Afegir visualització de percentatge inicial
    def refresh_tree_display_item(self, item):
        meta = self.item_meta.get(item)
        if not meta:
            return
    
        # Checkbox d'eliminació
        elim = '☒' if meta.get('eliminar') else '☐'
        # Checkbox dret de vot per membres
        dret = '☒' if meta.get('type') == 'member' and meta.get('dret_vot') else '☐' if meta.get('type') == 'member' else ''
    
        try:
            self.tree.set(item, 'Eliminar', elim)
            self.tree.set(item, 'DretVot', dret)
        except Exception:
            pass
    
        if meta.get('type') == 'member':
            # Comptatge de persones sota el membre (inclou Vacant)
            count = self.count_persons_under(item)
            try:
                self.tree.set(item, 'Persones', str(count))
            except Exception:
                pass
    
            # Percentatge calculat sobre persones vàlides amb dret a vot (ignora "Vacant")
            total = getattr(self, 'total_persones_vot', None)
            if total is None or total == 0:
                total = self.total_persons_with_voting()
    
            member_valid = self.count_valid_persons_under(item) if meta.get('dret_vot') else 0
            pct = (member_valid / total * 100.0) if (meta.get('dret_vot') and total > 0) else 0.0
            try:
                self.tree.set(item, 'Percentatge', f"{pct:.1f}%")
            except Exception:
                pass
    
            # Percentatge inicial (si existeix)
            if meta.get('percent_inicial') is not None:
                pct_ini_str = f"{meta['percent_inicial']:.1f}%"
            else:
                pct_ini_str = ""
            try:
                self.tree.set(item, 'PercentatgeInicial', pct_ini_str)
            except Exception:
                pass
        else:
            # Restableix columnes per no membres
            try:
                self.tree.set(item, 'Persones', '')
                self.tree.set(item, 'Percentatge', '')
                self.tree.set(item, 'PercentatgeInicial', '')
            except Exception:
                pass
    
        # Gestiona tags
        current_tags = list(self.tree.item(item, 'tags'))
    
        # Tag eliminat
        if meta.get('eliminar'):
            if 'eliminat' not in current_tags:
                current_tags.append('eliminat')
        else:
            if 'eliminat' in current_tags:
                current_tags = [t for t in current_tags if t != 'eliminat']
    
        # Tag no_vot
        apply_no_vot = False
        if meta.get('type') == 'member':
            apply_no_vot = not bool(meta.get('dret_vot'))
        else:
            parent = self.tree.parent(item)
            while parent:
                pmeta = self.item_meta.get(parent)
                if pmeta and pmeta.get('type') == 'member':
                    apply_no_vot = not bool(pmeta.get('dret_vot'))
                    break
                parent = self.tree.parent(parent)
        if apply_no_vot:
            if 'no_vot' not in current_tags:
                current_tags.append('no_vot')
        else:
            if 'no_vot' in current_tags:
                current_tags = [t for t in current_tags if t != 'no_vot']
    
        self.tree.item(item, tags=tuple(current_tags))


    def refresh_tree_display_all(self):
        self.total_persones_vot = self.total_persons_with_voting()
        def rec(item):
            self.refresh_tree_display_item(item)
            for ch in self.tree.get_children(item):
                rec(ch)
        for root in self.tree.get_children(''):
            rec(root)

    def refresh_subtree(self, item):
        for ch in self.tree.get_children(item):
            self.refresh_tree_display_item(ch)
            self.refresh_subtree(ch)

    def count_persons_under(self, item):
        total = 0
        for ch in self.tree.get_children(item):
            m = self.item_meta.get(ch)
            if not m:
                continue
            if m.get('type') == 'person':
                total += 1
            else:
                total += self.count_persons_under(ch)
        return total

    def is_effectively_eliminated(self, item):
        iid = item
        while iid:
            m = self.item_meta.get(iid)
            if m and m.get('eliminar'):
                return True
            iid = self.tree.parent(iid)
        return False

    def count_valid_persons_under(self, item):
        total = 0
        for ch in self.tree.get_children(item):
            m = self.item_meta.get(ch)
            if not m:
                continue
            if m.get('type') == 'person':
                # Comptem només si no està eliminada i el nom no és "Vacant"
                if not self.is_effectively_eliminated(ch) and m.get('nom') != "Vacant":
                    total += 1
            else:
                # Recorrem recursivament els fills
                total += self.count_valid_persons_under(ch)
        return total


    def total_persons_with_voting(self):
        total = 0
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'member' and meta.get('dret_vot'):
                if not self.is_effectively_eliminated(iid):
                    total += self.count_valid_persons_under(iid)
        return total

    # -------------- MODIFICAT: on_validate ------------------
    def on_validate(self):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
    
        persona_afegida = False  # Flag per saber si hem afegit una persona
    
        # 1. Partícips nous
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'particip' and meta.get('nou', False):
                cur.execute('INSERT INTO particips (nom) VALUES (?)', (meta['nom'],))
                meta['db_id'] = cur.lastrowid
                meta['nou'] = False
    
        # 2. Membres nous
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'member' and meta.get('nou', False):
                particip_id = meta.get('particip_id')
                if not particip_id:
                    pitem = self.tree.parent(iid)
                    pmeta = self.item_meta.get(pitem)
                    particip_id = pmeta.get('db_id') if pmeta else None
                if particip_id:
                    cur.execute(
                        "INSERT INTO membres (nom, particip_id, dret_vot) VALUES (?, ?, ?)",
                        (meta['nom'], particip_id, 1 if meta.get('dret_vot', False) else 0)
                    )
                    meta['db_id'] = cur.lastrowid
                    meta['nou'] = False
                    meta['particip_id'] = particip_id
    
        # 3. Persones noves
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'person' and meta.get('nou', False):
                membre_id = meta.get('membre_id')
                if not membre_id:
                    mitem = self.tree.parent(iid)
                    mmeta = self.item_meta.get(mitem)
                    membre_id = mmeta.get('db_id') if mmeta else None
                if membre_id:
                    cur.execute(
                        "INSERT OR REPLACE INTO persones (nom, membre_id, eliminat) VALUES (?, ?, 0)",
                        (meta['nom'], membre_id)
                    )
                    nou_id = cur.lastrowid
                    meta['db_id'] = nou_id
                    meta['nou'] = False
                    meta['membre_id'] = membre_id
    
                    # Si s'ha creat realment una persona nova, marquem-ho
                    if nou_id is not None and nou_id != 0:
                        persona_afegida = True
    
        conn.commit()
        conn.close()
    
        # Variables per controlar eliminacions i canvis de dret de vot
        to_mark = {'particip': set(), 'member': set(), 'person': set()}
        dret_vot_modificat = False
    
        for iid, meta in self.item_meta.items():
            if meta.get('eliminar'):
                if meta['type'] == 'particip' and meta['db_id']:
                    to_mark['particip'].add(meta['db_id'])
                elif meta['type'] == 'member' and meta['db_id']:
                    to_mark['member'].add(meta['db_id'])
                elif meta['type'] == 'person' and meta['db_id']:
                    to_mark['person'].add(meta['db_id'])
            if meta.get('type') == 'member' and meta.get('db_id') is not None:
                if meta.get('dret_vot') != meta.get('dret_vot_original'):
                    dret_vot_modificat = True
    
        # Desa l'estat de dret_vot a la BD
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'member' and meta.get('db_id') is not None:
                dret_vot_db = 1 if meta.get('dret_vot') else 0
                cur.execute('UPDATE membres SET dret_vot=? WHERE id=?', (dret_vot_db, meta['db_id']))
        conn.commit()
        conn.close()
    
        # Desa percentatges i dret de vot amb data de validació
        self.save_percentatges_validacio()
    
        # Si s'ha afegit una persona, només mostrem aquest missatge i sortim
        if persona_afegida:
            messagebox.showinfo('VALIDAR', 'Dades validades correctament')
            return
    
        # Si no hi ha eliminacions ni canvi de dret de vot
        if not any(to_mark.values()) and not dret_vot_modificat:
            messagebox.showinfo('VALIDAR', 'No hi ha canvis per validar.')
            return
    
        # Si hi ha elements per eliminar, demanem confirmació
        if any(to_mark.values()):
            if not messagebox.askyesno('VALIDAR', 'Confirma marcar com a eliminats els elements seleccionats?'):
                return
    
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        now = datetime.now().isoformat(sep=' ', timespec='seconds')
    
        # Marca com a eliminats, incloses persones "Vacant"
        if to_mark['person']:
            ids = tuple(to_mark['person'])
            cur.execute(f"""
                UPDATE persones
                SET eliminat = 1, data_eliminacio = ?
                WHERE id IN ({','.join('?' for _ in ids)})
            """, (now, *ids))
    
        if to_mark['member']:
            ids = tuple(to_mark['member'])
            cur.execute(f"""
                UPDATE membres
                SET eliminat = 1, data_eliminacio = ?
                WHERE id IN ({','.join('?' for _ in ids)})
            """, (now, *ids))
    
        if to_mark['particip']:
            ids = tuple(to_mark['particip'])
            cur.execute(f"SELECT id FROM membres WHERE particip_id IN ({','.join('?' for _ in ids)})", ids)
            mids = [r[0] for r in cur.fetchall()]
            if mids:
                cur.execute(f"""
                    UPDATE persones
                    SET eliminat = 1, data_eliminacio = ?
                    WHERE membre_id IN ({','.join('?' for _ in mids)})
                """, (now, *mids))
                cur.execute(f"""
                    UPDATE membres
                    SET eliminat = 1, data_eliminacio = ?
                    WHERE id IN ({','.join('?' for _ in mids)})
                """, (now, *mids))
            cur.execute(f"""
                UPDATE particips
                SET eliminat = 1, data_eliminacio = ?
                WHERE id IN ({','.join('?' for _ in ids)})
            """, (now, *ids))
    
        conn.commit()
        conn.close()
        self.load_from_db()
    
        # Actualitza dret_vot_original
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'member':
                meta['dret_vot_original'] = meta.get('dret_vot')
    
        # Missatges finals segons accions fetes
        if any(to_mark.values()) and dret_vot_modificat:
            message = 'S\'han validat eliminacions i s\'han actualitzat dret de vot i percentatges.'
        elif any(to_mark.values()):
            message = 'S\'han validat eliminacions.'
        elif dret_vot_modificat:
            message = 'S\'han actualitzat dret de vot i percentatges.'
        else:
            message = 'No hi ha canvis per validar.'
    
        messagebox.showinfo('VALIDAR', message)



    def save_percentatges_validacio(self):
        """Guarda a la base de dades els percentatges actuals de cada membre amb data/hora."""
        membres_percent = []
        total = self.total_persons_with_voting() if hasattr(self, 'total_persons_with_voting') else 0
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'member' and meta.get('db_id') and not self.is_effectively_eliminated(iid):
                member_valid = self.count_valid_persons_under(iid) if meta.get('dret_vot') else 0
                pct = (member_valid / total * 100.0) if (meta.get('dret_vot') and total > 0) else 0.0
                membres_percent.append((meta['db_id'], pct))
        if not membres_percent:
            return
        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('INSERT INTO validacions (datahora) VALUES (?)', (dt,))
        validacio_id = cur.lastrowid
        for membre_id, pct in membres_percent:
            cur.execute(
                'INSERT INTO percentatges_validacio (validacio_id, membre_id, percentatge) VALUES (?, ?, ?)',
                (validacio_id, membre_id, pct)
            )
        conn.commit()
        conn.close()

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        try:
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
        except Exception:
            pass
        app = ArbreApp()
        app.withdraw()
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO particips(nom) VALUES (?)", ("P",))
        pid = cur.lastrowid
        cur.execute("INSERT INTO membres(nom, particip_id) VALUES (?,?)", ("M1", pid))
        m1 = cur.lastrowid
        cur.execute("INSERT INTO membres(nom, particip_id) VALUES (?,?)", ("M2", pid))
        m2 = cur.lastrowid
        cur.executemany("INSERT INTO persones(nom, membre_id) VALUES (?,?)", [("A", m1), ("B", m1), ("C", m2)])
        conn.commit(); conn.close()
        app.load_from_db()
        print('SELFTEST OK')
        sys.exit(0)
    else:
        app = ArbreApp()
        app.mainloop()
