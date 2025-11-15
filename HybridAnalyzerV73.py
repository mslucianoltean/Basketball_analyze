import json
from datetime import datetime
import numpy as np
import math
import sys
import os

# =============================================================================
# CLASA PRINCIPALĂ DE ANALIZĂ HIBRIDĂ (V7.3 - VERIFICARE ISTORIC)
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
        self.THRESHOLD_HISTORIC_CONFLICT = 2.0 # Mișcare semnificativă (puncte)
        self.PENALTY_HISTORIC_CONFLICT = 30.0 # Penalizare pentru conflict
        self.CONSENSUS_OVERHEAT_THRESHOLD = 65.0 # Consensus supraîncălzit
        
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
                
                if line_data[f'{dir_keys[0]}_close'] < 1.85: score1 += 3
                if line_data[f'{dir_keys[1]}_close'] < 1.85: score2 += 3
                
                move1 = line_data[f'{dir_keys[0]}_open'] - line_data[f'{dir_keys[0]}_close']
                move2 = line_data[f'{dir_keys[1]}_open'] - line_data[f'{dir_keys[1]}_close']
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
                move1 = d[f'{dir_keys[0]}_open'] - d[f'{dir_keys[0]}_close']
                move2 = d[f'{dir_keys[1]}_open'] - d[f'{dir_keys[1]}_close']
                
                if move1 > STEAM_THRESHOLD: moves1.append({'line': d['line'], 'move': move1})
                if move2 > STEAM_THRESHOLD: moves2.append({'line': d['line'], 'move': move2})
            
            if len(moves1) >= 3: 
                steam[market] = {
                    'direction': dir_names[0], 
                    'strength': len(moves1), 
                    'avg_move': np.mean([m['move'] for m in moves1]), 
                    'lines_affected': moves1
                }
            elif len(moves2) >= 3: 
                steam[market] = {
                    'direction': dir_names[1], 
                    'strength': len(moves2), 
                    'avg_move': np.mean([m['move'] for m in moves2]), 
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
                
            closes1 = [lines_data[k][f'{dir_keys[0]}_close'] for k in LINE_ORDER]
            closes2 = [lines_data[k][f'{dir_keys[1]}_close'] for k in LINE_ORDER]
            
            diffs1 = np.diff(closes1)
            diffs2 = np.diff(closes2)
            std1, std2 = np.std(diffs1), np.std(diffs2)
            gradient[market]['uniformity'] = max(0, 100 - (std1 + std2) * 100)
            
            for i, diff in enumerate(diffs1):
                if abs(diff) > 0.15: 
                    gradient[market]['anomalies'].append({
                        'type': dir_names[0], 
                        'between': f"{LINE_ORDER[i]} și {LINE_ORDER[i+1]}", 
                        'diff': diff
                    })
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
            close_data = lines_data['close']
            if market == 'TOTAL':
                dir_keys = ('over', 'under')
                dir_names = ('TOTAL_OVER', 'TOTAL_UNDER')
            else:
                dir_keys = ('home', 'away')
                dir_names = ('HANDICAP_HOME', 'HANDICAP_AWAY')
            
            for line_key in LINE_KEYS:
                line_data = lines_data[line_key]
                
                if line_data[f'{dir_keys[0]}_close'] < close_data[f'{dir_keys[0]}_close'] - 0.20:
                    flags.append({
                        'type': f'TRAP_LINE_{dir_names[0]}', 
                        'line': line_data['line'], 
                        'cota': line_data[f'{dir_keys[0]}_close'], 
                        'vs_close': close_data[f'{dir_keys[0]}_close'], 
                        'severity': 'HIGH',
                        'move_open_close': round(line_data[f'{dir_keys[0]}_open'] - line_data[f'{dir_keys[0]}_close'], 3)
                    })
                
                if line_data[f'{dir_keys[1]}_close'] < close_data[f'{dir_keys[1]}_close'] - 0.20:
                    flags.append({
                        'type': f'TRAP_LINE_{dir_names[1]}', 
                        'line': line_data['line'], 
                        'cota': line_data[f'{dir_keys[1]}_close'], 
                        'vs_close': close_data[f'{dir_keys[1]}_close'], 
                        'severity': 'HIGH',
                        'move_open_close': round(line_data[f'{dir_keys[1]}_open'] - line_data[f'{dir_keys[1]}_close'], 3)
                    })
        
        return flags
        
    def _calculate_shannon_entropy(self, probabilities):
        """Calculează entropia Shannon."""
        probabilities = [p for p in probabilities if p > 0]
        if not probabilities: return 0.0
        total_sum = sum(probabilities)
        if total_sum == 0: return 0.0
        norm_probs = [p / total_sum for p in probabilities]
        entropy = -sum(p * math.log2(p) for p in norm_probs) 
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

            probs1 = [1.0 / lines_data[k][f'{dir_keys[0]}_close'] for k in LINE_ORDER]
            probs2 = [1.0 / lines_data[k][f'{dir_keys[1]}_close'] for k in LINE_ORDER]
            entropy1 = self._calculate_shannon_entropy(probs1)
            entropy2 = self._calculate_shannon_entropy(probs2)
            
            if self.consensus_score[market][dir_names[0]] > self.consensus_score[market][dir_names[1]] and entropy1 < ECC_THRESHOLD:
                alerts[market] = {'direction': dir_names[0], 'entropy': entropy1}
            elif self.consensus_score[market][dir_names[1]] > self.consensus_score[market][dir_names[0]] and entropy2 < ECC_THRESHOLD:
                alerts[market] = {'direction': dir_names[1], 'entropy': entropy2}

        return alerts
    
    def _analyze_historic_movement(self):
        """
        Analizează mișcarea istorică a liniei și identifică direcția dominantă inițială.
        """
        historic = {}
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
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
                    dominant_direction = 'UNDER' if market == 'TOTAL' else 'AWAY'
                elif movement < -self.THRESHOLD_HISTORIC_CONFLICT:
                    # Linia a coborât → Banii inițiali pe OVER
                    dominant_direction = 'OVER' if market == 'TOTAL' else 'HOME'
                else:
                    dominant_direction = None # Mișcare neutră
                
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
        
        return historic

    def _classify_trap_nature(self, trap_flags, market, direction):
        """Clasifică natura trap-ului: REAL (evită) sau CONTRARION (joacă contra)."""
        if not trap_flags:
            return None
        
        consensus_score = self.consensus_score[market][direction]
        steam_data = self.steam_detection[market]
        gradient_uniformity = self.gradient_analysis[market]['uniformity']
        entropy_alert = self.entropy_alerts[market]
        
        has_steam_on_trap = (steam_data and steam_data['direction'] == direction)
        steam_strength = steam_data['strength'] if has_steam_on_trap else 0
        
        historic_move = 0.0
        if market == 'TOTAL':
            try:
                open_line = self.TOTAL_LINES['close'].get('open_line_value')
                close_line = self.TOTAL_LINES['close']['line']
                if open_line is not None:
                    historic_move = abs(open_line - close_line)
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

    def _calculate_score_components(self):
        """
        Calculează componentele scorului pentru fiecare direcție (V7.3 logic cu Verificare Istoric).
        """
        scores = {}
        historic_penalty_applied = 0
        historic_move_diff = 0.0
        is_historic_risk = False
        is_historic_aligned_with_direction = False
        
        try:
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
            cons_score = self.consensus_score[market][direction]
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

            if market == 'TOTAL':
                current_historic_penalty = historic_penalty_applied
                
                is_historic_aligned_with_direction = \
                    (historic_move_diff > 0 and direction == 'OVER') or \
                    (historic_move_diff < 0 and direction == 'UNDER')
                
                if contrarion_bonus > 0 and is_historic_risk and is_historic_aligned_with_direction and is_steam:
                    if uniformity >= self.GRADIENT_CONFLUENCE_THRESHOLD:
                        confluence_bonus = self.BONUS_CONFLUENCE_TRIPLE_CHECK
                        current_historic_penalty = 0 
                        trap_analysis['recommended_action'] = f"🎯 JOACĂ CONTRA (V3.0.2 TC VALIDARE)"
                    else:
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

    def _calculate_kl_divergence_FIXED(self):
        """
        Calculează Divergența KL CORECTĂ (bidimensională, per direcție).
        """
        kld_scores = {}
        
        for market, lines_data in [('TOTAL', self.TOTAL_LINES), ('HANDICAP', self.HANDICAP_LINES)]:
            if market == 'TOTAL':
                dir_keys = ('over', 'under')
                dir_names = ('OVER', 'UNDER')
            else:
                dir_keys = ('home', 'away')
                dir_names = ('HOME', 'AWAY')
            
            close_data = lines_data['close']
            
            p_open_1 = 1.0 / close_data[f'{dir_keys[0]}_open']
            p_close_1 = 1.0 / close_data[f'{dir_keys[0]}_close']
            p_open_2 = 1.0 / close_data[f'{dir_keys[1]}_open']
            p_close_2 = 1.0 / close_data[f'{dir_keys[1]}_close']
            
            if p_open_1 > 0 and p_close_1 > 0:
                kld1 = p_close_1 * np.log(p_close_1 / p_open_1)
            else:
                kld1 = 0.0
                
            if p_open_2 > 0 and p_close_2 > 0:
                kld2 = p_close_2 * np.log(p_close_2 / p_open_2)
            else:
                kld2 = 0.0
            
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
            consensus = self.consensus_score[market][direction]
            
            steam_exceptional = (steam and steam['direction'] == direction and steam['strength'] >= 5)
            gradient_exceptional = (gradient > 95)
            consensus_safe = (consensus < self.CONSENSUS_OVERHEAT_THRESHOLD)
            historic_aligned = False
            
            if historic_data and historic_data['is_significant']:
                historic_aligned = (historic_data['dominant_direction'] == direction)
            else:
                historic_aligned = True # Dacă nu e mișcare semnificativă, considerăm aliniat
            
            confluence_checks = [steam_exceptional, gradient_exceptional, consensus_safe, historic_aligned]
            confluence_count = sum(confluence_checks)
            
            if confluence_count >= 3: # 3 din 4 criterii
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
            dir_key_lower = final_direction.lower() + '_close'
        else:
            lines_data = self.HANDICAP_LINES
            steam = self.steam_detection['HANDICAP']
            dir_key_lower = final_direction.lower() + '_close'
        
        original_line = lines_data['close']['line']
        cota = lines_data['close'][dir_key_lower]
        source = 'Close Line'
        
        if steam and steam['direction'] == final_direction:
            best_steam_line = max(steam['lines_affected'], key=lambda x: x['move'])
            
            for key, data in lines_data.items():
                if abs(data['line'] - best_steam_line['line']) < 0.1:
                    original_line = data['line']
                    cota = data[dir_key_lower]
                    source = f'Steam Line ({key.upper()})'
                    break
        
        # 3. ✅ APLICARE BUFFER PE DIRECȚIA FINALĂ
        if market_type == 'TOTAL':
            if final_direction == 'OVER':
                buffered_line = original_line + self.BUFFER_TOTAL_OVER
                buffer_reason = f'Buffer V7.3: {original_line:.1f} → {buffered_line:.1f} (OVER: L-5)'
            else:
                buffered_line = original_line + self.BUFFER_TOTAL_UNDER
                buffer_reason = f'Buffer V7.3: {original_line:.1f} → {buffered_line:.1f} (UNDER: L+7)'
        
        else:
            if original_line < 0:
                buffered_line = original_line + self.BUFFER_HANDICAP
            else:
                buffered_line = original_line + self.BUFFER_HANDICAP
            
            buffer_reason = f'Buffer V7.3: {original_line:.1f} → {buffered_line:.1f} (Handicap: +{self.BUFFER_HANDICAP})'

        # 4. Verificare trap real pe linia finală
        trap_analysis = self._score_data.get(f'{market_type}_{final_direction}', {}).get('Components', {}).get('Trap_Analysis', {})
        classification = trap_analysis.get('classification')
        
        if classification and classification['type'] == 'REAL':
            for flag in trap_analysis.get('flags', []):
                if abs(flag.get('line', -999) - original_line) < 0.1:
                    buffered_line = lines_data['close']['line']
                    if market_type == 'TOTAL':
                        buffered_line += self.BUFFER_TOTAL_OVER if final_direction == 'OVER' else self.BUFFER_TOTAL_UNDER
                    else:
                        buffered_line += self.BUFFER_HANDICAP
                    
                    buffer_reason = f'TRAP REAL detectat → Revenire la Close cu buffer'
                    break

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
        
        for key, score in self.confidence_matrix.items():
            if score >= 50.0:
                v7_action, reason = self._determine_v7_3_action(key)
                
                if v7_action in ['KEEP_V3', 'INVERT_V3', 'KEEP_V3_OVERRIDE']:
                    final_confidence = score
                    
                    if final_confidence > max_confidence:
                        max_confidence = final_confidence
                        best_key_v3 = key 
                        best_action = v7_action
                        best_reason = reason
        
        if max_confidence > 0.0:
            return {
                'key': best_key_v3, 
                'confidence': max_confidence, 
                'type': best_action,
                'reason': f'Decizie Hibrid V7.3: {best_action} | {best_reason}'
            }
        
        max_confidence_all = max(self.confidence_matrix.values())
        return {
            'key': 'SKIP', 
            'confidence': max_confidence_all, 
            'type': 'SKIP', 
            'reason': 'Încredere insuficientă sau filtrate de KLD.'
        }

    def generate_prediction(self):
        """Generează și returnează predicția finală V7.3."""
        
        final_decision = self._select_final_decision()
        
        if final_decision['type'].startswith('SKIP'):
            return {
                'decision': 'SKIP',
                'reason': final_decision['reason'],
                'confidence': final_decision['confidence'],
                'details': {}
            }
            
        best_direction_key = final_decision['key']
        market, direction = best_direction_key.split('_')
        v7_action = final_decision['type']
        
        optimal_line = self._select_optimal_line_FIXED(market, direction, v7_action) 
        final_direction = optimal_line['final_direction']
        
        # Construire rezultat detaliat
        result = {
            'decision': 'PLAY',
            'market': market,
            'direction_initial': direction,
            'direction_final': final_direction,
            'line_original': optimal_line['line_original'],
            'line_buffered': optimal_line['line'],
            'cota': optimal_line['cota'],
            'source': optimal_line['source'],
            'reason': optimal_line['reason'],
            'confidence': final_decision['confidence'],
            'v7_action': v7_action,
            'details': {
                'consensus_score': self.consensus_score,
                'steam_detection': self.steam_detection,
                'gradient_analysis': self.gradient_analysis,
                'manipulation_flags': self.manipulation_flags,
                'entropy_alerts': self.entropy_alerts,
                'historic_analysis': self.historic_analysis,
                'kld_scores': self._kld_scores,
                'confidence_matrix': self.confidence_matrix,
                'score_data': self._score_data
            }
        }
        
        self._save_decision_data(market, direction, optimal_line, final_decision['type'], final_decision['confidence'])
        return result

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
            'All_Total_Lines': self.TOTAL_LINES,
            'All_Handicap_Lines': self.HANDICAP_LINES
        }
