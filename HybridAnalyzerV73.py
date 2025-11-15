import json
from datetime import datetime
import numpy as np
import math
import sys
import os
import streamlit as st

# =============================================================================
# DEPENDENȚE FIREBASE & CONFIGURARE
# =============================================================================

COLLECTION_NAME_NBA = 'baschet'

FIREBASE_ENABLED = False
db = None

def initialize_firebase():
    global FIREBASE_ENABLED, db
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Încearcă să încarci credențialele din st.secrets (recomandat pentru Streamlit Cloud)
        # sau fallback la fișier local pentru rulare locală.
        if "firestore_creds" in st.secrets:
            # Use st.secrets for Streamlit Cloud deployment
            cred = credentials.Certificate(dict(st.secrets["firestore_creds"]))
        elif os.path.exists('oddsanalyze-5f88e-firebase-adminsdk-fbsvc-10e06f0474.json'):
            # Fallback to local file
            cred = credentials.Certificate('oddsanalyze-5f88e-firebase-adminsdk-fbsvc-10e06f0474.json')
        else:
            return False

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            FIREBASE_ENABLED = True
            return True
            
    except ImportError:
        return False 
    except Exception as e:
        print(f"Firebase Initialization Error: {e}")
        return False

# Apelăm inițializarea o singură dată
initialize_firebase()


def save_to_firebase(decision_data):
    """Salvează analiza în Firebase."""
    if not FIREBASE_ENABLED or db is None:
        return f"[INFO] Firebase nu este inițializat. Salvarea nu este posibilă."
    try:
        match_id = f"{decision_data['League']}_{decision_data['HomeTeam']}_VS_{decision_data['AwayTeam']}_V7_3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        decision_data_clean = json.loads(json.dumps(decision_data, default=str)) 
        db.collection(COLLECTION_NAME_NBA).document(match_id).set(decision_data_clean)
        
        return f"✅ Analiză salvată în Firebase!\n📋 ID: **{match_id}**"
        
    except Exception as e:
        return f"❌ Eroare Firebase: {e}"

def get_all_match_ids():
    """Recuperează toate ID-urile meciurilor din colecție."""
    if not FIREBASE_ENABLED or db is None:
        return []
    try:
        docs = db.collection(COLLECTION_NAME_NBA).stream()
        return [doc.id for doc in docs]
    except Exception:
        return []

def get_analysis_by_id(match_id):
    """Recuperează datele unei analize după ID."""
    if not FIREBASE_ENABLED or db is None:
        return None
    try:
        doc = db.collection(COLLECTION_NAME_NBA).document(match_id).get()
        return doc.to_dict()
    except Exception:
        return None

# =============================================================================
# CLASA PRINCIPALĂ DE ANALIZĂ HIBRIDĂ (V7.3 - VERIFICARE ISTORIC)
# Codul clasei HybridAnalyzerV73 este păstrat integral de aici în jos.
# =============================================================================

class HybridAnalyzerV73:
    """
    Analizator Hibrid Baschet V7.3 - VERIFICARE CONFLICT ISTORIC:
    1. ✅ Buffer sincronizat cu KLD (după inversare)
    2. ✅ Praguri KLD recalibrate (0.03 / 0.06)
    3. ✅ KLD bidimensional corect
    4. ✅ NOU: Verificare conflict între Steam și Mișcare Istorică
    """
    
    def __init__(self, league, home_team, away_team, total_lines_data, handicap_lines_data):
        self.LEAGUE = league
        self.HOME_TEAM = home_team
        self.AWAY_TEAM = away_team
        
        self.TOTAL_LINES = {k.lower(): v for k, v in total_lines_data.items()}
        self.HANDICAP_LINES = {k.lower(): v for k, v in handicap_lines_data.items()}
        
        # Constante de Ponderare V3.0.2 (Păstrate)
        self.WEIGHT_CONSENSUS = 0.50
        self.WEIGHT_GRADIENT = 0.15
        self.BONUS_STEAM = 25
        self.PENALTY_TRAP = 10
        self.PENALTY_ENTROPY = 15
        self.AGGRESSION_THRESHOLD = 0.25 
        self.PENALTY_HISTORIC_MOVE = 20 
        self.THRESHOLD_HISTORIC_MOVE = 5.0 
        self.BONUS_CONTRARION = 20  
        self.MULTIPLIER_REAL_TRAP = 1.5  
        self.PENALTY_V301_FORCED = 40.0 
        self.BONUS_CONFLUENCE_TRIPLE_CHECK = 15.0 
        self.GRADIENT_CONFLUENCE_THRESHOLD = 70.0 
        
        # ✅ Praguri KLD Recalibrate (V7.1)
        self.KLD_THRESHOLD_SAFE = 0.03
        self.KLD_THRESHOLD_SHOCK = 0.06
        
        # Buffer-uri (aplicate DUPĂ inversare KLD)
        self.BUFFER_TOTAL_OVER = -5.0
        self.BUFFER_TOTAL_UNDER = 7.0
        self.BUFFER_HANDICAP = 2.5
        
        # ✅ NOU V7.3: Constante pentru Verificare Istoric
        self.THRESHOLD_HISTORIC_CONFLICT = 2.0  # Mișcare semnificativă (puncte)
        self.PENALTY_HISTORIC_CONFLICT = 30.0   # Penalizare pentru conflict
        self.CONSENSUS_OVERHEAT_THRESHOLD = 65.0  # Consensus supraîncălzit
        
        # Analize de precizie (V3.0.2)
        self.consensus_score = self._calculate_consensus_score()
        self.steam_detection = self._detect_steam_moves()
        self.gradient_analysis = self._analyze_line_gradient()
        self.manipulation_flags = self._detect_manipulation()
        self.entropy_alerts = self._analyze_entropy()
        
        # ✅ NOU V7.3: Analiza mișcării istorice
        self.historic_analysis = self._analyze_historic_movement()
        
        # Construire matrice (după analiza istorică)
        self.confidence_matrix = self._build_confidence_matrix()
        
        # KLD Bidimensional Corect (V7.1)
        self._kld_scores = self._calculate_kl_divergence_FIXED()
        
        self.decision = {}
    
    # =============================================================================
    # SECȚIUNE ANALIZĂ V3.0.2 (PĂSTRATĂ INTEGRAL)
    # =============================================================================
    
    def _calculate_consensus_score(self):
        """Calculează scorul de consens pentru fiecare direcție."""
        consensus = {'TOTAL': {'OVER': 0, 'UNDER': 0}, 'HANDICAP': {'HOME': 0, 'AWAY': 0}}
        max_score = 7 * 5 
        LINE_KEYS = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
            if market == 'TOTAL':
                dir_keys = ('over', 'under')
            else:
                dir_keys = ('home', 'away')
                
            for line_key in LINE_KEYS:
                line_data = lines_data[line_key]
                score1, score2 = 0, 0
                
                # Use .get() with a default value to prevent KeyError if data is incomplete
                if line_data.get(f'{dir_keys[0]}_close', 999) < 1.85: score1 += 3
                if line_data.get(f'{dir_keys[1]}_close', 999) < 1.85: score2 += 3
                
                move1 = line_data.get(f'{dir_keys[0]}_open', 0) - line_data.get(f'{dir_keys[0]}_close', 0)
                move2 = line_data.get(f'{dir_keys[1]}_open', 0) - line_data.get(f'{dir_keys[1]}_close', 0)
                if move1 > 0.05: score1 += 2
                if move2 > 0.05: score2 += 2
                
                if market == 'TOTAL':
                    consensus['TOTAL']['OVER'] += score1
                    consensus['TOTAL']['UNDER'] += score2
                else:
                    consensus['HANDICAP']['HOME'] += score1
                    consensus['HANDICAP']['AWAY'] += score2
        
        for market in ['TOTAL', 'HANDICAP']:
            for direction in consensus[market]:
                consensus[market][direction] = (consensus[market][direction] / max_score) * 100
        
        return consensus
    
    def _detect_steam_moves(self):
        """Detectează mișcările Steam (sharp money)."""
        steam = {'TOTAL': None, 'HANDICAP': None}
        STEAM_THRESHOLD = 0.08
        LINE_KEYS = ['close', 'm3', 'm2', 'm1', 'p1', 'p2', 'p3']

        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
            if market == 'TOTAL':
                dir_keys = ('over', 'under')
                dir_names = ('OVER', 'UNDER')
            else:
                dir_keys = ('home', 'away')
                dir_names = ('HOME', 'AWAY')
                
            moves1, moves2 = [], []
            for k in LINE_KEYS:
                d = lines_data[k]
                # Use .get() with default 0 to handle potentially missing open/close values
                move1 = d.get(f'{dir_keys[0]}_open', 0) - d.get(f'{dir_keys[0]}_close', 0)
                move2 = d.get(f'{dir_keys[1]}_open', 0) - d.get(f'{dir_keys[1]}_close', 0)
                
                if move1 > STEAM_THRESHOLD: moves1.append({'line': d['line'], 'move': move1})
                if move2 > STEAM_THRESHOLD: moves2.append({'line': d['line'], 'move': move2})
            
            if len(moves1) >= 3: 
                steam[market] = {
                    'direction': dir_names[0], 
                    'strength': len(moves1), 
                    'avg_move': np.mean([m['move'] for m in moves1]) if moves1 else 0.0, 
                    'lines_affected': moves1
                }
            elif len(moves2) >= 3: 
                steam[market] = {
                    'direction': dir_names[1], 
                    'strength': len(moves2), 
                    'avg_move': np.mean([m['move'] for m in moves2]) if moves2 else 0.0, 
                    'lines_affected': moves2
                }
        
        return steam

    def _analyze_line_gradient(self):
        """Analizează uniformitatea gradientului de cote."""
        gradient = {'TOTAL': {'uniformity': 0, 'anomalies': []}, 'HANDICAP': {'uniformity': 0, 'anomalies': []}}
        LINE_ORDER = ['m3', 'm2', 'm1', 'close', 'p1', 'p2', 'p3']
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
            if market == 'TOTAL':
                dir_keys = ('over', 'under')
                dir_names = ('OVER', 'UNDER')
            else:
                dir_keys = ('home', 'away')
                dir_names = ('HOME', 'AWAY')
                
            # Filtrează cotele care există și sunt numerice
            closes1 = [lines_data[k][f'{dir_keys[0]}_close'] for k in LINE_ORDER if k in lines_data and f'{dir_keys[0]}_close' in lines_data[k]]
            closes2 = [lines_data[k][f'{dir_keys[1]}_close'] for k in LINE_ORDER if k in lines_data and f'{dir_keys[1]}_close' in lines_data[k]]
            
            if len(closes1) > 1:
                diffs1 = np.diff(closes1)
                std1 = np.std(diffs1)
                # Calculează uniformitatea
                gradient[market]['uniformity'] = max(0, 100 - (std1 + np.std(np.diff(closes2)) if len(closes2) > 1 else 0.0) * 100)
                
                for i, diff in enumerate(diffs1):
                    if abs(diff) > 0.15: 
                        gradient[market]['anomalies'].append({
                            'type': dir_names[0], 
                            'between': f"{LINE_ORDER[i]} și {LINE_ORDER[i+1]}", 
                            'diff': diff
                        })

            if len(closes2) > 1:
                diffs2 = np.diff(closes2)
                std2 = np.std(diffs2)
                gradient[market]['uniformity'] = max(0, 100 - (std2 + np.std(np.diff(closes1)) if len(closes1) > 1 else 0.0) * 100)
                
                for i, diff in enumerate(diffs2):
                    if abs(diff) > 0.15: 
                        gradient[market]['anomalies'].append({
                            'type': dir_names[1], 
                            'between': f"{LINE_ORDER[i]} și {LINE_ORDER[i+1]}", 
                            'diff': diff
                        })

        return gradient

    def _detect_manipulation(self):
        """Detectează trap lines (manipulări de piață)."""
        flags = []
        LINE_KEYS = ['m3', 'm2', 'm1', 'p1', 'p2', 'p3']
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
            if 'close' not in lines_data: continue
            
            close_data = lines_data['close']
            if market == 'TOTAL':
                dir_keys = ('over', 'under')
                dir_names = ('TOTAL_OVER', 'TOTAL_UNDER')
            else:
                dir_keys = ('home', 'away')
                dir_names = ('HANDICAP_HOME', 'HANDICAP_AWAY')
            
            close_cota_1 = close_data.get(f'{dir_keys[0]}_close', 999)
            close_cota_2 = close_data.get(f'{dir_keys[1]}_close', 999)
            
            for line_key in LINE_KEYS:
                if line_key not in lines_data: continue
                line_data = lines_data[line_key]
                
                cota_1 = line_data.get(f'{dir_keys[0]}_close', 999)
                cota_2 = line_data.get(f'{dir_keys[1]}_close', 999)
                open_cota_1 = line_data.get(f'{dir_keys[0]}_open', 999)
                open_cota_2 = line_data.get(f'{dir_keys[1]}_open', 999)
                
                if cota_1 < close_cota_1 - 0.20:
                    flags.append({
                        'type': f'TRAP_LINE_{dir_names[0]}', 
                        'line': line_data['line'], 
                        'cota': cota_1, 
                        'vs_close': close_cota_1, 
                        'severity': 'HIGH',
                        'move_open_close': round(open_cota_1 - cota_1, 3)
                    })
                
                if cota_2 < close_cota_2 - 0.20:
                    flags.append({
                        'type': f'TRAP_LINE_{dir_names[1]}', 
                        'line': line_data['line'], 
                        'cota': cota_2, 
                        'vs_close': close_cota_2, 
                        'severity': 'HIGH',
                        'move_open_close': round(open_cota_2 - cota_2, 3)
                    })
        
        return flags
        
    def _calculate_shannon_entropy(self, probabilities):
        """Calculează entropia Shannon."""
        probabilities = [p for p in probabilities if p > 0]
        if not probabilities: return 0.0
        total_sum = sum(probabilities)
        if total_sum == 0: return 0.0
        norm_probs = [p / total_sum for p in probabilities]
        entropy = -sum(p * math.log2(p) for p in norm_probs if p > 0) # Adaugă p > 0 pentru siguranță
        return entropy

    def _analyze_entropy(self):
        """Analizează entropia pentru a detecta concentrarea de probabilități."""
        alerts = {'TOTAL': None, 'HANDICAP': None}
        LINE_ORDER = ['m3', 'm2', 'm1', 'close', 'p1', 'p2', 'p3']
        ECC_THRESHOLD = 1.2 
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
            if market == 'TOTAL':
                dir_keys = ('over', 'under')
                dir_names = ('OVER', 'UNDER')
            else:
                dir_keys = ('home', 'away')
                dir_names = ('HOME', 'AWAY')

            probs1 = [1.0 / lines_data[k].get(f'{dir_keys[0]}_close', 0) for k in LINE_ORDER if k in lines_data and lines_data[k].get(f'{dir_keys[0]}_close', 0) > 1.0]
            probs2 = [1.0 / lines_data[k].get(f'{dir_keys[1]}_close', 0) for k in LINE_ORDER if k in lines_data and lines_data[k].get(f'{dir_keys[1]}_close', 0) > 1.0]
            entropy1 = self._calculate_shannon_entropy(probs1)
            entropy2 = self._calculate_shannon_entropy(probs2)
            
            cons1 = self.consensus_score[market].get(dir_names[0], 0)
            cons2 = self.consensus_score[market].get(dir_names[1], 0)

            if cons1 > cons2 and entropy1 < ECC_THRESHOLD and entropy1 > 0:
                alerts[market] = {'direction': dir_names[0], 'entropy': entropy1}
            elif cons2 > cons1 and entropy2 < ECC_THRESHOLD and entropy2 > 0:
                alerts[market] = {'direction': dir_names[1], 'entropy': entropy2}

        return alerts
    
    # =============================================================================
    # ✅ NOU V7.3: ANALIZĂ MIȘCARE ISTORICĂ
    # =============================================================================
    
    def _analyze_historic_movement(self):
        """
        Analizează mișcarea istorică a liniei și identifică direcția dominantă inițială.
        """
        historic = {}
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES)]: # Doar Total are open_line_value în inputul oferit
            if 'close' not in lines_data: continue
            close_data = lines_data['close']
            
            # Extrage linia istorică (open_line_value)
            open_line = close_data.get('open_line_value')
            close_line = close_data['line']
            
            if open_line is not None:
                movement = close_line - open_line
                is_significant = abs(movement) >= self.THRESHOLD_HISTORIC_CONFLICT
                
                # Determină direcția dominantă istorică
                if movement > self.THRESHOLD_HISTORIC_CONFLICT:
                    # Linia a urcat → Banii inițiali pe UNDER
                    dominant_direction = 'UNDER'
                elif movement < -self.THRESHOLD_HISTORIC_CONFLICT:
                    # Linia a coborât → Banii inițiali pe OVER
                    dominant_direction = 'OVER'
                else:
                    dominant_direction = None  # Mișcare neutră
                
                historic[market] = {
                    'open_line': open_line,
                    'close_line': close_line,
                    'movement': movement,
                    'dominant_direction': dominant_direction,
                    'is_significant': is_significant
                }
            else:
                # Dacă nu există open_line_value
                historic[market] = {
                    'open_line': None,
                    'close_line': close_line,
                    'movement': 0.0,
                    'dominant_direction': None,
                    'is_significant': False
                }
        
        # Logica pentru Handicap ar trebui să fie similară, dar lipsește 'open_line_value' din inputul Handicap
        if 'HANDICAP' not in historic:
             historic['HANDICAP'] = {
                'open_line': None,
                'close_line': self.HANDICAP_LINES.get('close', {}).get('line', 0.0),
                'movement': 0.0,
                'dominant_direction': None,
                'is_significant': False
            }

        return historic

    def _classify_trap_nature(self, trap_flags, market, direction):
        """Clasifică natura trap-ului: REAL (evită) sau CONTRARION (joacă contra)."""
        if not trap_flags:
            return None
        
        consensus_score = self.consensus_score[market].get(direction, 0)
        steam_data = self.steam_detection[market]
        gradient_uniformity = self.gradient_analysis[market]['uniformity']
        entropy_alert = self.entropy_alerts[market]
        
        has_steam_on_trap = (steam_data and steam_data['direction'] == direction)
        steam_strength = steam_data['strength'] if has_steam_on_trap else 0
        
        historic_move = 0.0
        try:
            historic_data = self.historic_analysis.get(market)
            if historic_data and historic_data['open_line'] is not None:
                 historic_move = abs(historic_data['open_line'] - historic_data['close_line'])
        except:
            pass
        
        severe_traps = sum(1 for f in trap_flags if f.get('severity') == 'HIGH')
        aggressive_traps = sum(1 for f in trap_flags if f.get('move_open_close', 0) >= 0.25)
        
        contrarion_score = 0
        real_trap_score = 0
        
        if consensus_score > 65: contrarion_score += 30
        elif consensus_score > 55: contrarion_score += 15
        
        if has_steam_on_trap:
            contrarion_score += 25
            if steam_strength >= 5: contrarion_score += 10
        
        if gradient_uniformity > 70: contrarion_score += 15
        if aggressive_traps >= 2: contrarion_score += 10
        if historic_move < 3.0: contrarion_score += 10
        
        if consensus_score < 40: real_trap_score += 30
        if not has_steam_on_trap: real_trap_score += 25
        if steam_data and steam_data['direction'] != direction: real_trap_score += 15
        if gradient_uniformity < 50: real_trap_score += 20
        if entropy_alert and entropy_alert['direction'] == direction: real_trap_score += 15
        if severe_traps >= 3: real_trap_score += 20
        if historic_move > 5.0: real_trap_score += 15
        
        if contrarion_score > real_trap_score + 20:
            trap_type = 'CONTRARION'
            confidence = min(100, (contrarion_score / 100) * 100)
            action = 'PLAY_CONTRA'
            reasoning = self._build_contrarion_reasoning(
                consensus_score, steam_strength, gradient_uniformity, 
                aggressive_traps, historic_move
            )
        elif real_trap_score > contrarion_score + 20:
            trap_type = 'REAL'
            confidence = min(100, (real_trap_score / 100) * 100)
            action = 'AVOID'
            reasoning = self._build_real_trap_reasoning(
                consensus_score, has_steam_on_trap, gradient_uniformity,
                severe_traps, entropy_alert, historic_move
            )
        else:
            trap_type = 'AMBIGUOUS'
            confidence = 50
            action = 'CAUTION'
            reasoning = f"Semnale mixte: Contrarion={contrarion_score}, Real={real_trap_score}. Prudență."
        
        return {
            'type': trap_type,
            'confidence': round(confidence, 1),
            'reasoning': reasoning,
            'action': action,
            'scores': {
                'contrarion': contrarion_score,
                'real_trap': real_trap_score
            }
        }

    def _build_contrarion_reasoning(self, consensus, steam, gradient, aggressive, historic):
        """Construiește explicația pentru TRAP Contrarion."""
        reasons = []
        if consensus > 65: 
            reasons.append(f"✓ Consensus puternic ({consensus:.1f}%) = supraîncărcare publică")
        if steam >= 3: 
            reasons.append(f"✓ Steam agresiv ({steam} linii) = mișcare profesională")
        if gradient > 70: 
            reasons.append(f"✓ Gradient uniform ({gradient:.1f}%) = mișcare controlată")
        if aggressive >= 2: 
            reasons.append(f"✓ {aggressive} trap-uri agresive = overreaction piață")
        if historic < 3: 
            reasons.append(f"✓ Linie stabilă istoric ({historic:.1f}pt) = risc redus")
        return " | ".join(reasons)

    def _build_real_trap_reasoning(self, consensus, steam, gradient, severe, entropy, historic):
        """Construiește explicația pentru TRAP Real."""
        reasons = []
        if consensus < 40: 
            reasons.append(f"✗ Consensus slab ({consensus:.1f}%) = lipsă suport")
        if not steam: 
            reasons.append("✗ Fără Steam = lipsă interes profesional")
        if gradient < 50: 
            reasons.append(f"✗ Gradient neuniform ({gradient:.1f}%) = manipulare")
        if severe >= 3: 
            reasons.append(f"✗ {severe} trap-uri severe = manipulare sistematică")
        if entropy: 
            reasons.append(f"✗ Alertă entropie = concentrare suspectă")
        if historic > 5: 
            reasons.append(f"✗ Linie instabilă istoric ({historic:.1f}pt) = risc major")
        return " | ".join(reasons)

# ========================================================================
# =============================================================================
# PARTEA 2/3 - CONTINUARE HybridAnalyzerV73
# =============================================================================

    def _calculate_score_components(self):
        """
        Calculează componentele scorului pentru fiecare direcție (V7.3 logic cu Verificare Istoric).
        Include toate bonusurile și penalizările + CONFLICT ISTORIC.
        """
        scores = {}
        historic_penalty_applied = 0
        historic_move_diff = 0.0
        is_historic_risk = False
        is_historic_aligned_with_direction = False
        
        try:
            # Doar pentru Total, unde avem Open Line Istorică
            if 'close' in self.TOTAL_LINES:
                open_line = self.TOTAL_LINES['close'].get('open_line_value') 
                close_line = self.TOTAL_LINES['close']['line']
                if open_line is not None:
                    historic_move_diff = close_line - open_line
                    if abs(historic_move_diff) >= self.THRESHOLD_HISTORIC_MOVE:
                        historic_penalty_applied = self.PENALTY_HISTORIC_MOVE
                        is_historic_risk = True
        except (KeyError, TypeError, ValueError):
            pass 
        
        for market_dir in ['TOTAL_OVER', 'TOTAL_UNDER', 'HANDICAP_HOME', 'HANDICAP_AWAY']:
            market, direction = market_dir.split('_')
            cons_score = self.consensus_score[market].get(direction, 0)
            uniformity = self.gradient_analysis[market]['uniformity']
            cons_points = cons_score * self.WEIGHT_CONSENSUS
            grad_points = uniformity * self.WEIGHT_GRADIENT
            
            steam_bonus = 0
            is_steam = False
            if self.steam_detection[market] and self.steam_detection[market]['direction'] == direction:
                steam_bonus = self.BONUS_STEAM
                is_steam = True
            
            trap_penalty = 0
            contrarion_bonus = 0
            trap_flags = [f for f in self.manipulation_flags if direction in f.get('type', '')] 
            trap_analysis = {
                'flags': trap_flags, 
                'points': 0, 
                'recommended_action': 'N/A', 
                'is_ignored': False,
                'classification': None
            }
            
            if trap_flags:
                trap_classification = self._classify_trap_nature(trap_flags, market, direction)
                trap_analysis['classification'] = trap_classification
                
                if trap_classification['type'] == 'CONTRARION':
                    trap_penalty = 0
                    contrarion_bonus = self.BONUS_CONTRARION
                    trap_analysis['points'] = -contrarion_bonus
                    trap_analysis['recommended_action'] = f"🎯 JOACĂ CONTRA (Confidence: {trap_classification['confidence']:.1f}%)"
                    trap_analysis['is_contrarion'] = True
                
                elif trap_classification['type'] == 'REAL':
                    trap_penalty = len(trap_flags) * self.PENALTY_TRAP * self.MULTIPLIER_REAL_TRAP
                    trap_analysis['points'] = trap_penalty
                    trap_analysis['recommended_action'] = f"🚫 EVITĂ (Confidence: {trap_classification['confidence']:.1f}%)"
                    trap_analysis['is_contrarion'] = False
                
                else:
                    trap_penalty = len(trap_flags) * self.PENALTY_TRAP
                    trap_analysis['points'] = trap_penalty
                    trap_analysis['recommended_action'] = f"⚠️ PRUDENȚĂ (Semnale mixte)"
                    trap_analysis['is_contrarion'] = False

            entropy_penalty = 0
            if self.entropy_alerts[market] and self.entropy_alerts[market]['direction'] == direction:
                entropy_penalty = self.PENALTY_ENTROPY
            
            current_historic_penalty = 0
            confluence_bonus = 0 
            
            # ✅ NOU V7.3: VERIFICARE CONFLICT ISTORIC
            historic_conflict_penalty = 0
            is_historic_conflict = False
            
            historic_data = self.historic_analysis.get(market)
            if historic_data and historic_data['is_significant']:
                dominant_historic = historic_data['dominant_direction']
                
                # Verifică dacă direcția curentă e în CONFLICT cu direcția istorică
                if dominant_historic and dominant_historic != direction:
                    is_historic_conflict = True
                    historic_conflict_penalty = self.PENALTY_HISTORIC_CONFLICT
                    
                    # Logica de printat se va muta în funcția de afișare Streamlit
            
            if market == 'TOTAL':
                current_historic_penalty = historic_penalty_applied
                
                # Aliniere specifică pentru Total (pentru Triple Check)
                if historic_move_diff != 0:
                    is_historic_aligned_with_direction = \
                        (historic_move_diff < 0 and direction == 'OVER') or \
                        (historic_move_diff > 0 and direction == 'UNDER')
                
                # Logica Triple Check - (Bonus Contrarion ȘI Risc Istoric ȘI Aliniat ȘI Steam)
                if contrarion_bonus > 0 and is_historic_risk and is_historic_aligned_with_direction and is_steam:
                    if uniformity >= self.GRADIENT_CONFLUENCE_THRESHOLD:
                        confluence_bonus = self.BONUS_CONFLUENCE_TRIPLE_CHECK
                        current_historic_penalty = 0 
                        # Actualizează clasificarea Trap
                        trap_analysis['classification']['type'] = "CONTRARION (V3.0.2 TC VALIDARE)"
                        trap_analysis['recommended_action'] = f"🎯 JOACĂ CONTRA (V3.0.2 TC VALIDARE)"
                    else:
                        # Simularea erorii Triple Check
                        contrarion_bonus = 0 
                        trap_penalty = self.PENALTY_V301_FORCED
                        trap_analysis['classification']['type'] = "REAL (V3.0.2 FORCED)"
                        trap_analysis['recommended_action'] = f"🚫 EVITĂ (V3.0.2 SAFETY)"

            total_penalties = trap_penalty + entropy_penalty + current_historic_penalty + historic_conflict_penalty
            final_score = cons_points + grad_points + steam_bonus + contrarion_bonus + confluence_bonus - total_penalties
            final_score = max(0, min(100, final_score))
            
            scores[market_dir] = {
                'Final_Score': final_score,
                'Components': {
                    'Consensus': {'score': cons_score, 'points': cons_points},
                    'Gradient': {'score': uniformity, 'points': grad_points},
                    'Steam': {'is_active': is_steam, 'points': steam_bonus}, 
                    'Trap_Analysis': trap_analysis,
                    'Contrarion_Bonus': {'is_active': (contrarion_bonus > 0), 'points': contrarion_bonus},
                    'Confluence_Bonus': {'is_active': (confluence_bonus > 0), 'points': confluence_bonus}, 
                    'Entropy_Alert': {'is_active': (entropy_penalty > 0), 'points': entropy_penalty},
                    'Historic_Penalty': {
                        'is_active': is_historic_risk and market == 'TOTAL', 
                        'points': current_historic_penalty, 
                        'diff': abs(historic_move_diff) if market == 'TOTAL' else 0.0
                    },
                    'Historic_Conflict': {
                        'is_active': is_historic_conflict,
                        'points': historic_conflict_penalty,
                        'dominant_direction': historic_data['dominant_direction'] if historic_data and historic_data['is_significant'] else None,
                        'movement': historic_data['movement'] if historic_data else 0.0
                    }
                }
            }
            
        return scores

    def _build_confidence_matrix(self):
        """Construiește Matricea de Încredere V3."""
        score_data = self._calculate_score_components()
        self._score_data = score_data 
        
        return {key: data['Final_Score'] for key, data in score_data.items()}

    # =============================================================================
    # KLD BIDIMENSIONAL CORECT (V7.1 - Păstrat)
    # =============================================================================
    
    def _calculate_kl_divergence_FIXED(self):
        """
        Calculează Divergența KL CORECTĂ (bidimensională, per direcție).
        """
        kld_scores = {}
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
            if 'close' not in lines_data: continue

            if market == 'TOTAL':
                dir_keys = ('over', 'under')
                dir_names = ('OVER', 'UNDER')
            else:
                dir_keys = ('home', 'away')
                dir_names = ('HOME', 'AWAY')
            
            close_data = lines_data['close']
            
            p_open_1 = 1.0 / close_data.get(f'{dir_keys[0]}_open', 999) if close_data.get(f'{dir_keys[0]}_open', 999) > 1.0 else 0.0
            p_close_1 = 1.0 / close_data.get(f'{dir_keys[0]}_close', 999) if close_data.get(f'{dir_keys[0]}_close', 999) > 1.0 else 0.0
            p_open_2 = 1.0 / close_data.get(f'{dir_keys[1]}_open', 999) if close_data.get(f'{dir_keys[1]}_open', 999) > 1.0 else 0.0
            p_close_2 = 1.0 / close_data.get(f'{dir_keys[1]}_close', 999) if close_data.get(f'{dir_keys[1]}_close', 999) > 1.0 else 0.0
            
            kld1 = 0.0
            if p_open_1 > 0 and p_close_1 > 0:
                kld1 = p_close_1 * np.log(p_close_1 / p_open_1)
            
            kld2 = 0.0
            if p_open_2 > 0 and p_close_2 > 0:
                kld2 = p_close_2 * np.log(p_close_2 / p_open_2)
            
            if abs(kld1) > abs(kld2):
                max_kld = abs(kld1)
                dominant_direction = dir_names[0]
            else:
                max_kld = abs(kld2)
                dominant_direction = dir_names[1]
            
            kld_scores[market] = {
                dir_names[0]: kld1,
                dir_names[1]: kld2,
                'max': max_kld,
                'dominant_direction': dominant_direction
            }
            
        return kld_scores

    # =============================================================================
    # ✅ V7.3: LOGICA DE DECIZIE CU VERIFICARE ISTORIC
    # =============================================================================

    def _determine_v7_3_action(self, market_key):
        """
        Aplică Filtrele KLD Tri-Zone cu Override Logic îmbunătățit (V7.3).
        """
        
        market, direction = market_key.split('_')
        v3_score = self.confidence_matrix.get(market_key, 0)
        
        if v3_score < 50:
            return 'SKIP_V3_LOW_CONFIDENCE', 'Scor V3 sub 50'
        
        # NIVEL 0: Verificare Conflict Istoric (FORȚEAZĂ evaluare KLD)
        historic_data = self.historic_analysis.get(market)
        force_kld_evaluation = False
        
        if historic_data and historic_data['is_significant']:
            dominant_historic = historic_data['dominant_direction']
            if dominant_historic and dominant_historic != direction:
                force_kld_evaluation = True
        
        # NIVEL 1: Check Confluence Excepțional (doar dacă NU e conflict)
        if not force_kld_evaluation and v3_score >= 60:
            steam = self.steam_detection[market]
            gradient = self.gradient_analysis[market]['uniformity']
            consensus = self.consensus_score[market].get(direction, 0)
            
            steam_exceptional = (steam and steam['direction'] == direction and steam['strength'] >= 5)
            gradient_exceptional = (gradient > 95)
            consensus_safe = (consensus < self.CONSENSUS_OVERHEAT_THRESHOLD)
            historic_aligned = False
            
            if historic_data and historic_data['is_significant']:
                historic_aligned = (historic_data['dominant_direction'] == direction)
            else:
                historic_aligned = True  # Dacă nu e mișcare semnificativă, considerăm aliniat
            
            confluence_checks = [steam_exceptional, gradient_exceptional, consensus_safe, historic_aligned]
            confluence_count = sum(confluence_checks)
            
            if confluence_count >= 3:  # 3 din 4 criterii
                return 'KEEP_V3_OVERRIDE', f'Confluence {confluence_count}/4: Steam={steam_exceptional}, Gradient={gradient_exceptional}, Consensus Safe={consensus_safe}, Historic Aligned={historic_aligned}'
        
        # NIVEL 2: Evaluare KLD
        kld_data = self._kld_scores.get(market, {})
        kld_score = abs(kld_data.get(direction, 0.0))
        
        if kld_score <= self.KLD_THRESHOLD_SAFE:
            return 'KEEP_V3', f'KLD sigur ({kld_score:.4f})'
        
        elif self.KLD_THRESHOLD_SAFE < kld_score < self.KLD_THRESHOLD_SHOCK:
            return 'SKIP_KLD_MEDIUM_RISK', f'KLD zona neutră ({kld_score:.4f})'
        
        elif kld_score >= self.KLD_THRESHOLD_SHOCK:
            return 'INVERT_V3', f'KLD șoc ({kld_score:.4f})'
            
        return 'SKIP_DEFAULT', 'Nicio condiție îndeplinită'

    # =============================================================================
    # BUFFER SINCRONIZAT CU KLD (V7.1 - Păstrat)
    # =============================================================================

    def _select_optimal_line_FIXED(self, market_type, direction, v7_action):
        """
        Selectează linia finală și aplică Buffer-ul CORECT (după inversare KLD).
        """
        
        # 1. Determinare direcție finală (DUPĂ filtrare KLD)
        if v7_action == 'INVERT_V3':
            if market_type == 'TOTAL':
                final_direction = 'UNDER' if direction == 'OVER' else 'OVER'
            else:
                final_direction = 'AWAY' if direction == 'HOME' else 'HOME'
        else:
            final_direction = direction

        # 2. Selectare linie de bază (Steam sau Close)
        if market_type == 'TOTAL':
            lines_data = self.TOTAL_LINES
            steam = self.steam_detection['TOTAL']
        else:
            lines_data = self.HANDICAP_LINES
            steam = self.steam_detection['HANDICAP']
        
        dir_key_lower = final_direction.lower() + '_close'

        # Asigură-te că linia Close există
        if 'close' not in lines_data or dir_key_lower not in lines_data['close']:
            return {
                'line': 0.0,
                'line_original': 0.0,
                'cota': 0.0,
                'source': 'Date Invalide',
                'reason': 'Linia CLOSE lipsește sau este incompletă.',
                'final_direction': final_direction
            }

        original_line = lines_data['close']['line']
        cota = lines_data['close'][dir_key_lower]
        source = 'Close Line'
        
        if steam and steam['direction'] == final_direction:
            # Găsește linia cu cea mai mare mișcare Steam
            best_steam_line = max(steam['lines_affected'], key=lambda x: x['move'])
            
            # Găsește cheia corespunzătoare liniei (m3, p1 etc.)
            best_key = 'close'
            for key, data in lines_data.items():
                if abs(data['line'] - best_steam_line['line']) < 0.1:
                    best_key = key
                    break
            
            # Folosește linia și cota din cheia găsită
            original_line = lines_data[best_key]['line']
            cota = lines_data[best_key][dir_key_lower]
            source = f'Steam Line ({best_key.upper()})'
        
        # 3. ✅ APLICARE BUFFER PE DIRECȚIA FINALĂ
        if market_type == 'TOTAL':
            if final_direction == 'OVER':
                buffered_line = original_line + self.BUFFER_TOTAL_OVER
                buffer_reason = f'Buffer V7.3: {original_line:.1f} → {buffered_line:.1f} (OVER: L{self.BUFFER_TOTAL_OVER:+.1f})'
            else:
                buffered_line = original_line + self.BUFFER_TOTAL_UNDER
                buffer_reason = f'Buffer V7.3: {original_line:.1f} → {buffered_line:.1f} (UNDER: L{self.BUFFER_TOTAL_UNDER:+.1f})'
        
        else:
            # Pentru Handicap, buffer-ul este fix, aplicat liniei selectate
            buffered_line = original_line + self.BUFFER_HANDICAP
            buffer_reason = f'Buffer V7.3: {original_line:+.1f} → {buffered_line:+.1f} (Handicap: +{self.BUFFER_HANDICAP})'

        # 4. Verificare trap real pe linia finală (LOGICA DE RE-BUFFER)
        trap_analysis = self._score_data.get(f'{market_type}_{final_direction}', {}).get('Components', {}).get('Trap_Analysis', {})
        classification = trap_analysis.get('classification')
        
        if classification and classification['type'] == 'REAL':
            is_trap_on_original_line = False
            for flag in trap_analysis.get('flags', []):
                if abs(flag.get('line', -999) - original_line) < 0.1:
                    is_trap_on_original_line = True
                    break
            
            if is_trap_on_original_line:
                 # Dacă linia aleasă e un trap real, aplicăm buffer-ul pe linia Close originală
                buffered_line = lines_data['close']['line']
                if market_type == 'TOTAL':
                    buffered_line += self.BUFFER_TOTAL_OVER if final_direction == 'OVER' else self.BUFFER_TOTAL_UNDER
                else:
                    buffered_line += self.BUFFER_HANDICAP
                
                buffer_reason = f'TRAP REAL detectat pe linia aleasă → Revenire la Close cu buffer'
                original_line = lines_data['close']['line'] # Actualizează original line pentru afișare

        return {
            'line': round(buffered_line, 1),
            'line_original': round(original_line, 1),
            'cota': round(cota, 2),
            'source': source,
            'reason': buffer_reason,
            'final_direction': final_direction
        }

    def _select_final_decision(self):
        """
        Alege decizia finală, filtrată de KLD V7.3 cu verificare istoric.
        """
        
        max_confidence = 0.0
        best_key_v3 = 'SKIP'
        best_action = 'SKIP'
        best_reason = ''
        
        # Filtrează toate direcțiile care au scor >= 50
        candidates = []
        for key, score in self.confidence_matrix.items():
            if score >= 50.0:
                v7_action, reason = self._determine_v7_3_action(key)
                
                if v7_action in ['KEEP_V3', 'INVERT_V3', 'KEEP_V3_OVERRIDE']:
                    candidates.append({
                        'key': key,
                        'confidence': score,
                        'type': v7_action,
                        'reason': reason
                    })

        # Selectează cel mai mare scor dintre candidații validați
        if candidates:
            best_candidate = max(candidates, key=lambda x: x['confidence'])
            
            return {
                'key': best_candidate['key'], 
                'confidence': best_candidate['confidence'], 
                'type': best_candidate['type'],
                'reason': f'Decizie Hibrid V7.3: {best_candidate["type"]} | {best_candidate["reason"]}'
            }
        
        # Cazul SKIP (Nicio condiție îndeplinită)
        max_confidence_all = max(self.confidence_matrix.values()) if self.confidence_matrix else 0.0
        return {
            'key': 'SKIP', 
            'confidence': max_confidence_all, 
            'type': 'SKIP', 
            'reason': 'Încredere insuficientă (sub 50) sau filtrate de KLD.'
        }

# =============================================================================
# PARTEA 3/3 (FINAL) - CONTINUARE HybridAnalyzerV73
# Metode de afișare adaptate pentru a returna stringuri Markdown
# =============================================================================

    def generate_prediction_markdown(self):
        """Generează predicția finală V7.3 ca string Markdown."""
        
        output = []
        output.append(f"## 🏀 Analiză Hibrid V7.3 | **{self.HOME_TEAM} vs {self.AWAY_TEAM}** | {self.LEAGUE}")
        output.append("---")
        output.append("### 🔎 Sumar Analiză De Bază")
        
        output.extend(self._display_general_factors_markdown())
        
        final_decision = self._select_final_decision()
        
        if final_decision['type'].startswith('SKIP'):
            output.append("\n" + "---")
            output.append(f"## ❌ SKIP MECI")
            output.append(f"**Motiv:** {final_decision['reason']}")
            output.append(f"**Max Score V3:** {final_decision['confidence']:.1f}/100")
            output.append("---")
            return "\n".join(output)
            
        best_direction_key = final_decision['key']
        market, direction = best_direction_key.split('_')
        v7_action = final_decision['type']
        
        output.extend(self._display_decision_dashboard_markdown(best_direction_key, v7_action))
        
        optimal_line = self._select_optimal_line_FIXED(market, direction, v7_action) 
        final_direction = optimal_line['final_direction']
        
        output.append("\n" + "---")
        output.append(f"## 🏆 DECIZIE FINALĂ HIBRID V7.3: **{market} {final_direction}**")
        
        # Afișare KLD detaliat
        kld_data = self._kld_scores.get(market, {})
        kld_direction = abs(kld_data.get(direction, 0.0))
        output.append(f"* **Semnal V3 Inițial:** **{best_direction_key}** (Confidence: **{final_decision['confidence']:.1f}/100**)")
        output.append(f"* **Acțiune KLD:** `{v7_action}`")
        output.append(f"    * KLD **{direction}**: `{kld_direction:.4f}` (Prag Safe: `{self.KLD_THRESHOLD_SAFE}`, Shock: `{self.KLD_THRESHOLD_SHOCK}`)")
        
        if v7_action == 'INVERT_V3':
            output.append(f"    * ⚠️ **INVERSARE ACTIVĂ:** `{direction}` → `{final_direction}` (KLD ȘOC detectat)")
        elif v7_action == 'KEEP_V3_OVERRIDE':
            output.append(f"    * ✅ **OVERRIDE ACTIV:** KLD ignorat (Confluence excepțional)")
        
        # Afișare informații despre conflict istoric
        historic_data = self.historic_analysis.get(market)
        if historic_data and historic_data['is_significant']:
            output.append(f"\n### 📜 Analiza Istorică (Verificare Conflict)")
            output.append(f"* Linie Open: `{historic_data['open_line']:.1f}` | Linie Close: `{historic_data['close_line']:.1f}`")
            output.append(f"* Mișcare: `{historic_data['movement']:+.1f}` puncte")
            output.append(f"* Direcție Istorică Dominantă: **{historic_data['dominant_direction']}**")
            
            if historic_data['dominant_direction'] != final_direction:
                output.append(f"* 🚨 **ALERTĂ:** Conflict detectat! (Istoric: `{historic_data['dominant_direction']}` vs Final: `{final_direction}`)")
            else:
                output.append(f"* ✅ **Aliniere:** Direcția finală este aliniată cu mișcarea istorică.")

        output.append("\n### 💰 Propunere de Pariu")
        output.append(f"* **Linie Originală (fără buffer):** **{optimal_line['line_original']:.1f}**")
        output.append(f"* **Linie Jucată (cu buffer V7.3):** **{optimal_line['line']:.1f}**")
        output.append(f"* **Cota (Referință):** **{optimal_line['cota']:.2f}**")
        output.append(f"* **Sursă:** `{optimal_line['source']}`")
        output.append(f"* **Raționament Buffer:** `{optimal_line['reason']}`")
        output.append("---")
        
        # Salvarea datelor de decizie
        self._save_decision_data(market, direction, optimal_line, final_decision['type'], final_decision['confidence'])

        return "\n".join(output)

    def _display_general_factors_markdown(self):
        """Returnează factorii generali de analiză în format Markdown."""
        output = []
        
        output.append(f"#### 📊 Scor Consensus (0-100)")
        output.append(f"* **TOTAL:** **OVER={self.consensus_score['TOTAL']['OVER']:.1f}** | **UNDER={self.consensus_score['TOTAL']['UNDER']:.1f}**")
        output.append(f"* **HANDICAP:** **HOME={self.consensus_score['HANDICAP']['HOME']:.1f}** | **AWAY={self.consensus_score['HANDICAP']['AWAY']:.1f}**")
        
        if self.steam_detection['TOTAL'] or self.steam_detection['HANDICAP']:
            output.append(f"#### 🔥 Steam Detection (Sharp Money)")
        
        if self.steam_detection['TOTAL']:
            steam_t = self.steam_detection['TOTAL']
            output.append(f"* **TOTAL:** **{steam_t['direction']}** ({steam_t['strength']} linii, avg={steam_t['avg_move']:.3f})")
        if self.steam_detection['HANDICAP']:
            steam_h = self.steam_detection['HANDICAP']
            output.append(f"* **HANDICAP:** **{steam_h['direction']}** ({steam_h['strength']} linii, avg={steam_h['avg_move']:.3f})")
        
        output.append(f"#### 📈 Uniformitate Gradient")
        grad_t = self.gradient_analysis['TOTAL']
        grad_h = self.gradient_analysis['HANDICAP']
        output.append(f"* **TOTAL:** `{grad_t['uniformity']:.1f}/100`" + 
              (f" (**⚠️ Anomalii:** {len(grad_t['anomalies'])})" if grad_t['anomalies'] else ""))
        output.append(f"* **HANDICAP:** `{grad_h['uniformity']:.1f}/100`" + 
              (f" (**⚠️ Anomalii:** {len(grad_h['anomalies'])})" if grad_h['anomalies'] else ""))
        
        if self.manipulation_flags:
            output.append(f"#### 🚨 Flag-uri Manipulare (Trap Lines: {len(self.manipulation_flags)})")
            for flag in self.manipulation_flags:
                output.append(f"* **{flag['type']}:** Linie `{flag.get('line', 'N/A')}` Cota `{flag.get('cota', 'N/A')}`")
        
        output.append(f"#### 🧠 Alertă Entropie (Risc de Concentrare Cota)")
        if self.entropy_alerts['TOTAL']:
            alert = self.entropy_alerts['TOTAL']
            output.append(f"* **TOTAL:** **{alert['direction']}** - RISC CONCENTRARE (`{alert['entropy']:.2f}`). Penalizare -{self.PENALTY_ENTROPY}.")
        else:
            output.append("* **TOTAL:** Normal")
        if self.entropy_alerts['HANDICAP']:
            alert = self.entropy_alerts['HANDICAP']
            output.append(f"* **HANDICAP:** **{alert['direction']}** - RISC CONCENTRARE (`{alert['entropy']:.2f}`). Penalizare -{self.PENALTY_ENTROPY}.")
        else:
            output.append("* **HANDICAP:** Normal")
        
        output.append(f"#### 📜 Analiză Mișcare Istorică (V7.3)")
        for market in ['TOTAL', 'HANDICAP']:
            historic_data = self.historic_analysis.get(market)
            if historic_data and historic_data['open_line'] is not None:
                status = "**SEMNIFICATIV**" if historic_data['is_significant'] else "neutru"
                output.append(f"* **{market}:** Open `{historic_data['open_line']:.1f}` → Close `{historic_data['close_line']:.1f}`")
                output.append(f"    * Mișcare: `{historic_data['movement']:+.1f}` puncte ({status})")
                if historic_data['is_significant']:
                    output.append(f"    * Direcție Dominantă Istorică: **{historic_data['dominant_direction']}**")
            else:
                output.append(f"* **{market}:** Linie Open istorică indisponibilă")
             
        output.append(f"#### 🎯 Matrice Încredere V3 (0-100) - După Penalizări")
        for direction, score in self.confidence_matrix.items():
            status = "🟢 MARE" if score >= 70 else ("🟡 MEDIE" if score >= 50 else "🔴 SCĂZUTĂ")
            
            # Verifică conflict istoric
            market, dir_name = direction.split('_')
            historic_data = self.historic_analysis.get(market)
            conflict_marker = ""
            if historic_data and historic_data['is_significant'] and historic_data['dominant_direction'] != dir_name:
                conflict_marker = " ⚠️ CONFLICT"
            
            output.append(f"* **{direction}**: **{score:.1f}** ({status}){conflict_marker}")
        
        output.append(f"#### 🌡️ Scor KLD Bidimensional (Riscul Volatilității)")
        for market in ['TOTAL', 'HANDICAP']:
            kld_data = self._kld_scores.get(market, {})
            
            if market == 'TOTAL':
                dirs = ['OVER', 'UNDER']
            else:
                dirs = ['HOME', 'AWAY']
            
            output.append(f"* **{market}:**")
            for d in dirs:
                kld_val = abs(kld_data.get(d, 0.0))
                if kld_val <= self.KLD_THRESHOLD_SAFE:
                    zone = "🟢 SIGUR"
                elif kld_val < self.KLD_THRESHOLD_SHOCK:
                    zone = "🟡 NEUTRU"
                else:
                    zone = "🔴 ȘOC"
                output.append(f"    * **{d}**: `{kld_val:.4f}` ({zone})")
        
        return output

    def _display_decision_dashboard_markdown(self, best_direction_key, v7_action):
        """Afișează tabloul de bord detaliat pentru decizie în format Markdown."""
        data = self._score_data[best_direction_key]
        components = data['Components']
        market, direction = best_direction_key.split('_')
        output = []
        
        output.append(f"\n## 📊 Tablou de Bord Detaliat: **{best_direction_key}**")
        output.append(f"*(Ponderi: Consens x{self.WEIGHT_CONSENSUS}, Gradient x{self.WEIGHT_GRADIENT}, Steam +{self.BONUS_STEAM})*")
        
        output.append("\n### Puncte Bază și Bonusuri")
        
        output.append(f"* **1. Consens** ({components['Consensus']['score']:.1f}%): **+{components['Consensus']['points']:.1f}** puncte")
        output.append(f"* **2. Uniformitate Gradient** ({components['Gradient']['score']:.1f}%): **+{components['Gradient']['points']:.1f}** puncte")
        
        if components['Steam']['is_active']:
            steam_data = self.steam_detection[market]
            output.append(f"* **3. 🔥 STEAM Bonus:** (Pe {steam_data['strength']} linii, Avg Move: {steam_data['avg_move']:.3f}): **+{components['Steam']['points']:.1f}** puncte")
        else:
            output.append(f"* **3. Steam:** N/A (+0.0 puncte)")

        pen_trap = components['Trap_Analysis']['points']
        pen_entropy = components['Entropy_Alert']['points']
        pen_historic = components['Historic_Penalty']['points']
        pen_historic_conflict = components['Historic_Conflict']['points']
        bonus_contrarion = components['Contrarion_Bonus']['points']
        confluence_bonus = components['Confluence_Bonus']['points']
        
        if confluence_bonus > 0 or bonus_contrarion > 0:
            output.append(f"\n#### BONUSURI SPECIALE")
            if confluence_bonus > 0:
                output.append(f"* **⭐️ BONUS TRIPLE CHECK (V3.0.2):** **+{confluence_bonus:.1f}** puncte")
            if bonus_contrarion > 0 and confluence_bonus == 0:
                output.append(f"* **💰 BONUS CONTRARION:** **+{bonus_contrarion:.1f}** puncte")
        
        total_penalties = pen_trap + pen_entropy + pen_historic + pen_historic_conflict
        
        if total_penalties > 0:
            output.append(f"\n### Penalizări Totale: **-{total_penalties:.1f}** puncte")
            
            # Detalii Penalizări
            if pen_trap > 0 and components['Trap_Analysis']['classification']['type'] not in ["CONTRARION", "CONTRARION (V3.0.2 TC VALIDARE)"]:
                output.append(f"* **❌ Penalizare Trap:** **-{pen_trap:.1f}** puncte")
            
            if components['Historic_Penalty']['is_active']:
                hist = components['Historic_Penalty']
                output.append(f"* **❌ Penalizare ISTORICĂ (Instabilitate Linie):** **-{self.PENALTY_HISTORIC_MOVE}** puncte")
                output.append(f"    * Diferență Istorică: `{hist['diff']:.1f}` (Prag: `{self.THRESHOLD_HISTORIC_MOVE}`)")
            
            if components['Historic_Conflict']['is_active']:
                hist_conflict = components['Historic_Conflict']
                output.append(f"* **❌ PENALIZARE CONFLICT ISTORIC (V7.3):** **-{self.PENALTY_HISTORIC_CONFLICT}** puncte")
                output.append(f"    * Mișcare Istorică: `{hist_conflict['movement']:+.1f}` | Direcție Istorică: **{hist_conflict['dominant_direction']}**")
            
            if pen_entropy > 0:
                alert = self.entropy_alerts[market]
                output.append(f"* **❌ Alertă Entropie:** **-{pen_entropy:.1f}** puncte (Risc de concentrare `{alert['entropy']:.2f}`)")

        # Detalii Trap Line
        if components['Trap_Analysis']['flags']:
            output.append("\n### 🔍 Analiză Trap Line")
            classification = components['Trap_Analysis']['classification']
            
            if classification:
                output.append(f"* **CLASIFICARE:** **{classification['type']}** (Confidence: **{classification['confidence']:.1f}%**)")
                output.append(f"* **ACȚIUNE RECOMANDATĂ:** **{classification['action']}**")
                output.append(f"* **Raționament:** {classification['reasoning']}")
                
                if classification['type'] == 'REAL':
                    output.append(f"    * **⚠️ INTERPRETARE:** Trap autentic - **EVITĂ!**")
                elif classification['type'].startswith('CONTRARION'):
                    output.append(f"    * **💡 INTERPRETARE:** Trap-urile sunt CAPCANĂ pentru public! **JOACĂ CONTRA!**")
                elif classification['type'] == "REAL (V3.0.2 FORCED)":
                    output.append(f"    * **❌ INTERPRETARE:** Eșec Triple Check - **EVITĂ ABSOLUT!** (Penalizare -{self.PENALTY_V301_FORCED:.1f})")

        
        status = "🟢 MARE" if data['Final_Score'] >= 70 else ("🟡 MEDIE" if data['Final_Score'] >= 50 else "🔴 SCĂZUTĂ")
        output.append("\n" + "---")
        output.append(f"### **🎯 SCOR FINAL V3: {data['Final_Score']:.1f}/100 ({status})**")
        output.append(f"*(Acțiune KLD finală: **{v7_action}**)*")
        
        return output

    def _save_decision_data(self, market, direction_initial, optimal_line, decision_type, final_confidence):
        """Salvează datele de decizie în format structurat."""
        
        final_direction = optimal_line['final_direction']
        
        self.decision = {
            'League': self.LEAGUE,
            'HomeTeam': self.HOME_TEAM,
            'AwayTeam': self.AWAY_TEAM,
            'Data_Analiza_Salvare': datetime.now(),
            'Version': 'V7.3_HISTORIC_CHECK',
            'Decision_Type': decision_type,
            'Decision_Market': market,
            'Decision_Direction_Initial_V3': direction_initial,
            'Decision_Direction_Final': final_direction,
            'Decision_Line_BUFFERED': optimal_line['line'],
            'Decision_Line_ORIGINAL': optimal_line['line_original'],
            'Decision_Cota_REFERENCE': optimal_line['cota'],
            'Decision_Confidence_V3': final_confidence,
            'Decision_LineSource': optimal_line['source'],
            'Decision_Reason': optimal_line['reason'],
            'Historic_Analysis': self.historic_analysis,
            'KLD_Scores_Bidimensional': self._kld_scores,
            'Consensus_Score': self.consensus_score,
            'Confidence_Matrix_V3': self.confidence_matrix,
            'Fixes_Applied': {
                'FIX_1_Buffer_Sync': True,
                'FIX_2_KLD_Thresholds': {'SAFE': self.KLD_THRESHOLD_SAFE, 'SHOCK': self.KLD_THRESHOLD_SHOCK},
                'FIX_3_KLD_Bidimensional': True,
                'FIX_4_Historic_Conflict_Check': True
            },
            'All_Total_Lines': self.TOTAL_LINES,
            'All_Handicap_Lines': self.HANDICAP_LINES
        }
