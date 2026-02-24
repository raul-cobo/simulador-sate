import pandas as pd
import re

def parse_logic(logic_str):
    if not logic_str or str(logic_str).lower() == 'nan': return {}
    return {m: int(v) for m, v in re.findall(r'([a-zA-Z_]+)\s+(-?\d+)', str(logic_str))}

def format_logic(logic_dict):
    if not logic_dict: return ""
    return " | ".join([f"{k} {v}" for k, v in logic_dict.items() if v != 0])

print("⏳ Leyendo Prueba_SAPE.csv original...")
df = pd.read_csv('Prueba_SAPE.csv', sep=';', encoding='utf-8')

print("⚙️ Aplicando reglas clínicas de correlación...")
for idx, row in df.iterrows():
    for l in ['A', 'B', 'C', 'D']:
        col = f'OPCION_{l}_LOGIC'
        logic = parse_logic(row[col])
        if not logic: continue
        
        new_logic = logic.copy()
        
        if logic.get('locus_control', 0) > 0:
            new_logic['autonomy'] = new_logic.get('autonomy', 0) + max(1, logic['locus_control'])
            new_logic['achievement'] = new_logic.get('achievement', 0) + max(1, logic['locus_control'])
            
        if logic.get('risk_propensity', 0) > 0:
            new_logic['ambiguity_tolerance'] = new_logic.get('ambiguity_tolerance', 0) + max(1, logic['risk_propensity'] // 2)
            
        if logic.get('self_efficacy', 0) > 0:
            new_logic['locus_control'] = new_logic.get('locus_control', 0) + max(1, int(logic['self_efficacy'] * 0.8))
            new_logic['autonomy'] = new_logic.get('autonomy', 0) + max(1, int(logic['self_efficacy'] * 0.8))

        if logic.get('autonomy', 0) > 0:
            new_logic['self_efficacy'] = new_logic.get('self_efficacy', 0) + max(1, int(logic['autonomy'] * 0.8))
        elif logic.get('autonomy', 0) < 0:
            new_logic['self_efficacy'] = new_logic.get('self_efficacy', 0) + logic['autonomy']
            
        if logic.get('emotional_stability', 0) > 0:
            new_logic['risk_propensity'] = new_logic.get('risk_propensity', 0) + logic['emotional_stability']
            new_logic['ambiguity_tolerance'] = new_logic.get('ambiguity_tolerance', 0) + max(1, logic['emotional_stability'] // 2)
            
        if logic.get('innovativeness', 0) > 0:
            new_logic['autonomy'] = new_logic.get('autonomy', 0) + max(1, logic['innovativeness'] // 2)
            
        if logic.get('ambiguity_tolerance', 0) > 0:
            new_logic['risk_propensity'] = new_logic.get('risk_propensity', 0) + logic['ambiguity_tolerance']
        elif logic.get('ambiguity_tolerance', 0) < 0:
            new_logic['risk_propensity'] = new_logic.get('risk_propensity', 0) + logic['ambiguity_tolerance']
            
        df.at[idx, col] = format_logic(new_logic)

df.to_csv('Prueba_SAPE_Corregido.csv', sep=';', index=False, encoding='utf-8')
print("✅ ¡ÉXITO! Archivo 'Prueba_SAPE_Corregido.csv' generado en tu carpeta.")