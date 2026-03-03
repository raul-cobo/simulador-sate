# logic_sapp_refinery.py
import pandas as pd
import re
from typing import Dict, Any, List

class SAPPRefinery:
    """
    Motor de cálculo y validación de Compliance para el SAPP 
    (Sistema de Análisis del Perfil Profesional).
    """

    # Competencias donde fallar implica un riesgo legal o clínico severo
    CRITICAL_COMPETENCIES = ["ethical_integrity", "risk_management", "health_records"]

    @staticmethod
    def calculate_raw_scores(respuestas_usuario: Dict[str, str], df_preguntas: pd.DataFrame) -> Dict[str, int]:
        """
        Parseador puro: Extrae la lógica del CSV ('OPCION_X_LOGIC') y suma los puntos.
        Ej: {'1': 'A', '2': 'C'} -> {'ethical_integrity': -1, 'health_records': 1}
        """
        scores = {}
        # Recorremos el DataFrame filtrado de las 40 preguntas exactas
        for idx, row in df_preguntas.iterrows():
            pregunta_id = str(row['ID'])
            letra_elegida = respuestas_usuario.get(pregunta_id)
            
            if letra_elegida:
                col_logic = f'OPCION_{letra_elegida}_LOGIC'
                logic_str = row.get(col_logic, "")
                
                if pd.notna(logic_str) and str(logic_str).strip() != "":
                    # Parsear cadenas como "ethical_integrity 1 | strategic_vision -1"
                    parts = str(logic_str).split('|')
                    for p in parts:
                        match = re.match(r"([a-zA-Z_]+)\s+(-?\d+)", p.strip())
                        if match:
                            trait = match.group(1)
                            val = int(match.group(2))
                            scores[trait] = scores.get(trait, 0) + val
        return scores

    @staticmethod
    def refine_results(raw_scores: Dict[str, int], grupo_evaluado: str) -> Dict[str, Any]:
        """
        Audita las puntuaciones brutas y determina si hay banderas rojas (Riesgo Crítico).
        """
        refined = raw_scores.copy()
        critical_flags = []
        is_apt = True

        # 1. Auditoría de Banderas Rojas
        if refined.get('ethical_integrity', 0) < 0:
            critical_flags.append({
                "competency": "Integridad Ética",
                "message": "Vulneración de principios éticos fundamentales (ej: confidencialidad)."
            })
            is_apt = False

        if refined.get('risk_management', 0) < 0:
            critical_flags.append({
                "competency": "Gestión de Riesgos",
                "message": "Negligencia detectada en el manejo de situaciones de crisis."
            })
            is_apt = False

        # 2. Empaquetado final
        return {
            "grupo_evaluado": grupo_evaluado,
            "puntuaciones_competencias": refined,
            "critical_flags": critical_flags,
            "global_compliance": is_apt,
            "total_score": sum(refined.values())
        }