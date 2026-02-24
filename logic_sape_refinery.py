from typing import Dict, Any, List

class SAPERefinery:
    """
    Motor de refinamiento psicométrico para la prueba SAPE.
    Calcula IRE, Fricción, Delta, Fortalezas/Áreas de Mejora y Patrones Combinatorios Clínicos.
    """

    @staticmethod
    def refine_results(raw_scores: Dict[str, float]) -> Dict[str, Any]:
        refined = raw_scores.copy()
        
        def clamp(value: float) -> float:
            return max(0.0, min(100.0, value))

        rasgos_keys = ['achievement', 'risk_propensity', 'ambiguity_tolerance', 
                       'self_efficacy', 'emotional_stability', 'autonomy', 
                       'locus_control', 'innovativeness']
        
        puntuaciones = [refined.get(k, 50.0) for k in rasgos_keys]
        
        # ==========================================================
        # 1. CÁLCULO DE MACRO-MÉTRICAS (Potencial, IRE, Fricción, Delta)
        # ==========================================================
        # Potencial (Media basal)
        refined['potencial'] = round(sum(puntuaciones) / len(puntuaciones), 1)

        # IRE
        diferencias_ire = [abs(90.0 - p) for p in puntuaciones]
        media_diferencias = sum(diferencias_ire) / len(diferencias_ire)
        refined['ire'] = round(clamp(100.0 - media_diferencias), 1)

        # Fricción
        puntuacion_min = min(puntuaciones)
        puntuacion_max = max(puntuaciones)
        refined['friccion_defecto'] = round(refined['potencial'] - puntuacion_min, 1)
        refined['friccion_exceso'] = round(puntuacion_max - refined['potencial'], 1)

        # Delta
        rasgos_desviados = [p for p in puntuaciones if p < 70.0 or p > 90.0]
        if rasgos_desviados:
            media_desviados = sum(rasgos_desviados) / len(rasgos_desviados)
            refined['delta'] = round(abs(80.0 - media_desviados), 1)
        else:
            refined['delta'] = 0.0

        # ==========================================================
        # 2. ESCÁNER DE DESCARRILADORES SIMPLES
        # ==========================================================
        descarriladores = []
        for k in rasgos_keys:
            val = refined.get(k, 50.0)
            if val > 90.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Exceso', 'valor': val})
            elif val < 25.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Defecto', 'valor': val})
        refined['descarriladores'] = descarriladores

        # ==========================================================
        # 3. FORTALEZAS Y ÁREAS DE DESARROLLO
        # ==========================================================
        # Fortalezas: Top 3 valores entre 70 y 90 (o los más altos por debajo de 90)
        candidatos_fortalezas = [(k, v) for k, v in refined.items() if k in rasgos_keys and v <= 90.0]
        candidatos_fortalezas.sort(key=lambda x: x[1], reverse=True)
        refined['fortalezas'] = candidatos_fortalezas[:3]

        # Áreas de Desarrollo: Top 3 valores más altos que no superen el 70%
        candidatos_desarrollo = [(k, v) for k, v in refined.items() if k in rasgos_keys and v <= 70.0]
        candidatos_desarrollo.sort(key=lambda x: x[1], reverse=True)
        refined['areas_desarrollo'] = candidatos_desarrollo[:3]

        # ==========================================================
        # 4. MOTOR DE PATRONES COMBINATORIOS Y EXTREMOS
        # ==========================================================
        patrones = []
        
        ach = refined.get('achievement', 50.0)
        risk = refined.get('risk_propensity', 50.0)
        inn = refined.get('innovativeness', 50.0)
        se = refined.get('self_efficacy', 50.0)
        aut = refined.get('autonomy', 50.0)
        es = refined.get('emotional_stability', 50.0)
        loc = refined.get('locus_control', 50.0)
        ta = refined.get('ambiguity_tolerance', 50.0)

        # 4.1 Patrones Combinatorios Básicos
        if ach > 80 and es < 40:
            patrones.append({
                "nombre": "Excitable",
                "combo": "ALTA Necesidad de Logro + BAJA Estabilidad Emocional",
                "desc": "Quiere ganar a toda costa, pero no aguanta la presión. Explota contra el equipo."
            })
        if se > 80 and loc < 40:
            patrones.append({
                "nombre": "Audaz/Arrogante",
                "combo": "ALTA Autoeficacia + BAJO Locus de Control",
                "desc": "Se cree un genio, pero cuando falla, culpa a otros. Es el perfil más tóxico para inversores."
            })
        if ta < 40 and risk < 40:
            patrones.append({
                "nombre": "Reservado/Cauto",
                "combo": "BAJA Tolerancia Incertidumbre + BAJA Propensión al Riesgo",
                "desc": "Ante una crisis, se esconde y pide informes. Mata la startup por inanición."
            })
        if inn > 80 and ach < 40:
            patrones.append({
                "nombre": "Histriónico/Imaginativo",
                "combo": "ALTA Innovatividad + BAJA Necesidad de Logro",
                "desc": "Todo es 'storytelling' y fiestas de lanzamiento, pero no hay producto ni ventas reales."
            })

        # 4.2 Interacciones Combinatorias Extremas
        if ach > 80 and es < 40 and loc < 40:
            patrones.append({
                "nombre": "LIDERAZGO TÓXICO",
                "combo": "ALTA Necesidad de Logro + BAJA Estabilidad Emocional + BAJO Locus de Control",
                "desc": "El sujeto tiene una obsesión enfermiza por ganar, pero no tolera la frustración y cuando falla, siente que el mundo está en su contra. Descarriladores: EXCITABLE (Estallidos de ira) + ESCÉPTICO (Paranoia)."
            })
        if inn > 80 and se > 80 and ach < 40:
            patrones.append({
                "nombre": "IDEÓLOGO SIN ACCIÓN",
                "combo": "ALTA Innovatividad + ALTA Autoeficacia + BAJA Necesidad de Logro",
                "desc": "Tiene ideas brillantes y se cree un genio, pero no tiene disciplina para ejecutar el trabajo sucio. Descarriladores: IMAGINATIVO (Ideas sin base) + COLORIDO (Necesita ser el centro) + ARROGANTE."
            })
        if risk < 40 and aut < 40 and ach > 80:
            patrones.append({
                "nombre": "MICROMANAGER EXCESIVO",
                "combo": "BAJA Propensión al Riesgo + BAJA Autonomía + ALTA Necesidad de Logro",
                "desc": "Quiere que todo salga perfecto, pero le aterra equivocarse y no sabe actuar sin validación. Controla cada milímetro para evitar el miedo. Descarriladores: DILIGENTE (Perfeccionismo) + CAUTO."
            })
        if risk > 80 and se > 80 and loc < 40:
            patrones.append({
                "nombre": "EXCESIVAMENTE ARRIESGADO",
                "combo": "ALTA Propensión al Riesgo + ALTA Autoeficacia + BAJO Locus de Control",
                "desc": "Le encanta la adrenalina, se cree invencible y si sale mal, piensa que fue mala suerte. No tiene freno moral. Descarriladores: TRAVIESO/ASTUTO (Cruza líneas éticas) + ARROGANTE."
            })
        if inn < 40 and aut < 40 and es > 80:
            patrones.append({
                "nombre": "EJECUCIÓN MECÁNICA",
                "combo": "BAJA Innovatividad + BAJA Autonomía + ALTA Estabilidad Emocional",
                "desc": "Es muy resistente y trabaja duro, pero no tiene criterio propio ni ideas. Es la herramienta perfecta para un socio tóxico, pero un pésimo CEO. Descarriladores: OBEDIENTE + RESERVADO."
            })
        if ach < 40 and aut > 80 and loc < 40:
            patrones.append({
                "nombre": "RESISTENCIA PASIVA",
                "combo": "BAJA Necesidad de Logro + ALTA Autonomía + BAJO Locus de Control",
                "desc": "No quiere esforzarse demasiado, odia que le manden y culpa al sistema de su falta de éxito. Descarrilador: PASIVO-AGRESIVO (Boicotea plazos y crea mal ambiente)."
            })

        refined['patrones_clinicos'] = patrones

        return refined

    @staticmethod
    def get_clinical_flags(refined_data: Dict[str, Any]) -> List[str]:
        """Extrae advertencias cualitativas para el panel web."""
        flags = []
        descarriladores = refined_data.get('descarriladores', [])
        for d in descarriladores:
            if d['tipo'] == 'Exceso':
                flags.append(f"🚨 Riesgo de Descarrilamiento: El rasgo de {d['rasgo']} es excesivamente alto ({d['valor']}%).")
            elif d['tipo'] == 'Defecto':
                flags.append(f"🛑 Riesgo de Bloqueo: El rasgo de {d['rasgo']} es críticamente bajo ({d['valor']}%).")
                
        patrones = refined_data.get('patrones_clinicos', [])
        for p in patrones:
            flags.append(f"⚠️ PATRÓN DETECTADO: {p['nombre']}. {p['desc'][:100]}...")
            
        return flags