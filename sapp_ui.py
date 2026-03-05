# sapp_ui.py
import pandas as pd
import random
from datetime import datetime
from typing import Dict, List
from nicegui import ui, app

from logic_sapp_refinery import SAPPRefinery
from ui_results_sapp import render_dashboard_sapp

BG_COLOR = "#0E1117"

class SAPPInterface:
    def __init__(self, df_path: str, sector: str, supabase_client=None):
        self.df_path = df_path
        self.sector = sector  # Ej: 'Psicología organizacional'
        self.supabase = supabase_client
        
        self.grupo_seleccionado = None
        self.df_preguntas = None
        self.total_preguntas = 0
        
        self.current_idx = 0
        self.respuestas_usuario: Dict[str, str] = {}
        self.opciones_mezcladas: List[tuple] = []
        
        # Carga del CSV completo
        # Usamos utf-8-sig que es el estándar de Excel para evitar caracteres extraños
        try:
            self.df_completo = pd.read_csv(self.df_path, sep=';', encoding='utf-8-sig')
        except UnicodeDecodeError:
            # Si utf-8-sig falla, forzamos la lectura en formato europeo tradicional
            self.df_completo = pd.read_csv(self.df_path, sep=';', encoding='latin1')
        except Exception as e:
            ui.notify(f"Error cargando CSV SAPP: {e}", type='negative')

    # --- FASE 1: SELECTOR DE GRUPO ---
    def render_selector_grupo(self):
        with ui.column().classes('w-full max-w-5xl mx-auto items-center p-12 gap-8 mt-10'):
            ui.label('CONFIGURACIÓN DE EVALUACIÓN PROFESIONAL').classes('text-sm tracking-[.25em] text-[#83ABF1] font-bold')
            ui.label(f'Especialidad: {self.sector}').classes('text-3xl text-white font-light italic mb-8')
            
            with ui.row().classes('gap-8 justify-center w-full'):
                # Definimos los 3 grupos oficiales del Documento Maestro
                grupos = [
                    ('Competencias personales', 'psychology'),
                    ('Competencias profesionales', 'business_center'),
                    ('Competencias técnicas', 'terminal')
                ]
                
                for grupo_nombre, icono in grupos:
                    with ui.card().classes('bg-[#161B22] border border-[#83ABF1]/20 hover:border-[#83ABF1] transition-all cursor-pointer p-8 w-72 items-center group shadow-xl'):
                        ui.icon(icono, color='#83ABF1').classes('text-6xl mb-6 group-hover:scale-110 transition-transform')
                        ui.label(grupo_nombre.upper()).classes('text-center text-sm font-bold text-white mb-6 h-10')
                        ui.button('EVALUAR MÓDULO', on_click=lambda g=grupo_nombre: self.iniciar_test(g)).classes('w-full bg-[#0D248D] text-white font-bold')

    def iniciar_test(self, grupo: str):
        self.grupo_seleccionado = grupo
        # Filtramos por SECTOR y por GRUPO para obtener las 40 narrativas exactas
        self.df_preguntas = self.df_completo[
            (self.df_completo['SECTOR'] == self.sector) & 
            (self.df_completo['GRUPO'] == grupo)
        ].reset_index(drop=True)
        
        self.total_preguntas = len(self.df_preguntas)
        
        if self.total_preguntas == 0:
            ui.notify(f"No hay preguntas para {grupo} en {self.sector}.", type='negative')
            return
            
        self.current_idx = 0
        self.respuestas_usuario.clear()
        self._preparar_opciones_actuales()
        
        self.render_container.clear()
        with self.render_container:
            self.render_test_engine()

    # --- FASE 2: MOTOR DE PREGUNTAS ---
    def _preparar_opciones_actuales(self):
        row = self.df_preguntas.iloc[self.current_idx]
        opciones = []
        for letra in ['A', 'B', 'C', 'D']:
            txt = row.get(f'OPCION_{letra}_TXT')
            # Evitar opciones vacías (NaN) en la interfaz
            if pd.notna(txt) and str(txt).strip() != "":
                opciones.append((txt, letra))
        
        # Aleatorización estricta sin perder la lógica vinculada a la letra original
        random.shuffle(opciones)
        self.opciones_mezcladas = opciones

    async def _handle_click(self, letra_original: str):
        row = self.df_preguntas.iloc[self.current_idx]
        self.respuestas_usuario[str(row['ID'])] = letra_original
        
        self.current_idx += 1
        if self.current_idx < self.total_preguntas:
            self._preparar_opciones_actuales()
            self.render_test_engine.refresh()
        else:
            await self._finalizar_evaluacion()

    async def _finalizar_evaluacion(self):
        ui.notify("Evaluación completada. Procesando resultados...", color='positive')
        
        # 1. Motor Lógico (Refinería SAPP)
        raw_scores = SAPPRefinery.calculate_raw_scores(self.respuestas_usuario, self.df_preguntas)
        results = SAPPRefinery.refine_results(raw_scores, self.grupo_seleccionado)
        
        # 2. Persistencia en Supabase
        if self.supabase and app.storage.user.get('user_id'):
            eval_data = {
                "user_id": app.storage.user.get('user_id'),
                "org_id": app.storage.user.get('org_id'),
                "test_type": "SAPP",
                "sector_profile": f"{self.sector} - {self.grupo_seleccionado}",
                "raw_responses": self.respuestas_usuario,
                "calculated_scores": raw_scores,
                "refined_metrics": results,
                "created_at": datetime.now().isoformat()
            }
            try:
                self.supabase.table("evaluations").insert(eval_data).execute()
            except Exception as e:
                print(f"Error guardando SAPP en Supabase: {e}")

        # 3. Renderizado del Dashboard SAPP
        self.render_container.clear()
        with self.render_container:
            # Llamamos a la función de la matriz visual
            render_dashboard_sapp(results)

    @ui.refreshable
    def render_test_engine(self):
        if self.current_idx >= self.total_preguntas:
            return
            
        row = self.df_preguntas.iloc[self.current_idx]
        progreso = (self.current_idx / self.total_preguntas)
        
        with ui.column().classes('w-full max-w-4xl mx-auto items-center mt-8'):
            # Barra de progreso
            with ui.row().classes('w-full items-center gap-4 mb-8'):
                ui.linear_progress(value=progreso).props('stripe color="blue"').classes('flex-1 h-3 rounded-full')
                ui.label(f"{self.current_idx + 1}/{self.total_preguntas}").classes('text-gray-400 font-bold')

            # Narrativa
            with ui.card().classes('bg-[#161B22] border border-[#83ABF1]/20 p-8 w-full mb-8 rounded-xl shadow-2xl'):
                ui.label(f"Módulo: {self.grupo_seleccionado.upper()}").classes('text-xs text-[#83ABF1] font-black mb-2')
                ui.label(row['TITULO']).classes('text-2xl font-bold text-white mb-4')
                ui.label(row['NARRATIVA']).classes('text-lg text-gray-300 leading-relaxed')

            # Opciones
            with ui.column().classes('w-full gap-4'):
                for txt, letra in self.opciones_mezcladas:
                    with ui.button(on_click=lambda l=letra: self._handle_click(l)).classes(
                        'w-full text-left justify-start p-6 bg-[#0D248D] hover:bg-[#83ABF1] group transition-all rounded-xl shadow-lg'
                    ):
                        ui.label(str(txt).strip()).classes('text-white group-hover:text-black text-base whitespace-normal break-words w-full text-left')

    def render(self):
        ui.query('body').style('background-color: #0E1117; margin: 0;')
        self.render_container = ui.column().classes('w-full min-h-screen')
        with self.render_container:
            self.render_selector_grupo()