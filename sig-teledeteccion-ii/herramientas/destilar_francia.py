"""Francia: ráster de densidad de población (WorldPop 2020, 1 km) + contornos (Natural Earth) → escena liviana."""
import json, os, numpy as np, rasterio, shapefile
from rasterio.enums import Resampling
from shapely.geometry import shape, box
from shapely.ops import transform as stransform
from pyproj import Transformer
from PIL import Image
RAW='/private/tmp/claude-501/-Users-leandro-desarrollo-simulador-dron/ace1fa8d-b5d7-401b-9cec-9352135964ff/scratchpad/qgis-inv/Learn-QGIS-Fifth-Edition-main/Chapter_3/'
OUT='/Users/leandro/desarrollo/simulador-dron/sig-teledeteccion-ii/datos/francia/'; os.makedirs(OUT,exist_ok=True)
# 1) ráster: bajar a 1/3 de resolución (≈ 2,8 km) promediando; escala logarítmica para el PNG
with rasterio.open(RAW+'fra_pd_2020_1km_UNadj.tif') as d:
    a=d.read(1,out_shape=(d.height//3,d.width//3),resampling=Resampling.average).astype('float64'); nd=d.nodata; b=d.bounds
a[a<=nd+1]=np.nan if nd is not None else np.nan
h,w=a.shape; lon0,lat1=b.left,b.top; dlon=(b.right-b.left)/w; dlat=(b.top-b.bottom)/h
# georreferencia local: proyección Lambert-93 (EPSG:2154), metros
tr=Transformer.from_crs(4326,2154,always_xy=True)
xs=[tr.transform(b.left,b.bottom)[0],tr.transform(b.left,b.top)[0]]; ys=[tr.transform(b.left,b.bottom)[1],tr.transform(b.right,b.bottom)[1]]
# el ráster está en grados: lo dejo en grados pero declaro el tamaño de celda medio en km para el laboratorio
lat_c=(b.top+b.bottom)/2; px_m_x=dlon*111320*np.cos(np.radians(lat_c)); px_m_y=dlat*110574
W_M=w*px_m_x; H_M=h*px_m_y
v=a[np.isfinite(a)]; lo=0.0; hi=float(np.percentile(v,99.5))
img=np.full(a.shape,255,'uint8'); ok=np.isfinite(a)
img[ok]=np.clip(np.round(np.log1p(a[ok])/np.log1p(hi)*254),0,254).astype('uint8')
Image.fromarray(img,'L').save(OUT+'poblacion.png',optimize=True)
json.dump({'formato':'sig-lab-ii/raster/1','id':'poblacion','nombre':'Densidad de población 2020','archivo':'poblacion.png','ancho':w,'alto':h,'pixel_m':round((px_m_x+px_m_y)/2),'pixel_m_x':round(px_m_x),'pixel_m_y':round(px_m_y),
  'origen_sup_izq_m':[0,round(H_M)],'unidad':'hab/km²','tipo':'continuo','escala':'log','min':lo,'max':round(hi,1),'nodata_png':255,'valor':'expm1(png/254·log1p(max))','paleta':'poblacion',
  'descripcion':'Personas por km² estimadas para 2020 (ajustado a Naciones Unidas). Original de 1 km, aquí promediado a celdas de ≈ 2,8 km. Un ráster de valores continuos: cada celda guarda un número, no un color.',
  'fuente':'WorldPop (2020), «France population density 2020 UN-adjusted, 1 km», CC BY 4.0, distribuido con el repositorio de «Learn QGIS, 5.ª ed.» (Packt, MIT)'},open(OUT+'poblacion.json','w'),ensure_ascii=False,indent=0)
print(f"  poblacion.png {w}×{h} · {os.path.getsize(OUT+'poblacion.png')/1024:.0f} KB · máx {hi:.0f} hab/km² · celda ≈ {px_m_x/1000:.1f} km")
# 2) contornos de países (Natural Earth 1:10m) en coordenadas locales (grados → metros aprox. con la misma escala que el ráster)
def loc(lon,lat): return [round((lon-lon0)*px_m_x/dlon,0),round((lat-(b.bottom))*px_m_y/dlat,0)]
r=shapefile.Reader(RAW+'ne_10m_admin_0_countries/ne_10m_admin_0_countries',encoding='utf-8'); fld=[f[0] for f in r.fields[1:]]
i_n=fld.index('NAME'); i_p=fld.index('POP_EST'); i_e=fld.index('NAME_ES') if 'NAME_ES' in fld else None
caja=box(b.left,b.bottom,b.right,b.top); ents=[]
for rec,shp in zip(r.iterRecords(),r.iterShapes()):
    g=shape(shp.__geo_interface__)
    if not g.intersects(caja): continue
    g=g.intersection(caja).simplify(0.02,preserve_topology=True)
    if g.is_empty: continue
    def go(g):
        if g.geom_type=='Polygon': return {'g':[[loc(x,y) for x,y in g.exterior.coords]]}
        return {'partes':[[[loc(x,y) for x,y in p.exterior.coords]] for p in g.geoms if p.geom_type=='Polygon']}
    ents.append({'id':'pais-'+str(len(ents)+1),'atr':{'nombre':rec[i_e] if i_e else rec[i_n],'poblacion_est':int(rec[i_p]) if rec[i_p] else None},**go(g)})
json.dump({'formato':'sig-lab-ii/vector/1','id':'paises','nombre':'Países','geometria':'poligono','unidad':'m','bbox':[0,0,round(W_M),round(H_M)],'campos':[{'id':'nombre','tipo':'texto'},{'id':'poblacion_est','tipo':'numero'}],'n':len(ents),
  'descripcion':'Contornos de Francia y sus vecinos, simplificados (≈ 2 km).','fuente':'Natural Earth 1:10m Admin 0 (dominio público), con el repositorio de «Learn QGIS, 5.ª ed.»','entidades':ents},open(OUT+'paises.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump({'escena':'francia','nombre':'Francia · un ráster de población','bbox':[0,0,round(W_M),round(H_M)],'unidad':'m','crs_local':'grados WGS84 escalados a metros (aprox. equirrectangular en 46° N)','capas':[{'id':'paises','archivo':'paises.json'}],'rasters':[{'id':'poblacion','archivo':'poblacion.json'}],
  'descripcion':'Ejercicio del capítulo 3: un ráster de valores continuos (personas por km²) y cómo leerlo: identificar celdas, estirar el contraste, clasificar.'},open(OUT+'escena.json','w'),ensure_ascii=False,indent=1)
print(f"  paises.json: {len(ents)} países · {os.path.getsize(OUT+'paises.json')/1024:.0f} KB · escena {W_M/1000:.0f} × {H_M/1000:.0f} km")
