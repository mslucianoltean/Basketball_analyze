import streamlit as st
import json

# IMPORTURI CORECTATE: S-a inlocuit 'HybridAnalyzerV73' cu 'run_hybrid_analyzer'
# si 'get_all_match_ids'/'get_analysis_by_id' cu 'load_analysis_ids'/'load_analysis_data'
from HybridAnalyzerV73 import (
    run_hybrid_analyzer, 
    save_to_firebase, 
    load_analysis_ids, 
    load_analysis_data, 
    FIREBASE_ENABLED, 
    COLLECTION_NAME_NBA
)

st.set_page_config(layout="wide", page_title="Hybrid Analyzer V7.3")

# --- Initializare Stare ---
if 'analysis_output' not in st.session_state:
    st.session_state['analysis_output'] = ""
if 'result_data' not in st.session_state:
    st.session_state['result_data'] = {}


# --- Bara Laterala (Sidebar) ---

with st.sidebar:
    st.header("Vizualizează Analize Salvate 📜")

    if FIREBASE_ENABLED:
        match_ids = load_analysis_ids()
        
        selected_id = st.selectbox(
            "Selectează ID Analiză:",
            match_ids,
            index=None
        )

        if st.button("Încarcă Analiză"):
            if selected_id and selected_id != "Firebase Dezactivat" and selected_id != "Eroare la Încărcare":
                data = load_analysis_data(selected_id)
                if data:
                    st.success(f"Analiza `{selected_id}` încărcată.")
                    
                    # Afișează datele brute în sidebar
                    st.subheader("Date Analiză Brute")
                    # Folosim json.dumps pentru formatare mai lizibila
                    st.json(data)
                    
                    # Afișează raportul formatat in pagina principala
                    st.session_state['analysis_output'] = data.get('analysis_markdown', "Raportul formatat nu a fost găsit în datele salvate.")
                    st.session_state['result_data'] = data
                else:
                    st.error("Nu s-au putut încărca datele pentru ID-ul selectat.")
            else:
                st.warning("Vă rugăm să selectați un ID valid.")
    else:
        st.info("Funcționalitatea Firebase este dezactivată (Lipsesc st.secrets).")

# --- Pagina Principală ---

st.title("🏀 Hybrid Analyzer V7.3 - Analiză Baschet")
st.markdown("Introduceți cotele de deschidere (Open) și închidere (Close) pentru 7 linii adiacente.")


# --- Formular de Input ---
with st.form(key='hybrid_analysis_form'):
    
    st.subheader("Detalii Meci")
    col_liga, col_gazda, col_oaspete = st.columns(3)
    
    liga = col_liga.text_input("Liga", "NBA")
    echipa_gazda = col_gazda.text_input("Echipa Gazdă", "Lakers")
    echipa_oaspete = col_oaspete.text_input("Echipa Oaspete", "Celtics")

    data_input = {'liga': liga, 'echipa_gazda': echipa_gazda, 'echipa_oaspete': echipa_oaspete}

    st.markdown("---")
    
    # Coloane pentru introducerea datelor
    st.subheader("Total Puncte (Over/Under) - 7 Linii")
    
    # Header
    col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns(6)
    col_h1.markdown("**Linia**")
    col_h2.markdown("**Valoare**")
    col_h3.markdown("**Over Open**")
    col_h4.markdown("**Over Close**")
    col_h5.markdown("**Under Open**")
    col_h6.markdown("**Under Close**")
    
    # Liniile TP
    tp_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
    tp_lines_labels = ['Close Line', '-3 pts (M3)', '-2 pts (M2)', '-1 pts (M1)', '+1 pts (P1)', '+2 pts (P2)', '+3 pts (P3)']
    
    # Campul istoric open (V7.3 specific)
    st.markdown("---")
    st.subheader("Linia Open Istorică")
    col_open_hist, _ = st.columns([1, 5])
    tp_line_open_hist = col_open_hist.number_input("Open Istoric", min_value=150.0, max_value=300.0, value=220.5, step=0.5, format="%.1f")
    data_input['tp_line_open_hist'] = tp_line_open_hist
    st.markdown("---")

    for key, label in zip(tp_lines_keys, tp_lines_labels):
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        col1.markdown(f"**{label}**")
        data_input[f'tp_line_{key}'] = col2.number_input("", min_value=150.0, max_value=300.0, value=220.0, step=0.5, format="%.1f", key=f'tp_val_{key}')
        data_input[f'tp_open_over_{key}'] = col3.number_input("", min_value=1.0, max_value=5.0, value=1.90, step=0.01, format="%.2f", key=f'tp_oo_{key}')
        data_input[f'tp_close_over_{key}'] = col4.number_input("", min_value=1.0, max_value=5.0, value=1.95, step=0.01, format="%.2f", key=f'tp_co_{key}')
        data_input[f'tp_open_under_{key}'] = col5.number_input("", min_value=1.0, max_value=5.0, value=1.90, step=0.01, format="%.2f", key=f'tp_ou_{key}')
        data_input[f'tp_close_under_{key}'] = col6.number_input("", min_value=1.0, max_value=5.0, value=1.85, step=0.01, format="%.2f", key=f'tp_cu_{key}')

    st.markdown("---")

    st.subheader("Handicap (Home/Away) - 7 Linii")

    # Header Handicap
    col_hh1, col_hh2, col_hh3, col_hh4, col_hh5, col_hh6 = st.columns(6)
    col_hh1.markdown("**Linia**")
    col_hh2.markdown("**Valoare**")
    col_hh3.markdown("**Home Open**")
    col_hh4.markdown("**Home Close**")
    col_hh5.markdown("**Away Open**")
    col_hh6.markdown("**Away Close**")

    # Liniile HD (Cheile sunt identice cu TP)
    hd_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
    hd_lines_labels = ['Close Line', '-3 pts (M3)', '-2 pts (M2)', '-1 pts (M1)', '+1 pts (P1)', '+2 pts (P2)', '+3 pts (P3)']

    for key, label in zip(hd_lines_keys, hd_lines_labels):
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        col1.markdown(f"**{label}**")
        # Valoarea liniei (ex: -5.0)
        data_input[f'hd_line_{key}'] = col2.number_input("", min_value=-20.0, max_value=20.0, value=-5.0, step=0.5, format="%.1f", key=f'hd_val_{key}')
        
        # Home (Gazda)
        data_input[f'hd_open_home_{key}'] = col3.number_input("", min_value=1.0, max_value=5.0, value=1.90, step=0.01, format="%.2f", key=f'hd_ho_{key}')
        data_input[f'hd_close_home_{key}'] = col4.number_input("", min_value=1.0, max_value=5.0, value=1.95, step=0.01, format="%.2f", key=f'hd_hc_{key}')
        
        # Away (Oaspete)
        data_input[f'hd_open_away_{key}'] = col5.number_input("", min_value=1.0, max_value=5.0, value=1.90, step=0.01, format="%.2f", key=f'hd_ao_{key}')
        data_input[f'hd_close_away_{key}'] = col6.number_input("", min_value=1.0, max_value=5.0, value=1.85, step=0.01, format="%.2f", key=f'hd_ac_{key}')
    
    st.markdown("---")
    
    # Butonul de Rulare
    submitted = st.form_submit_button("🔥 Rulează Analiza Hibrid V7.3")

    if submitted:
        # Apelam functia principala de analiza
        markdown_output, result_data = run_hybrid_analyzer(data_input)
        
        # Salvare in Stare
        st.session_state['analysis_output'] = markdown_output
        st.session_state['result_data'] = result_data


# --- Zona de Rezultate ---

if st.session_state['analysis_output']:
    st.markdown("---")
    st.header("✨ Rezultate Analiză")
    
    # Afiseaza rezultatul in format Markdown
    st.markdown(st.session_state['analysis_output'])
    
    # Buton de Salvare
    if FIREBASE_ENABLED and st.session_state['result_data'].get('final_bet_direction') not in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK']:
        st.markdown("---")
        if st.button("💾 Salvează Decizia în Firebase"):
            save_to_firebase(st.session_state['result_data'])
    elif st.session_state['result_data'].get('final_bet_direction') in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK']:
        st.warning("Analiza este un SKIP. Nu se recomandă salvarea sau plasarea unui pariu.")
    elif not FIREBASE_ENABLED:
        st.warning("Conexiunea Firebase este dezactivată. Salvarea nu este disponibilă.")
