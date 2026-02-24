import statistics
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
        
        # 1. MACRO-MÉTRICAS (Potencial, IRE, Fricción, Delta)
        
        # --- POTENCIAL: Media menos la varianza ---
        media_potencial = sum(puntuaciones) / len(puntuaciones)
        varianza = statistics.pvariance(puntuaciones) if len(puntuaciones) > 0 else 0.0
        refined['potencial'] = round(clamp(media_potencial - varianza), 1)

        # --- IRE: Distancia al Percentil 90 sectorial ---
        if raw_sums and limites:
            ires_rasgo = []
            for k in rasgos_keys:
                min_t = limites.get(k, {}).get('min', 0)
                max_t = limites.get(k, {}).get('max', 100)
                user_raw = raw_sums.get(k, min_t)
                
                # Puntuación percentil 90% = D7 + 0.9 * (E7 - D7)
                p90 = min_t + 0.9 * (max_t - min_t)
                
                # Aplicando la fórmula de la tabla: (Puntuación en crudo / P90) * 100
                if p90 != 0:
                    ire_r = (user_raw / p90) * 100
                else:
                    ire_r = 0.0
                ires_rasgo.append(ire_r)
            
            # Media de los IREs de todos los rasgos
            ire_general = sum(ires_rasgo) / len(ires_rasgo) if ires_rasgo else 0
            refined['ire'] = round(clamp(ire_general), 1)
        else:
            # Fallback de seguridad por si no llegan los datos brutos
            diferencias_ire = [abs(90.0 - p) for p in puntuaciones]
            media_diferencias = sum(diferencias_ire) / len(diferencias_ire)
            refined['ire'] = round(clamp(100.0 - media_diferencias), 1)

        # --- FRICCIONES ---
        puntuacion_min = min(puntuaciones)
        puntuacion_max = max(puntuaciones)
        
        if puntuacion_max > 90.0:
            refined['friccion_exceso'] = round(puntuacion_max - refined['potencial'], 1)
        else:
            refined['friccion_exceso'] = 0.0
            
        if puntuacion_min < 70.0:
            refined['friccion_defecto'] = round(refined['potencial'] - puntuacion_min, 1)
        else:
            refined['friccion_defecto'] = 0.0

        # --- DELTA: Distancia al P80 de los rasgos fuera de la zona óptima ---
        rasgos_desviados = [p for p in puntuaciones if p < 70.0 or p > 90.0]
        if rasgos_desviados:
            media_desviados = sum(rasgos_desviados) / len(rasgos_desviados)
            refined['delta'] = round(abs(80.0 - media_desviados), 1)
        else:
            refined['delta'] = 0.0

        # 2. ESCÁNER DE DESCARRILADORES
        descarriladores = []
        for k in rasgos_keys:
            val = refined.get(k, 50.0)
            if val > 90.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Exceso', 'valor': val})
            elif val < 25.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Defecto', 'valor': val})
        refined['descarriladores'] = descarriladores

        # 3. FORTALEZAS Y ÁREAS DE DESARROLLO (Frontera Óptima)
        candidatos_fortalezas = [(k, v) for k, v in refined.items() if k in rasgos_keys and 70.0 <= v <= 90.0]
        candidatos_fortalezas.sort(key=lambda x: x[1], reverse=True)
        refined['fortalezas'] = candidatos_fortalezas[:3]

        candidatos_desarrollo = [(k, v) for k, v in refined.items() if k in rasgos_keys and v < 70.0]
        candidatos_desarrollo.sort(key=lambda x: x[1], reverse=True)
        refined['areas_desarrollo'] = candidatos_desarrollo[:3]

        # 4. PATRONES COMBINATORIOS
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
            patrones.append({"nombre": "LIDERAZGO TÓXICO", "combo": "ALTA Necesidad de Logro + BAJA Estabilidad Emocional + BAJO Locus de Control", "desc": "El sujeto tiene una obsesión enfermiza por ganar, pero no tolera la frustración y cuando falla, siente que el mundo está en su contra. Descarriladores: EXCITABLE + ESCÉPTICO."})
        if inn > 80 and se > 80 and ach < 40:
            patrones.append({"nombre": "IDEÓLOGO SIN ACCIÓN", "combo": "ALTA Innovatividad + ALTA Autoeficacia + BAJA Necesidad de Logro", "desc": "Tiene ideas brillantes y se cree un genio, pero no tiene disciplina para ejecutar el trabajo sucio. Descarriladores: IMAGINATIVO + COLORIDO + ARROGANTE."})
        if risk < 40 and aut < 40 and ach > 80:
            patrones.append({"nombre": "MICROMANAGER EXCESIVO", "combo": "BAJA Propensión al Riesgo + BAJA Autonomía + ALTA Necesidad de Logro", "desc": "Quiere que todo salga perfecto, pero le aterra equivocarse y no sabe actuar sin validación. Descarriladores: DILIGENTE + CAUTO."})
        if risk > 80 and se > 80 and loc < 40:
            patrones.append({"nombre": "EXCESIVAMENTE ARRIESGADO", "combo": "ALTA Propensión al Riesgo + ALTA Autoeficacia + BAJO Locus de Control", "desc": "Le encanta la adrenalina, se cree invencible y si sale mal, piensa que fue mala suerte. Descarriladores: TRAVIESO/ASTUTO + ARROGANTE."})
        if inn < 40 and aut < 40 and es > 80:
            patrones.append({"nombre": "EJECUCIÓN MECÁNICA", "combo": "BAJA Innovatividad + BAJA Autonomía + ALTA Estabilidad Emocional", "desc": "Es muy resistente y trabaja duro, pero no tiene criterio propio ni ideas. Descarriladores: OBEDIENTE + RESERVADO."})
        if ach < 40 and aut > 80 and loc < 40:
            patrones.append({"nombre": "RESISTENCIA PASIVA", "combo": "BAJA Necesidad de Logro + ALTA Autonomía + BAJO Locus de Control", "desc": "No quiere esforzarse demasiado, odia que le manden y culpa al sistema. Descarrilador: PASIVO-AGRESIVO."})

        refined['patrones_clinicos'] = patrones
        return refined

    @staticmethod
    def get_clinical_flags(refined_data: Dict[str, Any]) -> List[str]:
        flags = []
        for d in refined_data.get('descarriladores', []):
            flags.append(f"🚨 Riesgo de Bloqueo/Descarrilamiento: El rasgo de {d['rasgo']} está en zona crítica ({d['valor']}%).")
        for p in refined_data.get('patrones_clinicos', []):
            flags.append(f"⚠️ PATRÓN DETECTADO: {p['nombre']}. {p['desc'][:100]}...")
        return flags