"""Rásters de Brooklyn → PNG 8 bits + JSON (georreferencia local en metros).
Recorte = bounds de los rásters de análisis del libro (951×826 celdas de 10 ft)."""
import json, os, numpy as np, rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from PIL import Image
RAW='/private/tmp/claude-501/-Users-leandro-desarrollo-simulador-dron/ace1fa8d-b5d7-401b-9cec-9352135964ff/scratchpad/qgis-inv/nyc/training_dataset/'
OUT='/Users/leandro/desarrollo/simulador-dron/sig-teledeteccion-ii/datos/brooklyn/'
FT=0.3048; X0,Y0,X1,Y1=982199.0,188225.0,991709.0,196485.0; W,H=951,826
FUENTE_NYC='NYC OpenData · dataset de práctica de «QGIS By Example» (Packt)'
def leer(path, shape=(H,W), resamp=Resampling.nearest):
    with rasterio.open(RAW+path) as d:
        win=from_bounds(X0,Y0,X1,Y1,transform=d.transform)
        a=d.read(1,window=win,out_shape=shape,resampling=resamp).astype('float64')
        if d.nodata is not None: a[np.isclose(a,d.nodata)]=np.nan
        a[a<-1e30]=np.nan
        return a
def guardar(id_, a, nombre, tipo, unidad='', clases=None, fuente=FUENTE_NYC, descripcion='', paleta='gris', etapa=None):
    h,w=a.shape; px=(X1-X0)*FT/w
    meta={'formato':'sig-lab-ii/raster/1','id':id_,'nombre':nombre,'archivo':id_+'.png','ancho':w,'alto':h,'pixel_m':round(px,3),
          'origen_sup_izq_m':[0,round((Y1-Y0)*FT,1)],'unidad':unidad,'tipo':tipo,'paleta':paleta,'descripcion':descripcion,'fuente':fuente}
    if etapa: meta['etapa']=etapa
    if tipo=='clases':
        img=np.where(np.isnan(a),0,a).astype('uint8'); meta['clases']=clases; meta['nodata_png']=0
    else:
        v=a[np.isfinite(a)]; lo,hi=float(np.percentile(v,0.2)),float(np.percentile(v,99.8))
        if tipo=='rango': lo,hi=float(np.nanmin(a)),float(np.nanmax(a))
        img=np.full(a.shape,255,'uint8'); ok=np.isfinite(a)
        img[ok]=np.clip(np.round((a[ok]-lo)/(hi-lo+1e-9)*254),0,254).astype('uint8')
        meta.update({'min':round(lo,3),'max':round(hi,3),'nodata_png':255,'valor':'min + png/254·(max−min)'})
    Image.fromarray(img,'L').save(OUT+id_+'.png',optimize=True)
    json.dump(meta,open(OUT+id_+'.json','w'),ensure_ascii=False,indent=0)
    print(f"  {id_:<26} {w}×{h} {tipo:<8} {os.path.getsize(OUT+id_+'.png')/1024:6.0f} KB  {('rango '+str(meta.get('min'))+'…'+str(meta.get('max'))) if tipo!='clases' else str(len(clases))+' clases'}")
dem=leer('06_visibility_analysis/raster/lidar_dem.tif')*FT
guardar('dem',dem,'Elevación del terreno (LiDAR)','continuo','m',descripcion='Modelo digital de elevación derivado de LiDAR 2010, celdas de 10 ft, valores convertidos a metros.',paleta='terreno')
guardar('sombreado',leer('06_visibility_analysis/raster/hillshade.tif'),'Sombreado del relieve','continuo','',descripcion='Hillshade calculado sobre el DEM: cuánta luz recibiría cada celda con el sol al noroeste.',paleta='gris')
CL={'1':{'nombre':'Arbolado','color':'#2f7a3d'},'2':{'nombre':'Césped y arbustos','color':'#9ccb6a'},'3':{'nombre':'Suelo desnudo','color':'#c9a86a'},'4':{'nombre':'Agua','color':'#4d8fd1'},'5':{'nombre':'Edificios','color':'#b4433a'},'6':{'nombre':'Calles y vías','color':'#6b6b6b'},'7':{'nombre':'Otras superficies pavimentadas','color':'#b9b3ad'}}
guardar('cobertura',leer('rasters/landcover_2010.tif'),'Cobertura del suelo 2010','clases',clases=CL,fuente='University of Vermont Spatial Analysis Lab + NYC Urban Field Station (2012), «New York City Landcover 2010 (3ft)», vía «QGIS By Example»',descripcion='Clasificación por objetos a partir de LiDAR 2010 y ortofotos de 4 bandas; exactitud global 96 %. Aquí remuestreada de 3 ft a 10 ft.',paleta='clases')
guardar('ruido_calor',leer('07_suitability_analysis/raster/noise_heatmap_clip.tif',resamp=Resampling.bilinear),'Densidad de denuncias por ruido','continuo','denuncias/celda',descripcion='Mapa de calor de las denuncias por ruido al 311 (celdas de 177 ft), interpolado al recorte.',paleta='calor')
S='07_suitability_analysis/raster/'
for k,(f,nom) in {'proximidad_parques':('parks_proximity','Distancia al parque más cercano'),'proximidad_escuelas':('schools_proximity','Distancia a la escuela más cercana'),'proximidad_subte':('subway_entances_proximity','Distancia a la boca de subte más cercana'),'proximidad_ciclovias':('bike_routes_proximity','Distancia a la ciclovía más cercana'),'proximidad_canchas':('athletic_facilities_proximity','Distancia a la instalación deportiva más cercana')}.items():
    guardar(k,leer(S+f+'.tif')*FT,nom,'continuo','m',descripcion='Etapa 1 de la aptitud: distancia euclidiana desde cada celda a la entidad más cercana.',paleta='distancia',etapa=1)
for k,(f,nom,mx) in {'rango_parques':('parks_proximity_ranks','Rango: parques',3),'rango_escuelas':('schools_proximity_ranks','Rango: escuelas',4),'rango_subte':('subway_entances_proximity_ranks','Rango: subte',4),'rango_ciclovias':('bike_routes_proximity_ranks','Rango: ciclovías',3),'rango_canchas':('athletic_facilities_proximity_ranks','Rango: deportes',5)}.items():
    guardar(k,leer(S+f+'.tif'),nom,'rango','rango 1 (peor) → '+str(mx)+' (mejor)',descripcion='Etapa 2: la distancia reclasificada en rangos ordinales; mayor = más apto.',paleta='rango',etapa=2)
for k,(f,nom) in {'rango_museos':('museumart_ranked','Rango: densidad de museos y galerías'),'rango_arbolado':('tree_ranked','Rango: densidad de arbolado'),'rango_ruido':('noise_ranked','Rango: ruido (menos es mejor)')}.items():
    guardar(k,leer(S+f+'.tif'),nom,'rango','rango',descripcion='Etapa 2 sobre una densidad (celdas de 50 o 175 ft en el original, remuestreadas).',paleta='rango',etapa=2)
guardar('aptitud_libro',leer(S+'suitability.tif'),'Aptitud según el libro (superposición ponderada)','continuo','puntaje',descripcion='Etapa 3: resultado de referencia calculado en QGIS por el autor del libro con sus pesos. El laboratorio permite recalcularla con otros pesos.',paleta='aptitud',etapa=3)
guardar('aptitud_maxima_libro',leer(S+'max_suitability.tif'),'Celdas de aptitud máxima (libro)','clases',clases={'1':{'nombre':'Aptitud máxima','color':'#d62828'}},descripcion='Etapa 4: las celdas que superan el umbral elegido por el autor.',etapa=4)
print("\ntotal brooklyn/:",round(sum(os.path.getsize(OUT+f) for f in os.listdir(OUT))/1048576,2),"MB")
