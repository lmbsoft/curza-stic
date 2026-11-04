#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caso 2 del Estudio de informes (BI): «El tablero de gestión del municipio».
Municipalidad de Bahía Serena (FICTICIA) — datos inventados con fines didácticos.

Este script es la ÚNICA fuente de verdad de los datos del caso:
  1. Define las filas a mano (personal, licencias, expedientes).
  2. Verifica que cada «giro» que prometen las misiones realmente ocurra
     (si alguien edita una fila y rompe una misión, el script lo avisa).
  3. Exporta los archivos para copiar y pegar en Hojas de cálculo / Looker Studio:
       *.csv  → coma, fechas ISO (aaaa-mm-dd), UTF-8. Ideal para «Carga de archivos».
       *.tsv  → tabulación, fechas dd/mm/aaaa, UTF-8 con BOM. Para pegar en una
                planilla configurada en español (Argentina).
       bi-gp-municipio.xlsx → las tres tablas en hojas separadas (si hay openpyxl).
  4. Inserta los mismos CSV dentro de los simuladores (entre las marcas
     /*@@DATOS-INICIO@@*/ … /*@@DATOS-FIN@@*/), para que funcionen sin internet.

Uso:  python3 bi-gp-datos/generar_datos.py      (desde la raíz del repositorio)
"""
import csv, io, os, re, statistics, sys
from datetime import date, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

SP, OP, DS, AC, HA, LE = ('Servicios Públicos', 'Obras Públicas', 'Desarrollo Social',
                          'Atención Ciudadana', 'Hacienda', 'Legales')
PP, PT, CO = 'Planta permanente', 'Planta transitoria', 'Contratado'

# ----------------------------------------------------------------------------
# 1) PERSONAL — una fila por agente (dotación al 31/08/2026)
#    legajo, área, situación de revista, edad, antigüedad (años)
# ----------------------------------------------------------------------------
PERSONAL = [
    (1004, HA, PP, 63, 35), (1008, SP, PP, 61, 34), (1015, OP, PP, 59, 30),
    (1019, SP, PP, 57, 29), (1023, DS, PP, 56, 28), (1031, AC, PP, 55, 25),
    (1034, SP, PP, 54, 26), (1038, HA, PP, 57, 27), (1046, OP, PP, 53, 23),
    (1049, LE, PP, 54, 22), (1052, SP, PP, 50, 21), (1058, DS, PP, 51, 22),
    (1069, AC, PP, 49, 18), (1073, HA, PP, 52, 21), (1077, SP, PP, 47, 18),
    (1085, DS, PP, 48, 19), (1094, OP, PP, 46, 16), (1103, SP, PP, 45, 15),
    (1112, AC, PP, 42, 11), (1116, DS, PP, 44, 13), (1121, SP, PP, 43, 12),
    (1127, HA, PP, 46, 10),
    (1226, SP, PT, 39, 7), (1233, OP, PT, 41, 8), (1241, AC, PT, 37, 6),
    (1248, SP, PT, 35, 5), (1255, OP, PT, 36, 5), (1267, SP, PT, 31, 3),
    (1279, OP, PT, 33, 4), (1288, DS, PT, 38, 6), (1294, AC, PT, 30, 3),
    (1302, LE, PT, 40, 6),
    (1338, SP, CO, 28, 2), (1347, OP, CO, 29, 2), (1352, DS, CO, 32, 3),
    (1361, SP, CO, 26, 1), (1366, HA, CO, 34, 2), (1374, DS, CO, 27, 1),
    (1381, AC, CO, 25, 0), (1389, HA, CO, 31, 1),
]

def costo_dia(sit, antig):
    """Costo laboral diario (ficticio): base por situación + plus por antigüedad."""
    base, plus = {PP: (50000, 600), PT: (45000, 500), CO: (39000, 500)}[sit]
    return int(round((base + plus * antig) / 100.0) * 100)

AGENTE = {leg: dict(area=a, sit=s, edad=e, antig=t, costo=costo_dia(s, t))
          for (leg, a, s, e, t) in PERSONAL}

# ----------------------------------------------------------------------------
# 2) LICENCIAS — una fila por licencia (enero a agosto 2026)
#    fecha de inicio, legajo, tipo, días   (área y costo_dia salen del legajo)
#    Una fila trae «s/d» en días A PROPÓSITO (dato sucio).
# ----------------------------------------------------------------------------
ENF, ACC, CUI, EST = 'Enfermedad', 'Accidente de trabajo', 'Cuidado familiar', 'Estudio'
LICENCIAS = [
    # Servicios Públicos
    ('2026-01-14', 1052, ENF, 3), ('2026-02-09', 1338, CUI, 2), ('2026-03-23', 1121, ENF, 2),
    ('2026-05-11', 1077, ACC, 20), ('2026-05-26', 1008, ENF, 5), ('2026-06-02', 1248, ENF, 4),
    ('2026-06-15', 1034, ENF, 7), ('2026-06-24', 1052, ENF, 3), ('2026-07-06', 1267, CUI, 3),
    ('2026-07-13', 1008, ENF, 8), ('2026-07-20', 1338, EST, 2), ('2026-07-27', 1121, ENF, 4),
    ('2026-08-10', 1103, ACC, 24), ('2026-08-24', 1248, ENF, 2),
    # Obras Públicas
    ('2026-01-27', 1046, ENF, 2), ('2026-03-16', 1255, ACC, 19), ('2026-04-20', 1015, ENF, 3),
    ('2026-06-08', 1233, ACC, 23), ('2026-06-29', 1347, ENF, 3), ('2026-07-08', 1279, ACC, 27),
    ('2026-07-22', 1046, CUI, 2),
    # Desarrollo Social
    ('2026-02-16', 1374, EST, 1), ('2026-03-09', 1058, CUI, 2), ('2026-04-27', 1023, ENF, 4),
    ('2026-05-18', 1116, ENF, 3), ('2026-06-10', 1288, ENF, 5), ('2026-06-17', 1058, ENF, 4),
    ('2026-07-15', 1374, EST, 2), ('2026-08-03', 1023, CUI, 1),
    # Atención Ciudadana
    ('2026-01-20', 1069, ENF, 2), ('2026-03-02', 1294, ENF, 's/d'), ('2026-03-30', 1241, EST, 1),
    ('2026-04-06', 1031, CUI, 2), ('2026-05-04', 1112, ENF, 3), ('2026-05-20', 1069, ENF, 2),
    ('2026-06-03', 1294, ENF, 3), ('2026-06-22', 1031, ENF, 4), ('2026-07-01', 1241, CUI, 2),
    ('2026-07-29', 1112, ENF, 3),
    # Hacienda
    ('2026-02-23', 1366, EST, 1), ('2026-05-06', 1073, ENF, 2), ('2026-06-12', 1004, ENF, 3),
    ('2026-07-17', 1366, EST, 2), ('2026-08-12', 1073, CUI, 1),
    # Legales (área de 2 personas: sirve para la lección de privacidad)
    ('2026-06-05', 1302, ENF, 2),
]
LICENCIAS.sort(key=lambda r: r[0])

# ----------------------------------------------------------------------------
# 3) EXPEDIENTES — trámites iniciados de enero a agosto 2026
#    nº, fecha de inicio, área, trámite, canal, estado, días de resolución, plazo
#    Días VACÍO = sigue en trámite (no es cero).
# ----------------------------------------------------------------------------
REC, CER, HAB, LIC, PER, SUB = ('Reclamo vecinal', 'Certificado', 'Habilitación comercial',
                                'Licitación', 'Permiso de obra', 'Subsidio')
PLAZO = {REC: 10, CER: 5, HAB: 30, LIC: 90, PER: 45, SUB: 20}
AREA_DE = {REC: SP, CER: AC, HAB: HA, LIC: HA, PER: OP, SUB: DS}
W, P = 'Web', 'Presencial'
R, T = 'Resuelto', 'En trámite'
EXPEDIENTES = [
    (1, '2026-01-02', LIC, P, R, 240), (2, '2026-01-08', CER, P, R, 4),
    (3, '2026-01-12', REC, W, R, 3),   (4, '2026-01-14', PER, P, R, 58),
    (5, '2026-01-19', HAB, P, R, 27),  (6, '2026-01-21', SUB, P, R, 17),
    (7, '2026-01-26', REC, P, R, 9),   (8, '2026-01-28', PER, W, R, 44),
    (9, '2026-02-04', CER, W, R, 1),   (10, '2026-02-09', LIC, P, T, None),
    (11, '2026-02-11', HAB, W, R, 15), (12, '2026-02-18', REC, W, R, 5),
    (13, '2026-02-25', PER, P, R, 52), (14, '2026-03-03', CER, P, R, 6),
    (15, '2026-03-09', SUB, W, R, 9),  (16, '2026-03-11', REC, P, R, 12),
    (17, '2026-03-16', HAB, P, R, 21), (18, '2026-03-23', LIC, P, R, 85),
    (19, '2026-03-31', CER, W, R, 2),  (20, '2026-04-06', PER, W, R, 41),
    (21, '2026-04-08', REC, W, R, 4),  (22, '2026-04-15', HAB, W, R, 12),
    (23, '2026-04-20', LIC, P, R, 70), (24, '2026-05-04', PER, P, R, 49),
    (25, '2026-05-06', REC, P, R, 7),  (26, '2026-05-13', CER, P, R, 3),
    (27, '2026-05-20', HAB, P, R, 24), (28, '2026-05-27', SUB, P, R, 14),
    (29, '2026-06-03', REC, W, R, 6),  (30, '2026-06-10', PER, W, R, 47),
    (31, '2026-06-17', HAB, W, R, 18), (32, '2026-06-24', SUB, W, R, 12),
    (33, '2026-07-01', REC, P, R, 8),  (34, '2026-07-08', CER, W, R, 2),
    (35, '2026-07-15', PER, P, T, None), (36, '2026-08-05', SUB, P, T, None),
    (37, '2026-08-12', HAB, W, T, None), (38, '2026-08-24', REC, W, T, None),
    (39, '2026-08-26', PER, W, T, None), (40, '2026-08-27', REC, P, T, None),
]
CORTE = date(2026, 8, 31)

# ----------------------------------------------------------------------------
# Tablas finales (lo que se exporta y se embebe)
# ----------------------------------------------------------------------------
CAB_PERSONAL = ['legajo', 'area', 'situacion', 'edad', 'antiguedad_anios']
CAB_LICENCIAS = ['fecha_inicio', 'legajo', 'area', 'tipo', 'dias', 'costo_dia']
CAB_EXPEDIENTES = ['expediente', 'fecha_inicio', 'area', 'tramite', 'canal', 'estado',
                   'dias_resolucion', 'plazo_dias']

T_PERSONAL = [[leg, a, s, e, t] for (leg, a, s, e, t) in PERSONAL]
T_LICENCIAS = [[f, leg, AGENTE[leg]['area'], tipo, d, AGENTE[leg]['costo']]
               for (f, leg, tipo, d) in LICENCIAS]
T_EXPEDIENTES = [['EX-2026-%04d' % n, f, AREA_DE[tr], tr, can, est,
                  '' if d is None else d, PLAZO[tr]]
                 for (n, f, tr, can, est, d) in EXPEDIENTES]

# ============================================================================
# VERIFICACIONES: cada giro que prometen las misiones
# ============================================================================
fallas = []
contador = [0]
def check(cond, msg):
    contador[0] += 1
    if not cond:
        fallas.append(msg)

def es_num(v):
    return isinstance(v, (int, float))

def agrupar(filas, idx_dim, idx_met=None, filtro=None):
    g = {}
    for f in filas:
        if filtro and not filtro(f):
            continue
        g.setdefault(f[idx_dim], [])
        if idx_met is not None and es_num(f[idx_met]):
            g[f[idx_dim]].append(f[idx_met])
    return g

def top(d):
    orden = sorted(d.items(), key=lambda kv: -kv[1])
    check(len(orden) < 2 or orden[0][1] != orden[1][1], 'empate en el primer puesto: %r' % orden[:2])
    return orden[0][0]

# --- consistencia general ---------------------------------------------------
check(len(PERSONAL) == 40 and len({p[0] for p in PERSONAL}) == 40, 'personal: 40 legajos únicos')
for (leg, a, s, e, t) in PERSONAL:
    check(e - t >= 18, 'legajo %d: ingresó antes de los 18 años' % leg)
for (f, leg, tipo, d) in LICENCIAS:
    check(leg in AGENTE, 'licencia de un legajo inexistente: %d' % leg)
    check(date.fromisoformat(f).weekday() < 5, 'licencia que empieza en fin de semana: %s' % f)
fechas_lic = [r[0] for r in LICENCIAS]
check(len(fechas_lic) == len(set(fechas_lic)), 'hay fechas de licencia repetidas')
# sin superposición de licencias de una misma persona
por_leg = {}
for (f, leg, tipo, d) in LICENCIAS:
    por_leg.setdefault(leg, []).append((date.fromisoformat(f), d if es_num(d) else 1))
for leg, ls in por_leg.items():
    ls.sort()
    for (a, da), (b, _) in zip(ls, ls[1:]):
        check(a + timedelta(days=da) <= b, 'licencias superpuestas del legajo %d' % leg)
check(sum(1 for r in LICENCIAS if not es_num(r[3])) == 1, 'debe haber exactamente 1 dato sucio')
nums = [e[0] for e in EXPEDIENTES]
check(nums == list(range(1, 41)), 'expedientes numerados 1..40 sin huecos')
check([e[1] for e in EXPEDIENTES] == sorted(e[1] for e in EXPEDIENTES), 'nº de expediente crece con la fecha')
for (n, f, tr, can, est, d) in EXPEDIENTES:
    check((est == R) == (d is not None), 'EX %d: estado y días no coinciden' % n)
    if d is not None:
        check(date.fromisoformat(f) + timedelta(days=d) <= CORTE, 'EX %d se resolvería después del corte' % n)

L = T_LICENCIAS            # índices: 0 fecha,1 legajo,2 area,3 tipo,4 dias,5 costo
E = T_EXPEDIENTES          # índices: 0 exp,1 fecha,2 area,3 tramite,4 canal,5 estado,6 dias,7 plazo
dias_area = {k: sum(v) for k, v in agrupar(L, 2, 4).items()}
dot_area = {}
for p in PERSONAL:
    dot_area[p[1]] = dot_area.get(p[1], 0) + 1
med = statistics.median
prom = statistics.mean

# --- Etapa 1 ----------------------------------------------------------------
check(top(dias_area) == SP, 'E1-M3: Servicios Públicos debe perder más días en total')
prom_area = {k: prom(v) for k, v in agrupar(E, 2, 6).items() if v}
med_area = {k: med(v) for k, v in agrupar(E, 2, 6).items() if v}
check(top(prom_area) == HA, 'E1-M4: con PROMEDIO la más lenta debe ser Hacienda')
check(top(med_area) == OP, 'E1-M4: con MEDIANA la más lenta debe ser Obras Públicas')
vacios = sum(1 for e in E if e[6] == '')
check(vacios == 7, 'E1-M5: 7 expedientes en trámite (vacíos)')
op_vals = [e[6] for e in E if e[2] == OP and e[6] != '']
op_cero = [e[6] if e[6] != '' else 0 for e in E if e[2] == OP]
check(prom(op_vals) - prom(op_cero) > 10, 'E1-M5: rellenar con 0 debe «mejorar» Obras más de 10 días')
dias_mes = {}
for f in L:
    if es_num(f[4]):
        dias_mes[f[0][:7]] = dias_mes.get(f[0][:7], 0) + f[4]
check(top(dias_mes) == '2026-06', 'E1-M6: junio debe ser el mes con más días perdidos')
lic_ac = [f for f in L if f[2] == AC]
check(len(lic_ac) == 10 and len({f[1] for f in lic_ac}) == 5, 'E1-M7: Atención Ciudadana = 10 licencias, 5 personas')
edad_sit = {k: prom(v) for k, v in agrupar(T_PERSONAL, 2, 3).items()}
check(top(edad_sit) == PP, 'E1-M8: la planta permanente debe tener la edad promedio más alta')

# --- Etapa 2 ----------------------------------------------------------------
check(top(dot_area) == SP, 'E2-M2: Servicios Públicos debe ser el área más grande')
pp_pct = 100.0 * sum(1 for p in PERSONAL if p[2] == PP) / len(PERSONAL)
check(pp_pct == 55.0, 'E2-M3: la planta permanente debe ser el 55 %%, es %.1f' % pp_pct)
porciones = sum(1 for f in L if es_num(f[4]) and f[4] > 0)
check(porciones == 44, 'E2-M4: la torta de licencias por fecha debe tener 44 porciones')
check(med([e[6] for e in E if e[3] == PER and e[6] != '']) == 48, 'E2-M5: mediana de permiso de obra = 48')
med_canal = {k: med(v) for k, v in agrupar(E, 4, 6).items() if v}
check(med_canal[W] < med_canal[P], 'E2-M7: la Web debe resolver más rápido (mediana)')

# --- Etapa 3 ----------------------------------------------------------------
check(dias_area[OP] == 79 and med_area[OP] == 48, 'E3-M2: Obras = 79 días perdidos y mediana 48')
atraso = {k: med(v) - PLAZO[k] for k, v in agrupar(E, 3, 6).items() if v}
check([k for k, v in atraso.items() if v > 0] == [PER], 'E3-M3: solo el permiso de obra debe estar fuera de plazo')
invierno = sum(f[4] for f in L if es_num(f[4]) and '2026-06-01' <= f[0] <= '2026-07-31')
check(invierno == 116, 'E3-M4: invierno (jun–jul) = 116 días, es %d' % invierno)
total_dias = sum(f[4] for f in L if es_num(f[4]))
check(invierno / total_dias > 0.5, 'E3-M4: el invierno debe concentrar más de la mitad de los días')
costo_tipo, cant_tipo = {}, {}
for f in L:
    cant_tipo[f[3]] = cant_tipo.get(f[3], 0) + 1
    if es_num(f[4]):
        costo_tipo[f[3]] = costo_tipo.get(f[3], 0) + f[4] * f[5]
check(top(cant_tipo) == ENF, 'E3-M6: la enfermedad debe ser la licencia más frecuente')
check(top(costo_tipo) == ACC, 'E3-M6: el accidente de trabajo debe ser lo que más cuesta')
check(costo_tipo[ACC] > 1.1 * costo_tipo[ENF], 'E3-M6: el accidente debe costar al menos 10 % más que la enfermedad')
por_agente = {a: dias_area.get(a, 0) / dot_area[a] for a in dot_area}
check(top(por_agente) == OP, 'E3-M9: Obras Públicas debe perder más días POR AGENTE')
check(len({f[1] for f in L if f[2] == LE}) < 3, 'E3-M7: Legales debe quedar por debajo del umbral de 3 personas')

# ============================================================================
# EXPORTACIÓN
# ============================================================================
def iso_a_ar(v):
    if isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        a, m, d = v.split('-')
        return '%s/%s/%s' % (d, m, a)
    return v

def texto_csv(cab, filas, sep=',', fechas_ar=False):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=sep, lineterminator='\n')
    w.writerow(cab)
    for f in filas:
        w.writerow([iso_a_ar(v) if fechas_ar else v for v in f])
    return buf.getvalue()

TABLAS = [('personal', CAB_PERSONAL, T_PERSONAL),
          ('licencias', CAB_LICENCIAS, T_LICENCIAS),
          ('expedientes', CAB_EXPEDIENTES, T_EXPEDIENTES)]

def exportar():
    for nombre, cab, filas in TABLAS:
        with open(os.path.join(AQUI, nombre + '.csv'), 'w', encoding='utf-8', newline='') as fh:
            fh.write(texto_csv(cab, filas))
        with open(os.path.join(AQUI, nombre + '.tsv'), 'w', encoding='utf-8-sig', newline='') as fh:
            fh.write(texto_csv(cab, filas, sep='\t', fechas_ar=True))
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        print('  (sin openpyxl: no se genera el .xlsx)')
        return
    wb = Workbook()
    wb.remove(wb.active)
    for nombre, cab, filas in TABLAS:
        ws = wb.create_sheet(nombre)
        ws.append(cab)
        for c in ws[1]:
            c.font = Font(bold=True)
        for f in filas:
            fila = []
            for v in f:
                if isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
                    fila.append(date.fromisoformat(v))
                elif v == '':
                    fila.append(None)
                else:
                    fila.append(v)
            ws.append(fila)
        for col in ws.columns:
            ancho = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(ancho + 2, 10), 28)
            for c in col[1:]:
                if isinstance(c.value, date):
                    c.number_format = 'DD/MM/YYYY'
    wb.properties.creator = 'Seminario de TIC'
    wb.properties.title = 'Caso municipio (datos ficticios)'
    wb.save(os.path.join(AQUI, 'bi-gp-municipio.xlsx'))

BLOQUE = re.compile(r'/\*@@DATOS-INICIO@@\*/.*?/\*@@DATOS-FIN@@\*/', re.S)

def bloque_js():
    partes = ['/*@@DATOS-INICIO@@*/',
              '/* Datos generados por bi-gp-datos/generar_datos.py — no editar a mano. */']
    for nombre, cab, filas in TABLAS:
        partes.append('const CSV_%s = `%s`;' % (nombre.upper(), texto_csv(cab, filas).strip()))
    partes.append('/*@@DATOS-FIN@@*/')
    return '\n'.join(partes)

def insertar():
    destinos = ['bi-gp-1-fuentes.html', 'bi-gp-2-informes.html', 'bi-gp-3-interactivo.html',
                os.path.join('bi-gp-datos', 'index.html')]
    for rel in destinos:
        ruta = os.path.join(RAIZ, rel)
        if not os.path.exists(ruta):
            print('  (todavía no existe %s)' % rel)
            continue
        with open(ruta, encoding='utf-8') as fh:
            html = fh.read()
        if not BLOQUE.search(html):
            print('  ⚠ %s no tiene las marcas de datos' % rel)
            continue
        nuevo = BLOQUE.sub(lambda m: bloque_js(), html, count=1)
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
    print('  personal: %d · licencias: %d · expedientes: %d filas'
          % (len(T_PERSONAL), len(T_LICENCIAS), len(T_EXPEDIENTES)))
    exportar()
    insertar()
    if '--resumen' in sys.argv:
        print('\nDías por área:', dias_area)
        print('Días por agente:', {k: round(v, 2) for k, v in por_agente.items()})
        print('Promedio / mediana por área:', {k: (round(prom_area[k], 1), med_area[k]) for k in prom_area})
        print('Mediana por canal:', med_canal)
        print('Atraso mediano por trámite:', atraso)
        print('Días por mes:', dict(sorted(dias_mes.items())))
        print('Invierno:', invierno, 'de', total_dias)
        print('Costo por tipo:', costo_tipo, '\nCantidad por tipo:', cant_tipo)
        print('Costo total:', sum(costo_tipo.values()))
        print('Edad promedio por situación:', {k: round(v, 2) for k, v in edad_sit.items()})
        print('Dotación por área:', dot_area)
        print('Obras: promedio %.2f → con ceros %.2f' % (prom(op_vals), prom(op_cero)))
        resueltos = [e[6] for e in E if e[6] != '']
        print('Mediana global de días: %s · promedio global %.2f → con ceros %.2f'
              % (med(resueltos), prom(resueltos), sum(resueltos) / len(E)))
