import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import math
# IMPORTANT: Importăm firestore din modulul firebase_admin
from firebase_admin import firestore

# --- Global Configuration and Firebase Setup ---

# Variabila de colectie
COLLECTION_NAME_NBA = "baschet"

FIREBASE_ENABLED = False
db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    # Preluam Timestamp din firestore, esential pentru salvare
    from firebase_admin.firestore import SERVER_TIMESTAMP
except ImportError:
    pass

def initialize_firebase():
    """Initializes Firebase connection using st.secrets exclusively."""
    global FIREBASE_ENABLED, db
    
    if FIREBASE_ENABLED:
        return True # Deja initializat

    try:
        # 1. Verifica importurile
        if 'firebase_admin' not in globals():
            return False
            
        # 2. Verifica si incarca credentialele
        if "firestore_creds" in st.secrets:
            cred = credentials.Certificate(dict(st.secrets["firestore_creds"]))
        else:
            print("⚠️ Credentialele Firebase ('firestore_creds') nu sunt gasite in st.secrets.")
            return False

        # 3. Initializare aplicatie Firebase
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            FIREBASE_ENABLED = True
            print("✅ Conexiune Firebase reusita.")
            return True
            
    except Exception as e:
        # Trateaza orice eroare de conexiune/initializare FARA a bloca aplicatia
        print(f"❌ Eroare fatala la initializarea Firebase: {e}") 
        # Dezactiveaza Firebase in caz de eroare
        FIREBASE_ENABLED = False
        return False

# Attempt to initialize Firebase when the script loads
try:
    initialize_firebase()
except Exception as e:
    FIREBASE_ENABLED = False
    print(f"Eroare de initializare Firebase global: {e}")

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
    Calculeaza Decizia Finala KLD Bidimensional V7.3.
    """
    
    avg_kld = (kld_total + kld_handicap) / 2
    
    # 1. Decizia de baza bazata pe KLD Total Points
    if kld_total < treshold_kld_low:
        action_total = "KEEP"
    elif treshold_kld_low <= kld_total < treshold_kld_high:
        action_total = "EVAL"
    elif treshold_kld_high <= kld_total < treshold_kld_very_high:
        action_total = "INVERT"
    elif treshold_kld_very_high <= kld_total < treshold_kld_limit:
        action_total = "OVERRIDE"
    else: # kld_total >= treshold_kld_limit
        action_total = "RISK"

    # 2. Decizia finala si ajustarile pe baza KLD Handicap
    final_action = action_total
    
    if action_total == "KEEP":
        if kld_handicap > treshold_kld_high:
            final_action = "EVAL_H"
        
    elif action_total == "EVAL":
        if kld_handicap > treshold_kld_very_high:
            final_action = "INVERT_H"
        elif kld_handicap < treshold_kld_low:
            final_action = "KEEP"

    elif action_total == "INVERT":
        if kld_handicap < treshold_kld_low:
            final_action = "EVAL"

    elif action_total == "OVERRIDE":
        if kld_handicap < treshold_kld_low:
            final_action = "INVERT"

    # 3. Riscul Absolut
    if kld_total >= treshold_kld_limit and kld_handicap >= treshold_kld_limit:
        final_action = "SKIP_DOUBLE_RISK"
    elif kld_total >= treshold_kld_limit or kld_handicap >= treshold_kld_limit:
        if final_action in ["KEEP", "EVAL"]:
            final_action = "EVAL_RISK"
        elif final_action in ["INVERT", "OVERRIDE"]:
             final_action = "INVERT_RISK"

    # V7.3 Buffer logic
    buffer_value = 0.0
    
    if final_action.startswith("INVERT"):
        buffer_value = 1.0 + (avg_kld * 5.0)
    elif final_action.startswith("OVERRIDE"):
        buffer_value = 1.5 + (avg_kld * 7.5)
    
    buffer_value = max(0.0, min(buffer_value, 4.0))

    return final_action, buffer_value

def run_hybrid_analyzer(data: dict) -> (str, dict):
    """
    Ruleaza Analiza Hibrid V7.3 pe baza datelor de input.
    """
    
    # --- 1. Data Cleaning and Preparation ---
    try:
        # Extragem cheile pentru a popula structurile interne
        tp_lines = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
        tp_data = {}
        for line in tp_lines:
            tp_data[line] = {
                'line': data.get(f'tp_line_{line}', 0.0),
                'open_over': data.get(f'tp_open_over_{line}', 1.0),
                'close_over': data.get(f'tp_close_over_{line}', 1.0),
                'open_under': data.get(f'tp_open_under_{line}', 1.0),
                'close_under': data.get(f'tp_close_under_{line}', 1.0)
            }
        
        # Historical Open Line 
        close_line_val = tp_data.get('close', {}).get('line', 0.0)
        historical_open_line = data.get('tp_line_open_hist', close_line_val) 
        
        # Handicap Data (HD)
        hd_lines = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
        hd_data = {}
        for line in hd_lines:
            hd_data[line] = {
                'line': data.get(f'hd_line_{line}', 0.0),
                'open_home': data.get(f'hd_open_home_{line}', 1.0),
                'close_home': data.get(f'hd_close_home_{line}', 1.0),
                'open_away': data.get(f'hd_open_away_{line}', 1.0),
                'close_away': data.get(f'hd_close_away_{line}', 1.0)
            }
        
    except Exception as e:
        return f"❌ **Eroare la prelucrarea datelor de intrare:** Asigurati-va ca toate campurile numerice sunt completate corect.\nDetalii: {e}", {}

    # --- 2. Consensus Determination ---
    initial_line_tp = tp_data['close']['line']
    
    if initial_line_tp < historical_open_line:
        consensus_direction = "OVER"
        consensus_line_change = historical_open_line - initial_line_tp
    elif initial_line_tp > historical_open_line:
        consensus_direction = "UNDER"
        consensus_line_change = initial_line_tp - historical_open_line
    else:
        consensus_direction = "STABLE"
        consensus_line_change = 0.0

    if consensus_direction == "OVER":
        line_change_coeff = 1.0
    elif consensus_direction == "UNDER":
        line_change_coeff = -1.0
    else:
        line_change_coeff = 0.0
        
    # --- 3. KLD (Kullback-Leibler Divergence) Calculation ---
    
    kld_total_list = []
    kld_handicap_list = []
    
    def calculate_ip(odd):
        return (1/odd) if odd > 1.0 else 0.0
        
    for line_key in tp_lines:
        data_tp_line = tp_data[line_key]
        
        P_over = calculate_ip(data_tp_line['open_over'])
        Q_over = calculate_ip(data_tp_line['close_over'])
        P_under = calculate_ip(data_tp_line['open_under'])
        Q_under = calculate_ip(data_tp_line['close_under'])
        
        if Q_over > 0 and P_over > 0:
            kld_over = P_over * math.log(P_over / Q_over)
        else:
            kld_over = 0.0
            
        if Q_under > 0 and P_under > 0:
            kld_under = P_under * math.log(P_under / Q_under)
        else:
            kld_under = 0.0
        
        if line_change_coeff > 0:
             kld_line = kld_over - kld_under
        else:
             kld_line = kld_under - kld_over

        kld_total_list.append(kld_line)

    for line_key in hd_lines:
        data_hd_line = hd_data[line_key]
        
        P_home = calculate_ip(data_hd_line['open_home'])
        Q_home = calculate_ip(data_hd_line['close_home'])
        P_away = calculate_ip(data_hd_line['open_away'])
        Q_away = calculate_ip(data_hd_line['close_away'])
        
        if Q_home > 0 and P_home > 0:
            kld_home = P_home * math.log(P_home / Q_home)
        else:
            kld_home = 0.0
            
        if Q_away > 0 and P_away > 0:
            kld_away = P_away * math.log(P_away / Q_away)
        else:
            kld_away = 0.0
        
        kld_line = abs(kld_home) + abs(kld_away)
        kld_handicap_list.append(kld_line)
    
    final_kld_total = np.mean([abs(k) for k in kld_total_list])
    final_kld_handicap = np.mean(kld_handicap_list)

    # --- 4. Hybrid Decision (KLD Bidimensional V7.3) ---
    kld_action, buffer_value = calculate_kld_bidimensional(final_kld_total, final_kld_handicap)

    if kld_action.startswith("KEEP") or kld_action.startswith("EVAL"):
        final_bet_direction = consensus_direction
    elif kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE"):
        if consensus_direction == "OVER":
            final_bet_direction = "UNDER"
        elif consensus_direction == "UNDER":
            final_bet_direction = "OVER"
        else:
            final_bet_direction = "STABLE/SKIP"
    elif kld_action.startswith("SKIP"):
        final_bet_direction = "SKIP"
    else:
        final_bet_direction = "EVAL/SKIP"


    # --- 5. Final Output Generation ---
    final_line = initial_line_tp
    
    close_data = tp_data.get('close', {})
    
    if final_bet_direction == "OVER":
        final_odd = close_data.get('close_over', 0.0) 
        if kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE"):
            buffered_line = final_line + buffer_value
        else:
            buffered_line = final_line - buffer_value
    elif final_bet_direction == "UNDER":
        final_odd = close_data.get('close_under', 0.0)
        if kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE"):
            buffered_line = final_line - buffer_value
        else:
            buffered_line = final_line + buffer_value
    else:
        buffered_line = final_line
        final_odd = 0.0
        buffer_value = 0.0
        
    # --- Formatting the Final Report ---
    
    output_markdown = f"""
## 📊 Raport Analiza Hibrid V7.3 - {data.get('liga', 'N/A')}
### 📜 Meci: **{data.get('echipa_gazda', 'N/A')} vs {data.get('echipa_oaspete', 'N/A')}**

---

### 1. 🔍 Sumar Miscare de Linie (Consensus)
* Linie Open Istorica: **{historical_open_line:.1f}**
* Linie Close (Curenta): **{initial_line_tp:.1f}**
* Diferenta: **{consensus_line_change:.2f} puncte**
* **Consensusul Pietei:** Piata a impins linia spre **{consensus_direction}** (Linia a mers {('JOS' if consensus_direction == 'OVER' else 'SUS')}).
* Cota de Referinta (Close): **{final_odd if final_odd != 0.0 else 'N/A'}**

---

### 2. 📉 Divergenta KLD (Kullback-Leibler Divergence)
| Market | KLD Mediu (Absolut) | Pragul de Semnal | Semnificatie |
| :--- | :---: | :---: | :--- |
| **Total Points (TP)** | **{final_kld_total:.4f}** | 0.25 (INVERT) | Masoara forta si directia miscarii. |
| **Handicap (HD)** | **{final_kld_handicap:.4f}** | 0.40 (OVERRIDE) | Masoara stabilitatea si riscul pietei de Handicap. |

---

### 3. 🎯 DECIZIA FINALA HIBRID V7.3
* **Actiunea KLD Total Points:** {kld_action}
* **Decizia KLD Bidimensionala (FINAL):** **{kld_action}**
* **Factor Buffer V7.3:** **{buffer_value:.2f} puncte**

| Actiunea | Semnificatie | Propunere |
| :--- | :--- | :--- |
| **KEEP** | KLD slab, incredere in consensus. | **{consensus_direction}** |
| **EVAL** | KLD mediu, necesita analiza manuala. | **{consensus_direction} (ATENTIE)** |
| **INVERT** | KLD puternic, pariaza IMPOTRIVA consensusului. | **{final_bet_direction}** |
| **OVERRIDE** | KLD foarte puternic, semnal maxim de Trap/Inversare. | **{final_bet_direction}** |
| **SKIP** | KLD nesigur sau risc dublu. | **NU PARIA** |

---

### 4. ✅ PROPUNEREA DE PARIU (Total Points)

* **Directia Propusa:** **{final_bet_direction}**
* **Linia Originala:** **{final_line:.1f}**
* **Linia Bufferata V7.3:** **{buffered_line:.2f}**
* **Cota de Referinta:** **{final_odd if final_odd != 0.0 else 'N/A'}**

> 💡 **Instructiune:** Cauta linia **{final_bet_direction}** la o valoare cat mai apropiata de **{buffered_line:.2f}** cu o cota de minim **{final_odd if final_odd != 0.0 else 'N/A'}** sau mai mare.
"""
    
    # Data structure for saving to Firebase
    result_data = {
        'liga': data.get('liga'),
        'gazda': data.get('echipa_gazda'),
        'oaspete': data.get('echipa_oaspete'),
        'date_input': data, # Salvam toate datele de input pentru reincarcare!
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
        'timestamp': SERVER_TIMESTAMP if FIREBASE_ENABLED and 'SERVER_TIMESTAMP' in globals() else pd.Timestamp.now().strftime('%Y%m%d%H%M%S')
    }
    
    return output_markdown, result_data

# --- Firebase Save Function ---

def save_to_firebase(data: dict) -> bool:
    """Saves the final analysis data to the Firestore collection defined by COLLECTION_NAME_NBA."""
    if not FIREBASE_ENABLED or not db:
        st.error("❌ Salvarea a esuat: Conexiunea Firebase este dezactivata.")
        return False
        
    try:
        timestamp_str = data.get('timestamp') if isinstance(data.get('timestamp'), str) else pd.Timestamp.now().strftime('%Y%m%d%H%M%S')
        doc_name = f"{data.get('liga', 'L')}-{data.get('gazda', 'G')}-vs-{data.get('oaspete', 'O')}-{timestamp_str}"
        doc_name = doc_name.replace(" ", "_").replace("/", "-")
        
        db.collection(COLLECTION_NAME_NBA).document(doc_name).set(data)
        st.success(f"✅ Analiza a fost salvata cu succes in Firebase sub ID-ul: `{doc_name}`")
        return True
    except Exception as e:
        st.error(f"❌ Eroare la salvarea in Firestore: {e}")
        return False

# --- Firebase Load Functions (Pentru pagina de Rapoarte) ---

def load_analysis_ids():
    """Fetches all document IDs from the configured collection."""
    global FIREBASE_ENABLED, db
    if not FIREBASE_ENABLED or not db:
        return ["Firebase Dezactivat"]
        
    try:
        docs = db.collection(COLLECTION_NAME_NBA).list_documents() 
        ids = [doc.id for doc in docs]
        ids.sort(reverse=True)
        return ids[:100]
    except Exception as e:
        st.error(f"❌ Eroare la citirea ID-urilor din Firestore: {e}") 
        return ["Eroare la Incarcare"]

def load_analysis_data(doc_id: str):
    """Fetches a single analysis document by its ID."""
    if not FIREBASE_ENABLED or not db:
        return None
        
    try:
        doc_ref = db.collection(COLLECTION_NAME_NBA).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            st.warning(f"ID-ul {doc_id} nu a fost gasit.")
            return None
    except Exception as e:
        st.error(f"❌ Eroare la incarcarea datelor analizei: {e}")
        return None

# --- NOU: Functie pentru Incarcarea Tuturor Rapoartelor (Pentru reports.py) ---
def load_all_analysis_data(limit=100):
    """Fetches key data for all analysis documents."""
    global FIREBASE_ENABLED, db
    # Folosim direct clasa firestore importata de la inceput
    if not FIREBASE_ENABLED or not db or 'firestore' not in globals():
        return []
        
    try:
        # Sortam după timestamp (cel mai nou primul) și limităm la 100 de documente
        docs = db.collection(COLLECTION_NAME_NBA).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({
                'ID': doc.id,
                'Liga': data.get('liga', 'N/A'),
                'Meci': f"{data.get('gazda', 'N/A')} vs {data.get('oaspete', 'N/A')}",
                'Linie Originala': f"{data.get('original_line', 0.0):.1f}",
                'Directia Finala': data.get('final_bet_direction', 'EVAL'),
                'Actiune KLD': data.get('kld_action', 'EVAL'),
                'KLD Total': f"{data.get('kld_total', 0.0):.4f}",
                'Linie Bufferata': f"{data.get('buffered_line', 0.0):.2f}",
                # Conversie sigură a timestamp-ului
                'Timestamp': str(data.get('timestamp')),
                'analysis_markdown': data.get('analysis_markdown') 
            })
        return results
    except Exception as e:
        print(f"❌ Eroare la citirea datelor de raport din Firestore: {e}") 
        return []
