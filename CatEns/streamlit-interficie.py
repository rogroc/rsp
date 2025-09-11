import streamlit as st
import pandas as pd

# ───────────────────────────────
# Classe CanvasTree (versió Streamlit)
# ───────────────────────────────
class CanvasTree:
    def __init__(self, columns, column_colors=None, row_height=25):
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

    def render_header(self):
        """Mostra la capçalera amb els noms de les columnes i els colors."""
        cols = st.columns(len(self.columns))
        for i, (col, color) in enumerate(zip(self.columns, self.column_colors)):
            cols[i].markdown(
                f"<div style='background-color:{color}; padding:8px; font-weight:bold; text-align:center;'>{col}</div>",
                unsafe_allow_html=True
            )

    def render_table_placeholder(self):
        """Mostra una taula buida (placeholder)"""
        df = pd.DataFrame(columns=self.columns)
        st.dataframe(df, use_container_width=True, height=200)

# ───────────────────────────────
# Exemple d’ús
# ───────────────────────────────
def main():
    st.title("CanvasTree en Streamlit (versió inicial)")

    columns = ["Nom", "Carrec", "Departament"]
    column_colors = ["#f0f0f0", "#d0f0d0", "#d0d0f0"]

    tree = CanvasTree(columns, column_colors)

    tree.render_header()
    tree.render_table_placeholder()


if __name__ == "__main__":
    main()
