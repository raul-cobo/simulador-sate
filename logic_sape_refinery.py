from typing import Dict, Any, List

class SAPERefinery:
    """
    Motor de refinamiento psicométrico para la prueba SAPE.
    Calcula Clústeres, IRE, Fricción, Delta y escanea Descarriladores.
    """

    @staticmethod
    def refine_results(raw_scores: Dict[str, float]) -> Dict[str, Any]:
        refined = raw_scores.copy()
        
        def clamp(value: float) -> float:
            return max(0.0, min(100.0, value))
            
        n_ach = refined.get('achievement', 50.0)
        risk = refined.get('risk_propensity', 50.0)
        ta = refined.get('ambiguity_tolerance', 50.0)
        se = refined.get('self_efficacy', 50.0)
        es = refined.get('emotional_stability', 50.0)
        autonomy = refined.get('autonomy', 50.0)
        loc = refined.get('locus_control', 50.0)
        innov = refined.get('innovativeness', 50.0)

        # ==========================================================
        # 1. CÁLCULO DE MACRO-MÉTRICAS AUDEO (IRE, FRICCIÓN, DELTA)
        # ==========================================================
        
        rasgos_keys = ['achievement', 'risk_propensity', 'ambiguity_tolerance', 
                       'self_efficacy', 'emotional_stability', 'autonomy', 
                       'locus_control', 'innovativeness']
        
        puntuaciones = [refined.get(k, 50.0) for k in rasgos_keys]
        
        # --- A. IRE (Índice de Resiliencia Emprendedora) ---
        # Mide la distancia absoluta respecto al 90%. Los excesos (>90) y defectos (<90) RESTAN.
        diferencias_ire = [abs(90.0 - p) for p in puntuaciones]
        media_diferencias = sum(diferencias_ire) / len(diferencias_ire)
        refined['ire'] = round(clamp(100.0 - media_diferencias), 1)

        # --- B. FRICCIÓN (Defecto y Exceso) ---
        media_rasgos = sum(puntuaciones) / len(puntuaciones)
        puntuacion_min = min(puntuaciones)
        puntuacion_max = max(puntuaciones)
        
        refined['friccion_defecto'] = round(media_rasgos - puntuacion_min, 1)
        refined['friccion_exceso'] = round(puntuacion_max - media_rasgos, 1)

        # --- C. DELTA ---
        # Frontera estricta: Busca los rasgos que están por debajo de 70 o por encima de 90
        rasgos_desviados = [p for p in puntuaciones if p < 70.0 or p > 90.0]
        if rasgos_desviados:
            media_desviados = sum(rasgos_desviados) / len(rasgos_desviados)
            refined['delta'] = round(abs(80.0 - media_desviados), 1) # Diferencia respecto a la media óptima (80)
        else:
            refined['delta'] = 0.0 # Perfil perfectamente encajado en la zona 70-90

        # ==========================================================
        # 2. ESCÁNER DE DESCARRILADORES
        # ==========================================================
        descarriladores = []
        for k in rasgos_keys:
            val = refined.get(k, 50.0)
            if val > 90.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Exceso', 'valor': val})
            elif val < 25.0:
                descarriladores.append({'rasgo': k, 'tipo': 'Defecto', 'valor': val})
                
        refined['descarriladores'] = descarriladores

        return refined

    @staticmethod
    def get_clinical_flags(refined_data: Dict[str, Any]) -> List[str]:
        """
        Extrae advertencias cualitativas formateadas para el panel de consultoría o PDF.
        """
        flags = []
        
        # Banderas de descarriladores
        descarriladores = refined_data.get('descarriladores', [])
        for d in descarriladores:
            if d['tipo'] == 'Exceso':
                flags.append(f"🚨 Riesgo de Descarrilamiento (Exceso): El rasgo de {d['rasgo']} es excesivamente alto ({d['valor']}%). Podría generar fricción severa.")
            elif d['tipo'] == 'Defecto':
                flags.append(f"🛑 Riesgo de Bloqueo (Defecto): El rasgo de {d['rasgo']} es críticamente bajo ({d['valor']}%). Requiere compensación externa urgente.")
                
        return flags