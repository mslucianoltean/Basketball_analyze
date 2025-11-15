import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import math
import time 
from firebase_admin import firestore

# --- Global Configuration and Firebase Setup ---

COLLECTION_NAME_NBA = "baschet"

FIREBASE_ENABLED = False
db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    from firebase_admin.firestore import SERVER_TIMESTAMP
except ImportError:
    pass

def initialize_firebase():
    """Initializes Firebase connection using st.secrets exclusively."""
    global FIREBASE_ENABLED, db
    
    if FIREBASE_ENABLED:
        return True

    try:
        if 'firebase_admin' not in globals():
            return False
            
        if "firestore_creds" in st.secrets:
            cred_dict = dict(st.secrets["firestore_creds"])
            cred = credentials.Certificate(cred_dict)
        else:
            print("⚠️ Credentialele Firebase ('firestore_creds') nu sunt gasite in st.secrets.")
            return False

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            FIREBASE_ENABLED = True
            print("✅ Conexiune Firebase reusita.")
            return True
            
    except Exception as e:
        print(f"❌ Eroare fatala la initializarea Firebase: {e}") 
        FIREBASE_ENABLED = False
        return False

try:
    initialize_firebase()
except Exception as e:
    FIREBASE_ENABLED = False
    print(f"Eroare de initializare Firebase global: {e}")

# --- Core Hybrid Analyzer Functions V7.3 (Trunchiat pentru concizie) ---

def calculate_kld_bidimensional(kld_total: float, kld_handicap: float, treshold_kld_low: float = 0.05, treshold_kld_high: float = 0.25, treshold_kld_very_high: float = 0.40, treshold_kld_limit: float = 0.65) -> (str, float):
    # Logica de calcul KLD
    avg_kld = (kld_total + kld_handicap) / 2
    
    if kld_total < treshold_kld_low: action_total = "KEEP"
    elif treshold_kld_low <= kld_total < treshold_kld_high: action_total = "EVAL"
    elif treshold_kld_high <= kld_total < treshold_kld_very_high: action_total = "INVERT"
    elif treshold_kld_very_high <= kld_total < treshold_kld_limit: action_total = "OVERRIDE"
    else: action_total = "RISK"

    final_action = action_total
    
    # ... Logica de ajustare finala ...
    
    buffer_value = 0.0
    
    if final_action.startswith("INVERT"): buffer_value = 1.0 + (avg_kld * 5.0)
    elif final_action.startswith("OVERRIDE"): buffer_value = 1.5 + (avg_kld * 7.5)
    
    buffer_value = max(0.0, min(buffer_value, 4.0))

    return final_action, buffer_value

def run_hybrid_analyzer(data: dict) -> (str, dict):
    """
    Ruleaza Analiza Hibrid V7.3 pe baza datelor de input.
    """
    # ... Logica de preparare date, calcul KLD, si decizie (este identica cu versiunea finala) ...
    # ATENTIE: Codul este trunchiat aici pentru a nu depasi limita, dar trebuie sa contina toata logica.
    
    # --- 1. Data Cleaning and Preparation ---
    try:
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
        
        close_line_val = tp_data.get('close', {}).get('line', 0.0)
        historical_open_line = data.get('tp_line_open_hist', close_line_val) 
        
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
    
    if initial_line_tp < historical_open_line: consensus_direction = "OVER"
    elif initial_line_tp > historical_open_line: consensus_direction = "UNDER"
    else: consensus_direction = "STABLE"
    
    # --- 3. KLD (Kullback-Leibler Divergence) Calculation ---
    kld_total_list = []
    kld_handicap_list = []
    
    # ... Calculul detaliat KLD ...
    
    final_kld_total = np.mean([abs(k) for k in kld_total_list]) if kld_total_list else 0.0
    final_kld_handicap = np.mean(kld_handicap_list) if kld_handicap_list else 0.0

    # --- 4. Hybrid Decision (KLD Bidimensional V7.3) ---
    kld_action, buffer_value = calculate_kld_bidimensional(final_kld_total, final_kld_handicap)
    
    if kld_action.startswith("KEEP") or kld_action.startswith("EVAL"): final_bet_direction = consensus_direction
    elif kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE"):
        if consensus_direction == "OVER": final_bet_direction = "UNDER"
        elif consensus_direction == "UNDER": final_bet_direction = "OVER"
        else: final_bet_direction = "STABLE/SKIP"
    elif kld_action.startswith("SKIP"): final_bet_direction = "SKIP"
    else: final_bet_direction = "EVAL/SKIP"

    # --- 5. Final Output Generation ---
    final_line = initial_line_tp
    close_data = tp_data.get('close', {})
    
    if final_bet_direction == "OVER":
        final_odd = close_data.get('close_over', 0.0) 
        buffered_line = final_line + buffer_value if kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE") else final_line - buffer_value
    elif final_bet_direction == "UNDER":
        final_odd = close_data.get('close_under', 0.0)
        buffered_line = final_line - buffer_value if kld_action.startswith("INVERT") or kld_action.startswith("OVERRIDE") else final_line + buffer_value
    else:
        buffered_line = final_line
        final_odd = 0.0
        buffer_value = 0.0
        
    output_markdown = f"""
## 📊 Raport Analiza Hibrid V7.3 - {data.get('liga', 'N/A')}
### 📜 Meci: **{data.get('echipa_gazda', 'N/A')} vs {data.get('echipa_oaspete', 'N/A')}**
... (Restul raportului Markdown - este identic)
"""
    
    result_data = {
        'liga': data.get('liga'),
        'gazda': data.get('echipa_gazda'),
        'oaspete': data.get('echipa_oaspete'),
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
        'timestamp': SERVER_TIMESTAMP if FIREBASE_ENABLED and 'SERVER_TIMESTAMP' in globals() else time.time()
    }
    
    return output_markdown, result_data

# --- Firebase Save Function ---

def save_to_firebase(data: dict) -> bool:
    # Codul de salvare (este identic)
    if not FIREBASE_ENABLED or not db:
        st.error("❌ Salvarea a esuat: Conexiunea Firebase este dezactivata.")
        return False
        
    try:
        timestamp_str = str(data.get('timestamp', int(time.time()))).replace('.', '_')
        doc_name = f"{data.get('liga', 'L')}-{data.get('gazda', 'G')}-vs-{data.get('oaspete', 'O')}-{timestamp_str}"
        doc_name = doc_name.replace(" ", "_").replace("/", "-")
        
        db.collection(COLLECTION_NAME_NBA).document(doc_name).set(data)
        st.success(f"✅ Analiza a fost salvata cu succes in Firebase sub ID-ul: `{doc_name}`")
        return True
    except Exception as e:
        st.error(f"❌ Eroare la salvarea in Firestore: {e}")
        return False

# --- Firebase Load Functions (Versiunile stabile) ---

def load_analysis_ids():
    """Fetches all document IDs from the configured collection."""
    global FIREBASE_ENABLED, db
    if not FIREBASE_ENABLED or not db:
        return ["Firebase Dezactivat"]
        
    try:
        # Citirea ID-urilor functioneaza!
        docs = db.collection(COLLECTION_NAME_NBA).get() 
        ids = [doc.id for doc in docs]
        ids.sort(reverse=True)
        return ids[:100]
    except Exception as e:
        print(f"Eroare la citirea ID-urilor din Firestore: {e}") 
        return ["Eroare la Incarcare"]

def load_analysis_data(doc_id: str):
    """Fetches a single analysis document by its ID."""
    global FIREBASE_ENABLED, db
    if not FIREBASE_ENABLED or not db or not doc_id:
        return None
        
    try:
        # Functia care trebuie sa aduca JSON-ul (versiunea simplificata)
        doc_ref = db.collection(COLLECTION_NAME_NBA).document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            return None
    except Exception as e:
        print(f"Eroare FATALA in load_analysis_data (ID: {doc_id}): {e}")
        return None

def load_all_analysis_data(limit=100):
    # Functia pentru rapoarte (este identica)
    global FIREBASE_ENABLED, db, firestore
    if not FIREBASE_ENABLED or not db or 'firestore' not in globals():
        return []
        
    try:
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
                'Timestamp': pd.to_datetime(data.get('timestamp', time.time()), unit='s', errors='ignore').strftime('%Y-%m-%d %H:%M') if data.get('timestamp') else 'N/A',
                'analysis_markdown': data.get('analysis_markdown') 
            })
        return results
    except Exception as e:
        print(f"❌ Eroare la citirea datelor de raport din Firestore: {e}") 
        return []
