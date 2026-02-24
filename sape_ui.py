import pandas as pd
import random
import asyncio
import pdf_generator
import datetime
from typing import Dict, Any, List
from nicegui import ui, app

from logic_sape_refinery import SAPERefinery
from ui_results import render_dashboard_resultados

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

    # CAMBIO 1: Ahora devolvemos una tupla con los scores y las sumas brutas
    def _calcular_brutos_reales(self) -> tuple[Dict[str, float], Dict[str, float]]:
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
                
        # AQUÍ ESTÁ LA MAGIA: Devolvemos ambos para que el Refinador tenga datos precisos
        return scores, sumas_brutas

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
        # CAMBIO 2: Desempaquetamos los dos valores que nos da el método actualizado
        raw_scores, sumas_brutas = self._calcular_brutos_reales() 
        
        # CAMBIO 3: Le pasamos toda la info matemática al Refinador
        datos_refinados = SAPERefinery.refine_results(
            raw_scores=raw_scores, 
            raw_sums=sumas_brutas, 
            limites=self.limites_sector
        )
        
        username = app.storage.user.get('username', 'anonimo')
        org_id = app.storage.user.get('org_id', 'generica')

        if self.supabase:
            try:
                payload = {"user_id": username, "org_id": org_id, "test_type": "SAPE", "sector": self.sector, "status": "completed", "results": datos_refinados, "raw_answers": self.respuestas_usuario}
                self.supabase.table("evaluations").insert(payload).execute()
            except Exception as e: print(f"Error BD: {e}")

        self.header_contenedor.clear()
        self.contenedor_principal.clear()
        
        with self.contenedor_principal:
            # 1. Intentamos dibujar el panel. Si hay error de cualquier tipo, lo pasamos por alto.
            try:
                render_dashboard_resultados(datos_refinados)
            except Exception as e:
                ui.label(f"⚠️ Error cargando la pantalla de resultados: {e}").classes('text-red-500 font-bold p-4 bg-red-100 rounded')
                
            # 2. BOTÓN PDF BLINDADO Y SEPARADO
            with ui.row().classes('w-full max-w-5xl mx-auto justify-center pb-12 pt-4 bg-[#0E1117]'):
                ui.button('DESCARGAR INFORME PDF', on_click=lambda: asyncio.create_task(self._descargar_pdf(datos_refinados, username, org_id))).classes(
                    'bg-[#0D248D] hover:bg-[#5898D4] text-white font-bold py-4 px-10 rounded-xl shadow-2xl transition-all hover:scale-105'
                ).props('icon=picture_as_pdf')

    async def _descargar_pdf(self, datos, user, org):
        try:
            ui.notify('Generando informe corporativo...', type='info')
            demograficos = {'org': org, 'sector': self.sector, 'fecha': datetime.datetime.now().strftime("%d/%m/%Y")}
            ruta = pdf_generator.generar_pdf_sape(user, datos, SAPERefinery.get_clinical_flags(datos), demograficos)
            ui.download(ruta)
            ui.notify('Informe descargado con éxito', type='positive')
        except Exception as e:
            ui.notify(f'Error generando PDF.', type='negative')
            print(f"Error PDF: {e}")

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
        
        titulo_txt = str(fila.get('TITULO', 'Sin título')).strip().capitalize()
        narrativa_txt = str(fila.get('NARRATIVA', '...')).strip().capitalize()

        with ui.row().classes('w-full max-w-7xl mx-auto flex-1 items-stretch pt-10 gap-12 px-6 flex-nowrap'):
            with ui.column().classes('w-[55%] flex flex-col gap-6 justify-center pb-20'):
                ui.label(titulo_txt).classes('text-[24px] font-bold text-[#83ABF1] leading-tight')
                ui.label(narrativa_txt).classes('text-[18px] text-white leading-relaxed')

            with ui.column().classes('w-[45%] flex flex-col justify-center gap-6 pb-20'):
                for txt, letra in self.opciones_mezcladas:
                    txt_oracion = str(txt).strip().capitalize()
                    
                    btn = ui.button(on_click=lambda l=letra: self._handle_click(l), color=None)
                    btn.props('no-caps')
                    btn.classes(
                        'w-full text-left p-6 rounded-xl text-white '
                        '!bg-[#0D248D] hover:!bg-[#5898D4] '
                        'hover:scale-[1.15] '
                        'transition-all duration-300 ease-out border-none shadow-lg'
                    )
                    
                    with btn: 
                        ui.label(txt_oracion).classes('text-[12px] text-white whitespace-normal break-words w-full text-left')

    def render(self):
        ui.query('body').style(f'background-color: {BG_COLOR}; margin: 0;')
        self.header_contenedor = ui.row().classes('w-full')
        with self.header_contenedor: self.header_progress()
        self.contenedor_principal = ui.column().classes('w-full min-h-[90vh]')
        with self.contenedor_principal: self.render_layout()