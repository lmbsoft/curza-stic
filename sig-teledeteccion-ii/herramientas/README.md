# Herramientas de destilado

Scripts que producen `../datos/` a partir de los ejemplos de los libros y de las
escenas satelitales. Son reproducibles; no hace falta correrlos para usar el
laboratorio (los datos ya están generados).

**Entradas** (fuera del repo, en `qgis-packt/` del proyecto):
- `9781782174677.zip` → *QGIS By Example*, `training_dataset/` (Brooklyn). Descomprimir.
- `Learn-QGIS-Fifth-Edition-main.zip` → *Learn QGIS 5.ª ed.*; descomprimir y extraer los
  `.gpkg` de los zips internos de cada capítulo a una carpeta `gpkg/`.
- Escenas satelitales: se bajan por ventana con `rasterio` desde Earth Search
  (Sentinel‑2, bucket público `sentinel-cogs`) y Planetary Computer (Landsat 8,
  token SAS anónimo de la colección `landsat-c2-l2`). Ver `destilar_satelital.py`
  para el formato de los `.npy` intermedios y `FUENTES.md` para las fechas e ids.

**Entorno:** Python 3.9 con `numpy pyshp shapely pyproj rasterio pillow scipy requests`.
Las rutas `RAW`/`S` al principio de cada script apuntan a la carpeta de trabajo
donde se descomprimieron las entradas: ajustarlas antes de correr.

**Formato de salida** (`sig-lab-ii/vector/1` y `sig-lab-ii/raster/1`):
- Vector: JSON con `entidades[{id, atr{}, g | partes}]`, coordenadas en metros locales
  (origen = esquina inferior izquierda de la escena), geometría simplificada.
- Ráster: PNG de 8 bits + JSON con `pixel_m`, `origen_sup_izq_m`, `min`/`max` (valor =
  `min + png/254·(max−min)`, 255 = sin dato), o `clases{}` para rásters temáticos,
  o `escala: log` para la población.
