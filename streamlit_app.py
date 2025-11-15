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

# --- 1. Initializare Valori Implicite COMPLETE (Toate ca STRING-uri) ---
DEFAULT_FORM_DATA = {
    'liga': "NBA", 'echipa_gazda': "Lakers", 'echipa_oaspete': "Celtics",
    'tp_line_open_hist': "220.5", 
}

# Adaugam valorile implicite pentru cele 7 linii TP si 7 linii HD (ca STRING)
for key in ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']:
    DEFAULT_FORM_DATA[f'tp_line_{key}'] = "220.0"
    DEFAULT_FORM_DATA[f'tp_open_over_{key}'] = "1.90"
    DEFAULT_FORM_DATA[f'tp_close_over_{key}'] = "1.95"
    DEFAULT_FORM_DATA[f'tp_open_under_{key}'] = "1.90"
    DEFAULT_FORM_DATA[f'tp_close_under_{key}'] = "1.85"
    
    DEFAULT_FORM_DATA[f'hd_line_{key}'] = "-5.0"
    DEFAULT_FORM_DATA[f'hd_open_home_{key}'] = "1.90"
    DEFAULT_FORM_DATA[f'hd_close_home_{key}'] = "1.95"
    DEFAULT_FORM_DATA[f'hd_open_away_{key}'] = "1.90"
    DEFAULT_FORM_DATA[f'hd_close_away_{key}'] = "1.85"


# --- 2. Initializare Stare Streamlit ---

if 'analysis_output' not in st.session_state:
    st.session_state['analysis_output'] = ""
if 'result_data' not in st.session_state:
    st.session_state['result_data'] = {}

# Sursa unica de adevar pentru inputuri
if 'form_data' not in st.session_state:
    st.session_state['form_data'] = DEFAULT_FORM_DATA.copy()
    
# --- 3. Functie Ajutatoare pentru Populare Formular ---
def get_value(key):
    """
    Returneaza valoarea din starea sesiunii ca STRING (sau valoarea implicita).
    """
    val = st.session_state['form_data'].get(key)
    if val is None or str(val).lower() == 'none':
        return DEFAULT_FORM_DATA.get(key, "")
    return str(val)


# --- 4. Functie pentru Conversia la Rulare (String -> Float) ---
def convert_and_run(data_input_str):
    """Convertește inputurile string în float și rulează analiza."""
    data_input_float = {}
    
    for k, v in data_input_str.items():
        if k in ['liga', 'echipa_gazda', 'echipa_oaspete']:
            data_input_float[k] = v
        else:
            try:
                # Folosim .strip() pentru a elimina spațiile și convertim
                data_input_float[k] = float(v.strip()) 
            except ValueError:
                st.error(f"❌ Eroare de formatare: Valoarea '{v}' pentru '{k}' nu este un număr valid. Va rugam corectati.")
                return None, None
                
    return run_hybrid_analyzer(data_input_float)


# --- Bara Laterala (Sidebar) ---

with st.sidebar:
    st.header("Vizualizeaza Analize Salvate 📜")

    if FIREBASE_ENABLED:
        match_ids = load_analysis_ids()
        
        selected_id = st.selectbox(
            "Selecteaza ID Analiza (Top 100):",
            match_ids,
            index=None,
            key='selectbox_id'
        )

        if st.button("Incarca Analiza pentru Reanaliza"):
            if selected_id and selected_id not in ["Firebase Dezactivat", "Eroare la Incarcare"]:
                data = load_analysis_data(selected_id)
                if data:
                    st.success(f"Analiza `{selected_id}` incarcata. Datele populeaza formularul principal...")
                    
                    new_form_data = DEFAULT_FORM_DATA.copy()
                    
                    if 'date_input' in data:
                        # 1. ACTUALIZARE FORM_DATA cu valori STRING
                        for k in DEFAULT_FORM_DATA.keys():
                            # Ne asiguram ca nu avem erori chiar daca datele sunt vechi (cheia lipseste)
                            v = data['date_input'].get(k)
                            if v is not None:
                                new_form_data[k] = str(v)
                    
                    # 2. ACTUALIZARE STARE (Sursa de adevar)
                    st.session_state['form_data'] = new_form_data
                    
                    # 3. ACTUALIZARE RAPORT
                    # Mesaj clar dacă raportul lipsește (meci salvat înainte de actualizare)
                    markdown_output = data.get('analysis_markdown', "⚠️ Raport Detaliat Lipsă: Acest document a fost salvat înainte de ultima actualizare. Repopularea a fost efectuată. Rulați analiza pentru a genera raportul nou.")
                    st.session_state['analysis_output'] = markdown_output
                    st.session_state['result_data'] = data
                    
                    st.subheader("Date Analiza Brute (Firebase)")
                    st.json(data)
                    
                    # Fortam re-renderizarea pentru a vedea datele in inputuri
                    st.rerun() 
                    
                else:
                    st.error(f"Nu s-au putut incarca datele pentru ID-ul {selected_id}.")
            else:
                st.warning("Va rugam sa selectati un ID valid.")
    else:
        st.info("Functionalitatea Firebase este dezactivata (Lipsesc st.secrets).")


# --- Pagina Principala ---

st.title("🏀 Hybrid Analyzer V7.3 - Analiza Baschet")
st.markdown("Introduceti cotele de deschidere (Open) si inchidere (Close) pentru 7 linii adiacente.")


# --- Formular (cu text_input pentru stabilitate) ---

st.subheader("Detalii Meci")
col_liga, col_gazda, col_oaspete = st.columns(3)

# Folosim chei statice, get_value aduce STRING-ul din st.session_state['form_data']
liga = col_liga.text_input("Liga", value=get_value('liga'), key='liga')
echipa_gazda = col_gazda.text_input("Echipa Gazda", value=get_value('echipa_gazda'), key='echipa_gazda')
echipa_oaspete = col_oaspete.text_input("Echipa Oaspete", value=get_value('echipa_oaspete'), key='echipa_oaspete')

data_input_str = {'liga': liga, 'echipa_gazda': echipa_gazda, 'echipa_oaspete': echipa_oaspete}

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

# Campul istoric open
st.markdown("---")
st.subheader("Linia Open Istorica")
col_open_hist, _ = st.columns([1, 5])

key_hist = 'tp_line_open_hist'
tp_line_open_hist = col_open_hist.text_input("Open Istoric", value=get_value(key_hist), key=key_hist) 
data_input_str[key_hist] = tp_line_open_hist
st.markdown("---")

tp_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
tp_lines_labels = ['Close Line', '-3 pts (M3)', '-2 pts (M2)', '-1 pts (M1)', '+1 pts (P1)', '+2 pts (P2)', '+3 pts (P3)']

# Liniile TP
for key, label in zip(tp_lines_keys, tp_lines_labels):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    col1.markdown(f"**{label}**")
    
    data_input_str[f'tp_line_{key}'] = col2.text_input("", value=get_value(f'tp_line_{key}'), key=f'tp_line_{key}') 
    data_input_str[f'tp_open_over_{key}'] = col3.text_input("", value=get_value(f'tp_open_over_{key}'), key=f'tp_open_over_{key}')
    data_input_str[f'tp_close_over_{key}'] = col4.text_input("", value=get_value(f'tp_close_over_{key}'), key=f'tp_close_over_{key}')
    data_input_str[f'tp_open_under_{key}'] = col5.text_input("", value=get_value(f'tp_open_under_{key}'), key=f'tp_open_under_{key}')
    data_input_str[f'tp_close_under_{key}'] = col6.text_input("", value=get_value(f'tp_close_under_{key}'), key=f'tp_close_under_{key}')

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
    data_input_str[f'hd_line_{key}'] = col2.text_input("", value=get_value(f'hd_line_{key}'), key=f'hd_line_{key}')
    
    data_input_str[f'hd_open_home_{key}'] = col3.text_input("", value=get_value(f'hd_open_home_{key}'), key=f'hd_open_home_{key}')
    data_input_str[f'hd_close_home_{key}'] = col4.text_input("", value=get_value(f'hd_close_home_{key}'), key=f'hd_close_home_{key}')
    
    data_input_str[f'hd_open_away_{key}'] = col5.text_input("", value=get_value(f'hd_open_away_{key}'), key=f'hd_open_away_{key}')
    data_input_str[f'hd_close_away_{key}'] = col6.text_input("", value=get_value(f'hd_close_away_{key}'), key=f'hd_close_away_{key}')

st.markdown("---")

# Butonul de Rulare
if st.button("🔥 Ruleaza Analiza Hibrid V7.3"):
    # 1. Salvarea datelor curente in st.session_state (sursa de adevar)
    st.session_state['form_data'].update(data_input_str)
    
    # 2. Convertim si Rulam
    markdown_output, result_data = convert_and_run(data_input_str)
    
    # 3. Salvare in Stare doar daca rularea a avut succes
    if markdown_output:
        st.session_state['analysis_output'] = markdown_output
        st.session_state['result_data'] = result_data


# --- Zona de Rezultate ---

if st.session_state['analysis_output']:
    st.markdown("---")
    st.header("✨ Rezultate Analiza")
    
    st.markdown(st.session_state['analysis_output'])
    
    final_dir = st.session_state['result_data'].get('final_bet_direction')
    
    if FIREBASE_ENABLED and final_dir not in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK', 'STABLE/SKIP']:
        st.markdown("---")
        if st.button("💾 Salveaza Decizia in Firebase"):
            save_to_firebase(st.session_state['result_data'])
    elif final_dir in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK', 'STABLE/SKIP']:
        st.warning(f"Analiza este {final_dir}. Nu se recomanda salvarea sau plasarea unui pariu.")
    elif not FIREBASE_ENABLED:
        st.warning("Conexiunea Firebase este dezactivata. Salvarea nu este disponibila.")
