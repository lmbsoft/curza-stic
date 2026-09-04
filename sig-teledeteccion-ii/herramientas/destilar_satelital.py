"""Bandas satelitales (Sentinel-2 L2A y Landsat 8 C2 L2) → PNG 8 bits por banda + escena.json.
Los recortes se bajaron por ventana desde COGs públicos (Earth Search / Planetary Computer)."""
import json, os, numpy as np
from PIL import Image
from pyproj import Transformer
S='/private/tmp/claude-501/-Users-leandro-desarrollo-simulador-dron/ace1fa8d-b5d7-401b-9cec-9352135964ff/scratchpad/s2/'
OUT='/Users/leandro/desarrollo/simulador-dron/sig-teledeteccion-ii/datos/'
def bbox_local(aoi, epsg):
    tr=Transformer.from_crs(4326,epsg,always_xy=True)
    xs,ys=zip(*[tr.transform(aoi[0],aoi[1]),tr.transform(aoi[2],aoi[1]),tr.transform(aoi[2],aoi[3]),tr.transform(aoi[0],aoi[3])])
    return min(xs),min(ys),max(xs),max(ys)
def png_banda(carpeta, id_, refl, nombre, lam, pixel_m, H_M, extra=None):
    ok=np.isfinite(refl); lo=0.0; hi=float(np.percentile(refl[ok],99.9)); hi=max(hi,0.05)
    img=np.full(refl.shape,255,'uint8'); img[ok]=np.clip(np.round(refl[ok]/hi*254),0,254).astype('uint8')
    Image.fromarray(img,'L').save(OUT+carpeta+'/'+id_+'.png',optimize=True)
    meta={'formato':'sig-lab-ii/raster/1','id':id_,'nombre':nombre,'archivo':id_+'.png','ancho':int(refl.shape[1]),'alto':int(refl.shape[0]),'pixel_m':pixel_m,'origen_sup_izq_m':[0,round(H_M,1)],
          'unidad':'reflectancia','tipo':'banda','longitud_onda':lam,'min':lo,'max':round(hi,4),'nodata_png':255,'valor':'png/254·max'}
    if extra: meta.update(extra)
    json.dump(meta,open(OUT+carpeta+'/'+id_+'.json','w'),ensure_ascii=False,indent=0)
    return os.path.getsize(OUT+carpeta+'/'+id_+'.png')
def png_clases(carpeta,id_,a,nombre,clases,pixel_m,H_M,desc):
    Image.fromarray(a.astype('uint8'),'L').save(OUT+carpeta+'/'+id_+'.png',optimize=True)
    json.dump({'formato':'sig-lab-ii/raster/1','id':id_,'nombre':nombre,'archivo':id_+'.png','ancho':int(a.shape[1]),'alto':int(a.shape[0]),'pixel_m':pixel_m,'origen_sup_izq_m':[0,round(H_M,1)],'tipo':'clases','clases':clases,'nodata_png':0,'descripcion':desc,'paleta':'clases'},open(OUT+carpeta+'/'+id_+'.json','w'),ensure_ascii=False,indent=0)
SCL={'1':{'nombre':'Saturado o defectuoso','color':'#ff0004'},'2':{'nombre':'Sombra oscura','color':'#3b3b3b'},'3':{'nombre':'Sombra de nube','color':'#8a5a2b'},'4':{'nombre':'Vegetación','color':'#3fa34d'},'5':{'nombre':'Sin vegetación','color':'#d9c27a'},'6':{'nombre':'Agua','color':'#2f6fd1'},'7':{'nombre':'Nube (baja probabilidad)','color':'#a3a3a3'},'8':{'nombre':'Nube (media)','color':'#c8c8c8'},'9':{'nombre':'Nube (alta)','color':'#f2f2f2'},'10':{'nombre':'Cirro','color':'#7fd3f7'},'11':{'nombre':'Nieve o hielo','color':'#e6f7ff'}}
S2B={'B02':('Azul','490 nm'),'B03':('Verde','560 nm'),'B04':('Rojo','665 nm'),'B08':('Infrarrojo cercano (NIR)','842 nm'),'B11':('Infrarrojo de onda corta 1 (SWIR1)','1610 nm'),'B12':('Infrarrojo de onda corta 2 (SWIR2)','2190 nm')}
L8B={'blue':('B2','Azul','482 nm'),'green':('B3','Verde','562 nm'),'red':('B4','Rojo','655 nm'),'nir08':('B5','Infrarrojo cercano (NIR)','865 nm'),'swir16':('B6','SWIR1','1610 nm'),'swir22':('B7','SWIR2','2200 nm')}
def sentinel(carpeta, prefijo, aoi, epsg, meta_fecha, sufijo='', etiqueta=''):
    x0,y0,x1,y1=bbox_local(aoi,epsg); H_M=y1-y0; total=0; bandas=[]
    for b,(nom,lam) in S2B.items():
        a=np.load(f'{S}{prefijo}_{b}.npy').astype('float64'); refl=a/10000.0
        px=10 if b in ('B02','B03','B04','B08') else 20
        # las de 20 m ya vienen sobremuestreadas a 10 m en Viedma; en Alerces se leyeron a 10 m
        px=round((x1-x0)/a.shape[1],2)
        total+=png_banda(carpeta,f'{sufijo}{b}',refl,f'{etiqueta}{b} · {nom}',lam,px,H_M,{'sensor':'Sentinel-2 MSI (L2A)','banda':b,'resolucion_nativa_m':10 if b in ('B02','B03','B04','B08') else 20,'escala_original':'DN/10000 = reflectancia de superficie'})
        bandas.append({'id':f'{sufijo}{b}','archivo':f'{sufijo}{b}.json'})
    scl=np.load(f'{S}{prefijo}_SCL.npy')
    if scl.shape!=a.shape:
        scl=np.kron(scl,np.ones((a.shape[0]//scl.shape[0]+1,a.shape[1]//scl.shape[1]+1),dtype=scl.dtype))[:a.shape[0],:a.shape[1]]
    png_clases(carpeta,f'{sufijo}SCL',scl,f'{etiqueta}Clasificación de escena (SCL)',SCL,round((x1-x0)/a.shape[1],2),H_M,'Máscara de calidad que genera el procesador L2A: qué píxeles son nube, sombra, agua o vegetación. Sirve para saber qué NO analizar.')
    bandas.append({'id':f'{sufijo}SCL','archivo':f'{sufijo}SCL.json'})
    return bandas,total,[x0,y0,x1,y1]
def landsat(carpeta, aoi, epsg, sufijo='L8_'):
    x0,y0,x1,y1=bbox_local(aoi,epsg); H_M=y1-y0; total=0; bandas=[]
    for key,(b,nom,lam) in L8B.items():
        a=np.load(f'{S}viedma_landsat_{key}.npy').astype('float64'); refl=a*0.0000275-0.2; refl[a==0]=np.nan
        px=round((x1-x0)/a.shape[1],2)
        total+=png_banda(carpeta,f'{sufijo}{b}',refl,f'Landsat {b} · {nom}',lam,px,H_M,{'sensor':'Landsat 8 OLI (Collection 2, Level 2)','banda':b,'resolucion_nativa_m':30,'escala_original':'DN·0,0000275 − 0,2 = reflectancia de superficie'})
        bandas.append({'id':f'{sufijo}{b}','archivo':f'{sufijo}{b}.json'})
    qa=np.load(f'{S}viedma_landsat_qa_pixel.npy'); cl=np.ones(qa.shape,'uint8')*1
    cl[(qa>>7)&1==1]=2; cl[((qa>>3)&1==1)|((qa>>4)&1==1)]=3; cl[qa==1]=0
    png_clases(carpeta,f'{sufijo}QA',cl,'Landsat · máscara de calidad (QA_PIXEL simplificada)',{'1':{'nombre':'Despejado','color':'#d9c27a'},'2':{'nombre':'Agua','color':'#2f6fd1'},'3':{'nombre':'Nube o sombra','color':'#c8c8c8'}},round((x1-x0)/a.shape[1],2),H_M,'Bits de calidad del píxel resumidos en tres clases.')
    bandas.append({'id':f'{sufijo}QA','archivo':f'{sufijo}QA.json'})
    return bandas,total,[x0,y0,x1,y1]
# ── Viedma ──
m=json.load(open(S+'viedma_meta.json')); AOI=[-63.07,-40.86,-62.93,-40.77]; ep=int(str(m['epsg']).split(':')[-1])
os.makedirs(OUT+'viedma',exist_ok=True)
bS2,tS2,bb=sentinel('viedma','viedma',AOI,ep,m['fecha'],sufijo='S2_',etiqueta='Sentinel-2 ')
ml=json.load(open(S+'viedma_landsat_meta.json')); bL8,tL8,bb2=landsat('viedma',AOI,int(str(ml['epsg']).split(':')[-1]))
W=bb[2]-bb[0]; H=bb[3]-bb[1]
json.dump({'escena':'viedma','nombre':'Valle de Viedma · dos satélites, un mismo lugar','bbox':[0,0,round(W,1),round(H,1)],'unidad':'m','crs_local':f'EPSG:{ep} (UTM 20 S) trasladado al origen local','lonlat':AOI,
  'sensores':[{'id':'S2','nombre':'Sentinel-2 (ESA / Copernicus)','fecha':m['fecha'],'tesela':m['tesela'],'nubes_pct':m['nubes'],'item':m['id'],'pixel_m':10,'bandas':bS2},
              {'id':'L8','nombre':'Landsat 8 (NASA / USGS)','fecha':ml['fecha'],'plataforma':ml['plataforma'],'nubes_pct':ml['nubes'],'item':ml['id'],'pixel_m':30,'bandas':bL8}],
  'descripcion':'Viedma, Carmen de Patagones, el río Negro y el valle irrigado, en verano. La misma escena vista por dos sensores con distinta resolución: composiciones de bandas, NDVI y qué se pierde al pasar de 10 m a 30 m.',
  'fuente':'Sentinel-2 L2A © ESA / Copernicus Sentinel data 2026, vía Earth Search (Element 84) · Landsat 8 C2 L2 cortesía del U.S. Geological Survey, vía Microsoft Planetary Computer'},open(OUT+'viedma/escena.json','w'),ensure_ascii=False,indent=1)
print(f"  viedma: S2 {tS2/1024:.0f} KB + L8 {tL8/1024:.0f} KB · escena {W/1000:.1f} × {H/1000:.1f} km")
# ── Los Alerces (antes / después) ──
ma=json.load(open(S+'alerces_meta.json'))
if all(os.path.exists(f'{S}alerces_{t}_{b}.npy') for t in ('pre','post') for b in list(S2B)+['SCL']):
    os.makedirs(OUT+'alerces',exist_ok=True); ep=int(str(ma['epsg']).split(':')[-1])
    bP,tP,bb=sentinel('alerces','alerces_pre',ma['aoi'],ep,ma['pre']['fecha'],sufijo='pre_',etiqueta='Antes · ')
    bQ,tQ,_=sentinel('alerces','alerces_post',ma['aoi'],ep,ma['post']['fecha'],sufijo='post_',etiqueta='Después · ')
    W=bb[2]-bb[0]; H=bb[3]-bb[1]
    json.dump({'escena':'alerces','nombre':'Los Alerces · antes y después del incendio','bbox':[0,0,round(W,1),round(H,1)],'unidad':'m','crs_local':f'EPSG:{ep} trasladado al origen local','lonlat':ma['aoi'],'centro_lonlat':ma['centro'],
      'fechas':{'antes':ma['pre']['fecha'],'despues':ma['post']['fecha']},'tesela':ma['tesela'],'items':{'antes':ma['pre']['id'],'despues':ma['post']['id']},'pixel_m':10,'bandas_antes':bP,'bandas_despues':bQ,
      'descripcion':'Parque Nacional Los Alerces (Chubut). El incendio comenzó el 25 de enero de 2024. Dos escenas Sentinel-2 sin nubes, una de cinco días antes y otra de tres semanas después: NBR de cada fecha, dNBR y estimación del área quemada.',
      'fuente':'Sentinel-2 L2A © ESA / Copernicus Sentinel data 2024, vía Earth Search (Element 84)'},open(OUT+'alerces/escena.json','w'),ensure_ascii=False,indent=1)
    print(f"  alerces: antes {tP/1024:.0f} KB + después {tQ/1024:.0f} KB · escena {W/1000:.1f} × {H/1000:.1f} km")
else: print("  alerces: bandas incompletas, se exporta después")
