# /pages/reports.py

import streamlit as st
import pandas as pd

# Presupunem că HybridAnalyzerV73 este in directorul root (pentru import)
from HybridAnalyzerV73 import load_all_analysis_data, FIREBASE_ENABLED 

st.set_page_config(layout="wide", page_title="Rapoarte Baschet Salvate")

st.title("📜 Rapoarte Analize Salvate (Firebase)")

if not FIREBASE_ENABLED:
    st.error("Conexiunea Firebase este dezactivată. Nu se pot încărca rapoartele.")
else:
    # --- Incarcare Date ---
    # Nu folosim cache pentru a vedea datele noi imediat.
    
    if st.button("Reincarca Date (Citire din Firebase)") or 'reports_data' not in st.session_state:
        with st.spinner("Încărcare date din Firebase..."):
            st.session_state['reports_data'] = load_all_analysis_data()
        
    analysis_data = st.session_state.get('reports_data', [])


    if not analysis_data:
        st.info("Nu s-au găsit analize salvate. Vă rugăm să rulați și să salvați o analiză nouă pe pagina principală (pentru a avea toate câmpurile necesare).")
    else:
        # Convertim lista de dictionare in DataFrame pentru afisare facila
        df_display = pd.DataFrame(analysis_data)
        
        # Excludem coloana de markdown din afisarea initiala a tabelului
        df_table = df_display.drop(columns=['analysis_markdown'])
        
        st.subheader(f"Ultimele {len(df_table)} Analize Salvate")
        
        st.dataframe(df_table, use_container_width=True)
        
        st.markdown("---")
        
        # --- Sectiunea de Vizualizare Detaliata a Raportului ---
        st.subheader("Vizualizare Raport Detaliat")
        
        # Creem o lista de optiuni (Meci - ID)
        options = [f"{row['Meci']} - {row['ID']}" for index, row in df_table.iterrows()]
        
        selected_option = st.selectbox(
            "Selecteaza o Analiza pentru Vizualizare:",
            options,
            index=0
        )
        
        if selected_option:
            # Extragem ID-ul din optiunea selectata
            selected_id = selected_option.split(' - ')[-1].strip()
            
            # Căutăm direct în datele deja încărcate
            selected_row = df_display[df_display['ID'] == selected_id]
            
            if not selected_row.empty:
                report_markdown = selected_row.iloc[0]['analysis_markdown']
                
                if report_markdown:
                    st.markdown(report_markdown)
                else:
                    st.error("Raportul detaliat (Markdown) nu a fost găsit. Acesta este un document salvat înainte de actualizare. Vă rugăm să rulați o analiză nouă pentru a o genera.")
            else:
                 st.warning("Eroare la găsirea rândului selectat.")
