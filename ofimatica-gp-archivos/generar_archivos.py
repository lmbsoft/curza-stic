#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ofimática · Caso 2 «El municipio en la oficina» (Administración pública y Lic. en RRHH).
Municipalidad de Bahía Serena (FICTICIA) — datos inventados con fines didácticos.

Fuente única de los datos de los tres simuladores:
    writer-gp-maqueta.html   · calc-gp-1-formulas.html   · calc-gp-2-datos.html

Qué hace:
  1. Reutiliza las tablas del caso BI (bi-gp-datos/generar_datos.py): mismos agentes,
     licencias y expedientes, para que todos los simuladores cuenten la misma historia.
  2. Define los escenarios de la planilla básica, el registro de licencias de la
     planilla avanzada y los documentos del procesador de textos.
  3. Verifica que cada resultado que piden las misiones sea el que dicen los textos.
  4. Exporta los archivos para practicar en LibreOffice:
       calc-basico/   un TSV por misión (para pegar en A1) y un ODS con una hoja por misión
       calc-avanzado/ registro de licencias y expedientes en CSV, TSV y ODS
       writer/        documentos crudos en TXT, DOCX y ODT; plantilla y fuente para combinar
  5. Inserta los datos en los simuladores (entre /*@@DATOS-INICIO@@*/ y /*@@DATOS-FIN@@*/).

Uso:  python3 ofimatica-gp-archivos/generar_archivos.py   (desde la raíz del repositorio)
"""
import csv, io, json, os, re, shutil, subprocess, sys, tempfile
from datetime import date, datetime, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, 'bi-gp-datos'))
import generar_datos as BI          # noqa: E402  (mismas tablas que el caso BI)

if BI.fallas:
    sys.exit('Los datos del caso BI no pasan sus verificaciones: corré bi-gp-datos/generar_datos.py')

fallas, contador = [], [0]
def check(cond, msg):
    contador[0] += 1
    if not cond:
        fallas.append(msg)

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto',
         'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
def ar(fecha_iso):
    a, m, d = fecha_iso.split('-')
    return '%s/%s/%s' % (d, m, a)

# ============================================================================
# 1) PLANILLA BÁSICA — escenarios (celda → texto tal como se escribe en Calc)
# ============================================================================
FERIADOS = [('2026-07-09', 'Día de la Independencia'),
            ('2026-08-17', 'Paso a la Inmortalidad del Gral. San Martín'),
            ('2026-08-25', 'Aniversario de Bahía Serena (asueto municipal, ficticio)')]

ESCENARIOS = {
  'm1': {'titulo': 'Tipos de valores', 'celdas': {
      'A1': 'Ficha del agente: escribí en la columna B →', 'A2': 'Sueldo básico:', 'A3': 'Apellido:',
      'A4': 'Fecha de ingreso:', 'A5': 'Aporte jubilatorio:'}},
  'm2': {'titulo': 'Aporte jubilatorio', 'celdas': {
      'A1': 'Concepto', 'B1': 'Importe', 'A2': 'Sueldo bruto', 'B2': '850000',
      'A3': 'Aporte jubilatorio (11 %)'}},
  'm3': {'titulo': 'Horas extra de la semana', 'celdas': {
      'A1': 'Día', 'B1': 'Horas extra', 'A2': 'Lunes', 'B2': '2', 'A3': 'Martes', 'B3': '3',
      'A4': 'Miércoles', 'B4': '1', 'A5': 'Jueves', 'B5': '4', 'A6': 'Viernes', 'B6': '2',
      'A7': 'Sábado', 'B7': '6', 'A8': 'Domingo', 'B8': '5',
      'A10': 'Total:', 'A11': 'Promedio:', 'A12': 'Máximo:'}},
  'm4': {'titulo': 'Liquidación de horas extra', 'celdas': {
      'A1': 'Agente', 'B1': 'Horas extra', 'C1': 'Valor hora', 'D1': 'Importe',
      'A2': 'Aguilar', 'B2': '6', 'C2': '4850', 'A3': 'Benítez', 'B3': '9', 'C3': '4850',
      'A4': 'Cárdenas', 'B4': '4', 'C4': '5200', 'A5': 'Duarte', 'B5': '12', 'C5': '4600',
      'A6': 'Escobar', 'B6': '7', 'C6': '5200'}},
  'm5': {'titulo': 'Escala salarial por puntos', 'celdas': {
      'A1': 'Categoría', 'B1': 'Puntos', 'C1': 'Sueldo básico',
      'A2': 'Auxiliar', 'B2': '2400', 'A3': 'Administrativo', 'B3': '2650', 'A4': 'Técnico', 'B4': '2900',
      'A5': 'Profesional', 'B5': '3250', 'A6': 'Jefatura', 'B6': '3600',
      'E1': 'Valor del punto:', 'F1': '310,5'}},
  'm6': {'titulo': 'Demora en días corridos', 'celdas': {
      'A1': 'Expediente', 'B1': 'Inicio', 'C1': 'Resolución', 'D1': 'Días corridos',
      'A2': 'EX-2026-0004', 'B2': '14/01/2026', 'C2': '13/03/2026',
      'A3': 'EX-2026-0013', 'B3': '25/02/2026', 'C3': '18/04/2026',
      'A4': 'EX-2026-0020', 'B4': '06/04/2026', 'C4': '17/05/2026',
      'A6': 'Vencimiento a 45 días corridos del EX-2026-0004:'}},
  'm7': {'titulo': 'Plazos en días hábiles', 'celdas': {
      'A1': 'Expediente', 'B1': 'Inicio', 'C1': 'Plazo (días hábiles)', 'D1': 'Vence',
      'A2': 'EX-2026-0033', 'B2': '01/07/2026', 'C2': '10',
      'A3': 'EX-2026-0034', 'B3': '08/07/2026', 'C3': '5',
      'A4': 'EX-2026-0037', 'B4': '12/08/2026', 'C4': '10',
      'F1': 'Feriados', 'F2': ar(FERIADOS[0][0]), 'F3': ar(FERIADOS[1][0]), 'F4': ar(FERIADOS[2][0]),
      'G2': 'Independencia', 'G3': 'San Martín', 'G4': 'Asueto municipal',
      'A6': 'Fecha de control:', 'B6': '31/08/2026',
      'A7': 'Días hábiles desde el 01/07:'}},
  'm8': {'titulo': 'Ejecución presupuestaria', 'celdas': {
      'A1': 'Programa', 'B1': 'Crédito vigente', 'C1': 'Devengado', 'D1': '% ejecución',
      'A2': 'Servicios urbanos', 'B2': '120.000.000', 'C2': '78.000.000',
      'A3': 'Obras públicas', 'B3': '95.000.000', 'C3': '38.000.000',
      'A4': 'Desarrollo social', 'B4': '60.000.000', 'C4': '51.000.000',
      'A5': 'Administración general', 'B5': '45.000.000', 'C5': '31.500.000'}},
  'm9': {'titulo': 'Licencias de julio', 'celdas': {}},          # se completa desde las licencias reales
  'm10': {'titulo': 'Padrón para la credencial', 'celdas': {
      'A1': 'Apellido', 'B1': 'Nombre', 'C1': 'CUIL', 'D1': 'Para la credencial', 'E1': 'DNI',
      'A2': 'Paredes', 'B2': 'Lucía', 'C2': '27-31234567-8',
      'A3': 'Gómez', 'B3': 'Martín', 'C3': '20-28765432-1',
      'A4': 'Quiroga', 'B4': 'Ana María', 'C4': '27-35111222-3',
      'A5': 'Benítez', 'B5': 'Sergio', 'C5': '20-26333444-5'}},
  'm11': {'titulo': 'Adicional por antigüedad', 'celdas': {
      'A1': 'Agente', 'B1': 'Sueldo básico', 'C1': 'Ingreso', 'D1': 'Antigüedad (años)', 'E1': 'Adicional (2 % por año)',
      'A2': 'Paredes', 'B2': '822825,5', 'C2': '01/03/2004',
      'A3': 'Gómez', 'B3': '900450,75', 'C3': '15/08/2012',
      'A4': 'Quiroga', 'B4': '745200,25', 'C4': '02/05/2021'}},
  'm12': {'titulo': 'Presentismo de agosto', 'celdas': {
      'A1': 'Agente', 'B1': 'Ausencias injustificadas', 'C1': 'Tardanzas', 'D1': 'Presentismo', 'E1': 'Seguimiento',
      'A2': 'Paredes', 'B2': '0', 'C2': '1', 'A3': 'Gómez', 'B3': '0', 'C3': '3',
      'A4': 'Quiroga', 'B4': '1', 'C4': '0', 'A5': 'Benítez', 'B5': '3', 'C5': '6'}},
  'm13': {'titulo': 'Escenarios de paritaria', 'celdas': {
      'A1': 'Puntos ↓ · Valor del punto →', 'B1': '310,5', 'C1': '326,03', 'D1': '341,55',
      'A2': '2400', 'A3': '2650', 'A4': '2900', 'A5': '3250'}},
  'm14': {'titulo': 'Consulta de la escala', 'celdas': {
      'A1': 'Código', 'B1': 'Categoría', 'C1': 'Puntos', 'D1': 'Básico',
      'A2': 'C01', 'B2': 'Auxiliar', 'C2': '2400', 'D2': '745200',
      'A3': 'C02', 'B3': 'Administrativo', 'C3': '2650', 'D3': '822825',
      'A4': 'C03', 'B4': 'Técnico', 'C4': '2900', 'D4': '900450',
      'A5': 'C04', 'B5': 'Profesional', 'C5': '3250', 'D5': '1009125',
      'A6': 'C05', 'B6': 'Jefatura', 'C6': '3600', 'D6': '1117800',
      'F1': 'Código:', 'G1': 'C03', 'F2': 'Categoría:', 'F3': 'Básico:'}},
}
# m9: seis licencias reales de julio (del mismo registro del caso BI)
JULIO = [r for r in BI.T_LICENCIAS if r[0].startswith('2026-07') and r[1] in (1241, 1279, 1008, 1338, 1121, 1112)]
c9 = {'A1': 'Legajo', 'B1': 'Tipo', 'C1': 'Días', 'D1': '¿Larga?', 'E2': 'Licencias por enfermedad:', 'E3': 'Días por enfermedad:'}
for i, r in enumerate(JULIO, start=2):
    c9['A%d' % i], c9['B%d' % i], c9['C%d' % i] = str(r[1]), r[3], str(r[4])
ESCENARIOS['m9']['celdas'] = c9
ESCENARIOS['libre'] = {'titulo': 'Modo libre', 'celdas': {'A1': 'Planilla libre 🏛️'}}

# --- verificaciones de la planilla básica -----------------------------------
def dia_lab(ini, n, fer):
    d, k = ini, 0
    while k < n:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in fer:
            k += 1
    return d
def dias_lab(a, b, fer):
    return sum(1 for i in range((b - a).days + 1)
               if (a + timedelta(days=i)).weekday() < 5 and (a + timedelta(days=i)) not in fer)
FER = {date.fromisoformat(f) for f, _ in FERIADOS}
def dmy(s):
    d, m, a = s.split('/')
    return date(int(a), int(m), int(d))

check(len(JULIO) == 6, 'm9: hacen falta seis licencias de julio')
check(sum(1 for r in JULIO if r[3] == BI.ENF) == 3, 'm9: tres licencias por enfermedad')
check(sum(r[4] for r in JULIO if r[3] == BI.ENF) == 15, 'm9: 15 días por enfermedad')
check(sum(1 for r in JULIO if r[4] >= 10) == 1, 'm9: una sola licencia larga (el accidente)')
c6 = ESCENARIOS['m6']['celdas']
for i, dias in ((2, 58), (3, 52), (4, 41)):
    check((dmy(c6['C%d' % i]) - dmy(c6['B%d' % i])).days == dias, 'm6: fila %d no da %d días' % (i, dias))
check(dmy(c6['B2']) + timedelta(days=45) == date(2026, 2, 28), 'm6: el vencimiento corrido debe caer el 28/02')
c7 = ESCENARIOS['m7']['celdas']
VENCE_HABIL = {}
for i in (2, 3, 4):
    ini, n = dmy(c7['B%d' % i]), int(c7['C%d' % i])
    VENCE_HABIL[i] = dia_lab(ini, n, FER)
    check(VENCE_HABIL[i] > ini + timedelta(days=n), 'm7: el vencimiento hábil de la fila %d debe correrse' % i)
check(VENCE_HABIL[2] == date(2026, 7, 16) and VENCE_HABIL[4] == date(2026, 8, 28), 'm7: vencimientos esperados')
DIAS_HAB_CONTROL = dias_lab(dmy(c7['B2']), dmy(c7['B6']), FER)
check(DIAS_HAB_CONTROL == 41, 'm7: deberían ser 41 días hábiles del 01/07 al 31/08 (son %d)' % DIAS_HAB_CONTROL)
check(all(date.fromisoformat(f).weekday() < 5 for f, _ in FERIADOS), 'm7: los feriados deben caer en días de semana')
c8 = ESCENARIOS['m8']['celdas']
eje = [int(c8['C%d' % i].replace('.', '')) / int(c8['B%d' % i].replace('.', '')) for i in range(2, 6)]
check([round(x, 4) for x in eje] == [0.65, 0.4, 0.85, 0.7], 'm8: ejecuciones 65/40/85/70 %')
c10 = ESCENARIOS['m10']['celdas']
for i in range(2, 6):
    check(len(c10['C%d' % i]) == 13 and c10['C%d' % i][2] == '-' and c10['C%d' % i][11] == '-', 'm10: CUIL con formato XX-XXXXXXXX-X')
c5 = ESCENARIOS['m5']['celdas']
for i in range(2, 7):
    basico = int(c5['B%d' % i]) * 310.5
    check(basico == round(basico), 'm5: el básico de la fila %d debería ser entero' % i)
c14 = ESCENARIOS['m14']['celdas']
for i in range(2, 7):
    check(int(c14['D%d' % i]) == int(c14['C%d' % i]) * 310.5, 'm14: la escala debe coincidir con la de la misión 5')

# ============================================================================
# 2) PLANILLA AVANZADA — registro de licencias (con columna Mes)
# ============================================================================
CAB_REG = ['Fecha', 'Mes', 'Legajo', 'Área', 'Tipo', 'Días', 'Costo día']
REGISTRO = [[ar(f), MESES[int(f[5:7]) - 1], leg, area, tipo, d, costo]
            for (f, leg, area, tipo, d, costo) in BI.T_LICENCIAS]
fila_sucia = [i for i, r in enumerate(REGISTRO, start=2) if not isinstance(r[5], int)]
check(len(fila_sucia) == 1, 'calc2: un solo dato sucio')
FILA_SUCIA = fila_sucia[0]
LEG_SUCIO = REGISTRO[FILA_SUCIA - 2][2]
COSTO_TOTAL = sum(r[5] * r[6] for r in REGISTRO if isinstance(r[5], int))
COSTO_CORREGIDO = COSTO_TOTAL + 2 * REGISTRO[FILA_SUCIA - 2][6]
check(COSTO_TOTAL == 12305600, 'calc2: costo total sin el dato sucio = 12.305.600')
check(len(REGISTRO) + 1 <= 48, 'calc2: el registro entra en la grilla con lugar para el total')
acc = [r for r in REGISTRO if r[4] == BI.ACC]
check(len(acc) == 5, 'calc2-m2: 5 accidentes de trabajo')
sp5 = [r for r in REGISTRO if r[3] == BI.SP and isinstance(r[5], int) and r[5] >= 5]
check(len(sp5) == 5, 'calc2-m3: 5 licencias de Servicios Públicos de 5 días o más')
largas = [r for r in REGISTRO if isinstance(r[5], int) and r[5] >= 10]
check(len(largas) == 5 and all(r[4] == BI.ACC for r in largas), 'calc2-m11: las 5 licencias largas son accidentes')
check(len({r[2] for r in REGISTRO}) == 29, 'calc2-m10: 29 personas distintas')
op_sp = sum(r[5] for r in REGISTRO if r[3] in (BI.OP, BI.SP) and isinstance(r[5], int))
check(op_sp == 168, 'calc2-m8: Obras + Servicios = 168 días')

# ============================================================================
# 3) PROCESADOR DE TEXTOS — documentos (texto, estilo esperado)
# ============================================================================
TG, ST, T1, T2, CT, RO, AR, LN = ('Título general', 'Subtítulo', 'Título 1', 'Título 2',
                                  'Cuerpo de texto', 'Rótulo', 'Artículo', 'Numeración 1')
pers = {}
for p in BI.PERSONAL:
    pers.setdefault(p[2], []).append(p[3])
edad = {k: sum(v) / len(v) for k, v in pers.items()}
INFORME = [
  ('Informe de gestión de Recursos Humanos', TG),
  ('Municipalidad de Bahía Serena · Enero a agosto de 2026', ST),
  ('Presentación', T1),
  ('Este informe resume la situación del personal municipal entre enero y agosto de 2026: la dotación, el ausentismo y su costo, y el desempeño en la gestión de trámites. Está dirigido al Intendente y al gabinete, y acompaña al tablero de gestión publicado por la Dirección de Modernización.', CT),
  ('Todos los datos provienen de los registros administrativos del municipio. Las cifras de ausentismo se presentan agregadas por área y por tipo de licencia, sin datos que permitan identificar a las personas.', CT),
  ('Dotación del personal', T1),
  ('Situación de revista', T2),
  ('Al 31 de agosto, el municipio cuenta con 40 agentes. El 55 % pertenece a la planta permanente, el 25 % a la planta transitoria y el 20 % es personal contratado. Servicios Públicos es el área más numerosa, con 12 agentes.', CT),
  ('Edad y antigüedad', T2),
  ('La planta permanente promedia 51,5 años de edad, frente a 36 de la planta transitoria y 29 del personal contratado. En los próximos diez años una parte importante de la planta permanente estará en condiciones de jubilarse: hay que planificar el traspaso de saberes.', CT),
  ('Ausentismo', T1),
  ('Se registraron 45 licencias, que sumaron 223 días de trabajo perdidos y alcanzaron a 29 personas. Contar licencias y contar personas no es lo mismo: varias personas tuvieron más de una licencia en el período.', CT),
  ('Frecuencia y gravedad', T2),
  ('Las licencias por enfermedad son las más frecuentes (26 casos), pero los 5 accidentes de trabajo generaron más días perdidos y un costo mayor. Prevenir accidentes rinde más de lo que sugiere su frecuencia.', CT),
  ('El invierno', T2),
  ('Junio y julio concentraron 116 de los 223 días perdidos. Conviene anticipar reemplazos y reforzar la campaña de vacunación antigripal antes del invierno.', CT),
  ('Costo laboral', T2),
  ('El costo laboral del ausentismo del período fue de $ 12.305.600, calculado licencia por licencia según el costo diario de cada agente.', CT),
  ('Trámites y plazos', T1),
  ('Se iniciaron 40 expedientes: 33 están resueltos y 7 siguen en trámite. La demora mediana fue de 12 días. Los trámites iniciados por la web se resolvieron en una mediana de 9 días, contra 19 de los presenciales.', CT),
  ('El permiso de obra es el único trámite con una demora mediana superior a su plazo: 48 días contra 45 previstos.', CT),
  ('Recomendaciones', T1),
  ('Implementar un plan de prevención de accidentes de trabajo en Obras Públicas y Servicios Públicos.', CT),
  ('Planificar reemplazos para junio y julio, y adelantar la vacunación antigripal.', CT),
  ('Ampliar la gestión digital de trámites y revisar el circuito de los permisos de obra.', CT),
  ('Publicar trimestralmente una versión agregada de este informe, como parte de la transparencia activa.', CT),
]
RESOLUCION = [
  ('MUNICIPALIDAD DE BAHÍA SERENA', TG),
  ('Resolución Nº 214/2026', ST),
  ('Bahía Serena, 2 de septiembre de 2026', CT),
  ('VISTO:', RO),
  ('El expediente EX-2026-0041, por el cual la Dirección de Recursos Humanos propone ordenar el régimen de solicitud y registro de licencias del personal municipal; y', CT),
  ('CONSIDERANDO:', RO),
  ('Que el registro de licencias de enero a agosto de 2026 muestra que junio y julio concentraron más de la mitad de los días de trabajo perdidos;', CT),
  ('Que los accidentes de trabajo, aunque menos frecuentes que las licencias por enfermedad, generaron el mayor costo laboral del período;', CT),
  ('Que los datos de salud del personal son datos sensibles y su tratamiento debe limitarse a lo estrictamente necesario;', CT),
  ('Que ha tomado intervención la Asesoría Legal;', CT),
  ('Por ello,', CT),
  ('EL INTENDENTE MUNICIPAL DE BAHÍA SERENA', RO),
  ('RESUELVE:', RO),
  ('Apruébase el procedimiento de solicitud y registro de licencias que, como Anexo I, forma parte de la presente.', AR),
  ('Establécese que las licencias por enfermedad deberán justificarse con certificado médico dentro de las 48 horas hábiles.', AR),
  ('Dispónese que la Dirección de Recursos Humanos publique trimestralmente un informe agregado de ausentismo, sin datos que permitan identificar a las personas.', AR),
  ('Regístrese, comuníquese, publíquese en el Boletín Oficial municipal y archívese.', AR),
]
NOTIFICACION = [
  ('MUNICIPALIDAD DE BAHÍA SERENA', TG),
  ('Dirección de Recursos Humanos · Notificación de licencia', ST),
  ('Bahía Serena, 2 de septiembre de 2026', CT),
  ('Agente: [APELLIDO Y NOMBRE] · Legajo Nº [LEGAJO]', CT),
  ('Por la presente se le notifica que quedó registrada su licencia por [TIPO], iniciada el [FECHA DE INICIO], por [DÍAS] días.', CT),
  ('Ante cualquier consulta, puede dirigirse a la Dirección de Recursos Humanos de lunes a viernes, de 8 a 14 horas.', CT),
  ('Dirección de Recursos Humanos', CT),
]
CAMPOS = ['apellido_nombre', 'legajo', 'tipo', 'fecha_inicio', 'dias']
NOMBRES = {1023: 'Ferreyra, Marta', 1103: 'Luna, Walter', 1073: 'Sosa, Gabriela', 1248: 'Ibáñez, Diego'}
FUENTE_COMB = [[NOMBRES[r[1]], r[1], r[3], ar(r[0]), r[4]] for r in BI.T_LICENCIAS if r[0].startswith('2026-08')]
check(len(FUENTE_COMB) == 4 and all(isinstance(r[4], int) for r in FUENTE_COMB), 'writer: 4 licencias de agosto para notificar')
INSTRUCTIVO = [   # (texto tal como llegó, estilo esperado, estilo con el que llegó, formato directo)
  ('Instructivo para solicitar licencias', TG, CT, {'bold': True}),
  ('Dirección de Recursos Humanos', ST, CT, {'italic': True}),
  ('Paso a paso', T1, CT, {'bold': True}),
  ('1) Completar el formulario de solicitud con el tipo de licencia y las fechas.', LN, CT, {}),
  ('2) Adjuntar la documentación respaldatoria: certificado médico, constancia de examen o de cuidado familiar.', LN, CT, {'bold': True}),
  ('3) Presentar la solicitud ante la jefatura del área dentro de las 48 horas hábiles.', LN, CT, {}),
  ('4) Controlar en el sistema que la licencia quedó registrada.', LN, CT, {'italic': True}),
  ('Plazos', T1, T2, {}),
  ('Las licencias por enfermedad se justifican dentro de las 48 horas hábiles. Las licencias por estudio se solicitan con 5 días hábiles de anticipación.', CT, CT, {'italic': True}),
  ('Datos personales', T1, CT, {'bold': True}),
  ('Los certificados médicos son datos sensibles: se archivan en el legajo y no se comparten por correo ni por mensajería.', CT, CT, {}),
]
check(sum(1 for t, e in INFORME if e in (T1, T2)) == 10, 'writer: el informe tiene 10 títulos para el sumario')
check(sum(1 for t, e in RESOLUCION if e == AR) == 4, 'writer: la resolución llega con 4 artículos')
check(all(not re.match(r'(?i)^art', t) for t, e in RESOLUCION if e == AR), 'writer: los artículos no traen el número escrito')

# ============================================================================
# 4) EXPORTACIÓN
# ============================================================================
COLS = 'ABCDEFGHIJ'
def a_grilla(celdas):
    filas = max(int(re.sub(r'[A-Z]', '', r)) for r in celdas)
    cols = max(COLS.index(re.sub(r'\d', '', r)) for r in celdas) + 1
    g = [['' for _ in range(cols)] for _ in range(filas)]
    for ref, v in celdas.items():
        g[int(re.sub(r'[A-Z]', '', ref)) - 1][COLS.index(re.sub(r'\d', '', ref))] = v
    return g

def texto_tabla(cab, filas, sep, fechas_ar=True):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=sep, lineterminator='\n')
    if cab:
        w.writerow(cab)
    for f in filas:
        w.writerow(f)
    return buf.getvalue()

def tipar(v):
    """Convierte lo que se escribiría en Calc (es-AR) al valor que va al XLSX."""
    if not isinstance(v, str):
        return v, None
    t = v.strip()
    if re.fullmatch(r'\d{2}/\d{2}/\d{4}', t):
        return datetime.strptime(t, '%d/%m/%Y'), 'DD/MM/YYYY'
    if re.fullmatch(r'-?\d+(,\d+)?%', t):
        return float(t[:-1].replace(',', '.')) / 100, '0%'
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})+(,\d+)?', t):
        return float(t.replace('.', '').replace(',', '.')), '#,##0'
    if re.fullmatch(r'-?\d+(,\d+)?', t):
        n = float(t.replace(',', '.'))
        return (int(n) if n == int(n) else n), None
    return v, None

def guardar(ruta, texto, bom=False):
    with open(ruta, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='') as fh:
        fh.write(texto)

PERFIL_LO = os.path.join(tempfile.gettempdir(), 'lo-perfil-ofimatica-gp')
def soffice(origen, formato, destino_dir):
    if not shutil.which('soffice'):
        print('  (sin LibreOffice: no se genera %s)' % formato)
        return
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(['soffice', '-env:UserInstallation=file://' + PERFIL_LO, '--headless',
                            '--convert-to', formato, '--outdir', tmp, origen],
                           capture_output=True, text=True, timeout=180)
        hechos = [f for f in os.listdir(tmp) if f.endswith('.' + formato)]
        if not hechos:
            print('  ⚠ LibreOffice no convirtió %s: %s' % (os.path.basename(origen), r.stderr.strip()[:200]))
            return
        shutil.move(os.path.join(tmp, hechos[0]), os.path.join(destino_dir, hechos[0]))

def libro_xlsx(hojas, ruta):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    wb.remove(wb.active)
    for nombre, filas in hojas:
        ws = wb.create_sheet(nombre[:31])
        for i, fila in enumerate(filas, start=1):
            for j, v in enumerate(fila, start=1):
                if v == '' or v is None:
                    continue
                val, fmt = tipar(v)
                c = ws.cell(row=i, column=j, value=val)
                if fmt:
                    c.number_format = fmt
                if i == 1 and isinstance(val, str):
                    c.font = Font(bold=True)
        for col in ws.columns:
            ancho = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(ancho + 2, 10), 34)
    wb.properties.creator = 'Seminario de TIC'
    wb.save(ruta)

def nombre_escenario(clave):
    slug = re.sub(r'[^a-z0-9]+', '-', ESCENARIOS[clave]['titulo'].lower().translate(str.maketrans('áéíóúñü', 'aeiounu'))).strip('-')
    return 'm%02d-%s' % (int(clave[1:]), slug)

def exportar_calc():
    d = os.path.join(AQUI, 'calc-basico')
    hojas = []
    for clave in sorted((k for k in ESCENARIOS if k != 'libre'), key=lambda k: int(k[1:])):
        esc = ESCENARIOS[clave]
        g = a_grilla(esc['celdas'])
        nombre = nombre_escenario(clave)
        guardar(os.path.join(d, nombre + '.tsv'), texto_tabla(None, g, '\t'), bom=True)
        hojas.append(('M%d %s' % (int(clave[1:]), esc['titulo']), g))
    xlsx = os.path.join(tempfile.gettempdir(), 'escenarios-calc-basico.xlsx')
    libro_xlsx(hojas, xlsx)
    soffice(xlsx, 'ods', d)

    d = os.path.join(AQUI, 'calc-avanzado')
    filas_iso = [[f[0][6:] + '-' + f[0][3:5] + '-' + f[0][:2]] + f[1:] for f in REGISTRO]
    guardar(os.path.join(d, 'registro-licencias.csv'), texto_tabla(CAB_REG, filas_iso, ','))
    guardar(os.path.join(d, 'registro-licencias.tsv'), texto_tabla(CAB_REG, REGISTRO, '\t'), bom=True)
    xlsx = os.path.join(tempfile.gettempdir(), 'registro-licencias.xlsx')
    libro_xlsx([('Licencias', [CAB_REG] + REGISTRO)], xlsx)
    soffice(xlsx, 'ods', d)
    shutil.copy(os.path.join(RAIZ, 'bi-gp-datos', 'expedientes.csv'), os.path.join(d, 'expedientes.csv'))
    shutil.copy(os.path.join(RAIZ, 'bi-gp-datos', 'expedientes.tsv'), os.path.join(d, 'expedientes.tsv'))

def exportar_writer():
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:
        print('  (sin python-docx: no se generan DOCX/ODT)')
        Document = None
    d = os.path.join(AQUI, 'writer')
    docs = [('informe-rrhh-crudo', INFORME, None), ('resolucion-214-cruda', RESOLUCION, None),
            ('notificacion-plantilla', NOTIFICACION, None),
            ('instructivo-ensuciado', [(t, e) for t, e, _, _ in INSTRUCTIVO], INSTRUCTIVO)]
    for nombre, paras, sucio in docs:
        guardar(os.path.join(d, nombre + '.txt'), '\n\n'.join(t for t, _ in paras) + '\n')
        if not Document:
            continue
        doc = Document()
        doc.core_properties.author = 'Seminario de TIC'
        doc.core_properties.title = nombre
        for i, (t, _) in enumerate(paras):
            p = doc.add_paragraph()
            run = p.add_run(t)
            if sucio:                         # el documento «ensuciado»: formato directo a mano
                fd = sucio[i][3]
                run.bold = fd.get('bold') or None
                run.italic = fd.get('italic') or None
                if sucio[i][1] in (TG, T1):
                    run.font.size = Pt(15 if sucio[i][1] == TG else 13)
        ruta = os.path.join(d, nombre + '.docx')
        doc.save(ruta)
        soffice(ruta, 'odt', d)
    cab = ['apellido_nombre', 'legajo', 'tipo', 'fecha_inicio', 'dias']
    guardar(os.path.join(d, 'licencias-agosto-notificar.csv'), texto_tabla(cab, FUENTE_COMB, ','))
    guardar(os.path.join(d, 'licencias-agosto-notificar.tsv'), texto_tabla(cab, FUENTE_COMB, '\t'), bom=True)
    xlsx = os.path.join(tempfile.gettempdir(), 'licencias-agosto-notificar.xlsx')
    libro_xlsx([('Notificar', [cab] + FUENTE_COMB)], xlsx)
    soffice(xlsx, 'ods', d)

# ============================================================================
# 5) INSERCIÓN EN LOS SIMULADORES
# ============================================================================
BLOQUE = re.compile(r'/\*@@DATOS-INICIO@@\*/.*?/\*@@DATOS-FIN@@\*/', re.S)
def js(nombre, valor):
    return 'const %s = %s;' % (nombre, json.dumps(valor, ensure_ascii=False, separators=(',', ':')))
def bloque(*consts):
    return '\n'.join(['/*@@DATOS-INICIO@@*/',
                      '/* Datos generados por ofimatica-gp-archivos/generar_archivos.py — no editar a mano. */']
                     + list(consts) + ['/*@@DATOS-FIN@@*/'])

def insertar():
    tsv_registro = texto_tabla(CAB_REG, REGISTRO, '\t').strip()
    with open(os.path.join(RAIZ, 'bi-gp-datos', 'expedientes.csv'), encoding='utf-8') as fh:
        csv_exp = fh.read().strip()
    destinos = {
      'calc-gp-1-formulas.html': bloque(js('ESCENARIOS', {k: v['celdas'] for k, v in ESCENARIOS.items()})),
      'calc-gp-2-datos.html': bloque(js('REGISTRO_TSV', tsv_registro), js('EXPEDIENTES_CSV', csv_exp),
                                     js('FILA_SUCIA', FILA_SUCIA), js('LEGAJO_SUCIO', LEG_SUCIO)),
      'writer-gp-maqueta.html': bloque(
          js('DOC_INFORME', [[t, e] for t, e in INFORME]),
          js('DOC_RESOLUCION', [[t, e] for t, e in RESOLUCION]),
          js('DOC_NOTIFICACION', [[t, e] for t, e in NOTIFICACION]),
          js('DOC_INSTRUCTIVO', [[t, e, i, fd] for t, e, i, fd in INSTRUCTIVO]),
          js('CAMPOS_COMB', CAMPOS), js('FUENTE_COMB', FUENTE_COMB)),
      os.path.join('ofimatica-gp-archivos', 'index.html'): bloque(
          js('ARCH_ESCENARIOS', {k: {'titulo': v['titulo'], 'archivo': nombre_escenario(k), 'tsv': texto_tabla(None, a_grilla(v['celdas']), '\t').rstrip('\n')}
                                 for k, v in ESCENARIOS.items() if k != 'libre'}),
          js('ARCH_REGISTRO', tsv_registro),
          js('ARCH_FUENTE', texto_tabla(CAMPOS, FUENTE_COMB, '\t').strip()),
          js('ARCH_TEXTOS', {'informe-rrhh-crudo': '\n\n'.join(t for t, _ in INFORME),
                             'resolucion-214-cruda': '\n\n'.join(t for t, _ in RESOLUCION),
                             'notificacion-plantilla': '\n\n'.join(t for t, _ in NOTIFICACION),
                             'instructivo-ensuciado': '\n\n'.join(t for t, _, _, _ in INSTRUCTIVO)})),
    }
    for rel, contenido in destinos.items():
        ruta = os.path.join(RAIZ, rel)
        if not os.path.exists(ruta):
            print('  (todavía no existe %s)' % rel)
            continue
        with open(ruta, encoding='utf-8') as fh:
            html = fh.read()
        if not BLOQUE.search(html):
            print('  ⚠ %s no tiene las marcas de datos' % rel)
            continue
        nuevo = BLOQUE.sub(lambda m: contenido, html, count=1)
        if nuevo != html:
            with open(ruta, 'w', encoding='utf-8') as fh:
                fh.write(nuevo)
            print('  datos insertados en %s' % rel)

if __name__ == '__main__':
    if fallas:
        print('✖ Los datos NO cumplen lo que prometen las misiones:')
        for f in fallas:
            print('   -', f)
        sys.exit(1)
    print('✔ %d verificaciones superadas' % contador[0])
    if '--sin-archivos' not in sys.argv:
        exportar_calc()
        exportar_writer()
    insertar()
    if '--resumen' in sys.argv:
        print('Vencimientos hábiles m7:', {k: v.isoformat() for k, v in VENCE_HABIL.items()}, '| días hábiles al 31/08:', DIAS_HAB_CONTROL)
        print('Fila sucia del registro:', FILA_SUCIA, 'legajo', LEG_SUCIO, '| costo total', COSTO_TOTAL, '→ corregido', COSTO_CORREGIDO)
        print('Licencias de julio m9:', JULIO)
        print('Fuente de combinación:', FUENTE_COMB)
