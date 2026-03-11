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

    def _calcular_limites_sector(self) -> Dict[str, Dict[str, float]]:
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
            
            # NUEVA LÓGICA DE LÍMITES (Suelo de Azar)
            for dim, valores in q_data.items():
                if dim not in limites: limites[dim] = {'max': 0.0, 'min_practico': 0.0}
                
                # El máximo sigue siendo elegir la mejor opción
                limites[dim]['max'] += max(valores + [0])
                
                # El "Mínimo Práctico" ahora es la MEDIA de las opciones (lo que sacarías al azar).
                # Se asume que hay 4 opciones (A,B,C,D). Sumamos los valores y dividimos por 4.
                valores_completos = valores + [0] * (4 - len(valores))
                media_azar = sum(valores_completos) / 4.0
                
                limites[dim]['min_practico'] += media_azar
                
        return limites

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
                maximo = self.limites_sector[dim]['max']
                suelo_azar = self.limites_sector[dim]['min_practico']
                rango = maximo - suelo_azar
                
                # Nueva Normalización: Si sacas menos que el suelo de azar, la nota es 0 o muy baja.
                if rango > 0:
                    val_norm = ((suma - suelo_azar) / rango) * 100
                elif rango == 0 and suma >= maximo:
                    val_norm = 100.0 # Caso extremo
                else:
                    val_norm = 0.0
                    
                scores[dim] = round(max(0.0, min(100.0, val_norm)), 1)
                
        # ELIMINADO EL BLOQUE QUE CAUSABA EL NAME ERROR (CRASH PREGUNTA 40)
                
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
        try:
            raw_scores, sumas_brutas = self._calcular_brutos_reales() 
            
            # Generamos limites compatibles para el cálculo del IRE
            limites_compatibles = {
                dim: {'min': int(self.limites_sector[dim]['min_practico']), 'max': int(self.limites_sector[dim]['max'])} 
                for dim in self.limites_sector
            }
            
            datos_refinados = SAPERefinery.refine_results(raw_scores=raw_scores, raw_sums=sumas_brutas, limites=limites_compatibles)
        except Exception as e:
            ui.notify(f"Error procesando los resultados matemáticos: {e}", type="negative", timeout=10000)
            print(f"Error de cálculo: {e}")
            return # Detiene la ejecución si los números fallan irremediablemente
            
        # OBTENER EL ID REAL (UUID) PARA SUPABASE, NO SOLO EL USERNAME
        user_uuid = app.storage.user.get('user_id') 
        username = app.storage.user.get('username', 'anonimo')
        org_id = app.storage.user.get('org_id', 'generica')

        if self.supabase and user_uuid:
            try:
                # 1. GUARDAR LA EVALUACIÓN
                payload = {
                    "user_id": user_uuid, # AHORA USAMOS EL UUID REAL
                    "org_id": org_id, 
                    "test_type": "SAPE", 
                    "sector_profile": self.sector, 
                    "raw_responses": self.respuestas_usuario,
                    "refined_metrics": datos_refinados,
                    "attempt_number": 1,
                    "created_at": datetime.datetime.now().isoformat()
                }
                self.supabase.table("evaluations").insert(payload).execute()
                
                # 2. RESTAR 1 LICENCIA Y REGISTRAR HISTORIAL
                res_org = self.supabase.table('organizations').select('licencias_compradas').eq('id', org_id).execute()
                if res_org.data:
                    licencias_actuales = res_org.data[0].get('licencias_compradas', 0)
                    if licencias_actuales > 0:
                        self.supabase.table('organizations').update({'licencias_compradas': licencias_actuales - 1}).eq('id', org_id).execute()
                        
                        # Historial
                        try:
                            log_payload = {
                                "org_id": org_id,
                                "action_type": "LICENSE_CONSUMED",
                                "target_user": username,
                                "performed_by": "SYSTEM (SAPE)",
                                "status_color": "green",
                                "metadata": {"sector": self.sector, "test": "SAPE"}
                            }
                            self.supabase.table('action_logs').insert(log_payload).execute()
                        except Exception as el:
                            print(f"No se pudo guardar el log: {el}")

                # 3. Descontar intento de usuario
                res_user = self.supabase.table('users').select('intentos_disponibles').eq('id', user_uuid).execute()
                if res_user.data:
                    intentos = res_user.data[0].get('intentos_disponibles', 0)
                    if intentos > 0:
                        self.supabase.table('users').update({'intentos_disponibles': intentos - 1}).eq('id', user_uuid).execute()

            except Exception as e:
                print(f"Error Crítico guardando en Supabase: {e}")
                ui.notify(f"Aviso: Error de guardado en la nube. Mostrando resultados de todas formas.", type="warning")

        # Continuamos con el renderizado visual de resultados pase lo que pase con Supabase
        self.header_contenedor.clear()
        self.contenedor_principal.clear()
        
        with self.contenedor_principal:
            try:
                render_dashboard_resultados(datos_refinados)
            except Exception as e:
                ui.label(f"⚠️ Error cargando la pantalla de resultados: {e}").classes('text-red-500 font-bold p-4 bg-red-100 rounded')
                
            # BOTÓN PDF BLINDADO Y SEPARADO
            with ui.row().classes('w-full max-w-5xl mx-auto justify-center pb-12 pt-4 bg-[#0E1117]'):
                
                async def iniciar_descarga():
                    u_info = {'username': username, 'org_id': org_id}
                    await self._descargar_pdf(datos_refinados, u_info)
                
                ui.button('DESCARGAR INFORME PDF', on_click=iniciar_descarga).classes(
                    'bg-[#0D248D] hover:bg-[#5898D4] text-white font-bold py-4 px-10 rounded-xl shadow-2xl transition-all hover:scale-105'
                ).props('icon=picture_as_pdf')

    async def _descargar_pdf(self, datos, u_info):
        try:
            ui.notify('Generando informe corporativo...', type='info')
            ruta = pdf_generator.generar_informe(user_info=u_info, results=datos, test_type='SAPE')
            ui.download(ruta)
            ui.notify('Informe descargado con éxito', type='positive')
            
        except Exception as e:
            ui.notify(f"Error PDF: {str(e)}", type='negative', timeout=10000)
            print(f"Error PDF detallado: {e}")

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