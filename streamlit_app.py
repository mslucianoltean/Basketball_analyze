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

# --- LINIA DE DEBUGGING PENTRU PORNIRE ---
if not st.session_state.get('app_started', False):
    st.info("Aplicatia a pornit. Verificam starea Firebase...")
    st.session_state['app_started'] = True
# ------------------------------------------

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
    
# NOU: Cheia de Rerulare (Reset Key)
if 'rerun_key_suffix' not in st.session_state:
    st.session_state['rerun_key_suffix'] = 0

# --- 3. Functie Ajutatoare pentru Populare Formular ---
def get_value(key):
    """
    Returneaza valoarea din starea sesiunii, garantand tipul de date corect.
    Foloseste exclusiv st.session_state['form_data'] ca sursă de adevăr.
    """
    
    default_val = DEFAULT_FORM_DATA.get(key)
    val = st.session_state['form_data'].get(key) 
    
    if val is None or val == '' or str(val).lower() == 'none':
        return default_val
    
    # Pentru tipuri numerice (float/int), forțăm float nativ Python
    if isinstance(default_val, (float, int)):
        try:
            return float(val) 
        except (ValueError, TypeError):
            return default_val
            
    # Pentru string-uri, returnăm valoarea direct din form_data
    if isinstance(default_val, str):
        return str(val)
        
    return val if val is not None else default_val


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
            if selected_id and selected_id != "Firebase Dezactivat" and selected_id != "Eroare la Incarcare":
                data = load_analysis_data(selected_id)
                if data:
                    st.success(f"Analiza `{selected_id}` incarcata. Datele au populat formularul principal.")
                    
                    new_form_data = DEFAULT_FORM_DATA.copy()
                    
                    if 'date_input' in data:
                        new_form_data.update(data['date_input'])
                    
                    # 1. ACTUALIZARE FORM_DATA (Sursa de adevar)
                    st.session_state['form_data'] = new_form_data
                    
                    # 2. INCREMENTAM CHEIA PENTRU A FORȚA RE-RENDERIZAREA
                    st.session_state['rerun_key_suffix'] += 1
                    
                    st.session_state['analysis_output'] = data.get('analysis_markdown', "Raportul formatat nu a fost gasit in datele salvate.")
                    st.session_state['result_data'] = data
                    
                    st.subheader("Date Analiza Brute (Firebase)")
                    st.json(data)
                    
                    # BLOC DE CURATARE TIPURI DE DATE CRITICAL
                    st.markdown("---")
                    st.subheader("🔎 Curățare Tipuri de Date (FINAL CHECK)")
                    all_good = True
                    
                    for k, v in st.session_state['form_data'].items():
                        if k not in ['liga', 'echipa_gazda', 'echipa_oaspete']:
                            try:
                                # Fortam conversia la float nativ Python
                                st.session_state['form_data'][k] = float(v)
                            except Exception as e:
                                st.error(f"❌ Eșec Conversie: Cheia `{k}` (Tip: `{type(v)}`) nu poate fi convertită la float. Eroare: {e}")
                                all_good = False
                                break
                    
                    if all_good:
                        st.info("Toate tipurile de date numerice au fost curățate. Rulam din nou...")
                        st.rerun() 
                    else:
                        st.warning("⚠️ Erorile de conversie de tip de date blochează rularea.")
                    
                else:
                    st.error("Nu s-au putut incarca datele pentru ID-ul selectat.")
            else:
                st.warning("Va rugam sa selectati un ID valid.")
    else:
        st.info("Functionalitatea Firebase este dezactivata (Lipsesc st.secrets).")

# --- Pagina Principala ---

st.title("🏀 Hybrid Analyzer V7.3 - Analiza Baschet")
st.markdown("Introduceti cotele de deschidere (Open) si inchidere (Close) pentru 7 linii adiacente.")

current_key_suffix = str(st.session_state['rerun_key_suffix'])

# --- Formular (ELIMINAT st.form) ---

st.subheader("Detalii Meci")
col_liga, col_gazda, col_oaspete = st.columns(3)

# Detalii Meci - Folosim get_value care citeste din form_data
liga = col_liga.text_input("Liga", 
                           value=get_value('liga'), 
                           key='liga')
echipa_gazda = col_gazda.text_input("Echipa Gazda", 
                                    value=get_value('echipa_gazda'), 
                                    key='echipa_gazda')
echipa_oaspete = col_oaspete.text_input("Echipa Oaspete", 
                                       value=get_value('echipa_oaspete'), 
                                       key='echipa_oaspete')

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
st.subheader("Linia Open Istorica")
col_open_hist, _ = st.columns([1, 5])

key_hist = 'tp_line_open_hist'
tp_line_open_hist = col_open_hist.number_input("Open Istoric", min_value=150.0, max_value=300.0, 
                                              value=get_value(key_hist), step=0.5, format="%.1f", 
                                              key=key_hist + current_key_suffix) 
data_input[key_hist] = tp_line_open_hist
st.markdown("---")

tp_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
tp_lines_labels = ['Close Line', '-3 pts (M3)', '-2 pts (M2)', '-1 pts (M1)', '+1 pts (P1)', '+2 pts (P2)', '+3 pts (P3)']

# Liniile TP
for key, label in zip(tp_lines_keys, tp_lines_labels):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    col1.markdown(f"**{label}**")
    
    data_input[f'tp_line_{key}'] = col2.number_input("", min_value=150.0, max_value=300.0, 
                                                      value=get_value(f'tp_line_{key}'), step=0.5, format="%.1f", 
                                                      key=f'tp_line_{key}' + current_key_suffix) 
    data_input[f'tp_open_over_{key}'] = col3.number_input("", min_value=1.0, max_value=5.0, 
                                                           value=get_value(f'tp_open_over_{key}'), step=0.01, format="%.2f", 
                                                           key=f'tp_open_over_{key}' + current_key_suffix)
    data_input[f'tp_close_over_{key}'] = col4.number_input("", min_value=1.0, max_value=5.0, 
                                                            value=get_value(f'tp_close_over_{key}'), step=0.01, format="%.2f", 
                                                            key=f'tp_close_over_{key}' + current_key_suffix)
    data_input[f'tp_open_under_{key}'] = col5.number_input("", min_value=1.0, max_value=5.0, 
                                                            value=get_value(f'tp_open_under_{key}'), step=0.01, format="%.2f", 
                                                            key=f'tp_open_under_{key}' + current_key_suffix)
    data_input[f'tp_close_under_{key}'] = col6.number_input("", min_value=1.0, max_value=5.0, 
                                                             value=get_value(f'tp_close_under_{key}'), step=0.01, format="%.2f", 
                                                             key=f'tp_close_under_{key}' + current_key_suffix)

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
    data_input[f'hd_line_{key}'] = col2.number_input("", min_value=-20.0, max_value=20.0, 
                                                      value=get_value(f'hd_line_{key}'), step=0.5, format="%.1f", 
                                                      key=f'hd_line_{key}' + current_key_suffix)
    
    data_input[f'hd_open_home_{key}'] = col3.number_input("", min_value=1.0, max_value=5.0, 
                                                           value=get_value(f'hd_open_home_{key}'), step=0.01, format="%.2f", 
                                                           key=f'hd_open_home_{key}' + current_key_suffix)
    data_input[f'hd_close_home_{key}'] = col4.number_input("", min_value=1.0, max_value=5.0, 
                                                            value=get_value(f'hd_close_home_{key}'), step=0.01, format="%.2f", 
                                                            key=f'hd_close_home_{key}' + current_key_suffix)
    
    data_input[f'hd_open_away_{key}'] = col5.number_input("", min_value=1.0, max_value=5.0, 
                                                            value=get_value(f'hd_open_away_{key}'), step=0.01, format="%.2f", 
                                                            key=f'hd_open_away_{key}' + current_key_suffix)
    data_input[f'hd_close_away_{key}'] = col6.number_input("", min_value=1.0, max_value=5.0, 
                                                             value=get_value(f'hd_close_away_{key}'), step=0.01, format="%.2f", 
                                                             key=f'hd_close_away_{key}' + current_key_suffix)

st.markdown("---")

# Butonul de Rulare
if st.button("🔥 Ruleaza Analiza Hibrid V7.3"):
    # 1. Salvarea datelor curente in st.session_state (sursa de adevar)
    st.session_state['form_data'].update(data_input)
    
    # 2. Apelam functia principala de analiza
    markdown_output, result_data = run_hybrid_analyzer(data_input)
    
    # 3. Salvare in Stare
    st.session_state['analysis_output'] = markdown_output
    st.session_state['result_data'] = result_data

# --- Zona de Rezultate ---

if st.session_state['analysis_output']:
    st.markdown("---")
    st.header("✨ Rezultate Analiza")
    
    # Afiseaza rezultatul in format Markdown
    st.markdown(st.session_state['analysis_output'])
    
    # Buton de Salvare
    final_dir = st.session_state['result_data'].get('final_bet_direction')
    
    if FIREBASE_ENABLED and final_dir not in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK', 'STABLE/SKIP']:
        st.markdown("---")
        if st.button("💾 Salveaza Decizia in Firebase"):
            save_to_firebase(st.session_state['result_data'])
    elif final_dir in ['SKIP', 'EVAL/SKIP', 'SKIP_DOUBLE_RISK', 'STABLE/SKIP']:
        st.warning(f"Analiza este {final_dir}. Nu se recomanda salvarea sau plasarea unui pariu.")
    elif not FIREBASE_ENABLED:
        st.warning("Conexiunea Firebase este dezactivata. Salvarea nu este disponibila.")
