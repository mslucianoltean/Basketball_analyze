import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import math

# Try to import Firebase libraries, making the import conditional
FIREBASE_ENABLED = False
db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    # Define a placeholder for the Firebase database client
    # The actual initialization is done in initialize_firebase()
except ImportError:
    # If the firebase-admin library is not available, Firebase features will be disabled
    pass

# --- Firebase Initialization (Security Update) ---

def initialize_firebase():
    """Initializes Firebase connection using st.secrets exclusively."""
    global FIREBASE_ENABLED, db
    
    if FIREBASE_ENABLED:
        return True # Already initialized

    try:
        if "firestore_creds" in st.secrets:
            # Use st.secrets (recommended for secure Streamlit Cloud deployment)
            # st.secrets['firestore_creds'] is a dictionary with all the JSON keys
            cred = credentials.Certificate(dict(st.secrets["firestore_creds"]))
        else:
            # If secrets are not found, Firebase cannot be initialized securely
            st.warning("⚠️ Credențialele Firebase ('firestore_creds') nu sunt găsite în st.secrets. Funcționalitatea Firebase este dezactivată.")
            return False

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            FIREBASE_ENABLED = True
            print("Firebase successfully initialized via st.secrets.")
            return True
            
    except Exception as e:
        st.error(f"❌ Eroare la inițializarea Firebase: {e}")
        return False

# Attempt to initialize Firebase when the script loads
# This function is called by streamlit_app.py as well, but we keep it here for completeness
initialize_firebase()

# --- Core Hybrid Analyzer Functions V7.3 ---

def calculate_kld_bidimensional(
        kld_total: float,
        kld_handicap: float,
        # KLD threshold values for V7.3
        treshold_kld_low: float = 0.05, 
        treshold_kld_high: float = 0.25,
        treshold_kld_very_high: float = 0.40,
        treshold_kld_limit: float = 0.65
    ) -> (str, float):
    """
    Calculează Decizia Finală KLD Bidimensional V7.3.
    """
    
    avg_kld = (kld_total + kld_handicap) / 2
    
    # 1. Decizia de bază bazată pe KLD Total Points
    if kld_total < treshold_kld_low:
        action_total = "KEEP"
    elif treshold_kld_low <= kld_total < treshold_kld_high:
        action_total = "EVAL"
    elif treshold_kld_high <= kld_total < treshold_kld_very_high:
        action_total = "INVERT"
    elif treshold_kld_very_high <= kld_total < treshold_kld_limit:
        action_total = "OVERRIDE"
    else: # kld_total >= treshold_kld_limit
        action_total = "RISK" # Or a similar high-risk flag

    # 2. Decizia finală și ajustările pe baza KLD Handicap
    final_action = action_total
    
    if action_total == "KEEP":
        if kld_handicap > treshold_kld_high:
            final_action = "EVAL_H" # Keep, but Handicap KLD suggests evaluation
        
    elif action_total == "EVAL":
        if kld_handicap > treshold_kld_very_high:
            final_action = "INVERT_H" # Invert due to strong Handicap KLD signal
        elif kld_handicap < treshold_kld_low:
            final_action = "KEEP" # Confirm Keep due to low Handicap KLD signal

    elif action_total == "INVERT":
        if kld_handicap < treshold_kld_low:
            final_action = "EVAL" # Invert Total is weak, pull back to EVAL due to low Handicap KLD

    elif action_total == "OVERRIDE":
        # Override is a strong signal, Handicap KLD must be very low to question it
        if kld_handicap < treshold_kld_low:
            final_action = "INVERT" # Pull back from OVERRIDE to INVERT

    # 3. Riscul Absolut (Uncorrelated High KLD)
    if kld_total >= treshold_kld_limit and kld_handicap >= treshold_kld_limit:
        final_action = "SKIP_DOUBLE_RISK"
    elif kld_total >= treshold_kld_limit or kld_handicap >= treshold_kld_limit:
        # High risk on one market means we should probably SKIP/EVAL
        if final_action in ["KEEP", "EVAL"]:
            final_action = "EVAL_RISK"
        elif final_action in ["INVERT", "OVERRIDE"]:
             final_action = "INVERT_RISK"

    # V7.3 Buffer logic: If final_action is INVERT or OVERRIDE, apply a buffer based on avg_kld
    buffer_value = 0.0
    
    if final_action.startswith("INVERT"):
        # Buffer calculation for Invert actions
        buffer_value = 1.0 + (avg_kld * 5.0) # Base 1.0 + KLD influence
    elif final_action.startswith("OVERRIDE"):
        # Stronger buffer for Override actions
        buffer_value = 1.5 + (avg_kld * 7.5) # Base 1.5 + Higher KLD influence
    
    # Ensure buffer is non-negative and capped
    buffer_value = max(0.0, min(buffer_value, 4.0)) # Capped at 4.0 points

    return final_action, buffer_value

def run_hybrid_analyzer(data: dict) -> (str, dict):
    """
    Rulează Analiza Hibrid V7.3 pe baza datelor de input.
    Returnează rezultatul (Markdown) și un dicționar cu datele cheie.
    """
    
    # --- 1. Data Cleaning and Preparation ---
    # Convert all relevant string inputs to float, handling potential errors
    try:
        # Total Points Data (TP)
        tp_lines = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
        tp_data = {}
        for line in tp_lines:
            tp_data[line] = {
                'line': data[f'tp_line_{line}'],
                'open_over': data[f'tp_open_over_{line}'],
                'close_over': data[f'tp_close_over_{line}'],
                'open_under': data[f'tp_open_under_{line}'],
                'close_under': data[f'tp_close_under_{line}']
            }
        
        # Historical Open Line (V7.3 Specific)
        historical_open_line = data.get('tp_line_open_hist', tp_data['close']['line']) 
        
        # Handicap Data (HD)
        hd_lines = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
        hd_data = {}
        for line in hd_lines:
            hd_data[line] = {
                'line': data[f'hd_line_{line}'],
                'open_home': data[f'hd_open_home_{line}'],
                'close_home': data[f'hd_close_home_{line}'],
                'open_away': data[f'hd_open_away_{line}'],
                'close_away': data[f'hd_close_away_{line}']
            }
        
    except Exception as e:
        return f"❌ **Eroare la prelucrarea datelor de intrare:** Asigurați-vă că toate câmpurile numerice sunt completate corect.\nDetalii: {e}", {}

    # --- 2. Consensus Determination (The 'True' Market Direction) ---
    
    # Simple check: Which way did the line move for Total Points close line?
    initial_line_tp = tp_data['close']['line']
    
    # Consensus: Market is favoring the side that saw the line decrease (in value, i.e., Over)
    # or the side that saw the line increase (in value, i.e., Under)
    if initial_line_tp < historical_open_line:
        consensus_direction = "OVER"
        consensus_line_change = historical_open_line - initial_line_tp
    elif initial_line_tp > historical_open_line:
        consensus_direction = "UNDER"
        consensus_line_change = initial_line_tp - historical_open_line
    else:
        consensus_direction = "STABLE"
        consensus_line_change = 0.0

    # The direction of the line change is crucial for subsequent analysis
    if consensus_direction == "OVER":
        line_change_side = "Over"
        line_change_coeff = 1.0 # Multiplier for KLD calculations
    elif consensus_direction == "UNDER":
        line_change_side = "Under"
        line_change_coeff = -1.0
    else:
        line_change_side = "Stable"
        line_change_coeff = 0.0
        
    # --- 3. KLD (Kullback-Leibler Divergence) Calculation (Core Logic) ---
    
    # KLD is calculated based on the divergence of Open vs. Close implied probabilities across lines
    kld_total_list = []
    kld_handicap_list = []
    
    # Function to calculate Implied Probability (IP)
    def calculate_ip(odd):
        return (1/odd) if odd > 1.0 else 0.0
        
    # Calculate KLD for Total Points (TP)
    for line_key in tp_lines:
        data_tp = tp_data[line_key]
        
        # Implied Probabilities (P - Open, Q - Close)
        P_over = calculate_ip(data_tp['open_over'])
        Q_over = calculate_ip(data_tp['close_over'])
        
        P_under = calculate_ip(data_tp['open_under'])
        Q_under = calculate_ip(data_tp['close_under'])
        
        # Normalization (Bookmaker margin removal - simple approach)
        sum_P = P_over + P_under
        sum_Q = Q_over + Q_under
        
        # P_norm = [P_over / sum_P, P_under / sum_P]
        # Q_norm = [Q_over / sum_Q, Q_under / sum_Q]
        
        # Calculate KLD for Over and Under (using normalized IPs)
        # KLD(P||Q) = sum(P(i) * log(P(i)/Q(i)))
        # For our purposes, we use a simplified KLD-like metric to show movement divergence
        
        # KLD for Over
        if Q_over > 0 and P_over > 0:
            kld_over = P_over * math.log(P_over / Q_over)
        else:
            kld_over = 0.0
            
        # KLD for Under
        if Q_under > 0 and P_under > 0:
            kld_under = P_under * math.log(P_under / Q_under)
        else:
            kld_under = 0.0
        
        # Total KLD for this line (signed based on consensus direction)
        # We assign the KLD value to the side that moved (or based on our consensus)
        if line_change_coeff > 0: # Market consensus is OVER (line moved down)
             kld_line = kld_over - kld_under # Positive value means Over divergence is stronger (confirming consensus)
        else: # Market consensus is UNDER (line moved up) or Stable
             kld_line = kld_under - kld_over # Positive value means Under divergence is stronger (confirming consensus)

        kld_total_list.append(kld_line)

    # Calculate KLD for Handicap (HD) - Same logic, using Home/Away
    for line_key in hd_lines:
        data_hd = hd_data[line_key]
        
        P_home = calculate_ip(data_hd['open_home'])
        Q_home = calculate_ip(data_hd['close_home'])
        
        P_away = calculate_ip(data_hd['open_away'])
        Q_away = calculate_ip(data_hd['close_away'])
        
        # KLD for Home
        if Q_home > 0 and P_home > 0:
            kld_home = P_home * math.log(P_home / Q_home)
        else:
            kld_home = 0.0
            
        # KLD for Away
        if Q_away > 0 and P_away > 0:
            kld_away = P_away * math.log(P_away / Q_away)
        else:
            kld_away = 0.0
        
        # For Handicap KLD, we just average the absolute divergence
        # as the initial line movement (consensus) isn't as critical here
        kld_line = abs(kld_home) + abs(kld_away)
        kld_handicap_list.append(kld_line)
    
    # Final KLD values (Average of all 7 lines)
    final_kld_total = np.mean([abs(k) for k in kld_total_list])
    final_kld_handicap = np.mean(kld_handicap_list)

    # --- 4. Hybrid Decision (KLD Bidimensional V7.3) ---
    
    kld_action, buffer_value = calculate_kld_bidimensional(final_kld_total, final_kld_handicap)

    # Determine the Final Direction based on KLD Action and Consensus
    if kld_action.startswith("KEEP") or kld_action.startswith("EVAL"):
        # KEEP/EVAL means confirm the market consensus direction
        final_bet_direction = consensus_direction
    elif kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE"):
        # INVERT/OVERRIDE means bet against the market consensus direction
        if consensus_direction == "OVER":
            final_bet_direction = "UNDER"
        elif consensus_direction == "UNDER":
            final_bet_direction = "OVER"
        else:
            final_bet_direction = "STABLE/SKIP" # Should not happen often
    elif kld_action.startswith("SKIP"):
        final_bet_direction = "SKIP"
    else:
        final_bet_direction = "EVAL/SKIP"


    # --- 5. Final Output Generation (Markdown) ---
    
    # Determine the final line and odd
    final_line = initial_line_tp
    
    if final_bet_direction == "OVER":
        final_odd = tp_data['close']['close_over']
        # Apply buffer for INVERT/OVERRIDE
        if kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE"):
            buffered_line = final_line + buffer_value
            # For OVER, a higher line means a lower odd (less favorable)
            # Use the odd of the original line as the 'reference odd'
        else:
            buffered_line = final_line - buffer_value
            # For OVER, a lower line means a lower odd (more favorable)
    elif final_bet_direction == "UNDER":
        final_odd = tp_data['close']['close_under']
        # Apply buffer for INVERT/OVERRIDE
        if kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE"):
            buffered_line = final_line - buffer_value
            # For UNDER, a lower line means a lower odd (less favorable)
            # Use the odd of the original line as the 'reference odd'
        else:
            buffered_line = final_line + buffer_value
            # For UNDER, a higher line means a lower odd (more favorable)
    else:
        # For SKIP/EVAL/STABLE, set buffer to 0
        buffered_line = final_line
        final_odd = 0.0 # Placeholder
        buffer_value = 0.0
        
    # --- Formatting the Final Report ---
    
    output_markdown = f"""
## 📊 Raport Analiză Hibrid V7.3 - {data['liga']}
### 📜 Meci: **{data['echipa_gazda']} vs {data['echipa_oaspete']}**

---

### 1. 🔍 Sumar Mișcare de Linie (Consensus)
* Linie Open Istorică: **{historical_open_line}**
* Linie Close (Curentă): **{initial_line_tp}**
* Diferență: **{consensus_line_change:.2f} puncte**
* **Consensusul Pieței:** Piața a împins linia spre **{consensus_direction}** (Linia a mers {('JOS' if consensus_direction == 'OVER' else 'SUS')}).
* Cota de Referință (Close): **{final_odd if final_odd != 0.0 else 'N/A'}**

---

### 2. 📉 Divergența KLD (Kullback-Leibler Divergence)
Divergența dintre cotele **Open** și **Close** pe 7 linii adiacente (M3, M2, M1, Close, P1, P2, P3).

| Market | KLD Mediu (Absolut) | Pragul de Semnal | Semnificație |
| :--- | :---: | :---: | :--- |
| **Total Points (TP)** | **{final_kld_total:.4f}** | 0.25 (INVERT) | Măsoară forța și direcția mișcării. |
| **Handicap (HD)** | **{final_kld_handicap:.4f}** | 0.40 (OVERRIDE) | Măsoară stabilitatea și riscul pieței de Handicap. |

---

### 3. 🎯 DECIZIA FINALĂ HIBRID V7.3
Decizia combină semnalul KLD de pe Total Points cu cel de pe Handicap, aplicând o logică bidimensională strictă.

* **Acțiunea KLD Total Points:** {kld_action} (Semnalul de bază dat de TP KLD)
* **Decizia KLD Bidimensională (FINAL):** **{kld_action}**
* **Factor Buffer V7.3:** **{buffer_value:.2f} puncte** (Activ doar pentru INVERT/OVERRIDE)

| Acțiunea | Semnificație | Propunere |
| :--- | :--- | :--- |
| **KEEP** | KLD slab, încredere în consensus. | **{consensus_direction}** |
| **EVAL** | KLD mediu, necesită analiză manuală. | **{consensus_direction} (ATENȚIE)** |
| **INVERT** | KLD puternic, pariază ÎMPOTRIVA consensusului. | **{final_bet_direction}** |
| **OVERRIDE** | KLD foarte puternic, semnal maxim de Trap/Inversare. | **{final_bet_direction}** |
| **SKIP** | KLD nesigur sau risc dublu. | **NU PARIA** |

---

### 4. ✅ PROPUNEREA DE PARIU (Total Points)

* **Direcția Propusă:** **{final_bet_direction}**
* **Linia Originală:** **{final_line}**
* **Linia Bufferată V7.3:** **{buffered_line:.2f}** (Aceasta este linia minimă acceptabilă)
* **Cota de Referință:** **{final_odd if final_odd != 0.0 else 'N/A'}**

> 💡 **Instrucțiune:** Caută linia **{final_bet_direction}** la o valoare cât mai apropiată de **{buffered_line:.2f}** cu o cotă de minim **{final_odd if final_odd != 0.0 else 'N/A'}** sau mai mare.
"""
    
    # Data structure for saving to Firebase
    result_data = {
        'liga': data['liga'],
        'gazda': data['echipa_gazda'],
        'oaspete': data['echipa_oaspete'],
        'date_input': data,
        'kld_total': final_kld_total,
        'kld_handicap': final_kld_handicap,
        'consensus_direction': consensus_direction,
        'final_bet_direction': final_bet_direction,
        'kld_action': kld_action,
        'buffer_value': buffer_value,
        'original_line': final_line,
        'buffered_line': buffered_line,
        'reference_odd': final_odd,
        'analysis_markdown': output_markdown,
        'timestamp': firestore.SERVER_TIMESTAMP if FIREBASE_ENABLED else None
    }
    
    return output_markdown, result_data

# --- Firebase Save Function (Called from streamlit_app.py) ---

def save_to_firebase(data: dict) -> bool:
    """Saves the final analysis data to the 'baschet' collection in Firestore."""
    if not FIREBASE_ENABLED or not db:
        st.error("❌ Salvarea a eșuat: Conexiunea Firebase este dezactivată sau neinițializată.")
        return False
        
    try:
        # Create a document name based on match details
        doc_name = f"{data['liga']}-{data['gazda']}-vs-{data['oaspete']}-{data['timestamp']}"
        doc_name = doc_name.replace(" ", "_").replace("/", "-")
        
        # Save to the 'baschet' collection
        db.collection("baschet").document(doc_name).set(data)
        st.success(f"✅ Analiza a fost salvată cu succes în Firebase sub ID-ul: `{doc_name}`")
        return True
    except Exception as e:
        st.error(f"❌ Eroare la salvarea în Firestore: {e}")
        return False

# --- Firebase Load Function (Called from streamlit_app.py) ---

def load_analysis_ids():
    """Fetches all document IDs from the 'baschet' collection."""
    if not FIREBASE_ENABLED or not db:
        return ["Firebase Dezactivat"]
        
    try:
        docs = db.collection("baschet").list_documents()
        ids = [doc.id for doc in docs]
        return ids
    except Exception as e:
        st.error(f"❌ Eroare la citirea ID-urilor din Firestore: {e}")
        return ["Eroare la Încărcare"]

def load_analysis_data(doc_id: str):
    """Fetches a single analysis document by its ID."""
    if not FIREBASE_ENABLED or not db:
        return None
        
    try:
        doc_ref = db.collection("baschet").document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            st.warning(f"ID-ul {doc_id} nu a fost găsit.")
            return None
    except Exception as e:
        st.error(f"❌ Eroare la încărcarea datelor analizei: {e}")
        return None
