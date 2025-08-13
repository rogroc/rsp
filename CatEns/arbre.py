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
            nom TEXT UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS membres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            particip_id INTEGER,
            UNIQUE(nom, particip_id),
            FOREIGN KEY(particip_id) REFERENCES particips(id) ON DELETE CASCADE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS persones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            membre_id INTEGER,
            UNIQUE(nom, membre_id),
            FOREIGN KEY(membre_id) REFERENCES membres(id) ON DELETE CASCADE
        )
    ''')
    # Noves taules per a validacions i percentatges
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
        self.geometry('900x600')
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

        self.tree = ttk.Treeview(central, columns=('Eliminar','DretVot','Persones','Percentatge'), show='tree headings')
        self.tree.heading('#0', text='Nom / Nivell')
        self.tree.column('#0', width=360)
        self.tree.heading('Eliminar', text='Eliminar')
        self.tree.column('Eliminar', width=80, anchor='center')
        self.tree.heading('DretVot', text='Dret de vot')
        self.tree.column('DretVot', width=80, anchor='center')
        self.tree.heading('Persones', text='Persones membre')
        self.tree.column('Persones', width=100, anchor='center')
        self.tree.heading('Percentatge', text='Percentatge membre')
        self.tree.column('Percentatge', width=110, anchor='center')
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

    # ------------------------ BD helpers ------------------------
    def load_from_db(self):
        self.tree.delete(*self.tree.get_children())
        self.item_meta.clear()
        entitat_nom = self.get_entitat_nom()
        entitat_item = self.tree.insert('', 'end', text=entitat_nom, open=True, tags=('entity',))
        self.item_meta[entitat_item] = {'type':'entity', 'db_id': None, 'eliminar':False, 'dret_vot':False}
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT id, nom FROM particips ORDER BY nom')
        parts = cur.fetchall()
        for pid, pname in parts:
            p_item = self.tree.insert(entitat_item, 'end', text=pname, open=True, tags=('particip',))
            self.item_meta[p_item] = {'type':'particip', 'db_id': pid, 'eliminar':False, 'dret_vot':False}
            cur.execute('SELECT id, nom FROM membres WHERE particip_id=? ORDER BY nom', (pid,))
            membres = cur.fetchall()
            for mid, mname in membres:
                m_item = self.tree.insert(p_item, 'end', text=mname, open=True, tags=('member',))
                self.item_meta[m_item] = {'type':'member', 'db_id': mid, 'eliminar':False, 'dret_vot':False}
                cur.execute('SELECT id, nom FROM persones WHERE membre_id=? ORDER BY nom', (mid,))
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
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        if created:
            try:
                cur.execute('INSERT INTO particips (nom) VALUES (?)', (name,))
                conn.commit()
                pid = cur.lastrowid
            except sqlite3.IntegrityError:
                cur.execute('SELECT id FROM particips WHERE nom=?', (name,))
                pid = cur.fetchone()[0]
        else:
            cur.execute('SELECT id FROM particips WHERE nom=?', (name,))
            row = cur.fetchone()
            pid = row[0] if row else None
        conn.close()
        entita_item = self.get_entitat_item()
        exists = False
        for child in self.tree.get_children(entita_item):
            meta = self.item_meta.get(child)
            if meta and meta['type']=='particip' and meta['db_id']==pid:
                exists = True
                self.tree.see(child)
                break
        if not exists:
            item = self.tree.insert(entita_item, 'end', text=name, open=True, tags=('particip',))
            self.item_meta[item] = {'type':'particip', 'db_id':pid, 'eliminar':False, 'dret_vot':False}
        self.refresh_tree_display_all()

    def on_add_membre(self, particip_item):
        meta = self.item_meta.get(particip_item)
        if not meta or meta['type']!='particip':
            return
        particip_id = meta['db_id']
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT nom FROM membres ORDER BY nom')
        membres = [r[0] for r in cur.fetchall()]
        conn.close()
        dlg = ChooseOrCreateDialog(self, 'Afegir membre', membres)
        if dlg.result_value is None:
            return
        name, created = dlg.result_value
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        if created:
            try:
                cur.execute('INSERT INTO membres (nom, particip_id) VALUES (?, ?)', (name, particip_id))
                conn.commit()
                mid = cur.lastrowid
            except sqlite3.IntegrityError:
                cur.execute('SELECT id FROM membres WHERE nom=? AND particip_id=?', (name, particip_id))
                row = cur.fetchone()
                mid = row[0] if row else None
        else:
            cur.execute('SELECT id FROM membres WHERE nom=? AND particip_id=?', (name, particip_id))
            row = cur.fetchone()
            if row:
                mid = row[0]
            else:
                cur.execute('INSERT INTO membres (nom, particip_id) VALUES (?, ?)', (name, particip_id))
                conn.commit()
                mid = cur.lastrowid
        conn.close()
        exists = False
        for child in self.tree.get_children(particip_item):
            meta = self.item_meta.get(child)
            if meta and meta['type']=='member' and meta['db_id']==mid:
                exists = True
                self.tree.see(child)
                break
        if not exists:
            item = self.tree.insert(particip_item, 'end', text=name, open=True, tags=('member',))
            self.item_meta[item] = {'type':'member', 'db_id':mid, 'eliminar':False, 'dret_vot':False}
        self.refresh_tree_display_all()

    def on_add_persona(self, membre_item):
        meta = self.item_meta.get(membre_item)
        if not meta or meta['type']!='member':
            return
        membre_id = meta['db_id']
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT nom FROM persones ORDER BY nom')
        persones = [r[0] for r in cur.fetchall()]
        conn.close()
        dlg = ChooseOrCreateDialog(self, 'Afegir persona', persones)
        if dlg.result_value is None:
            return
        name, created = dlg.result_value
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        if created:
            try:
                cur.execute('INSERT INTO persones (nom, membre_id) VALUES (?, ?)', (name, membre_id))
                conn.commit()
                pid = cur.lastrowid
            except sqlite3.IntegrityError:
                cur.execute('SELECT id FROM persones WHERE nom=? AND membre_id=?', (name, membre_id))
                row = cur.fetchone()
                pid = row[0] if row else None
        else:
            cur.execute('SELECT id FROM persones WHERE nom=? AND membre_id=?', (name, membre_id))
            row = cur.fetchone()
            if row:
                pid = row[0]
            else:
                cur.execute('INSERT INTO persones (nom, membre_id) VALUES (?, ?)', (name, membre_id))
                conn.commit()
                pid = cur.lastrowid
        conn.close()
        exists = False
        for child in self.tree.get_children(membre_item):
            meta = self.item_meta.get(child)
            if meta and meta['type']=='person' and meta['db_id']==pid:
                exists = True
                self.tree.see(child)
                break
        if not exists:
            item = self.tree.insert(membre_item, 'end', text=name, open=True, tags=('person',))
            self.item_meta[item] = {'type':'person', 'db_id':pid, 'eliminar':False, 'dret_vot':False}
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

    def refresh_tree_display_item(self, item):
        meta = self.item_meta.get(item)
        if not meta:
            return
        elim = '☒' if meta.get('eliminar') else '☐'
        if meta.get('type') == 'member':
            dret = '☒' if meta.get('dret_vot') else '☐'
        else:
            dret = ''
        try:
            self.tree.set(item, 'Eliminar', elim)
            self.tree.set(item, 'DretVot', dret)
        except Exception:
            pass
        if meta.get('type') == 'member':
            count = self.count_persons_under(item)
            try:
                self.tree.set(item, 'Persones', str(count))
            except Exception:
                pass
            total = getattr(self, 'total_persones_vot', None)
            if total is None or total == 0:
                total = self.total_persons_with_voting()
            member_valid = self.count_valid_persons_under(item) if meta.get('dret_vot') else 0
            pct = (member_valid / total * 100.0) if (meta.get('dret_vot') and total > 0) else 0.0
            try:
                self.tree.set(item, 'Percentatge', f"{pct:.1f}%")
            except Exception:
                pass
        else:
            try:
                self.tree.set(item, 'Persones', '')
                self.tree.set(item, 'Percentatge', '')
            except Exception:
                pass

        current_tags = list(self.tree.item(item, 'tags'))

        if meta.get('eliminar'):
            if 'eliminat' not in current_tags:
                current_tags.append('eliminat')
        else:
            if 'eliminat' in current_tags:
                current_tags = [t for t in current_tags if t != 'eliminat']

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
                if not self.is_effectively_eliminated(ch):
                    total += 1
            else:
                total += self.count_valid_persons_under(ch)
        return total

    def total_persons_with_voting(self):
        total = 0
        for iid, meta in self.item_meta.items():
            if meta.get('type') == 'member' and meta.get('dret_vot'):
                if not self.is_effectively_eliminated(iid):
                    total += self.count_valid_persons_under(iid)
        return total

    def on_validate(self):
        to_mark = {'particip': set(), 'member': set(), 'person': set()}
        dret_vot_modificat = False
    
        # Detecta elements marcats per eliminar i canvis en dret de vot
        for iid, meta in self.item_meta.items():
            if meta.get('eliminar'):
                if meta['type'] == 'particip' and meta['db_id']:
                    to_mark['particip'].add(meta['db_id'])
                elif meta['type'] == 'member' and meta['db_id']:
                    to_mark['member'].add(meta['db_id'])
                elif meta['type'] == 'person' and meta['db_id']:
                    to_mark['person'].add(meta['db_id'])
    
            # Comprovem si el dret de vot ha canviat
            if meta['type'] == 'member' and meta.get('dret_vot_original') is not None:
                if meta.get('dret_vot_actual') != meta['dret_vot_original']:
                    dret_vot_modificat = True
    
        # Guardem percentatges i dret de vot amb data de validació
        self.save_percentatges_validacio()  # hauria d'incloure percentatges i dret de vot
    
        # Si no hi ha eliminacions ni canvi de dret de vot, avisem
        if not any(to_mark.values()) and not dret_vot_modificat:
            messagebox.showinfo('VALIDAR', 'No hi ha elements marcats per eliminar ni dret de vot modificat.')
            return
    
        # Si hi ha elements per marcar com a eliminats, demana confirmació
        if any(to_mark.values()):
            if not messagebox.askyesno('VALIDAR', 'Confirma marcar com a eliminats els elements seleccionats?'):
                return
    
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        now = datetime.now().isoformat(sep=' ', timespec='seconds')
    
        # Marca com a eliminats
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
    
        # Missatge segons si només hi ha dret de vot modificat o eliminacions
        if dret_vot_modificat and not any(to_mark.values()):
            message = 'Percentatges i dret de vot guardats amb data de validació.'
        else:
            message = 'Elements marcats com a eliminats i percentatges guardats.'
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
