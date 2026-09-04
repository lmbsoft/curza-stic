"""Destila el dataset de Brooklyn (QGIS By Example · datos abiertos de NYC)
a capas livianas para el Laboratorio SIG y Teledetección II.

Formato propio (no es GIS real, es representación):
  vector  → JSON: coordenadas en METROS locales (origen = esquina inferior
            izquierda del recorte), geometría simplificada y muestreada.
  raster  → PNG de 8 bits + JSON con georreferencia local, escala de valores
            y leyenda. Valor = min + png/254*(max-min); 255 = sin dato.
Recorte: el mismo AOI de 951×826 celdas de 10 ft que usa el libro en sus
análisis de aptitud y visibilidad (≈ 2,9 × 2,5 km sobre el norte de Brooklyn).
"""
import json, os, random, sys, numpy as np, rasterio, shapefile
sys.stdout.reconfigure(line_buffering=True)
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union
from PIL import Image

RAW='/private/tmp/claude-501/-Users-leandro-desarrollo-simulador-dron/ace1fa8d-b5d7-401b-9cec-9352135964ff/scratchpad/qgis-inv/nyc/training_dataset/'
OUT='/Users/leandro/desarrollo/simulador-dron/sig-teledeteccion-ii/datos/brooklyn/'
FT=0.3048
X0,Y0,X1,Y1=982199.0,188225.0,991709.0,196485.0          # bounds de los rásters del libro (ftUS, EPSG:2263)
AOI=box(X0,Y0,X1,Y1); W_M=(X1-X0)*FT; H_M=(Y1-Y0)*FT
ORIGEN={'crs_original':'EPSG:2263 · NAD83 / New York Long Island (ftUS)','x0':X0,'y0':Y0,'factor_a_metros':FT,
        'nota':'x_local = (x_original − x0)·0,3048 ; y_local = (y_original − y0)·0,3048'}
random.seed(2026)
def loc(x,y): return [round((x-X0)*FT,1),round((y-Y0)*FT,1)]
def ring(coords): return [loc(x,y) for x,y in coords]
def geom_out(g):
    t=g.geom_type
    if t=='Point': return {'g':loc(g.x,g.y)}
    if t=='LineString': return {'g':ring(g.coords)}
    if t=='Polygon': return {'g':[ring(g.exterior.coords)]+[ring(i.coords) for i in g.interiors]}
    if t in ('MultiPolygon','MultiLineString','MultiPoint'):
        return {'partes':[geom_out(p)['g'] for p in g.geoms]}
    return None
def capa(shp, id_, nombre, tipo, campos, filtro=None, muestra=None, simp=1.5, descripcion=''):
    r=shapefile.Reader(RAW+'shapefiles/'+shp,encoding='latin-1')
    fields=[f[0] for f in r.fields[1:]]; ents=[]; n_orig=0
    for sr in r.iterShapeRecords():
        n_orig+=1
        bb=getattr(sr.shape,'bbox',None)
        if bb is None:  # punto
            px,py=sr.shape.points[0]
            if not (X0<=px<=X1 and Y0<=py<=Y1): continue
        elif bb[2]<X0 or bb[0]>X1 or bb[3]<Y0 or bb[1]>Y1: continue
        g=shape(sr.shape.__geo_interface__)
        if not g.is_valid: g=g.buffer(0)
        if not g.intersects(AOI): continue
        g=g.intersection(AOI) if tipo!='punto' else g
        if g.is_empty: continue
        rec=dict(zip(fields,sr.record))
        if filtro and not filtro(rec): continue
        if simp and tipo!='punto': g=g.simplify(simp/FT,preserve_topology=True)
        atr={k2:(rec[k1] if not callable(k1) else k1(rec)) for k1,k2 in campos}
        atr={k:(v.strip() if isinstance(v,str) else v) for k,v in atr.items()}
        go=geom_out(g)
        if go: ents.append({'atr':atr,**go})
    if muestra and len(ents)>muestra: ents=random.sample(ents,muestra)
    for i,e in enumerate(ents,1): e['id']=f'{id_[:3]}-{i:04d}'
    out={'formato':'sig-lab-ii/vector/1','id':id_,'nombre':nombre,'geometria':tipo,'unidad':'m','origen':ORIGEN,'bbox':[0,0,round(W_M,1),round(H_M,1)],
         'campos':[{'id':k2,'tipo':'numero' if ents and isinstance(ents[0]['atr'][k2],(int,float)) else 'texto'} for _,k2 in campos],
         'n_original_ciudad':n_orig,'n':len(ents),'simplificacion_m':simp,'descripcion':descripcion,
         'fuente':'NYC OpenData / NYC DoITT · dataset de práctica de «QGIS By Example» (Packt)','entidades':ents}
    json.dump(out,open(OUT+id_+'.json','w'),ensure_ascii=False,separators=(',',':'))
    print(f"  {id_:<22} {tipo:<8} {len(ents):>5} entidades (de {n_orig} en la ciudad) · {os.path.getsize(OUT+id_+'.json')/1024:6.0f} KB")

capa('parks.shp','parques','Parques y plazas','poligono',[('park_name','nombre'),('landuse','uso'),('statu_desc','estado')],descripcion='Polígonos del sistema de parques de la ciudad.')
capa('public_schools.shp','escuelas','Escuelas públicas','punto',[('schoolname','nombre'),('sch_type','tipo'),('zip','cp')],descripcion='Escuelas públicas con su tipo (elemental, media, secundaria).')
capa('subway_stations.shp','estaciones','Estaciones de subte','punto',[('name','nombre'),('line','lineas')])
capa('subway_entrances.shp','bocas_subte','Bocas de subte','punto',[('name','nombre'),('line','lineas')],descripcion='Accesos a la red de subte: la capa que el libro usa para la proximidad.')
capa('bike_routes.shp','ciclovias','Ciclovías','linea',[('street','calle'),('onoffst','tipo'),('allclasses','clase')])
capa('museums.shp','museos','Museos','punto',[('name','nombre'),('zip','cp')])
capa('art_galleries.shp','galerias','Galerías de arte','punto',[('name','nombre'),('zip','cp')])
capa('athletic_facilities.shp','canchas','Instalaciones deportivas','poligono',[('name','nombre'),('primary_sp','deporte'),('surface_ty','superficie')])
capa('hurricane_evacuation_zones.shp','zonas_evacuacion','Zonas de evacuación por huracán','poligono',[('zone','zona')],simp=3,descripcion='Zona 1 = evacuar primero. Datos de la Oficina de Emergencias de NYC.')
capa('hurricane_inundation_zones.shp','zonas_inundacion','Zonas de inundación por huracán','poligono',[('category','categoria')],simp=3,descripcion='Categoría de huracán (Saffir-Simpson) a partir de la cual la zona se inunda.')
capa('zipcode.shp','codigos_postales','Códigos postales','poligono',[('zipcode','cp'),('po_name','localidad'),('population','poblacion')],simp=3)
capa('roads.shp','calles','Calles','linea',[('name','nombre'),('type','tipo'),('oneway','mano_unica')],filtro=lambda r:(r.get('type') or '') in ('primary','secondary','tertiary','residential','motorway','trunk','primary_link','secondary_link'),simp=2,descripcion='Calles (OpenStreetMap), solo las de circulación vehicular.')
capa('wifi_public.shp','wifi','Wi-Fi público','punto',[('name','nombre'),('provider','proveedor'),('type','tipo')])
capa('colleges_universities.shp','universidades','Universidades','punto',[('name','nombre')])
capa('trees.shp','arboles','Arbolado urbano (muestra)','punto',[('ONSTREET','calle'),('SITE','sitio')],muestra=2500,descripcion='Muestra aleatoria de 2.500 de los árboles relevados dentro del recorte.')
capa('noise.shp','ruido','Denuncias por ruido (muestra)','punto',[('complaint_','tipo'),('descriptor','detalle'),('location_t','lugar')],muestra=1200,descripcion='Muestra de denuncias al 311 por ruido.')
capa('bicycle_parking.shp','bicicleteros','Bicicleteros','punto',[('capacity','capacidad'),('covered','cubierto')])
