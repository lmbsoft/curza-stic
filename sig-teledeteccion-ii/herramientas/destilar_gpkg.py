"""Escenas vectoriales de «Learn QGIS, 5.ª ed.» (Packt, MIT) → JSON liviano en metros locales.
Cada escena se proyecta a su zona UTM y se traslada al origen local (esquina inferior izquierda)."""
import json, os, sqlite3, numpy as np
from shapely import wkb
from shapely.ops import transform as stransform
from pyproj import Transformer, CRS
G='/private/tmp/claude-501/-Users-leandro-desarrollo-simulador-dron/ace1fa8d-b5d7-401b-9cec-9352135964ff/scratchpad/qgis-inv/gpkg/'
OUT='/Users/leandro/desarrollo/simulador-dron/sig-teledeteccion-ii/datos/'
def leer(f,t):
    con=sqlite3.connect(G+f+'.gpkg'); cur=con.cursor()
    gc=cur.execute("select column_name from gpkg_geometry_columns where table_name=?",(t,)).fetchone()[0]
    srs=cur.execute("select s.organization_coordsys_id from gpkg_contents c join gpkg_spatial_ref_sys s on s.srs_id=c.srs_id where c.table_name=?",(t,)).fetchone()[0]
    cols=[r[1] for r in cur.execute(f'pragma table_info("{t}")')]; out=[]
    for row in cur.execute(f'select * from "{t}"'):
        d=dict(zip(cols,row)); blob=d.pop(gc)
        if blob is None: continue
        envl=(blob[3]>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[envl]
        out.append((wkb.loads(bytes(blob[hdr:])),d))
    return out,srs
def escena(carpeta, nombre, capas, utm_epsg, fuente, descripcion, recorte_km=None, centro_capa=None):
    os.makedirs(OUT+carpeta,exist_ok=True)
    datos={}; allx=[]; ally=[]
    for cid,(f,t,tipo,campos,simp,nom,desc) in capas.items():
        feats,srs=leer(f,t)
        tr=Transformer.from_crs(CRS.from_epsg(srs if srs!=900913 else 3857),CRS.from_epsg(utm_epsg),always_xy=True)
        gs=[(stransform(tr.transform,g),a) for g,a in feats]
        datos[cid]=(gs,tipo,campos,simp,nom,desc,f,t,len(feats))
        for g,_ in gs: b=g.bounds; allx+=[b[0],b[2]]; ally+=[b[1],b[3]]
    if recorte_km:
        from shapely.geometry import box
        c=datos[centro_capa][0][0][0].centroid; r=recorte_km*500
        caja=box(c.x-r,c.y-r,c.x+r,c.y+r)
        for cid in datos:
            gs=[(g.intersection(caja),a) for g,a in datos[cid][0]]; gs=[(g,a) for g,a in gs if not g.is_empty]
            datos[cid]=(gs,)+datos[cid][1:]
        allx=[c.x-r,c.x+r]; ally=[c.y-r,c.y+r]
    x0,y0=min(allx),min(ally); W=max(allx)-x0; H=max(ally)-y0
    pad=0.02*max(W,H); x0-=pad; y0-=pad; W+=2*pad; H+=2*pad
    def loc(x,y): return [round(x-x0,1),round(y-y0,1)]
    def ring(c): return [loc(x,y) for x,y in c]
    def go(g):
        t=g.geom_type
        if t=='Point': return {'g':loc(g.x,g.y)}
        if t=='LineString': return {'g':ring(g.coords)}
        if t=='Polygon': return {'g':[ring(g.exterior.coords)]+[ring(i.coords) for i in g.interiors]}
        return {'partes':[go(p)['g'] for p in g.geoms]}
    manif={'escena':carpeta,'nombre':nombre,'bbox':[0,0,round(W,1),round(H,1)],'unidad':'m','crs_local':f'EPSG:{utm_epsg} trasladado al origen local ({x0:.0f}, {y0:.0f})','fuente':fuente,'descripcion':descripcion,'capas':[]}
    for cid,(gs,tipo,campos,simp,nom,desc,f,t,n0) in datos.items():
        ents=[]
        for i,(g,a) in enumerate(gs,1):
            if simp and tipo!='punto': g=g.simplify(simp,preserve_topology=True)
            if g.is_empty: continue
            atr={k2:a.get(k1) for k1,k2 in campos}
            ents.append({'id':f'{cid[:3]}-{i:03d}','atr':atr,**go(g)})
        out={'formato':'sig-lab-ii/vector/1','id':cid,'nombre':nom,'geometria':tipo,'unidad':'m','bbox':manif['bbox'],'campos':[{'id':k2,'tipo':'numero' if ents and isinstance(ents[0]['atr'][k2],(int,float)) else 'texto'} for _,k2 in campos],
             'n_original':n0,'n':len(ents),'simplificacion_m':simp,'descripcion':desc,'fuente':f'{fuente} · archivo {f}.gpkg, tabla «{t}»','entidades':ents}
        json.dump(out,open(OUT+carpeta+'/'+cid+'.json','w'),ensure_ascii=False,separators=(',',':'))
        manif['capas'].append({'id':cid,'archivo':cid+'.json'})
        print(f"  {carpeta:<12} {cid:<16} {tipo:<8} n={len(ents):>4}  {os.path.getsize(OUT+carpeta+'/'+cid+'.json')/1024:6.0f} KB")
    json.dump(manif,open(OUT+carpeta+'/escena.json','w'),ensure_ascii=False,indent=1)
    print(f"  → {carpeta}: {W/1000:.1f} × {H/1000:.1f} km")
LQ='«Learn QGIS, 5th ed.» (Sarafova & Ivanov, Packt 2025, repositorio MIT) · datos derivados de OpenStreetMap (© colaboradores de OSM, ODbL)'
# La escena del capítulo 8 se descartó: sus capas están en lugares distintos (India, Alaska y Costa Rica); el ejercicio de buffer/selección se hace con Brooklyn y Ámsterdam.
escena('kilimanjaro','Kilimanjaro · cumbre, glaciares y ríos',{
  'limite':('Area','Area','poligono',[('protect_class','clase_proteccion')],20,'Parque nacional','Límite del Parque Nacional Kilimanjaro (OSM).'),
  'cumbre':('Peak','Peak','punto',[('natural','tipo'),('volcano:status','estado_volcan')],0,'Cumbre','Punto de la cumbre.'),
  'glaciares':('Glacier','Glacier','poligono',[('natural','tipo'),('wikipedia','wikipedia')],5,'Glaciares','Los seis glaciares que quedan en la cima.'),
  'rios':('River','River','linea',[('waterway','tipo'),('name:en','nombre')],15,'Ríos y arroyos','Cursos de agua que bajan de la montaña.')},
  32737,LQ,'Ejercicio del capítulo 5: tres tipos de geometría en un mismo lugar —punto, línea y polígono— con sus atributos.',recorte_km=30,centro_capa='cumbre')
escena('amsterdam','Ámsterdam · cafés, veredas y barrios',{
  'barrios':('Amsterdam_neigh','place_neighbourhood_amsterdam','poligono',[('name','nombre')],3,'Barrios','Barrios del centro (OSM).'),
  'cafes':('Amsterdam_cafes','amenity_cafe','punto',[('name','nombre'),('organic','organico')],0,'Cafés','Cafés relevados en OSM.'),
  'veredas':('Amsterdam_footway','Footway','linea',[('highway','tipo')],2,'Sendas peatonales','Sendas y veredas peatonales (OSM).')},
  32631,LQ,'Ejercicio del capítulo 9: ¿cuántos cafés tiene cada barrio? Unión espacial por ubicación y proximidad a pie.')
