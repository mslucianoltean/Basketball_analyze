import streamlit as st
import json

# IMPORTURI
from HybridAnalyzerV73 import (
    run_hybrid_analyzer, 
    save_to_firebase, 
    load_analysis_ids, 
    load_analysis_data, 
    FIREBASE_ENABLED, 
    COLLECTION_NAME_NBA
)

st.set_page_config(layout="wide", page_title="Hybrid Analyzer V7.3")

# --- 1. Initializare Valori Implicite COMPLETE ---
DEFAULT_FORM_DATA = {
    'liga': "NBA", 'echipa_gazda': "Lakers", 'echipa_oaspete': "Celtics",
    'tp_line_open_hist': 220.5,
}

# Adaugam valorile implicite pentru cele 7 linii TP si 7 linii HD (ca float)
for key in ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']:
    DEFAULT_FORM_DATA[f'tp_line_{key}'] = 220.0
    DEFAULT_FORM_DATA[f'tp_open_over_{key}'] = 1.90
    DEFAULT_FORM_DATA[f'tp_close_over_{key}'] = 1.95
    DEFAULT_FORM_DATA[f'tp_open_under_{key}'] = 1.90
    DEFAULT_FORM_DATA[f'tp_close_under_{key}'] = 1.85
    
    DEFAULT_FORM_DATA[f'hd_line_{key}'] = -5.0
    DEFAULT_FORM_DATA[f'hd_open_home_{key}'] = 1.90
    DEFAULT_FORM_DATA[f'hd_close_home_{key}'] = 1.95
    DEFAULT_FORM_DATA[f'hd_open_away_{key}'] = 1.90
    DEFAULT_FORM_DATA[f'hd_close_away_{key}'] = 1.85


# --- 2. Initializare Stare Streamlit ---

if 'analysis_output' not in st.session_state:
    st.session_state['analysis_output'] = ""
if 'result_data' not in st.session_state:
    st.session_state['result_data'] = {}

# Sursa unica de adevar pentru inputuri
if 'form_data' not in st.session_state:
    st.session_state['form_data'] = DEFAULT_FORM_DATA.copy()


# --- 3. Functie Ajutatoare pentru Populare Formular (ROBUSTĂ) ---
def get_value(key):
    """Returnează valoarea din starea sesiunii, forțând conversia la tipul corect și tratând None/NULL."""
    
    default_val = DEFAULT_FORM_DATA.get(key)
    # Folosim .get() pentru a prelua din starea sesiunii, cu default-ul general ca ultim resort
    val = st.session_state['form_data'].get(key, default_val)

    # Gestiunea NULL/NONE sau a valorilor lipsa din Firebase
    if val is None or val == 'None' or val == '':
        return default_val
        
    # Conversia tipurilor (crucială pentru number_input)
    if isinstance(default_val, (float, int)):
        try:
            return float(val)
        except (ValueError, TypeError):
            # Dacă conversia eșuează, revenim la valoarea implicită
            return default_val
            
    # Returnăm valoarea pentru string-uri (text_input)
    return val 


# --- Bara Laterala (Sidebar) ---

with st.sidebar:
    st.header("Vizualizează Analize Salvate 📜")

    if FIREBASE_ENABLED:
        match_ids = load_analysis_ids()
        
        selected_id = st.selectbox(
            "Selectează ID Analiză (Top 100):",
            match_ids,
            index=None,
            key='selectbox_id'
        )

        if st.button("Încarcă Analiză pentru Reanaliză"):
            if selected_id and selected_id != "Firebase Dezactivat" and selected_id != "Eroare la Încărcare":
                data = load_analysis_data(selected_id)
                if data:
                    st.success(f"Analiza `{selected_id}` încărcată. Datele au populat formularul principal.")
                    
                    # 1. INITIALIZEAZA CU VALORILE IMPLICITE COMPLETE
                    new_form_data = DEFAULT_FORM_DATA.copy()
                    
                    # 2. FUZIONEAZA DATELE VECHI PESTE CELE NOI
                    if 'date_input' in data:
                        # Suprascrie valorile implicite doar cu ceea ce s-a gasit in Firebase
                        new_form_data.update(data['date_input'])
                    
                    # 3. ACTUALIZEAZĂ STAREA SESIUNII CU NOUA LISTĂ DE CHEI COMPLETE
                    st.session_state['form_data'] = new_form_data
                    
                    # 4. Actualizeaza starea pentru raport
                    st.session_state['analysis_output'] = data.get('analysis_markdown', "Raportul formatat nu a fost găsit în datele salvate.")
                    st.session_state['result_data'] = data
                    
                    # Afișează datele brute in sidebar
                    st.subheader("Date Analiză Brute (Firebase)")
                    st.json(data)
                    
                    # RE-RULEAZA APLICATIA PENTRU A ACTUALIZA FORMULARUL
                    st.experimental_rerun() 
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
    
    # Detalii Meci
    liga = col_liga.text_input("Liga", value=get_value('liga'), key='liga')
    echipa_gazda = col_gazda.text_input("Echipa Gazdă", value=get_value('echipa_gazda'), key='echipa_gazda')
    echipa_oaspete = col_oaspete.text_input("Echipa Oaspete", value=get_value('echipa_oaspete'), key='echipa_oaspete')

    data_input = {'liga': liga, 'echipa_gazda': echipa_gazda, 'echipa_oaspete': echipa_oaspete}

    st.markdown("---")
    
    # --- Total Puncte ---
    st.subheader("Total Puncte (Over/Under) - 7 Linii")
    
    # Header
    col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns(6)
    col_h1.markdown("**Linia**")
    col_h2.markdown("**Valoare**")
    col_h3.markdown("**Over Open**")
    col_h4.markdown("**Over Close**")
    col_h5.markdown("**Under Open**")
    col_h6.markdown("**Under Close**")
    
    # Campul istoric open (V7.3 specific)
    st.markdown("---")
    st.subheader("Linia Open Istorică")
    col_open_hist, _ = st.columns([1, 5])
    
    key_hist = 'tp_line_open_hist'
    tp_line_open_hist = col_open_hist.number_input("Open Istoric", min_value=150.0, max_value=300.0, 
                                                  value=get_value(key_hist), step=0.5, format="%.1f", key=key_hist)
    data_input[key_hist] = tp_line_open_hist
    st.markdown("---")

    tp_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
    tp_lines_labels = ['Close Line', '-3 pts (M3)', '-2 pts (M2)', '-1 pts (M1)', '+1 pts (P1)', '+2 pts (P2)', '+3 pts (P3)']
    
    # Liniile TP
    for key, label in zip(tp_lines_keys, tp_lines_labels):
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        col1.markdown(f"**{label}**")
        
        data_input[f'tp_line_{key}'] = col2.number_input("", min_value=150.0, max_value=300.0, 
                                                          value=get_value(f'tp_line_{key}'), step=0.5, format="%.1f", key=f'tp_line_{key}')
        data_input[f'tp_open_over_{key}'] = col3.number_input("", min_value=1.0, max_value=5.0, 
                                                               value=get_value(f'tp_open_over_{key}'), step=0.01, format="%.2f", key=f'tp_open_over_{key}')
        data_input[f'tp_close_over_{key}'] = col4.number_input("", min_value=1.0, max_value=5.0, 
                                                                value=get_value(f'tp_close_over_{key}'), step=0.01, format="%.2f", key=f'tp_close_over_{key}')
        data_input[f'tp_open_under_{key}'] = col5.number_input("", min_value=1.0, max_value=5.0, 
                                                                value=get_value(f'tp_open_under_{key}'), step=0.01, format="%.2f", key=f'tp_open_under_{key}')
        data_input[f'tp_close_under_{key}'] = col6.number_input("", min_value=1.0, max_value=5.0, 
                                                                 value=get_value(f'tp_close_under_{key}'), step=0.01, format="%.2f", key=f'tp_close_under_{key}')

    st.markdown("---")

    # --- Handicap ---
    st.subheader("Handicap (Home/Away) - 7 Linii")

    # Header Handicap
    col_hh1, col_hh2, col_hh3, col_hh4, col_hh5, col_hh6 = st.columns(6)
    col_hh1.markdown("**Linia**")
    col_hh2.markdown("**Valoare**")
    col_hh3.markdown("**Home Open**")
    col_hh4.markdown("**Home Close**")
    col_hh5.markdown("**Away Open**")
    col_hh6.markdown("**Away Close**")

    hd_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']

    # Liniile HD
    for key, label in zip(hd_lines_keys, tp_lines_labels):
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        col1.markdown(f"**{label}**")
        # Valoarea liniei (ex: -5.0)
        data_input[f'hd_line_{key}'] = col2.number_input("", min_value=-20.0, max_value=20.0, 
                                                          value=get_value(f'hd_line_{key}'), step=0.5, format="%.1f", key=f'hd_line_{key}')
        
        # Home (Gazda)
        data_input[f'hd_open_home_{key}'] = col3.number_input("", min_value=1.0, max_value=5.0, 
                                                               value=get_value(f'hd_open_home_{key}'), step=0.01, format="%.2f", key=f'hd_open_home_{key}')
        data_input[f'hd_close_home_{key}'] = col4.number_input("", min_value=1.0, max_value=5.0, 
                                                                value=get_value(f'hd_close_home_{key}'), step=0.01, format="%.2f", key=f'hd_close_home_{key}')
        
        # Away (Oaspete)
        data_input[f'hd_open_away_{key}'] = col5.number_input("", min_value=1.0, max_value=5.0, 
                                                                value=get_value(f'hd_open_away_{key}'), step=0.01, format="%.2f", key=f'hd_open_away_{key}')
        data_input[f'hd_close_away_{key}'] = col6.number_input("", min_value=1.0, max_value=5.0, 
                                                                 value=get_value(f'hd_close_away_{key}'), step=0.01, format="%.2f", key=f'hd_close_away_{key}')
    
    st.markdown("---")
    
    # Butonul de Rulare
    submitted = st.form_submit_button("🔥 Rulează Analiza Hibrid V7.3")

    if submitted:
        # La submit, copiem TOATE valorile curente ale formularului in st.session_state['form_data']
        st.session_state['form_data'].update(data_input)
        
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
    final_dir = st.session_state['result_data'].get('final_bet_direction')
    
    if FIREBASE_ENABLED and final_dir not in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK', 'STABLE/SKIP']:
        st.markdown("---")
        if st.button("💾 Salvează Decizia în Firebase"):
            save_to_firebase(st.session_state['result_data'])
    elif final_dir in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK', 'STABLE/SKIP']:
        st.warning(f"Analiza este {final_dir}. Nu se recomandă salvarea sau plasarea unui pariu.")
    elif not FIREBASE_ENABLED:
        st.warning("Conexiunea Firebase este dezactivată. Salvarea nu este disponibilă.")
