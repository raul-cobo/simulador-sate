import statistics
import math
from typing import Dict, Any, List

class SAPERefinery:
    @staticmethod
    def refine_results(raw_scores: Dict[str, float], raw_sums: Dict[str, float] = None, limites: Dict[str, Dict[str, int]] = None) -> Dict[str, Any]:
        refined = raw_scores.copy()
        
        def clamp(value: float) -> float:
            return max(0.0, min(100.0, value))

        rasgos_keys = ['achievement', 'risk_propensity', 'ambiguity_tolerance', 
                       'self_efficacy', 'emotional_stability', 'autonomy', 
                       'locus_control', 'innovativeness']
        
        puntuaciones = [refined.get(k, 50.0) for k in rasgos_keys]
        
        # ==========================================
        # 1. MACRO-MÉTRICAS (Potencial, IRE, Fricción, Delta)
        # ==========================================
        
        # --- POTENCIAL EMPRENDEDOR ---
        # Calculamos la media. Penalizamos la inestabilidad usando la Desviación Típica (no la varianza bruta)
        media_potencial = sum(puntuaciones) / len(puntuaciones) if puntuaciones else 0.0
        desviacion_tipica = statistics.pstdev(puntuaciones) if len(puntuaciones) > 0 else 0.0
        
        # El potencial es la media, pero restando la mitad de su desviación para penalizar perfiles erráticos
        refined['potencial'] = round(clamp(media_potencial - (desviacion_tipica * 0.5)), 1)

        # --- ÍNDICE DE RESILIENCIA EVOLUTIVA (IRE) ---
        if raw_sums and limites:
            ires_rasgo = []
            for k in rasgos_keys:
                min_t = limites.get(k, {}).get('min', 0)
                max_t = limites.get(k, {}).get('max', 100)
                user_raw = raw_sums.get(k, min_t)
                
                # Puntuación percentil 90%
                p90 = min_t + 0.9 * (max_t - min_t)
                
                if p90 != 0:
                    ire_r = (user_raw / p90) * 100
                else:
                    ire_r = 0.0
                ires_rasgo.append(ire_r)
            
            ire_general = sum(ires_rasgo) / len(ires_rasgo) if ires_rasgo else 0
            refined['ire'] = round(clamp(ire_general), 1)
        else:
            # Fallback robusto si fallan los límites
            refined['ire'] = round(clamp(media_potencial * 0.9), 1)

        # --- FRICCIÓN (UNIFICADA) ---
        puntuacion_min = min(puntuaciones) if puntuaciones else 0
        puntuacion_max = max(puntuaciones) if puntuaciones else 100
        
        friccion_total = 0.0
        if puntuacion_max > 90.0:
            friccion_total += (puntuacion_max - refined['potencial'])
        if puntuacion_min < 50.0: # Ajustado a 50 para detectar cuellos de botella reales
            friccion_total += (refined['potencial'] - puntuacion_min)
            
        refined['friccion'] = round(clamp(friccion_total / 2), 1) # Lo promediamos para no asustar

        # --- DELTA ---
        # Diferencia entre el potencial actual y el perfil ideal (85)
        refined['delta'] = round(clamp(85.0 - refined['potencial']), 1)

        # ==========================================
        # 2. ESCÁNER DE DESCARRILADORES
        # ==========================================
        descarriladores = []
        for k in rasgos_keys:
            val = refined.get(k, 50.0)
            if val > 90.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Exceso', 'valor': val})
            elif val < 25.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Defecto', 'valor': val})
        refined['descarriladores'] = descarriladores

        # ==========================================
        # 3. FORTALEZAS Y ÁREAS DE DESARROLLO
        # ==========================================
        candidatos_fortalezas = [(k, v) for k, v in refined.items() if k in rasgos_keys and 70.0 <= v <= 90.0]
        candidatos_fortalezas.sort(key=lambda x: x[1], reverse=True)
        refined['fortalezas'] = candidatos_fortalezas[:3]

        candidatos_desarrollo = [(k, v) for k, v in refined.items() if k in rasgos_keys and v < 70.0]
        candidatos_desarrollo.sort(key=lambda x: x[1], reverse=True)
        refined['areas_desarrollo'] = candidatos_desarrollo[:3]

        # ==========================================
        # 4. PATRONES COMBINATORIOS
        # ==========================================
        patrones = []
        ach = refined.get('achievement', 50.0)
        risk = refined.get('risk_propensity', 50.0)
        inn = refined.get('innovativeness', 50.0)
        se = refined.get('self_efficacy', 50.0)
        aut = refined.get('autonomy', 50.0)
        es = refined.get('emotional_stability', 50.0)
        loc = refined.get('locus_control', 50.0)
        ta = refined.get('ambiguity_tolerance', 50.0)

        if ach > 80 and es < 40:
            patrones.append({"nombre": "Excitable", "combo": "ALTA Necesidad de Logro + BAJA Estabilidad Emocional", "desc": "Quiere ganar a toda costa, pero no aguanta la presión. Explota contra el equipo."})
        if se > 80 and loc < 40:
            patrones.append({"nombre": "Audaz/Arrogante", "combo": "ALTA Autoeficacia + BAJO Locus de Control", "desc": "Se cree un genio, pero cuando falla, culpa a otros. Es el perfil más tóxico para inversores."})
        if ta < 40 and risk < 40:
            patrones.append({"nombre": "Reservado/Cauto", "combo": "BAJA Tolerancia Incertidumbre + BAJA Propensión al Riesgo", "desc": "Ante una crisis, se esconde y pide informes. Mata la startup por inanición."})
        if inn > 80 and ach < 40:
            patrones.append({"nombre": "Histriónico/Imaginativo", "combo": "ALTA Innovatividad + BAJA Necesidad de Logro", "desc": "Todo es 'storytelling' y fiestas de lanzamiento, pero no hay producto ni ventas reales."})
        if ach > 80 and es < 40 and loc < 40:
            patrones.append({"nombre": "LIDERAZGO TÓXICO", "combo": "ALTA Necesidad de Logro + BAJA Estabilidad Emocional + BAJO Locus de Control", "desc": "El sujeto tiene una obsesión enfermiza por ganar, pero no tolera la frustración y cuando falla, siente que el mundo está en su contra."})
        if inn > 80 and se > 80 and ach < 40:
            patrones.append({"nombre": "IDEÓLOGO SIN ACCIÓN", "combo": "ALTA Innovatividad + ALTA Autoeficacia + BAJA Necesidad de Logro", "desc": "Tiene ideas brillantes y se cree un genio, pero no tiene disciplina para ejecutar el trabajo sucio."})
        if risk < 40 and aut < 40 and ach > 80:
            patrones.append({"nombre": "MICROMANAGER EXCESIVO", "combo": "BAJA Propensión al Riesgo + BAJA Autonomía + ALTA Necesidad de Logro", "desc": "Quiere que todo salga perfecto, pero le aterra equivocarse y no sabe actuar sin validación."})
        if risk > 80 and se > 80 and loc < 40:
            patrones.append({"nombre": "EXCESIVAMENTE ARRIESGADO", "combo": "ALTA Propensión al Riesgo + ALTA Autoeficacia + BAJO Locus de Control", "desc": "Le encanta la adrenalina, se cree invencible y si sale mal, piensa que fue mala suerte."})
        if inn < 40 and aut < 40 and es > 80:
            patrones.append({"nombre": "EJECUCIÓN MECÁNICA", "combo": "BAJA Innovatividad + BAJA Autonomía + ALTA Estabilidad Emocional", "desc": "Es muy resistente y trabaja duro, pero no tiene criterio propio ni ideas."})
        if ach < 40 and aut > 80 and loc < 40:
            patrones.append({"nombre": "RESISTENCIA PASIVA", "combo": "BAJA Necesidad de Logro + ALTA Autonomía + BAJO Locus de Control", "desc": "No quiere esforzarse demasiado, odia que le manden y culpa al sistema."})

        refined['patrones_clinicos'] = patrones
        return refined

    @staticmethod
    def get_clinical_flags(refined_data: Dict[str, Any]) -> List[str]:
        flags = []
        for d in refined_data.get('descarriladores', []):
            flags.append(f"🚨 Riesgo: El rasgo de {d['rasgo']} está en zona crítica ({d['valor']}%).")
        for p in refined_data.get('patrones_clinicos', []):
            flags.append(f"⚠️ PATRÓN: {p['nombre']}. {p['desc'][:90]}...")
        return flags