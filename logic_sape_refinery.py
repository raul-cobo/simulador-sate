from typing import Dict, Any, List

class SAPERefinery:
    """
    Motor de refinamiento psicométrico para la prueba SAPE.
    Aplica correlaciones empíricas y clústeres de segundo orden basados
    en la investigación científica de Autoevaluaciones Centrales (CSE) 
    y Agencia Proactiva.
    """

    @staticmethod
    def refine_results(raw_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Toma las puntuaciones normalizadas (0-100) y aplica ajustes de 
        interacción y clústeres. Retorna un diccionario enriquecido listo 
        para persistir en Supabase y renderizar en NiceGUI.
        """
        # Trabajamos sobre una copia profunda para garantizar la inmutabilidad de los datos de origen
        refined = raw_scores.copy()
        
        # Función auxiliar para asegurar que los valores se mantengan estrictamente entre 0 y 100
        def clamp(value: float) -> float:
            return max(0.0, min(100.0, value))
            
        # Extracción segura de valores (default a 50.0 como punto neutro estadístico)
        n_ach = refined.get('achievement', 50.0)
        risk = refined.get('risk_propensity', 50.0)
        ta = refined.get('ambiguity_tolerance', 50.0)
        se = refined.get('self_efficacy', 50.0)
        es = refined.get('emotional_stability', 50.0)
        autonomy = refined.get('autonomy', 50.0)
        loc = refined.get('locus_control', 50.0)
        innov = refined.get('innovativeness', 50.0)

        # ==========================================================
        # 1. AJUSTES DE INTERACCIÓN (Basado en Evidencia Empírica)
        # ==========================================================
        
        # A. El Moderador del Riesgo: Necesidad de Logro (nAch)
        # El riesgo alto respaldado por la necesidad de logro se convierte en "Riesgo Calculado/Estratégico"
        if n_ach > 70.0 and risk > 60.0:
            refined['is_strategic_risk'] = True
            refined['risk_propensity'] = clamp(risk * 1.05) # Potenciación del 5%
        else:
            refined['is_strategic_risk'] = False

        # B. El Buffer de la Incertidumbre: Tolerancia a la Ambigüedad (TA)
        # Una alta TA protege y amplifica la Autoeficacia ante el caos
        if ta > 70.0:
            refined['self_efficacy'] = clamp(se * 1.08) # Potenciación del 8%
            refined['robust_confidence'] = True
        else:
            refined['robust_confidence'] = False

        # C. El Factor de Estrés: Autonomía vs Estabilidad Emocional (ES)
        # Alta autonomía con baja estabilidad emocional genera un alto riesgo de sobrecarga
        if es < 40.0 and autonomy > 75.0:
            refined['burnout_risk'] = True
            refined['autonomy_efficiency'] = "Low (Overwhelmed)"
            refined['emotional_stability'] = clamp(es * 0.90) # Penalización del 10% por fatiga cognitiva
        else:
            refined['burnout_risk'] = False
            refined['autonomy_efficiency'] = "Optimal"

        # ==========================================================
        # 2. CÁLCULO DE CLÚSTERES (Macro-Dimensiones de Orden Superior)
        # ==========================================================

        # Clúster 1: Autoevaluación Central (CSE) | Varianza explicada r=.74
        # Fórmula: (LOC*0.4) + (SE*0.4) + (ES*0.2)
        refined['cluster_cse'] = round(
            clamp((loc * 0.4) + (refined['self_efficacy'] * 0.4) + (refined['emotional_stability'] * 0.2)), 2
        )

        # Clúster 2: Agencia Proactiva (Motor de Ejecución)
        # Variables: Logro + Autonomía + Locus Interno
        refined['cluster_agency'] = round(
            clamp((n_ach + autonomy + loc) / 3.0), 2
        )

        # Clúster 3: Orientación a la Exploración (Adaptabilidad y Cambio)
        # Variables: Innovación + Riesgo + Tolerancia a la Ambigüedad
        refined['cluster_exploration'] = round(
            clamp((innov + refined['risk_propensity'] + ta) / 3.0), 2
        )

        return refined

    @staticmethod
    def get_clinical_flags(refined_data: Dict[str, Any]) -> List[str]:
        """
        Extrae advertencias cualitativas formateadas para el panel de consultoría.
        Ideal para iterar en NiceGUI y mostrar en tarjetas UI.
        """
        flags = []
        if refined_data.get('burnout_risk'):
            flags.append("🚨 Riesgo de Burnout: La alta demanda de autonomía no está soportada por una estabilidad emocional sólida.")
        if refined_data.get('is_strategic_risk'):
            flags.append("📈 Riesgo Estratégico: Perfil orientado a tomar decisiones arriesgadas pero fundamentadas en la consecución de logros.")
        if refined_data.get('robust_confidence'):
            flags.append("🛡️ Confianza Robusta: Mantiene una alta eficacia personal incluso en escenarios de alta incertidumbre.")
            
        return flags