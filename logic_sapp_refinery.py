# logic_sapp_refinery.py
import pandas as pd

class SAPPRefinery:
    
    @staticmethod
    def calculate_raw_scores(user_responses: dict, df_preguntas: pd.DataFrame) -> dict:
        """
        Calcula la puntuación bruta sumando y restando los valores exactos
        definidos en las columnas lógicas del Excel.
        """
        scores = {}
        
        for index, row in df_preguntas.iterrows():
            q_id = str(row['ID'])
            if q_id in user_responses:
                letra_elegida = user_responses[q_id]
                col_logic = f'OPCION_{letra_elegida}_LOGIC'
                logic_val = row.get(col_logic)
                
                # Si la opción tiene lógica (ej: "ethical_integrity 1" o "ethical_integrity -1")
                if pd.notna(logic_val) and str(logic_val).strip() != "":
                    partes = str(logic_val).strip().split()
                    if len(partes) == 2:
                        competencia = partes[0]
                        try:
                            valor = int(partes[1])
                            # Sumamos o restamos el valor a la competencia
                            scores[competencia] = scores.get(competencia, 0) + valor
                        except ValueError:
                            pass
                            
        return scores

    @staticmethod
    def refine_results(raw_scores: dict, grupo_seleccionado: str) -> dict:
        """
        Transforma la puntuación bruta (-10 a 10) en un porcentaje (-100% a 100%).
        """
        refined_competencies = {}
        
        for comp, score in raw_scores.items():
            # Regla: 10 puntos = 100%. Por tanto, multiplicamos por 10.
            porcentaje = score * 10
            
            # Limitamos por seguridad entre -100 y 100
            porcentaje = max(-100, min(100, porcentaje))
            
            refined_competencies[comp] = {
                'raw_score': score,
                'percentage': porcentaje
            }
            
        return {
            'module': grupo_seleccionado,
            'competencies': refined_competencies
        }