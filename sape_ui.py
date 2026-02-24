import pandas as pd
import random
import asyncio
import pdf_generator
import datetime
from typing import Dict, Any, List
from nicegui import ui, app

from logic_sape_refinery import SAPERefinery
from ui_results import render_dashboard_resultados

# --- CONSTANTES DE ESTILO ---
BG_COLOR = "#0E1117"
ACCENT_COLOR = "#83ABF1"

class SAPEInterface:
    def __init__(self, df_path: str, sector: str, supabase_client=None):
        self.df_path = df_path
        self.sector = sector
        self.supabase = supabase_client
        
        df_completo = pd.read_csv(self.df_path, sep=';', encoding='utf-8')
        self.df_sector = df_completo[df_completo['SECTOR'] == self.sector].reset_index(drop=True)
        self.total_preguntas = len(self.df_sector)
        
        self.current_idx = 0
        self.respuestas_usuario: Dict[str, str] = {}
        self.opciones_mezcladas: List[tuple] = []
        self.limites_sector = self._calcular_limites_sector()
        self._preparar_opciones_actuales()

    def _calcular_limites_sector(self) -> Dict[str, Dict[str, int]]:
        limites = {}
        for _, row in self.df_sector.iterrows():
            q_data = {}
            for letra in ['A', 'B', 'C', 'D']:
                logic = str(row.get(f'OPCION_{letra}_LOGIC', ''))
                if logic and str(logic).strip() not in ['nan', '', '0']:
                    for regla in logic.split('|'):
                        partes = regla.strip().split()
                        if len(partes) >= 2:
                            dim, val = partes[0], int(partes[1])
                            if dim not in q_data: q_data[dim] = []
                            q_data[dim].append(val)
            for dim, valores in q_data.items():
                if dim not in limites: limites[dim] = {'max': 0, 'min': 0}
                limites[dim]['max'] += max(valores + [0])
                limites[dim]['min'] += min(valores + [0])
        return limites

    def _calcular_brutos_reales(self) -> Dict[str, float]:
        sumas_brutas = {}
        for q_id, letra in self.respuestas_usuario.items():
            fila = self.df_sector[self.df_sector['ID'].astype(str) == str(q_id)] if 'ID' in self.df_sector.columns else self.df_sector.iloc[[int(q_id)]]
            if fila.empty: continue
            logic = str(fila.iloc[0].get(f'OPCION_{letra}_LOGIC', ''))
            if logic and str(logic).strip() not in ['nan', '', '0']:
                for regla in logic.split('|'):
                    partes = regla.strip().split()
                    if len(partes) >= 2:
                        dim, val = partes[0], int(partes[1])
                        sumas_brutas[dim] = sumas_brutas.get(dim, 0) + val
        
        scores = {}
        for dim, suma in sumas_brutas.items():
            if dim in self.limites_sector:
                rango = self.limites_sector[dim]['max'] - self.limites_sector[dim]['min']
                val_norm = ((suma - self.limites_sector[dim]['min']) / rango) * 100 if rango != 0 else 50.0
                scores[dim] = round(max(0.0, min(100.0, val_norm)), 1)
        return scores

    def _preparar_opciones_actuales(self):
        if self.current_idx >= self.total_preguntas: return
        fila = self.df_sector.iloc[self.current_idx]
        opciones = [(fila.get(f'OPCION_{l}_TXT'), l) for l in ['A', 'B', 'C', 'D'] if pd.notna(fila.get(f'OPCION_{l}_TXT'))]
        random.shuffle(opciones)
        self.opciones_mezcladas = opciones

    async def _handle_click(self, letra_original: str):
        p_id = str(self.df_sector.iloc[self.current_idx]['ID'] if 'ID' in self.df_sector.columns else self.current_idx)
        self.respuestas_usuario[p_id] = letra_original
        self.current_idx += 1
        if self.current_idx < self.total_preguntas:
            self._preparar_opciones_actuales()
            self.render_layout.refresh() 
            self.header_progress.refresh()
        else:
            await self._finalizar_test()

    async def _finalizar_test(self):
        # 1. Cálculos e IA
        raw_scores = self._calcular_brutos_reales() 
        datos_refinados = SAPERefinery.refine_results(raw_scores)
        username = app.storage.user.get('username', 'anonimo')
        org_id = app.storage.user.get('org_id', 'generica')

        # 2. Guardado en Supabase
        if self.supabase:
            try:
                payload = {"user_id": username, "org_id": org_id, "test_type": "SAPE", "sector": self.sector, "status": "completed", "results": datos_refinados, "raw_answers": self.respuestas_usuario}
                self.supabase.table("evaluations").insert(payload).execute()
            except Exception as e: print(f"⚠️ Error BD: {e}")

        # 3. Limpieza y Renderizado ÚNICO
        self.header_contenedor.clear()
        self.contenedor_principal.clear()
        with self.contenedor_principal:
            render_dashboard_resultados(
                datos_refinados, 
                callback_pdf=lambda: self._descargar_pdf(datos_refinados, username, org_id)
            )

    async def _descargar_pdf(self, datos, user, org):
        try:
            ui.notify('Generando informe...', type='info')
            demograficos = {'org': org, 'sector': self.sector, 'fecha': datetime.datetime.now().strftime("%d/%m/%Y")}
            ruta = pdf_generator.generar_pdf_sape(user, datos, SAPERefinery.get_clinical_flags(datos), demograficos)
            ui.download(ruta)
        except Exception as e:
            ui.notify(f'Error: {e}', type='negative')

    @ui.refreshable
    def header_progress(self):
        with ui.row().classes('w-full items-center justify-between p-6'):
            ui.image('logo_blanco.png').classes('w-48')
            with ui.column().classes('w-1/3 items-end gap-1'):
                mes = min(self.current_idx + 1, self.total_preguntas)
                ui.label(f"Mes {mes} de {self.total_preguntas}").classes('text-white font-semibold')
                ui.linear_progress(value=mes/self.total_preguntas, color=ACCENT_COLOR).classes('h-2 w-full rounded-full')

    @ui.refreshable
    def render_layout(self):
        if self.current_idx >= len(self.df_sector): return
        fila = self.df_sector.iloc[self.current_idx]
        with ui.row().classes('w-full max-w-7xl mx-auto flex-1 items-stretch pt-10 gap-12 px-6 flex-nowrap'):
            with ui.column().classes('w-[55%] flex flex-col gap-6 justify-center pb-20'):
                ui.label(fila.get('TITULO', 'Sin Título')).classes(f'text-4xl font-black text-[{ACCENT_COLOR}]')
                ui.label(fila.get('NARRATIVA', '...')).classes('text-2xl text-white font-light')
            with ui.column().classes('w-[45%] flex flex-col justify-center gap-6 pb-20'):
                for txt, letra in self.opciones_mezcladas:
                    btn = ui.button(on_click=lambda l=letra: self._handle_click(l))
                    btn.style('background-color: #0D248D; color: white;')
                    btn.classes('w-full text-left p-6 rounded-xl hover:scale-[1.02] transition-all')
                    with btn: ui.label(txt).classes('text-lg font-medium text-white')

    def render(self):
        ui.query('body').style(f'background-color: {BG_COLOR}; margin: 0;')
        self.header_contenedor = ui.row().classes('w-full')
        with self.header_contenedor: self.header_progress()
        self.contenedor_principal = ui.column().classes('w-full min-h-[90vh]')
        with self.contenedor_principal: self.render_layout()