import streamlit as st
from HybridAnalyzerV73 import HybridAnalyzerV73, save_to_firebase, get_all_match_ids, get_analysis_by_id, FIREBASE_ENABLED, COLLECTION_NAME_NBA
import numpy as np

st.set_page_config(layout="wide", page_title="Hybrid Analyzer V7.3")

# Inițializarea session state
if 'total_lines' not in st.session_state:
    st.session_state.total_lines = {}
if 'handicap_lines' not in st.session_state:
    st.session_state.handicap_lines = {}
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None


# Funcție utilitară pentru a randa inputul de cote
def render_line_input(market_type, line_key, default_line=None):
    if market_type == 'TOTAL':
        key_prefix = 't'
        title = f"Total Points Line ({line_key})"
        dir_keys = ('over', 'under')
        dir_names = ('Over', 'Under')
    else:
        key_prefix = 'h'
        title = f"Handicap Line ({line_key})"
        dir_keys = ('home', 'away')
        dir_names = ('Home', 'Away')
    
    st.subheader(f"Linia {title}")
    
    col1, col2, col3 = st.columns([1, 1, 1])

    # 1. Valoarea Liniei
    line_value = col1.number_input("Valoarea Liniei", value=default_line or 0.0, step=0.5, format="%.1f", 
                                   key=f'{key_prefix}_{line_key}_line')
    
    # 2. Open Line Value (doar pentru Close Total)
    open_line_value = None
    if market_type == 'TOTAL' and line_key == 'close':
        open_line_value_str = col2.text_input("Linie Open Istorică (V7.3)", 
                                              key=f'{key_prefix}_{line_key}_open_line_value', 
                                              help="Introduceți linia istorică deschisă. Lăsați gol dacă nu este disponibilă.")
        try:
            open_line_value = float(open_line_value_str)
        except ValueError:
            if open_line_value_str:
                st.warning("Linia Open Istorică trebuie să fie un număr.")
            open_line_value = None
    
    # 3. Cote Open/Close
    st.markdown("##### COTE")
    colA, colB, colC, colD = st.columns(4)

    # Direcția 1 (Over/Home)
    d1_open = colA.number_input(f"{dir_names[0]} Open", value=1.90, step=0.01, format="%.2f", 
                                key=f'{key_prefix}_{line_key}_{dir_keys[0]}_open')
    d1_close = colB.number_input(f"{dir_names[0]} Close", value=1.90, step=0.01, format="%.2f", 
                                 key=f'{key_prefix}_{line_key}_{dir_keys[0]}_close')
    
    # Direcția 2 (Under/Away)
    d2_open = colC.number_input(f"{dir_names[1]} Open", value=1.90, step=0.01, format="%.2f", 
                                key=f'{key_prefix}_{line_key}_{dir_keys[1]}_open')
    d2_close = colD.number_input(f"{dir_names[1]} Close", value=1.90, step=0.01, format="%.2f", 
                                 key=f'{key_prefix}_{line_key}_{dir_keys[1]}_close')
    
    # Salvarea datelor
    data = {
        'line': line_value,
        f'{dir_keys[0]}_open': d1_open,
        f'{dir_keys[0]}_close': d1_close,
        f'{dir_keys[1]}_open': d2_open,
        f'{dir_keys[1]}_close': d2_close
    }
    if market_type == 'TOTAL' and line_key == 'close':
        data['open_line_value'] = open_line_value
    
    if market_type == 'TOTAL':
        st.session_state.total_lines[line_key] = data
    else:
        st.session_state.handicap_lines[line_key] = data


# Funcție principală de analiză
def run_analysis(league, home, away, total_lines, handicap_lines):
    try:
        analyzer = HybridAnalyzerV73(league.upper(), home.upper(), away.upper(), total_lines, handicap_lines)
        st.session_state.analyzer = analyzer
        
        # Generarea outputului Markdown și salvarea deciziei în obiectul analyzer
        markdown_output = analyzer.generate_prediction_markdown()
        
        # Afișarea rezultatului
        st.markdown("---")
        st.markdown("## 📊 Rezultate Analiză Hibrid V7.3")
        st.markdown(markdown_output, unsafe_allow_html=True)
        
        # Afișarea butonului de salvare
        if analyzer.decision and not analyzer.decision['Decision_Type'].startswith('SKIP') and FIREBASE_ENABLED:
            if st.button("💾 Salvează Decizia în Firebase", key="save_btn"):
                st.info(save_to_firebase(analyzer.decision))

    except Exception as e:
        st.error(f"❌ A apărut o eroare în timpul analizei: {e}")
        st.exception(e)


# --- INTERFAȚA STREAMLIT ---

# Sidebar pentru vizualizarea analizelor salvate
with st.sidebar:
    st.header("Vizualizează Analize Salvate 📜")
    
    if FIREBASE_ENABLED:
        match_ids = get_all_match_ids()
        if match_ids:
            selected_id = st.selectbox("Selectează ID Analiză", options=[''] + match_ids, key='selected_match_id')
            
            if selected_id:
                if st.button("Încarcă Analiză", key="load_btn"):
                    analysis_data = get_analysis_by_id(selected_id)
                    if analysis_data:
                        # Afișează o versiune simplificată a analizei
                        st.subheader(f"Analiză: {selected_id}")
                        st.json(analysis_data)
                    else:
                        st.warning("Nu s-au putut încărca datele pentru acest ID.")
        else:
            st.info("Nu există analize salvate în Firebase sau colecția este goală.")
    else:
        st.warning(f"Firebase dezactivat. Verificați credențialele. Colecție: {COLLECTION_NAME_NBA}")


# Pagina principală
st.title("🏀 Hybrid Analyzer V7.3 - Instrument de Analiză Baschet")
st.markdown("### Introduceți datele pentru 7 linii de cote (Open/Close) pentru a rula analiza Hibrid V7.3.")

with st.form("input_form"):
    
    st.header("1. Detalii Meci")
    col1, col2, col3 = st.columns(3)
    league = col1.text_input("Liga (ex: NBA)", value="NBA")
    home_team = col2.text_input("Echipa Gazdă (ex: LAL)", value="HOME")
    away_team = col3.text_input("Echipa Oaspete (ex: GSW)", value="AWAY")

    # --- INPUT TOTAL POINTS ---
    st.header("2. Total Puncte - 7 Linii")
    
    # Close Line (cu Open Line Istorică)
    render_line_input('TOTAL', 'close', default_line=220.0)
    st.markdown("---")
    
    # Minus Lines
    st.subheader("Linii În Jos (-3, -2, -1)")
    col_m3, col_m2, col_m1 = st.columns(3)
    with col_m3: render_line_input('TOTAL', 'm3', default_line=217.0)
    with col_m2: render_line_input('TOTAL', 'm2', default_line=218.0)
    with col_m1: render_line_input('TOTAL', 'm1', default_line=219.0)
    st.markdown("---")
    
    # Plus Lines
    st.subheader("Linii În Sus (+1, +2, +3)")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1: render_line_input('TOTAL', 'p1', default_line=221.0)
    with col_p2: render_line_input('TOTAL', 'p2', default_line=222.0)
    with col_p3: render_line_input('TOTAL', 'p3', default_line=223.0)
    
    # --- INPUT HANDICAP ---
    st.header("3. Handicap - 7 Linii")
    
    # Close Line
    render_line_input('HANDICAP', 'close', default_line=-5.0)
    st.markdown("---")
    
    # Minus Lines (mai spre 0)
    st.subheader("Linii În Jos (ex: -8, -7, -6)")
    col_hm3, col_hm2, col_hm1 = st.columns(3)
    with col_hm3: render_line_input('HANDICAP', 'm3', default_line=-8.0)
    with col_hm2: render_line_input('HANDICAP', 'm2', default_line=-7.0)
    with col_hm1: render_line_input('HANDICAP', 'm1', default_line=-6.0)
    st.markdown("---")
    
    # Plus Lines (mai departe de 0)
    st.subheader("Linii În Sus (ex: -4, -3, -2)")
    col_hp1, col_hp2, col_hp3 = st.columns(3)
    with col_hp1: render_line_input('HANDICAP', 'p1', default_line=-4.0)
    with col_hp2: render_line_input('HANDICAP', 'p2', default_line=-3.0)
    with col_hp3: render_line_input('HANDICAP', 'p3', default_line=-2.0)
    
    
    # Buton de Analiză
    submitted = st.form_submit_button("🔥 Rulează Analiza Hibrid V7.3")

if submitted:
    run_analysis(league, home_team, away_team, st.session_state.total_lines, st.session_state.handicap_lines)

# Afișează analiza curentă dacă există
if st.session_state.analyzer:
    st.markdown("---")
    st.markdown("### Analiza Curentă (Vizualizare Detaliată)")
    # Re-rulăm doar pentru afișare (datele sunt în session_state.analyzer.decision)
    st.markdown(st.session_state.analyzer.generate_prediction_markdown(), unsafe_allow_html=True)
