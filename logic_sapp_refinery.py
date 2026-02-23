import pandas as pd
from typing import Dict, Any, List, Tuple

class SAPPRefinery:
    """
    Motor de cálculo y validación de Compliance para el SAPP 
    (Sistema de Análisis del Perfil Profesional).
    Basado en el Modelo del Cubo de Competencias (Rodolfa et al.).
    """

    # --- CONSTANTES DE ARQUITECTURA (Documento Maestro) ---
    COMPETENCY_GROUPS = {
        "personal": ["therapeutic_alliance", "reflective_practice", "ethical_integrity", "professionalism"],
        "professional": ["case_formulation", "differential_diagnosis", "evidence_based_treatment", "risk_management"],
        "technical": ["clinical_psychometrics", "diagnostic_manuals", "health_records", "telepractice"]
    }

    # Competencias donde fallar implica un riesgo legal o clínico severo
    CRITICAL_COMPETENCIES = ["ethical_integrity", "risk_management", "health_records"]

    @staticmethod
    def calculate_raw_scores(respuestas_usuario: Dict[str, str], df_preguntas: pd.DataFrame) -> Dict[str, int]:
        """
        Parseador puro: Extrae la lógica del CSV ('OPCION_X_LOGIC') y suma los puntos.
        Ej: {'1': 'A', '2': 'C'} -> {'ethical_integrity': -1, 'health_records': 1}
        """
        resultados = {}
        df = df_preguntas.copy()
        df['ID'] = df['ID'].astype(str)

        for q_id, letra in respuestas_usuario.items():
            fila = df[df['ID'] == str(q_id)]
            if fila.empty: 
                continue
            
            logica = fila.iloc[0].get(f'OPCION_{letra}_LOGIC')
            if pd.notna(logica) and str(logica).strip() not in ['0', 'nan', '']:
                # Soporta cadenas múltiples ej: "ethical_integrity -1 | professionalism 1"
                for regla in str(logica).split('|'):
                    partes = regla.strip().split()
                    if len(partes) >= 2:
                        comp_id = partes[0]
                        val = int(partes[1])
                        resultados[comp_id] = resultados.get(comp_id, 0) + val
                        
        return resultados

    @staticmethod
    def evaluate_compliance(raw_scores: Dict[str, int]) -> Dict[str, Any]:
        """
        Evalúa las puntuaciones brutas generando el Mapa de Especialidad 
        y disparando Red Flags (Negligencias) si se violan las líneas rojas.
        """
        refined = raw_scores.copy()
        
        # 1. CÁLCULO POR BLOQUES (Cubo de Rodolfa)
        # Sumamos los puntos obtenidos en cada uno de los 3 ejes fundamentales
        block_scores = {
            "personal_score": sum(refined.get(c, 0) for c in SAPPRefinery.COMPETENCY_GROUPS["personal"]),
            "professional_score": sum(refined.get(c, 0) for c in SAPPRefinery.COMPETENCY_GROUPS["professional"]),
            "technical_score": sum(refined.get(c, 0) for c in SAPPRefinery.COMPETENCY_GROUPS["technical"])
        }
        refined.update(block_scores)

        # 2. VALIDACIÓN DE LÍNEAS ROJAS (Red Flags)
        # En el SAPP, las puntuaciones negativas en áreas críticas son inaceptables
        critical_flags = []
        is_apt = True # Se asume apto hasta que se demuestre lo contrario

        if refined.get('ethical_integrity', 0) < 0:
            critical_flags.append({
                "competency": "Integridad Ética",
                "severity": "CRITICAL",
                "message": "Vulneración de principios éticos fundamentales (ej: confidencialidad, límites)."
            })
            is_apt = False

        if refined.get('risk_management', 0) < 0:
            critical_flags.append({
                "competency": "Gestión de Riesgos",
                "severity": "CRITICAL",
                "message": "Negligencia detectada en el manejo de situaciones de crisis o riesgo vital."
            })
            is_apt = False

        if refined.get('health_records', 0) < 0:
            critical_flags.append({
                "competency": "Registros de Salud",
                "severity": "HIGH",
                "message": "Malas prácticas en la protección de datos e historia clínica electrónica."
            })
            is_apt = False # Dependiendo de tu criterio, esto podría no suspender, pero lo marcamos como grave.

        refined['critical_flags'] = critical_flags
        refined['global_compliance'] = is_apt

        # 3. IDENTIFICACIÓN DE FORTALEZAS (Para el informe positivo)
        # Si un usuario tiene más de 2 puntos en una competencia, es un "Punto Fuerte"
        strengths = [comp for comp, score in raw_scores.items() if score >= 2]
        refined['key_strengths'] = strengths

        return refined