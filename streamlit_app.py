import streamlit as st
import json

from HybridAnalyzerV73 import (
    run_hybrid_analyzer, 
    save_to_firebase, 
    load_analysis_ids, 
    load_analysis_data, 
    FIREBASE_ENABLED, 
    COLLECTION_NAME_NBA
)

st.set_page_config(layout="wide", page_title="Hybrid Analyzer V7.3")

# --- 1. Initializare Stare Streamlit ---

if 'analysis_output' not in st.session_state: st.session_state['analysis_output'] = ""
if 'result_data' not in st.session_state: st.session_state['result_data'] = {}
if 'form_data' not in st.session_state: st.session_state['form_data'] = {}
# SUFIX CRITIC: Se schimba la fiecare incarcare pentru a forta repopularea widget-urilor
if 'key_suffix' not in st.session_state: st.session_state['key_suffix'] = 0 
    
# --- 2. Functie Ajutatoare pentru Populare Formular (Returneaza string gol) ---
def get_value(key):
    """Citeste valoarea din starea sesiunii. Daca lipseste, returneaza string gol."""
    val = st.session_state['form_data'].get(key)
    if val is None or str(val).lower() == 'none':
        return "" # Returneaza string gol
    return str(val)

# --- 3. Functie pentru Conversia la Rulare (String -> Float) ---
def convert_and_run(data_input_str):
    data_input_float = {}
    
    for k, v in data_input_str.items():
        if k in ['liga', 'echipa_gazda', 'echipa_oaspete']:
            data_input_float[k] = v
        else:
            try:
                val_to_convert = v.strip() if v else "0.0" 
                data_input_float[k] = float(val_to_convert) 
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
        
        if st.button("Incarca Analiza & Repopuleaza Formularul"):
            if selected_id:
                safe_selected_id = selected_id.strip()
            else:
                safe_selected_id = None
            
            if safe_selected_id and safe_selected_id not in ["Firebase Dezactivat", "Eroare la Incarcare"]:
                data = load_analysis_data(safe_selected_id)
                
                if data:
                    st.success(f"Analiza `{safe_selected_id}` incarcata. Repopularea urmeaza imediat...")
                    
                    # Definim TOATE CHEILE PE CARE LE ASTEPTAM
                    all_keys = [
                        'liga', 'echipa_gazda', 'echipa_oaspete', 'tp_line_open_hist'
                    ]
                    for key_sufix in ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']:
                        all_keys.extend([
                            f'tp_line_{key_sufix}', f'tp_open_over_{key_sufix}', f'tp_close_over_{key_sufix}', f'tp_open_under_{key_sufix}', f'tp_close_under_{key_sufix}',
                            f'hd_line_{key_sufix}', f'hd_open_home_{key_sufix}', f'hd_close_home_{key_sufix}', f'hd_open_away_{key_sufix}', f'hd_close_away_{key_sufix}'
                        ])

                    new_form_data = {} 
                    if 'date_input' in data:
                        source_data = data['date_input']
                             
                        for k in all_keys:
                            v = source_data.get(k)
                            if v is not None:
                                new_form_data[k] = str(v)
                    # Adaugam si campurile de baza (liga, gazda, oaspete) care ar putea fi in radacina doc-ului vechi
                    new_form_data['liga'] = data.get('League', data.get('liga', ''))
                    new_form_data['echipa_gazda'] = data.get('HomeTeam', data.get('echipa_gazda', ''))
                    new_form_data['echipa_oaspete'] = data.get('AwayTeam', data.get('echipa_oaspete', ''))


                    # 1. ACTUALIZARE STARE
                    st.session_state['form_data'] = new_form_data
                    st.session_state['result_data'] = data
                    st.session_state['analysis_output'] = data.get('analysis_markdown', "⚠️ Raport Detaliat Lipsă. Rulați analiza pentru a genera raportul nou.")

                    # 2. INCREMENTARE SUFIX CHEIE CRITICĂ
                    st.session_state['key_suffix'] += 1 
                    
                    # 3. AFISARE JSON PENTRU DEBUGGING
                    st.subheader("Date Analiza Brute (Firebase - Debugging)")
                    st.json(data) 

                    # 4. PASUL CRITIC: Oprim scriptul curent si il repornim, folosind sintaxa stabila
                    st.rerun() 
                    
                else:
                    st.error(f"❌ EROARE CRITICA: S-a selectat ID-ul `{safe_selected_id}`, dar documentul nu a putut fi găsit/încărcat (funcția load_analysis_data a returnat None).")
            else:
                st.warning("Va rugam sa selectati un ID valid.")
    else:
        st.info("Functionalitatea Firebase este dezactivata (Lipsesc st.secrets).")


# --- Pagina Principala (Formularul) ---

st.title("🏀 Hybrid Analyzer V7.3 - Analiza Baschet")
st.markdown("Introduceti cotele de deschidere (Open) si inchidere (Close) pentru 7 linii adiacente.")

current_suffix = st.session_state['key_suffix'] # Preluam suficsul curent

st.subheader("Detalii Meci")
col_liga, col_gazda, col_oaspete = st.columns(3)

# Aplicam suficsul la chei
liga = col_liga.text_input("Liga", value=get_value('liga'), key=f"liga_{current_suffix}")
echipa_gazda = col_gazda.text_input("Echipa Gazda", value=get_value('echipa_gazda'), key=f"echipa_gazda_{current_suffix}")
echipa_oaspete = col_oaspete.text_input("Echipa Oaspete", value=get_value('echipa_oaspete'), key=f"echipa_oaspete_{current_suffix}")

data_input_str = {'liga': liga, 'echipa_gazda': echipa_gazda, 'echipa_oaspete': echipa_oaspete}

st.markdown("---")


st.subheader("Total Puncte (Total Points)")
key_hist = 'tp_line_open_hist'
tp_line_open_hist = st.columns([1, 5])[0].text_input("Open Istoric", value=get_value(key_hist), key=f"{key_hist}_{current_suffix}") 
data_input_str[key_hist] = tp_line_open_hist

tp_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
tp_lines_labels = ['Close Line', '-3 pts (M3)', '-2 pts (M2)', '-1 pts (M1)', '+1 pts (P1)', '+2 pts (P2)', '+3 pts (P3)']

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.markdown("**Linie**")
col2.markdown("**Linie**")
col3.markdown("**Open Over**")
col4.markdown("**Close Over**")
col5.markdown("**Open Under**")
col6.markdown("**Close Under**")

for key, label in zip(tp_lines_keys, tp_lines_labels):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.markdown(f"**{label}**")
    
    # Aplicam suficsul la chei TP
    key_tp_line = f'tp_line_{key}'
    data_input_str[key_tp_line] = col2.text_input(key_tp_line, value=get_value(key_tp_line), key=f"{key_tp_line}_{current_suffix}", label_visibility="hidden") 
    
    key_tp_open_over = f'tp_open_over_{key}'
    data_input_str[key_tp_open_over] = col3.text_input(key_tp_open_over, value=get_value(key_tp_open_over), key=f"{key_tp_open_over}_{current_suffix}", label_visibility="hidden")
    
    key_tp_close_over = f'tp_close_over_{key}'
    data_input_str[key_tp_close_over] = col4.text_input(key_tp_close_over, value=get_value(key_tp_close_over), key=f"{key_tp_close_over}_{current_suffix}", label_visibility="hidden")
    
    key_tp_open_under = f'tp_open_under_{key}'
    data_input_str[key_tp_open_under] = col5.text_input(key_tp_open_under, value=get_value(key_tp_open_under), key=f"{key_tp_open_under}_{current_suffix}", label_visibility="hidden")
    
    key_tp_close_under = f'tp_close_under_{key}'
    data_input_str[key_tp_close_under] = col6.text_input(key_tp_close_under, value=get_value(key_tp_close_under), key=f"{key_tp_close_under}_{current_suffix}", label_visibility="hidden")

st.markdown("---")
st.subheader("Handicap")

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.markdown("**Linie**")
col2.markdown("**Linie**")
col3.markdown("**Open Home**")
col4.markdown("**Close Home**")
col5.markdown("**Open Away**")
col6.markdown("**Close Away**")

hd_lines_keys = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']

for key, label in zip(hd_lines_keys, tp_lines_labels):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.markdown(f"**{label}**")
    
    # Aplicam suficsul la chei Handicap
    key_hd_line = f'hd_line_{key}'
    data_input_str[key_hd_line] = col2.text_input(key_hd_line, value=get_value(key_hd_line), key=f"{key_hd_line}_{current_suffix}", label_visibility="hidden")
    
    key_hd_open_home = f'hd_open_home_{key}'
    data_input_str[key_hd_open_home] = col3.text_input(key_hd_open_home, value=get_value(key_hd_open_home), key=f"{key_hd_open_home}_{current_suffix}", label_visibility="hidden")
    
    key_hd_close_home = f'hd_close_home_{key}'
    data_input_str[key_hd_close_home] = col4.text_input(key_hd_close_home, value=get_value(key_hd_close_home), key=f"{key_hd_close_home}_{current_suffix}", label_visibility="hidden")
    
    key_hd_open_away = f'hd_open_away_{key}'
    data_input_str[key_hd_open_away] = col5.text_input(key_hd_open_away, value=get_value(key_hd_open_away), key=f"{key_hd_open_away}_{current_suffix}", label_visibility="hidden")
    
    key_hd_close_away = f'hd_close_away_{key}'
    data_input_str[key_hd_close_away] = col6.text_input(key_hd_close_away, value=get_value(key_hd_close_away), key=f"{key_hd_close_away}_{current_suffix}", label_visibility="hidden")


# Butonul de Rulare
if st.button("🔥 Ruleaza Analiza Hibrid V7.3"):
    st.session_state['form_data'].update(data_input_str)
    markdown_output, result_data = convert_and_run(data_input_str)
    
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
