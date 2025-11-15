import streamlit as st
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from HybridAnalyzerV73 import HybridAnalyzerV73

# Configurare pagină
st.set_page_config(
    page_title="Analizor Baschet V7.3",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inițializare Firebase
def init_firebase():
    try:
        if not firebase_admin._apps:
            cred_dict = {
                "type": st.secrets["firebase"]["type"],
                "project_id": st.secrets["firebase"]["project_id"],
                "private_key_id": st.secrets["firebase"]["private_key_id"],
                "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["firebase"]["client_email"],
                "client_id": st.secrets["firebase"]["client_id"],
                "auth_uri": st.secrets["firebase"]["auth_uri"],
                "token_uri": st.secrets["firebase"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Eroare inițializare Firebase: {e}")
        return None

# Funcții utilitare
def save_to_firebase(decision_data, db):
    """Salvează analiza în Firebase."""
    try:
        match_id = f"{decision_data['League']}_{decision_data['HomeTeam']}_VS_{decision_data['AwayTeam']}_V7_3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        decision_data_clean = json.loads(json.dumps(decision_data, default=str))
        db.collection('baschet').document(match_id).set(decision_data_clean)
        return match_id
    except Exception as e:
        st.error(f"Eroare salvare Firebase: {e}")
        return None

def get_saved_matches(db):
    """Returnează toate meciurile salvate din Firebase."""
    try:
        matches = []
        docs = db.collection('baschet').stream()
        for doc in docs:
            match_data = doc.to_dict()
            matches.append({
                'id': doc.id,
                'league': match_data.get('League', 'N/A'),
                'home_team': match_data.get('HomeTeam', 'N/A'),
                'away_team': match_data.get('AwayTeam', 'N/A'),
                'date': match_data.get('Data_Analiza_Salvare', 'N/A'),
                'data': match_data
            })
        return matches
    except Exception as e:
        st.error(f"Eroare citire Firebase: {e}")
        return []

def create_line_inputs(prefix, line_names):
    """Creează input-uri pentru linii și cote."""
    lines_data = {}
    
    for line_name in line_names:
        with st.expander(f"Linia {line_name.upper()}", expanded=(line_name == 'close')):
            col1, col2 = st.columns(2)
            
            with col1:
                if line_name == 'close':
                    line_value = st.number_input(
                        f"Linie Close",
                        value=220.0,
                        key=f"{prefix}_{line_name}_line"
                    )
                    open_line_value = st.number_input(
                        f"Linie Open Istorică (IMPORTANT V7.3)",
                        value=219.5,
                        key=f"{prefix}_{line_name}_open_line"
                    )
                else:
                    line_value = st.number_input(
                        f"Linie {line_name.upper()}",
                        value=220.0,
                        key=f"{prefix}_{line_name}_line"
                    )
                
            with col2:
                if prefix == 'total':
                    over_open = st.number_input(f"Over Open", value=1.90, key=f"{prefix}_{line_name}_over_open")
                    over_close = st.number_input(f"Over Close", value=1.85, key=f"{prefix}_{line_name}_over_close")
                    under_open = st.number_input(f"Under Open", value=1.90, key=f"{prefix}_{line_name}_under_open")
                    under_close = st.number_input(f"Under Close", value=1.95, key=f"{prefix}_{line_name}_under_close")
                    
                    if line_name == 'close':
                        lines_data[line_name] = {
                            'line': line_value,
                            'open_line_value': open_line_value,
                            'over_open': over_open,
                            'over_close': over_close,
                            'under_open': under_open,
                            'under_close': under_close
                        }
                    else:
                        lines_data[line_name] = {
                            'line': line_value,
                            'over_open': over_open,
                            'over_close': over_close,
                            'under_open': under_open,
                            'under_close': under_close
                        }
                else:  # handicap
                    home_open = st.number_input(f"Home Open", value=1.90, key=f"{prefix}_{line_name}_home_open")
                    home_close = st.number_input(f"Home Close", value=1.85, key=f"{prefix}_{line_name}_home_close")
                    away_open = st.number_input(f"Away Open", value=1.90, key=f"{prefix}_{line_name}_away_open")
                    away_close = st.number_input(f"Away Close", value=1.95, key=f"{prefix}_{line_name}_away_close")
                    
                    lines_data[line_name] = {
                        'line': line_value,
                        'home_open': home_open,
                        'home_close': home_close,
                        'away_open': away_open,
                        'away_close': away_close
                    }
    
    return lines_data

def display_analysis_results(result):
    """Afișează rezultatele analizei."""
    if result['decision'] == 'SKIP':
        st.error(f"❌ SKIP MECI")
        st.info(f"**Motiv:** {result['reason']}")
        st.info(f"**Max Score V3:** {result['confidence']:.1f}/100")
        return
    
    # Afișare decizie PLAY
    st.success(f"🏆 DECIZIE FINALĂ HIBRID V7.3: {result['market']} {result['direction_final']}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Încredere V3", f"{result['confidence']:.1f}/100")
    with col2:
        st.metric("Linie Jucată", f"{result['line_buffered']:.1f}")
    with col3:
        st.metric("Cota Reference", f"{result['cota']:.2f}")
    
    # Detalii extinse
    with st.expander("📊 Detalii Analiză Completă", expanded=True):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Consensus", "Steam", "Gradient", "KLD", "Istoric"])
        
        with tab1:
            st.subheader("Scor Consensus")
            consensus = result['details']['consensus_score']
            col1, col2 = st.columns(2)
            with col1:
                st.write("**TOTAL**")
                st.write(f"OVER: {consensus['TOTAL']['OVER']:.1f}%")
                st.write(f"UNDER: {consensus['TOTAL']['UNDER']:.1f}%")
            with col2:
                st.write("**HANDICAP**")
                st.write(f"HOME: {consensus['HANDICAP']['HOME']:.1f}%")
                st.write(f"AWAY: {consensus['HANDICAP']['AWAY']:.1f}%")
        
        with tab2:
            st.subheader("Detecție Steam")
            steam = result['details']['steam_detection']
            if steam['TOTAL']:
                st.write(f"**TOTAL:** {steam['TOTAL']['direction']} ({steam['TOTAL']['strength']} linii)")
            if steam['HANDICAP']:
                st.write(f"**HANDICAP:** {steam['HANDICAP']['direction']} ({steam['HANDICAP']['strength']} linii)")
        
        with tab3:
            st.subheader("Analiză Gradient")
            gradient = result['details']['gradient_analysis']
            st.write(f"**TOTAL Uniformitate:** {gradient['TOTAL']['uniformity']:.1f}%")
            st.write(f"**HANDICAP Uniformitate:** {gradient['HANDICAP']['uniformity']:.1f}%")
        
        with tab4:
            st.subheader("KLD Bidimensional")
            kld = result['details']['kld_scores']
            for market in ['TOTAL', 'HANDICAP']:
                st.write(f"**{market}:**")
                if market in kld:
                    for direction in ['OVER', 'UNDER'] if market == 'TOTAL' else ['HOME', 'AWAY']:
                        if direction in kld[market]:
                            st.write(f"  {direction}: {abs(kld[market][direction]):.4f}")
        
        with tab5:
            st.subheader("Analiză Istorică")
            historic = result['details']['historic_analysis']
            for market in ['TOTAL', 'HANDICAP']:
                if market in historic:
                    data = historic[market]
                    if data['open_line'] is not None:
                        st.write(f"**{market}:**")
                        st.write(f"Open: {data['open_line']:.1f} → Close: {data['close_line']:.1f}")
                        st.write(f"Mișcare: {data['movement']:+.1f} puncte")
                        if data['is_significant']:
                            st.write(f"Direcție Dominantă: {data['dominant_direction']}")
    
    # Informații suplimentare
    st.info(f"**Acțiune KLD:** {result['v7_action']}")
    st.info(f"**Sursă Linie:** {result['source']}")
    st.info(f"**Raționament:** {result['reason']}")

# Interfața principală
def main():
    st.title("🏀 Analizor Baschet Hibrid V7.3")
    st.markdown("**Sistem profesionist de analiză a liniilor de baschet cu verificare istorică**")
    
    # Inițializare Firebase
    db = init_firebase()
    
    # Sidebar pentru navigare
    st.sidebar.title("Navigare")
    app_mode = st.sidebar.radio("Alege modul:", ["Analiză Nouă", "Meciuri Salvate"])
    
    if app_mode == "Analiză Nouă":
        render_new_analysis(db)
    else:
        render_saved_matches(db)

def render_new_analysis(db):
    """Render pentru analiza nouă."""
    st.header("🔍 Analiză Nouă Meci")
    
    # Informații de bază despre meci
    col1, col2, col3 = st.columns(3)
    with col1:
        league = st.text_input("Liga", value="NBA")
    with col2:
        home_team = st.text_input("Echipa Gazdă", value="LAKERS")
    with col3:
        away_team = st.text_input("Echipa Oaspete", value="WARRIORS")
    
    st.markdown("---")
    
    # Secțiunea TOTAL
    st.subheader("📈 Total Puncte - 7 Linii")
    total_line_names = ['m3', 'm2', 'm1', 'close', 'p1', 'p2', 'p3']
    total_lines = create_line_inputs('total', total_line_names)
    
    st.markdown("---")
    
    # Secțiunea HANDICAP
    st.subheader("⚖️ Handicap - 7 Linii")
    handicap_line_names = ['m3', 'm2', 'm1', 'close', 'p1', 'p2', 'p3']
    handicap_lines = create_line_inputs('handicap', handicap_line_names)
    
    st.markdown("---")
    
    # Butonul de analiză
    if st.button("🚀 Rulează Analiza V7.3", type="primary", use_container_width=True):
        with st.spinner("Analiză în curs... V7.3 cu verificare istorică"):
            try:
                analyzer = HybridAnalyzerV73(
                    league.upper(),
                    home_team.upper(),
                    away_team.upper(),
                    total_lines,
                    handicap_lines
                )
                
                result = analyzer.generate_prediction()
                
                # Afișare rezultate
                display_analysis_results(result)
                
                # Opțiune salvare
                if result['decision'] != 'SKIP' and db:
                    if st.button("💾 Salvează în Firebase", type="secondary"):
                        match_id = save_to_firebase(analyzer.decision, db)
                        if match_id:
                            st.success(f"Analiză salvată cu ID: {match_id}")
                
            except Exception as e:
                st.error(f"Eroare la analiză: {e}")

def render_saved_matches(db):
    """Render pentru meciurile salvate."""
    st.header("📂 Meciuri Salvate")
    
    if not db:
        st.error("Firebase nu este inițializat. Nu se pot încărca meciurile salvate.")
        return
    
    matches = get_saved_matches(db)
    
    if not matches:
        st.info("Nu există meciuri salvate.")
        return
    
    # Selector meci
    match_options = [f"{m['league']} - {m['home_team']} vs {m['away_team']} ({m['date']})" for m in matches]
    selected_match = st.selectbox("Alege meci:", match_options)
    
    if selected_match:
        match_index = match_options.index(selected_match)
        match_data = matches[match_index]['data']
        
        # Afișare informații meci
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Liga", match_data.get('League', 'N/A'))
        with col2:
            st.metric("Gazdă", match_data.get('HomeTeam', 'N/A'))
        with col3:
            st.metric("Oaspete", match_data.get('AwayTeam', 'N/A'))
        
        # Buton reanaliză
        if st.button("🔄 Reanalizează Meciul", type="primary"):
            # Extrage datele pentru repopulare
            st.session_state.reanalyze_data = {
                'league': match_data.get('League', ''),
                'home_team': match_data.get('HomeTeam', ''),
                'away_team': match_data.get('AwayTeam', ''),
                'total_lines': match_data.get('All_Total_Lines', {}),
                'handicap_lines': match_data.get('All_Handicap_Lines', {})
            }
            st.rerun()
        
        # Afișare decizie originală
        st.subheader("Decizie Originală")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"**Market:** {match_data.get('Decision_Market', 'N/A')}")
        with col2:
            st.info(f"**Direcție:** {match_data.get('Decision_Direction_Final', 'N/A')}")
        with col3:
            st.info(f"**Linie:** {match_data.get('Decision_Line_BUFFERED', 'N/A')}")
        with col4:
            st.info(f"**Încredere:** {match_data.get('Decision_Confidence_V3', 'N/A')}")
        
        # Detalii complete
        with st.expander("Vezi Date Complete Meci"):
            st.json(match_data)

# Rulare aplicație
if __name__ == "__main__":
    main()
