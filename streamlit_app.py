import streamlit as st
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from HybridAnalyzerV73 import HybridAnalyzerV73

# Configurare pagină
st.set_page_config(
    page_title="Analizor Baschet V7.3 - Raport Profesional",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inițializare Firebase corectată pentru firestore_creds
def init_firebase():
    try:
        if not firebase_admin._apps:
            # Folosește structura ta cu firestore_creds
            firestore_creds = st.secrets["firestore_creds"]
            
            cred_dict = {
                "type": firestore_creds["type"],
                "project_id": firestore_creds["project_id"],
                "private_key_id": firestore_creds["private_key_id"],
                "private_key": firestore_creds["private_key"].replace('\\n', '\n'),
                "client_email": firestore_creds["client_email"],
                "client_id": firestore_creds["client_id"],
                "auth_uri": firestore_creds["auth_uri"],
                "token_uri": firestore_creds["token_uri"],
                "auth_provider_x509_cert_url": firestore_creds["auth_provider_x509_cert_url"],
                "client_x509_cert_url": firestore_creds["client_x509_cert_url"]
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

def display_professional_report(result):
    """Afișează raportul profesional complet cu TOATE analizele."""
    
    st.markdown("---")
    st.header("📊 RAPORT PROFESIONAL COMPLET V7.3")
    st.markdown("---")
    
    if result['decision'] == 'SKIP':
        st.error("❌ DECIZIE: SKIP MECI")
        st.info(f"**Motiv:** {result['reason']}")
        st.info(f"**Scor Maxim V3:** {result['confidence']:.1f}/100")
        return
    
    # SECȚIUNEA 1: DECIZIA FINALĂ
    st.success("🎯 SECȚIUNEA 1: DECIZIE FINALĂ")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("MARKET", result['market'])
    with col2:
        st.metric("DIRECȚIE", result['direction_final'])
    with col3:
        st.metric("LINIE JUCATĂ", f"{result['line_buffered']:.1f}")
    with col4:
        st.metric("COTA", f"{result['cota']:.2f}")
    
    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("ÎNCREDERE V3", f"{result['confidence']:.1f}%")
    with col6:
        st.metric("ACȚIUNE KLD", result['v7_action'])
    with col7:
        st.metric("SURSA LINIE", result['source'])
    
    st.info(f"**🔍 Raționament Final:** {result['reason']}")
    
    # SECȚIUNEA 2: ANALIZĂ CONSENSUS
    st.markdown("---")
    st.header("📈 SECȚIUNEA 2: ANALIZĂ CONSENSUS")
    
    consensus = result['details']['consensus_score']
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("TOTAL PUNCTE")
        over_score = consensus['TOTAL']['OVER']
        under_score = consensus['TOTAL']['UNDER']
        
        st.progress(over_score/100, text=f"OVER: {over_score:.1f}%")
        st.progress(under_score/100, text=f"UNDER: {under_score:.1f}%")
        
        if over_score > under_score:
            st.success(f"✅ CONSENSUS DOMINANT: OVER (+{over_score - under_score:.1f}%)")
        else:
            st.success(f"✅ CONSENSUS DOMINANT: UNDER (+{under_score - over_score:.1f}%)")
    
    with col2:
        st.subheader("HANDICAP")
        home_score = consensus['HANDICAP']['HOME']
        away_score = consensus['HANDICAP']['AWAY']
        
        st.progress(home_score/100, text=f"HOME: {home_score:.1f}%")
        st.progress(away_score/100, text=f"AWAY: {away_score:.1f}%")
        
        if home_score > away_score:
            st.success(f"✅ CONSENSUS DOMINANT: HOME (+{home_score - away_score:.1f}%)")
        else:
            st.success(f"✅ CONSENSUS DOMINANT: AWAY (+{away_score - home_score:.1f}%)")
    
    # SECȚIUNEA 3: DETECȚIE STEAM & MONEY FLOW
    st.markdown("---")
    st.header("🔥 SECȚIUNEA 3: ANALIZĂ STEAM MONEY")
    
    steam = result['details']['steam_detection']
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("TOTAL STEAM")
        if steam['TOTAL']:
            steam_data = steam['TOTAL']
            st.success(f"✅ STEAM DETECTAT: {steam_data['direction']}")
            st.metric("Linii afectate", steam_data['strength'])
            st.metric("Move mediu", f"{steam_data['avg_move']:.3f}")
            st.info(f"**Linii cu steam:** {[m['line'] for m in steam_data['lines_affected']]}")
        else:
            st.warning("⚠️ NU s-a detectat Steam pe TOTAL")
    
    with col2:
        st.subheader("HANDICAP STEAM")
        if steam['HANDICAP']:
            steam_data = steam['HANDICAP']
            st.success(f"✅ STEAM DETECTAT: {steam_data['direction']}")
            st.metric("Linii afectate", steam_data['strength'])
            st.metric("Move mediu", f"{steam_data['avg_move']:.3f}")
            st.info(f"**Linii cu steam:** {[m['line'] for m in steam_data['lines_affected']]}")
        else:
            st.warning("⚠️ NU s-a detectat Steam pe HANDICAP")
    
    # SECȚIUNEA 4: ANALIZĂ GRADIENT ȘI MANIPULARE
    st.markdown("---")
    st.header("📊 SECȚIUNEA 4: ANALIZĂ GRADIENT ȘI MANIPULARE")
    
    gradient = result['details']['gradient_analysis']
    manipulation_flags = result['details']['manipulation_flags']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("UNIFORMITATE GRADIENT")
        total_uniformity = gradient['TOTAL']['uniformity']
        handicap_uniformity = gradient['HANDICAP']['uniformity']
        
        st.metric("TOTAL", f"{total_uniformity:.1f}%", 
                 delta="BUN" if total_uniformity > 70 else "RIȘCANT" if total_uniformity < 50 else "NORMAL")
        st.metric("HANDICAP", f"{handicap_uniformity:.1f}%", 
                 delta="BUN" if handicap_uniformity > 70 else "RIȘCANT" if handicap_uniformity < 50 else "NORMAL")
        
        if gradient['TOTAL']['anomalies']:
            st.warning(f"⚠️ Anomalii TOTAL: {len(gradient['TOTAL']['anomalies'])}")
        if gradient['HANDICAP']['anomalies']:
            st.warning(f"⚠️ Anomalii HANDICAP: {len(gradient['HANDICAP']['anomalies'])}")
    
    with col2:
        st.subheader("DETECȚIE MANIPULARE")
        if manipulation_flags:
            st.error(f"🚨 {len(manipulation_flags)} TRAP-URI DETECTATE")
            for flag in manipulation_flags[:3]:  # Arată primele 3
                st.write(f"• {flag['type']} - Linie {flag['line']} - Severitate: {flag['severity']}")
            if len(manipulation_flags) > 3:
                st.info(f"... și încă {len(manipulation_flags) - 3} trap-uri")
        else:
            st.success("✅ NICIO MANIPULARE DETECTATĂ")
    
    # SECȚIUNEA 5: ANALIZĂ KLD BIDIMENSIONALĂ
    st.markdown("---")
    st.header("🌡️ SECȚIUNEA 5: ANALIZĂ KLD (VOLATILITATE)")
    
    kld_scores = result['details']['kld_scores']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("TOTAL KLD")
        if 'TOTAL' in kld_scores:
            kld_data = kld_scores['TOTAL']
            over_kld = abs(kld_data.get('OVER', 0))
            under_kld = abs(kld_data.get('UNDER', 0))
            
            st.metric("OVER KLD", f"{over_kld:.4f}", 
                     delta="SIGUR" if over_kld <= 0.03 else "RIȘCANT" if over_kld >= 0.06 else "NORMAL")
            st.metric("UNDER KLD", f"{under_kld:.4f}", 
                     delta="SIGUR" if under_kld <= 0.03 else "RIȘCANT" if under_kld >= 0.06 else "NORMAL")
            
            st.info(f"**Direcție dominantă KLD:** {kld_data.get('dominant_direction', 'N/A')}")
    
    with col2:
        st.subheader("HANDICAP KLD")
        if 'HANDICAP' in kld_scores:
            kld_data = kld_scores['HANDICAP']
            home_kld = abs(kld_data.get('HOME', 0))
            away_kld = abs(kld_data.get('AWAY', 0))
            
            st.metric("HOME KLD", f"{home_kld:.4f}", 
                     delta="SIGUR" if home_kld <= 0.03 else "RIȘCANT" if home_kld >= 0.06 else "NORMAL")
            st.metric("AWAY KLD", f"{away_kld:.4f}", 
                     delta="SIGUR" if away_kld <= 0.03 else "RIȘCANT" if away_kld >= 0.06 else "NORMAL")
            
            st.info(f"**Direcție dominantă KLD:** {kld_data.get('dominant_direction', 'N/A')}")
    
    # SECȚIUNEA 6: ANALIZĂ ISTORICĂ ȘI CONFLICT
    st.markdown("---")
    st.header("📜 SECȚIUNEA 6: ANALIZĂ MIȘCARE ISTORICĂ")
    
    historic = result['details']['historic_analysis']
    
    for market in ['TOTAL', 'HANDICAP']:
        if market in historic:
            data = historic[market]
            if data['open_line'] is not None:
                st.subheader(f"{market} ISTORIC")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Open Line", f"{data['open_line']:.1f}")
                with col2:
                    st.metric("Close Line", f"{data['close_line']:.1f}")
                with col3:
                    movement = data['movement']
                    st.metric("Mișcare", f"{movement:+.1f}", 
                             delta="URCĂ" if movement > 0 else "COBOARĂ" if movement < 0 else "STABIL")
                
                if data['is_significant']:
                    if data['dominant_direction']:
                        if data['dominant_direction'] == result['direction_final']:
                            st.success(f"✅ ALINIERE: Mișcarea istorică confirmă direcția {result['direction_final']}")
                        else:
                            st.error(f"🚨 CONFLICT: Mișcarea istorică ({data['dominant_direction']}) contrazice direcția {result['direction_final']}")
    
    # SECȚIUNEA 7: ANALIZĂ ENȚROPIE ȘI CONCENTRARE
    st.markdown("---")
    st.header("🧠 SECȚIUNEA 7: ANALIZĂ ENȚROPIE")
    
    entropy_alerts = result['details']['entropy_alerts']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("TOTAL ENȚROPIE")
        if entropy_alerts['TOTAL']:
            alert = entropy_alerts['TOTAL']
            st.error(f"🚨 ALERTĂ ENȚROPIE: {alert['direction']}")
            st.metric("Scor Entropie", f"{alert['entropy']:.3f}")
            st.warning("⚠️ RISC: Concentrare extremă de probabilități detectată")
        else:
            st.success("✅ ENȚROPIE NORMALĂ")
            st.info("Distribuție sănătoasă a probabilităților")
    
    with col2:
        st.subheader("HANDICAP ENȚROPIE")
        if entropy_alerts['HANDICAP']:
            alert = entropy_alerts['HANDICAP']
            st.error(f"🚨 ALERTĂ ENȚROPIE: {alert['direction']}")
            st.metric("Scor Entropie", f"{alert['entropy']:.3f}")
            st.warning("⚠️ RISC: Concentrare extremă de probabilități detectată")
        else:
            st.success("✅ ENȚROPIE NORMALĂ")
            st.info("Distribuție sănătoasă a probabilităților")
    
    # SECȚIUNEA 8: MATRICEA DE ÎNCREDERE DETALIATĂ
    st.markdown("---")
    st.header("🎯 SECȚIUNEA 8: MATRICEA ÎNCREDERE V3 DETALIATĂ")
    
    confidence_matrix = result['details']['confidence_matrix']
    score_data = result['details']['score_data']
    
    for market_dir, score in confidence_matrix.items():
        if score >= 50:  # Arată doar direcțiile cu încredere >= 50%
            with st.expander(f"🔍 ANALIZĂ DETALIATĂ: {market_dir} (Scor: {score:.1f})", expanded=True):
                if market_dir in score_data:
                    components = score_data[market_dir]['Components']
                    
                    # Scoruri componente
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Consensus", f"{components['Consensus']['points']:.1f}")
                    with col2:
                        st.metric("Gradient", f"{components['Gradient']['points']:.1f}")
                    with col3:
                        st.metric("Steam", f"{components['Steam']['points']:.1f}")
                    with col4:
                        st.metric("Contrarion", f"{components['Contrarion_Bonus']['points']:.1f}")
                    
                    # Penalizări
                    if any([components['Trap_Analysis']['points'] > 0,
                           components['Entropy_Alert']['points'] > 0,
                           components['Historic_Penalty']['points'] > 0,
                           components['Historic_Conflict']['points'] > 0]):
                        
                        st.subheader("⚠️ Penalizări Aplicate")
                        penalty_cols = st.columns(4)
                        
                        with penalty_cols[0]:
                            if components['Trap_Analysis']['points'] > 0:
                                st.error(f"Trap: -{components['Trap_Analysis']['points']:.1f}")
                        
                        with penalty_cols[1]:
                            if components['Entropy_Alert']['points'] > 0:
                                st.error(f"Entropie: -{components['Entropy_Alert']['points']:.1f}")
                        
                        with penalty_cols[2]:
                            if components['Historic_Penalty']['points'] > 0:
                                st.error(f"Istoric: -{components['Historic_Penalty']['points']:.1f}")
                        
                        with penalty_cols[3]:
                            if components['Historic_Conflict']['points'] > 0:
                                st.error(f"Conflict: -{components['Historic_Conflict']['points']:.1f}")
                    
                    # Analiză Trap
                    if components['Trap_Analysis']['classification']:
                        trap_class = components['Trap_Analysis']['classification']
                        st.subheader("🔎 Analiză Trap Lines")
                        
                        if trap_class['type'] == 'CONTRARION':
                            st.success(f"🎯 TRAP CONTRARION DETECTAT (Confidence: {trap_class['confidence']}%)")
                            st.info(f"**Acțiune:** {trap_class['action']}")
                            st.info(f"**Raționament:** {trap_class['reasoning']}")
                        elif trap_class['type'] == 'REAL':
                            st.error(f"🚫 TRAP REAL DETECTAT (Confidence: {trap_class['confidence']}%)")
                            st.info(f"**Acțiune:** {trap_class['action']}")
                            st.info(f"**Raționament:** {trap_class['reasoning']}")
                        else:
                            st.warning(f"⚠️ TRAP AMBIGUU (Confidence: {trap_class['confidence']}%)")
                            st.info(f"**Acțiune:** {trap_class['action']}")
    
    # SECȚIUNEA 9: REZUMAT STRATEGIC
    st.markdown("---")
    st.header("💡 SECȚIUNEA 9: REZUMAT STRATEGIC")
    
    # Analiză confluence
    confluence_score = 0
    confluence_factors = []
    
    # Verifică factori de confluence
    if result['details']['steam_detection'][result['market']] and \
       result['details']['steam_detection'][result['market']]['direction'] == result['direction_final']:
        confluence_score += 1
        confluence_factors.append("✅ Steam confirmă direcția")
    
    if result['confidence'] >= 70:
        confluence_score += 1
        confluence_factors.append("✅ Încredere V3 ridicată (≥70%)")
    
    gradient_uniformity = result['details']['gradient_analysis'][result['market']]['uniformity']
    if gradient_uniformity >= 70:
        confluence_score += 1
        confluence_factors.append("✅ Gradient uniform")
    
    kld_direction = abs(result['details']['kld_scores'][result['market']].get(result['direction_initial'], 0))
    if kld_direction <= 0.03:
        confluence_score += 1
        confluence_factors.append("✅ KLD sigur")
    
    # Afișează scorul confluence
    st.subheader("📊 Scor Confluence Strategic")
    st.progress(confluence_score/4, text=f"Confluence Score: {confluence_score}/4")
    
    for factor in confluence_factors:
        st.write(factor)
    
    # Recomandare finală
    st.markdown("---")
    if confluence_score >= 3:
        st.success("🎯 **RECOMANDARE: PLAY PUTERNIC** - Multiple confirmări strategice")
    elif confluence_score >= 2:
        st.info("📈 **RECOMANDARE: PLAY STANDARD** - Confirmări moderate")
    else:
        st.warning("⚠️ **RECOMANDARE: PLAY CU PRUDENȚĂ** - Confirmări limitate")

# Interfața principală
def main():
    st.title("🏀 Analizor Baschet Hibrid V7.3 - Raport Profesional")
    st.markdown("**Sistem profesionist de analiză cu raport complet și detaliat**")
    
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
    if st.button("🚀 GENEREAZĂ RAPORT PROFESIONAL V7.3", type="primary", use_container_width=True):
        with st.spinner("Generare raport profesional complet..."):
            try:
                analyzer = HybridAnalyzerV73(
                    league.upper(),
                    home_team.upper(),
                    away_team.upper(),
                    total_lines,
                    handicap_lines
                )
                
                result = analyzer.generate_prediction()
                
                # Afișare raport profesional COMPLET
                display_professional_report(result)
                
                # Opțiune salvare
                if result['decision'] != 'SKIP' and db:
                    st.markdown("---")
                    if st.button("💾 Salvează Raportul în Firebase", type="secondary", use_container_width=True):
                        match_id = save_to_firebase(analyzer.decision, db)
                        if match_id:
                            st.success(f"✅ Raport salvat cu ID: {match_id}")
                
            except Exception as e:
                st.error(f"Eroare la generare raport: {e}")

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
        if st.button("🔄 Regenerare Raport Profesional", type="primary"):
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

# Rulare aplicație
if __name__ == "__main__":
    main()
