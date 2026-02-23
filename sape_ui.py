import pandas as pd
import random
import asyncio
import pdf_generator # Conectamos el motor de PDFs
from typing import Dict, Any, List
from nicegui import ui, app

from logic_sape_refinery import SAPERefinery
from ui_results import render_dashboard_resultados

# --- CONSTANTES DE ESTILO ---
BG_COLOR = "#0E1117"
CARD_COLOR = "#161B22"
ACCENT_COLOR = "#83ABF1"

class SAPEInterface:
    def __init__(self, df_path: str, sector: str, supabase_client=None):
        self.df_path = df_path
        self.sector = sector
        self.supabase = supabase_client
        
        # Carga y filtrado de datos puros
        df_completo = pd.read_csv(self.df_path, sep=';', encoding='utf-8')
        self.df_sector = df_completo[df_completo['SECTOR'] == self.sector].reset_index(drop=True)
        self.total_preguntas = len(self.df_sector)
        
        # Estado de la sesión (Reactivo)
        self.current_idx = 0
        self.respuestas_usuario: Dict[str, str] = {} # { "ID_pregunta": "LETRA" }
        self.opciones_mezcladas: List[tuple] = []
        
        # Pre-calculamos los límites matemáticos del sector para la normalización
        self.limites_sector = self._calcular_limites_sector()
        
        # Mezclamos la primera pregunta al inicializar
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
                            dim = partes[0]
                            val = int(partes[1])
                            if dim not in q_data:
                                q_data[dim] = []
                            q_data[dim].append(val)
            
            for dim, valores in q_data.items():
                if dim not in limites:
                    limites[dim] = {'max': 0, 'min': 0}
                limites[dim]['max'] += max(valores + [0])
                limites[dim]['min'] += min(valores + [0])
                
        return limites

    def _calcular_brutos_reales(self) -> Dict[str, float]:
        sumas_brutas = {}
        
        for q_id, letra in self.respuestas_usuario.items():
            if 'ID' in self.df_sector.columns:
                fila = self.df_sector[self.df_sector['ID'].astype(str) == str(q_id)]
            else:
                fila = self.df_sector.iloc[[int(q_id)]]
                
            if fila.empty:
                continue
                
            logic = str(fila.iloc[0].get(f'OPCION_{letra}_LOGIC', ''))
            if logic and str(logic).strip() not in ['nan', '', '0']:
                for regla in logic.split('|'):
                    partes = regla.strip().split()
                    if len(partes) >= 2:
                        dim = partes[0]
                        val = int(partes[1])
                        sumas_brutas[dim] = sumas_brutas.get(dim, 0) + val
                        
        scores_normalizados = {}
        for dim, suma in sumas_brutas.items():
            if dim in self.limites_sector:
                maximo = self.limites_sector[dim]['max']
                minimo = self.limites_sector[dim]['min']
                rango = maximo - minimo
                
                if rango != 0:
                    val_norm = ((suma - minimo) / rango) * 100
                    scores_normalizados[dim] = round(max(0.0, min(100.0, val_norm)), 1)
                else:
                    scores_normalizados[dim] = 50.0
                    
        return scores_normalizados

    def _preparar_opciones_actuales(self):
        if self.current_idx >= self.total_preguntas:
            return
            
        fila = self.df_sector.iloc[self.current_idx]
        opciones = []
        for letra in ['A', 'B', 'C', 'D']:
            texto = fila.get(f'OPCION_{letra}_TXT')
            if pd.notna(texto) and str(texto).strip() != "":
                opciones.append((texto, letra))
                
        random.shuffle(opciones)
        self.opciones_mezcladas = opciones

    async def _handle_click(self, letra_original: str):
        pregunta_id = str(self.df_sector.iloc[self.current_idx]['ID'] if 'ID' in self.df_sector.columns else self.current_idx)
        self.respuestas_usuario[pregunta_id] = letra_original
        
        self.current_idx += 1
        
        if self.current_idx < self.total_preguntas:
            self._preparar_opciones_actuales()
            self.render_layout.refresh() 
            self.header_progress.refresh()
        else:
            await self._finalizar_test()

    async def _finalizar_test(self):
        self.contenedor_principal.clear()
        self.header_contenedor.clear()
        
        with self.contenedor_principal:
            with ui.column().classes('w-full h-screen items-center justify-center gap-6'):
                ui.spinner('dots', size='xl', color=ACCENT_COLOR)
                ui.label("Procesando perfil SAPE...").classes('text-2xl text-white font-bold animate-pulse')

        await asyncio.sleep(1.0)

        # 1. MATEMÁTICAS PURAS
        raw_scores = self._calcular_brutos_reales() 

        # 2. IA PSICOMÉTRICA
        datos_refinados = SAPERefinery.refine_results(raw_scores)

        # 3. BASE DE DATOS: Guardado REAL en la tabla 'evaluations'
        if self.supabase:
            try:
                username = app.storage.user.get('username', 'anonimo')
                org_id = app.storage.user.get('org_id', 'generica')
                
                payload = {
                    "user_id": username,
                    "org_id": org_id,
                    "test_type": "SAPE",
                    "sector": self.sector,
                    "status": "completed",
                    "results": datos_refinados,
                    "raw_answers": self.respuestas_usuario 
                }
                
                self.supabase.table("evaluations").insert(payload).execute()
                print("✅ Evaluación guardada con éxito en Supabase.")
            except Exception as e:
                print(f"⚠️ Error guardando en BD 'evaluations': {e}")

        # 4. RENDERIZADO AL OCTÓGONO Y BOTÓN PDF
        self.contenedor_principal.clear()
        with self.contenedor_principal:
            render_dashboard_resultados(datos_refinados)
            
            # --- SECCIÓN DEL BOTÓN PDF ---
            ui.separator().classes('my-8 bg-gray-700')
            with ui.row().classes('w-full justify-center pb-12'):
                ui.button('DESCARGAR INFORME PDF', on_click=lambda: self._descargar_pdf(datos_refinados)).classes(
                    'bg-[#0D248D] text-white text-lg font-bold py-4 px-8 rounded-xl shadow-2xl hover:scale-105 transition-transform'
                ).props('icon=picture_as_pdf')

    async def _descargar_pdf(self, datos_refinados):
        try:
            ui.notify('Generando informe corporativo...', type='info')
            
            username = app.storage.user.get('username', 'Candidato')
            org_id = app.storage.user.get('org_id', 'Organización Desconocida')
            
            # Preparamos los datos demográficos ficticios (luego los podemos pedir en pantalla)
            demograficos = {
                'org': org_id,
                'edad': 'No especificada',
                'exp': 'No especificada'
            }
            
            # Llamamos a TU función exacta de pdf_generator.py
            ruta_pdf = pdf_generator.generar_pdf_sape(
                user_id=username, 
                scores=datos_refinados, # <-- Le pasamos TODOS los datos refinados (IRE, Delta, etc.)                alertas=datos_refinados.get('alertas', []),
                alertas=SAPERefinery.get_clinical_flags(datos_refinados), # <-- Sacamos las alertas de texto
                demograficos=demograficos
            )
            
            # Forzamos la descarga en el navegador del usuario
            ui.download(ruta_pdf)
            ui.notify('Informe descargado con éxito', type='positive')
            
        except Exception as e:
            ui.notify('Error al generar el PDF.', type='negative')
            print(f"⚠️ Error generando PDF: {e}")

    @ui.refreshable
    def header_progress(self):
        with ui.row().classes('w-full items-center justify-between p-6'):
            ui.image('logo_blanco.png').classes('w-48')
            
            with ui.column().classes('w-1/3 items-end gap-1'):
                mes_actual = min(self.current_idx + 1, self.total_preguntas)
                ui.label(f"Mes {mes_actual} de {self.total_preguntas}").classes('text-white font-semibold tracking-wide')
                progreso_valor = mes_actual / self.total_preguntas
                ui.linear_progress(value=progreso_valor, color=ACCENT_COLOR).classes('h-2 w-full bg-[#161B22] rounded-full')

    @ui.refreshable
    def render_layout(self):
        if self.current_idx >= len(self.df_sector):
            return

        fila = self.df_sector.iloc[self.current_idx]

        with ui.row().classes('w-full max-w-7xl mx-auto flex-1 items-stretch pt-10 gap-12 px-6 flex-nowrap'):
            
            with ui.column().classes('w-[55%] flex flex-col gap-6 justify-center pb-20'):
                ui.label(fila.get('TITULO', 'Sin Título')).classes(f'text-4xl font-black text-[{ACCENT_COLOR}] leading-tight')
                ui.label(fila.get('NARRATIVA', '...')).classes('text-2xl text-white leading-relaxed font-light tracking-wide')

            with ui.column().classes('w-[45%] flex flex-col justify-center gap-6 pb-20'):
              for texto_opcion, letra_original in self.opciones_mezcladas:
                    btn = ui.button(on_click=lambda l=letra_original: self._handle_click(l))
                    
                    # Forzamos el color mediante style en lugar de classes para asegurar que el navegador lo aplique
                    btn.style('background-color: #0D248D; color: white;')
                    
                    btn.classes(
                        'w-full text-left p-6 rounded-xl shadow-lg '
                        'hover:scale-[1.02] ' # Un hover más sutil y elegante
                        'transition-all duration-300 ease-out '
                        'border-none group'
                    )
                    
                    # Aseguramos que el texto interior también sea explícitamente blanco
                    with btn:
                        ui.label(texto_opcion).classes('text-lg leading-snug whitespace-normal break-words w-full font-medium').style('color: white;')
                    
                    with btn:
                        ui.label(texto_opcion).classes('text-lg leading-snug whitespace-normal break-words w-full font-medium text-white')

    def render(self):
        ui.query('body').style(f'background-color: {BG_COLOR}; margin: 0; padding: 0;')
        
        self.header_contenedor = ui.row().classes('w-full')
        with self.header_contenedor:
            self.header_progress()

        self.contenedor_principal = ui.column().classes('w-full min-h-[90vh] flex flex-col')
        with self.contenedor_principal:
            self.render_layout()