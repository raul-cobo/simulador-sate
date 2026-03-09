# sapp_ui.py
import pandas as pd
import random
import asyncio
from datetime import datetime
from typing import Dict, List
from nicegui import ui, app

from logic_sapp_refinery import SAPPRefinery
from ui_results_sapp import render_dashboard_sapp

BG_COLOR = "#0E1117"

class SAPPInterface:
    def __init__(self, df_path: str, sector: str, supabase_client=None):
        self.df_path = df_path
        self.sector = sector
        self.supabase = supabase_client
        
        self.grupo_seleccionado = None
        self.df_preguntas = None
        self.total_preguntas = 0
        
        self.current_idx = 0
        self.respuestas_usuario: Dict[str, str] = {}
        self.opciones_mezcladas: List[tuple] = []
        
        # Variables de control evolutivo
        self.intentos_disponibles = 3
        self.max_intentos = 3
        
        # Carga del CSV con gestión de encodings
        try:
            self.df_completo = pd.read_csv(self.df_path, sep=';', encoding='utf-8-sig')
        except UnicodeDecodeError:
            self.df_completo = pd.read_csv(self.df_path, sep=';', encoding='latin1')
        except Exception as e:
            ui.notify(f"Error cargando CSV SAPP: {e}", type='negative')

    def render(self):
        ui.query('body').style(f'background-color: {BG_COLOR}; margin: 0;')
        
        # 1. CABECERA FIJA
        self.header_contenedor = ui.row().classes('w-full justify-between items-center px-10 py-4 bg-[#0E1117] border-b border-gray-800 flex-nowrap')
        
        # 2. CONTENEDOR PRINCIPAL
        self.main_contenedor = ui.row().classes('w-full max-w-[1400px] mx-auto min-h-[70vh] items-center px-10 flex-nowrap')
        
        self.render_selector_grupo()

    # --- FASE 1: SELECTOR DE GRUPO (CON CONTROL DE CRÉDITOS) ---
    def render_selector_grupo(self):
        self.header_contenedor.clear()
        with self.header_contenedor:
            ui.image('logo_blanco.png').classes('w-48')
            ui.label('CONFIGURACIÓN S.A.P.P.').classes('text-[#83ABF1] font-bold tracking-widest')

        self.main_contenedor.clear()
        
        is_demo = app.storage.user.get('is_demo', False)
        user_id = app.storage.user.get('user_id')
        
        # --- VERIFICACIÓN DE CRÉDITOS EVOLUTIVOS ---
        if self.supabase and user_id:
            try:
                res = self.supabase.table('users').select('intentos_disponibles, max_intentos').eq('id', user_id).execute()
                if res.data:
                    self.intentos_disponibles = res.data[0].get('intentos_disponibles', 3)
                    self.max_intentos = res.data[0].get('max_intentos', 3)
            except Exception as e:
                print(f"Error al verificar créditos: {e}")

        with self.main_contenedor.classes('justify-center flex-col items-center'):
            
            # --- CASO A: SIN INTENTOS (BLOQUEO) ---
            if self.intentos_disponibles <= 0:
                ui.icon('verified', color='#22C55E', size='5rem').classes('mb-4 mt-10')
                ui.label('CICLO EVOLUTIVO COMPLETADO').classes('text-2xl text-white font-black tracking-widest mb-2')
                ui.label('Has agotado las 3 pasaciones de este módulo.').classes('text-gray-400 mb-8')
                
                # Botón directo para ir a la fase 3 (Resultados Evolutivos) que haremos luego
                ui.button('VER INFORME EVOLUTIVO', on_click=self._mostrar_informe_evolutivo).classes('bg-[#0D248D] text-white font-bold px-8 py-3 rounded-xl shadow-lg')
                return

            # --- CASO B: CON INTENTOS (FLUJO NORMAL) ---
            if is_demo:
                ui.label(f'MODO DINÁMICA: {self.sector.upper()}').classes('text-orange-400 font-bold tracking-widest text-sm mt-10')
            else:
                ui.label('SELECCIONA EL MÓDULO A EVALUAR').classes('text-sm tracking-[.25em] text-[#83ABF1] font-bold mt-10')
                ui.label(f'Especialidad: {self.sector}').classes('text-3xl text-white font-light italic mb-4')
            
            # Etiqueta de intentos restantes (gatillo psicológico de valor)
            ui.label(f'Pasación {self.max_intentos - self.intentos_disponibles + 1} de {self.max_intentos}').classes('text-xs font-mono bg-gray-800 text-white px-3 py-1 rounded-full mb-8')

            with ui.row().classes('gap-8 justify-center w-full mb-20'):
                # BOTÓN 1: Competencias Personales
                with ui.card().classes('bg-[#161B22] border border-[#83ABF1]/20 hover:border-[#83ABF1] transition-all cursor-pointer p-8 w-72 items-center group shadow-xl'):
                    ui.icon('psychology', color='#83ABF1').classes('text-6xl mb-6 group-hover:scale-110 transition-transform')
                    ui.label('COMPETENCIAS PERSONALES').classes('text-center text-sm font-bold text-white mb-6 h-10')
                    ui.button('INICIAR', on_click=lambda: self.iniciar_test('Competencias personales')).classes('w-full bg-[#0D248D] text-white font-bold')

                # BOTONES 2 y 3 (Ocultos si es Demo)
                if not is_demo:
                    with ui.card().classes('bg-[#161B22] border border-[#83ABF1]/20 hover:border-[#83ABF1] transition-all cursor-pointer p-8 w-72 items-center group shadow-xl'):
                        ui.icon('business_center', color='#83ABF1').classes('text-6xl mb-6 group-hover:scale-110 transition-transform')
                        ui.label('COMPETENCIAS PROFESIONALES').classes('text-center text-sm font-bold text-white mb-6 h-10')
                        ui.button('INICIAR', on_click=lambda: self.iniciar_test('Competencias profesionales')).classes('w-full bg-[#0D248D] text-white font-bold')

                    with ui.card().classes('bg-[#161B22] border border-[#83ABF1]/20 hover:border-[#83ABF1] transition-all cursor-pointer p-8 w-72 items-center group shadow-xl'):
                        ui.icon('terminal', color='#83ABF1').classes('text-6xl mb-6 group-hover:scale-110 transition-transform')
                        ui.label('COMPETENCIAS TÉCNICAS').classes('text-center text-sm font-bold text-white mb-6 h-10')
                        ui.button('INICIAR', on_click=lambda: self.iniciar_test('Competencias técnicas')).classes('w-full bg-[#0D248D] text-white font-bold')

    def iniciar_test(self, grupo: str):
        self.grupo_seleccionado = grupo
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
        
        self.main_contenedor.classes(remove='justify-center flex-col')
        self._mostrar_pregunta()

    # --- FASE 2: MOTOR DE PREGUNTAS (Sin cambios estructurales) ---
    def _preparar_opciones_actuales(self):
        row = self.df_preguntas.iloc[self.current_idx]
        opciones = []
        for letra in ['A', 'B', 'C', 'D']:
            txt = row.get(f'OPCION_{letra}_TXT')
            if pd.notna(txt) and str(txt).strip() != "":
                opciones.append((txt, letra))
        random.shuffle(opciones)
        self.opciones_mezcladas = opciones

    async def _handle_click(self, letra_original: str):
        row = self.df_preguntas.iloc[self.current_idx]
        self.respuestas_usuario[str(row['ID'])] = letra_original
        
        self.current_idx += 1
        if self.current_idx < self.total_preguntas:
            self._preparar_opciones_actuales()
            self._mostrar_pregunta()
        else:
            await self._finalizar_evaluacion()

    def _mostrar_pregunta(self):
        self.header_contenedor.clear()
        progreso = self.current_idx / self.total_preguntas
        
        with self.header_contenedor:
            ui.image('logo_blanco.png').classes('w-48')
            with ui.row().classes('items-center gap-4 w-1/3 justify-end flex-nowrap'):
                ui.linear_progress(value=progreso, show_value=False).props('color="blue"').classes('w-full h-2 rounded-full')
                ui.label(f"{self.current_idx + 1}/{self.total_preguntas}").classes('text-[#83ABF1] font-bold text-sm min-w-[40px] text-right')

        self.main_contenedor.clear()
        row_data = self.df_preguntas.iloc[self.current_idx]
        
        with self.main_contenedor:
            with ui.column().classes('w-[55%] flex flex-col gap-6 justify-center pr-16 pb-20'):
                ui.label(f"Módulo: {self.grupo_seleccionado}").classes('text-[12px] text-gray-500 font-black tracking-widest uppercase')
                ui.label(row_data['TITULO']).classes('text-[24px] font-bold text-[#83ABF1] leading-tight')
                ui.label(row_data['NARRATIVA']).classes('text-[18px] text-white leading-relaxed')

            with ui.column().classes('w-[45%] flex flex-col justify-center gap-5 pb-20'):
                for txt, letra in self.opciones_mezcladas:
                    txt_oracion = str(txt).strip().capitalize()
                    btn = ui.button(on_click=lambda l=letra: self._handle_click(l), color=None)
                    btn.props('no-caps')
                    btn.classes(
                        'w-full text-left p-6 rounded-xl text-white '
                        '!bg-[#0D248D] hover:!bg-[#5898D4] transition-all duration-300 shadow-lg'
                    )
                    with btn: 
                        ui.label(txt_oracion).classes('text-[14px] text-white whitespace-normal break-words w-full text-left')

    async def _finalizar_evaluacion(self):
        ui.notify("Evaluación completada. Procesando evolución...", color='positive')
        
        raw_scores = SAPPRefinery.calculate_raw_scores(self.respuestas_usuario, self.df_preguntas)
        results = SAPPRefinery.refine_results(raw_scores, self.grupo_seleccionado)
        user_id = app.storage.user.get('user_id')
        
        if self.supabase and user_id:
            # 1. Calculamos el número de pasación actual
            current_attempt = self.max_intentos - self.intentos_disponibles + 1
            
            # 2. Guardamos la evaluación marcando el intento
            eval_data = {
                "user_id": user_id,
                "org_id": app.storage.user.get('org_id'),
                "test_type": "SAPP",
                "sector_profile": f"{self.sector} - {self.grupo_seleccionado}",
                "raw_responses": self.respuestas_usuario,
                "calculated_scores": raw_scores,
                "refined_metrics": results,
                "attempt_number": current_attempt,
                "created_at": datetime.now().isoformat()
            }
            
            try:
                # Guardar evaluación
                self.supabase.table("evaluations").insert(eval_data).execute()
                
                # Descontar el intento en la tabla users
                nuevos_intentos = max(0, self.intentos_disponibles - 1)
                self.supabase.table("users").update({"intentos_disponibles": nuevos_intentos}).eq("id", user_id).execute()
                
                # Actualizar variable en memoria
                self.intentos_disponibles = nuevos_intentos
                
            except Exception as e:
                print(f"Error en el ciclo de guardado: {e}")

        self._mostrar_informe_evolutivo()

    def _mostrar_informe_evolutivo(self):
        self.header_contenedor.clear()
        self.main_contenedor.clear()
        self.main_contenedor.classes(remove='px-10 max-w-[1400px] flex-nowrap min-h-[70vh]')
        self.main_contenedor.classes(add='w-full justify-center p-0')
        
        with self.main_contenedor:
            # Aquí llamamos a la pantalla de resultados (que modificaremos en la Fase 3)
            # Pasaremos supabase client para que pueda consultar el histórico
            render_dashboard_sapp(self.grupo_seleccionado, app.storage.user, self.supabase)