# saiv_ui.py
import pandas as pd
import asyncio
from datetime import datetime
from typing import Dict
from nicegui import ui, app

# Importaciones de la lógica y la interfaz visual
from logic_saiv import SAIVRefinery 
from ui_results_saiv import render_dashboard_saiv

BG_COLOR = "#0E1117"

class SAIVInterface:
    def __init__(self, df_path: str, supabase_client=None):
        self.df_path = df_path
        self.supabase = supabase_client
        
        self.df_preguntas = None
        self.total_preguntas = 0
        
        self.current_idx = 0
        self.respuestas_usuario: Dict[str, int] = {} # Guardamos ints directamente
        
        # En SAIV, no hay opciones A,B,C,D en columnas. 
        # Es una escala Likert fija de 1 a 5 para el grado de interés.
        self.opciones_likert = [
            ("1 - Nada interesante", 1),
            ("2 - Poco interesante", 2),
            ("3 - Indiferente", 3),
            ("4 - Bastante interesante", 4),
            ("5 - Muy interesante", 5)
        ]
        
        # Variables de control evolutivo
        self.intentos_disponibles = 3
        self.max_intentos = 3
        
        # Carga del CSV
        try:
            self.df_completo = pd.read_csv(self.df_path, sep=';', encoding='utf-8-sig')
            self.df_preguntas = self.df_completo # En SAIV usamos todos los ítems
            self.total_preguntas = len(self.df_preguntas)
        except UnicodeDecodeError:
            self.df_completo = pd.read_csv(self.df_path, sep=';', encoding='latin1')
            self.df_preguntas = self.df_completo
            self.total_preguntas = len(self.df_preguntas)
        except Exception as e:
            ui.notify(f"Error cargando CSV SAIV: {e}", type='negative')

    def render(self):
        ui.query('body').style(f'background-color: {BG_COLOR}; margin: 0;')
        
        # 1. CABECERA FIJA
        self.header_contenedor = ui.row().classes('w-full justify-between items-center px-10 py-4 bg-[#0E1117] border-b border-gray-800 flex-nowrap')
        
        # 2. CONTENEDOR PRINCIPAL
        self.main_contenedor = ui.row().classes('w-full max-w-[1400px] mx-auto min-h-[70vh] items-center px-10 flex-nowrap')
        
        self.verificar_e_iniciar()

    def verificar_e_iniciar(self):
        self.header_contenedor.clear()
        with self.header_contenedor:
            ui.image('logo_blanco.png').classes('w-48')
            ui.label('S.A.I.V. - ORIENTACIÓN VOCACIONAL').classes('text-[#83ABF1] font-bold tracking-widest')

        self.main_contenedor.clear()
        
        user_id = app.storage.user.get('user_id')
        
        # --- VERIFICACIÓN DE CRÉDITOS ---
        if self.supabase and user_id:
            try:
                res = self.supabase.table('users').select('intentos_disponibles, max_intentos').eq('id', user_id).execute()
                if res.data:
                    self.intentos_disponibles = res.data[0].get('intentos_disponibles', 3)
                    self.max_intentos = res.data[0].get('max_intentos', 3)
            except Exception as e:
                print(f"Error al verificar créditos: {e}")

        # --- CASO A: SIN INTENTOS (BLOQUEO) ---
        if self.intentos_disponibles <= 0:
            with self.main_contenedor.classes('justify-center flex-col items-center'):
                ui.icon('verified', color='#22C55E', size='5rem').classes('mb-4 mt-10')
                ui.label('EVALUACIÓN COMPLETADA').classes('text-2xl text-white font-black tracking-widest mb-2')
                ui.label('Has agotado las pasaciones de este test.').classes('text-gray-400 mb-8')
                ui.button('VER INFORME VOCACIONAL', on_click=lambda: ui.notify('Ir al perfil de usuario (Pendiente)', type='info')).classes('bg-[#0D248D] text-white font-bold px-8 py-3 rounded-xl shadow-lg')
            return

        # --- CASO B: CON INTENTOS (INICIAR TEST DIRECTAMENTE) ---
        self.current_idx = 0
        self.respuestas_usuario.clear()
        self.main_contenedor.classes(remove='justify-center flex-col')
        self._mostrar_pregunta()

    # --- MOTOR DE PREGUNTAS ---
    async def _handle_click(self, valor_respuesta: int):
        row = self.df_preguntas.iloc[self.current_idx]
        self.respuestas_usuario[str(row['id'])] = valor_respuesta
        
        self.current_idx += 1
        if self.current_idx < self.total_preguntas:
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
            # Columna Izquierda: La Pregunta/Situación
            with ui.column().classes('w-[55%] flex flex-col gap-6 justify-center pr-16 pb-20'):
                ui.label("EVALÚA TU INTERÉS EN ESTA ACTIVIDAD").classes('text-[12px] text-gray-500 font-black tracking-widest uppercase')
                ui.label(row_data['TITULO']).classes('text-[24px] font-bold text-[#83ABF1] leading-tight')
                ui.label(row_data['NARRATIVA']).classes('text-[18px] text-white leading-relaxed')

            # Columna Derecha: Escala Likert de Interés
            with ui.column().classes('w-[45%] flex flex-col justify-center gap-4 pb-20'):
                for txt, valor in self.opciones_likert:
                    btn = ui.button(on_click=lambda v=valor: self._handle_click(v), color=None)
                    btn.props('no-caps')
                    btn.classes(
                        'w-full text-left p-5 rounded-xl text-white '
                        '!bg-[#161B22] border border-gray-800 hover:border-[#83ABF1] hover:!bg-[#0D248D] transition-all duration-300 shadow-md'
                    )
                    with btn: 
                        ui.label(txt).classes('text-[16px] font-bold w-full text-center')

    async def _finalizar_evaluacion(self):
        ui.notify("Evaluación vocacional completada. Procesando perfil...", color='positive')
        
        user_id = app.storage.user.get('user_id')
        
        # 1. Llamamos al Motor de Refinería SAIV
        try:
            results = SAIVRefinery.refine_results(self.respuestas_usuario, self.df_preguntas)
        except Exception as e:
            ui.notify(f"Error procesando resultados: {e}", type="negative")
            print(f"Error Refinería SAIV: {e}")
            return
            
        # 2. Guardamos en Supabase
        if self.supabase and user_id:
            current_attempt = self.max_intentos - self.intentos_disponibles + 1
            
            # Formato estándar de Audeo para la tabla evaluations
            eval_data = {
                "user_id": user_id,
                "org_id": app.storage.user.get('org_id'),
                "test_type": "SAIV",
                "sector_profile": "Orientacion Vocacional",
                "raw_responses": self.respuestas_usuario,
                "refined_metrics": results,  # Aquí va el dict que devuelve el logic_saiv
                "attempt_number": current_attempt,
                "created_at": datetime.now().isoformat()
            }
            
            try:
                self.supabase.table("evaluations").insert(eval_data).execute()
                nuevos_intentos = max(0, self.intentos_disponibles - 1)
                self.supabase.table("users").update({"intentos_disponibles": nuevos_intentos}).eq("id", user_id).execute()
                self.intentos_disponibles = nuevos_intentos
                
            except Exception as e:
                print(f"Error en el guardado Supabase SAIV: {e}")
                ui.notify("Aviso: No se pudo guardar en la nube. Mostrando resultados en local.", type="warning")

        # 3. Lanzamos la pantalla de resultados
        self._mostrar_informe_evolutivo(results)

    def _mostrar_informe_evolutivo(self, results):
        self.header_contenedor.clear()
        self.main_contenedor.clear()
        
        # Ajustamos clases para el dashboard final
        self.main_contenedor.classes(remove='px-10 max-w-[1400px] flex-nowrap min-h-[70vh]')
        self.main_contenedor.classes(add='w-full justify-center p-0')
        
        with self.main_contenedor:
            try:
                # Llamada al nuevo componente visual
                render_dashboard_saiv(results)
            except Exception as e:
                ui.label(f"⚠️ Error cargando la pantalla de resultados RIASEC: {e}").classes('text-red-500 font-bold p-4 bg-red-100 rounded')