import csv
import os

# CONFIGURACIÓN
VARIABLE_MAP = {
    "Logro": "achievement",
    "Riesgo": "risk_propensity",
    "Innovatividad": "innovativeness",
    "Locus": "locus_control",
    "Autoeficacia": "self_efficacy",
    "Autonomía": "autonomy",
    "Tolerancia Incertidumbre": "ambiguity_tolerance",
    "Estabilidad": "emotional_stability",
    # Descarriladores
    "Excitable": "excitable", "Escéptico": "skeptical", "Cauto": "cautious",
    "Reservado": "reserved", "Pasivo-Agresivo": "passive_aggressive",
    "Arrogante": "arrogant", "Travieso": "mischievous", "Astuto": "mischievous", 
    "Mercenario": "mischievous", "Mentiroso": "mischievous", "Corrupto": "mischievous",
    "Colorido": "melodramatic", "Histriónico": "melodramatic", "Imaginativo": "imaginative",
    "Diligente": "diligent", "Obediente": "dependent", "Dependiente": "dependent",
    "Psicópata": "reserved"
}

class SATE_Engine:
    def __init__(self):
        self.octagon = {k: 50 for k in set(VARIABLE_MAP.values()) if k not in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "imaginative", "diligent", "dependent"]}
        self.flags = {k: 0 for k in ["excitable", "skeptical", "cautious", "reserved", "passive_aggressive", "arrogant", "mischievous", "melodramatic", "imaginative", "diligent", "dependent"]}

    def parse_logic(self, logic_str):
        if not logic_str: return
        actions = logic_str.split('|')
        for action in actions:
            parts = action.strip().split()
            if len(parts) < 2: continue
            term = parts[0]
            try: val = int(parts[1])
            except ValueError: continue
            
            var_key = None
            for map_key, map_val in VARIABLE_MAP.items():
                if map_key in term: var_key = map_val; break
            
            if var_key:
                if var_key in self.flags:
                    if val > 0: self.flags[var_key] += val
                elif var_key in self.octagon:
                    self.octagon[var_key] = max(0, min(100, self.octagon[var_key] + val))

    def calculate_results(self):
        avg_octagon = sum(self.octagon.values()) / 8
        total_flags = sum(self.flags.values())
        triggers = []
        if self.octagon["achievement"] > 80 and self.octagon["emotional_stability"] < 30: triggers.append("TIRANO INSEGURO")
        if self.octagon["innovativeness"] > 80 and self.octagon["achievement"] < 40: triggers.append("FALSO PROFETA")
        if self.octagon["risk_propensity"] > 80 and self.octagon["locus_control"] < 40: triggers.append("LUDÓPATA")
        
        ire = avg_octagon - (total_flags * 3) - (len(triggers) * 15)
        return {"IRE": round(ire, 2), "Octagon_Avg": round(avg_octagon, 2), "Flags_Count": total_flags, "Cocktails": triggers}

def run():
    os.system('cls' if os.name == 'nt' else 'clear')
    engine = SATE_Engine()
    print("--- PRUEBA DE ESFUERZO S.A.T.E. v1 ---\n")
    
    try:
        with open('SATE_v1.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                print(f"[{row['ID']}] {row['TITULO'].upper()}\n{row['NARRATIVA']}\n")
                print(f"[A] {row['OPCION_A_TXT']}\n[B] {row['OPCION_B_TXT']}")
                if row.get('OPCION_C_TXT'): print(f"[C] {row['OPCION_C_TXT']}")
                
                while True:
                    choice = input("\n>> Tu decisión (A/B/C): ").upper().strip()
                    if choice in ['A', 'B', 'C']:
                        logic = row[f'OPCION_{choice}_LOGIC']
                        engine.parse_logic(logic)
                        break
                print("\n" + "-"*30 + "\n")
    except FileNotFoundError:
        print("ERROR: No encuentro el archivo SATE_v1.csv"); return

    res = engine.calculate_results()
    print(f"RESULTADO FINAL (IRE): {res['IRE']} / 100")
    print(f"Banderas Rojas: {res['Flags_Count']}")
    if res['Cocktails']: print(f"ALERTAS: {res['Cocktails']}")
    input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    run()