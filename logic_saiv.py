import pandas as pd
from typing import Dict, Any

class SAIVRefinery:
    @staticmethod
    def refine_results(raw_responses: Dict[str, int], df_preguntas: pd.DataFrame) -> Dict[str, Any]:
        """
        Procesa las respuestas del test SAIV, calcula las puntuaciones de las 6 dimensiones
        (invirtiendo los ítems necesarios) y genera el código vocacional (Top 3).
        """
        # Mapeo de siglas Audeo al modelo Holland (RIASEC)
        mapping = {
            'T': 'Realista (Técnico)',
            'C': 'Investigador (Científico)',
            'A': 'Artístico',
            'S': 'Social',
            'E': 'Emprendedor',
            'O': 'Convencional (Organizativo)'
        }
        
        # Inicializamos contadores
        scores = {k: 0 for k in mapping.keys()}
        counts = {k: 0 for k in mapping.keys()}
        
        # Procesar cada respuesta enviada por el usuario
        for item_id, value in raw_responses.items():
            # Buscar la fila correspondiente en el CSV
            row = df_preguntas[df_preguntas['id'] == item_id]
            if row.empty: 
                continue
                
            var = str(row.iloc[0]['VARIABLE']).strip().upper()
            if var not in scores:
                continue # Por si hay algún error en el CSV
                
            is_inverse = str(row.iloc[0]['ES_INVERSA']).strip().lower() in ['sí', 'si', 'yes', 'true', '1']
            
            # Ajustar valor si la pregunta es inversa (Escala 1 a 5)
            # Si responde 5 (Muy interesante) en una inversa, se convierte en 1.
            final_value = (6 - int(value)) if is_inverse else int(value)
            
            scores[var] += final_value
            counts[var] += 1
            
        # Calcular métricas refinadas (porcentajes)
        refined_metrics = {}
        for var, name in mapping.items():
            max_puntos = counts[var] * 5 # El valor máximo posible es responder 5 a todas
            
            if max_puntos > 0:
                percentage = round((scores[var] / max_puntos) * 100, 1)
            else:
                percentage = 0.0
                
            refined_metrics[var] = {
                "nombre": name,
                "percentage": percentage,
                "raw_score": scores[var],
                "items_count": counts[var]
            }
            
        # Determinar el código RIASEC ordenando de mayor a menor porcentaje
        # En caso de empate, el orden natural del diccionario actuará de desempate
        sorted_vars = sorted(refined_metrics.items(), key=lambda x: x[1]['percentage'], reverse=True)
        
        # Tomar las 3 letras predominantes
        riasec_code = "".join([v[0] for v in sorted_vars[:3]])
        top_interests = [v[1]['nombre'] for v in sorted_vars[:3]]
        
        return {
            "metrics": refined_metrics,
            "riasec_code": riasec_code,
            "top_interests": top_interests
        }