# Fuentes y atribuciones · Laboratorio SIG y Teledetección II

Todo lo que carga este laboratorio es un **destilado propio, liviano y sintético en
formato** (JSON + PNG de 8 bits, coordenadas en metros locales) construido a partir
de datos reales. No son los archivos originales ni sirven para análisis real:
sirven para *representar* lo que se hace en cada etapa de un procesamiento SIG.
Los originales, en sus formatos (Shapefile, GeoPackage, GeoTIFF, COG), se citan
abajo. Las herramientas que hicieron el destilado están en `herramientas/` y son
reproducibles.

## Datos de los libros (curados por sus autores)

| Escena | Origen | Licencia / atribución |
|---|---|---|
| **Brooklyn** (vectores y rásters) | Dataset de práctica de *QGIS By Example* (Packt). Capas de **NYC OpenData** (parques, escuelas, subte, ciclovías, museos, galerías, instalaciones deportivas, zonas de evacuación e inundación por huracán, códigos postales, wifi, bicicleteros, árboles, denuncias por ruido al 311) y calles de **OpenStreetMap**. | NYC OpenData: datos abiertos de la Ciudad de Nueva York. OSM: © colaboradores de OpenStreetMap, ODbL. |
| **Brooklyn · cobertura del suelo 2010** | *New York City Landcover 2010 (3 ft)*, University of Vermont Spatial Analysis Laboratory y NYC Urban Field Station (USDA Forest Service), 2012. Financiado por NUCFAC y NSF. Metadatos FGDC incluidos en el dataset. Aquí remuestreada de 3 ft a 10 ft. | Uso público para fines educativos; citar al originador. |
| **Brooklyn · relieve LiDAR y sombreado** | DEM LiDAR de NYC (2010) distribuido con *QGIS By Example*, en pies, aquí convertido a metros. | NYC OpenData. |
| **Brooklyn · etapas de aptitud** | Rásters intermedios (distancias, rangos, densidades) y resultado final calculados por el autor del libro en el capítulo 7 de *QGIS By Example*. Se muestran como referencia; el laboratorio recalcula la superposición con pesos propios. | Packt Publishing, material de soporte del libro. |
| **Kilimanjaro** | Capítulo 5 de *Learn QGIS, 5.ª ed.* (Sarafova & Ivanov, Packt 2025). Repositorio de código bajo licencia MIT (© 2025 Packt). Datos derivados de OpenStreetMap. | MIT (repositorio) · OSM © colaboradores, ODbL. |
| **Ámsterdam** | Capítulo 9 de *Learn QGIS, 5.ª ed.*: cafés, sendas peatonales y barrios, derivados de OpenStreetMap. | MIT (repositorio) · OSM © colaboradores, ODbL. |
| **Francia · población** | *France population density 2020, UN-adjusted, 1 km* (**WorldPop**, Universidad de Southampton), distribuido con el capítulo 3 de *Learn QGIS, 5.ª ed.* Aquí promediado a celdas de ≈ 2 km. | CC BY 4.0 — WorldPop (www.worldpop.org). |
| **Francia · países** | *Natural Earth* 1:10m, Admin 0 – Countries, distribuido con el mismo capítulo. Simplificado a ≈ 2 km. | Dominio público (Natural Earth). |

Se descartó la escena del capítulo 8 de *Learn QGIS* porque sus capas están en
lugares distintos (India, Alaska y Costa Rica): es un ejercicio abstracto y no
representa un territorio. *Practical GIS* (Packt) se consultó pero no aporta datos
utilizables aquí.

## Imágenes satelitales (descargadas para este laboratorio)

Se bajaron **solo recortes por ventana** desde archivos COG públicos; nunca la
escena completa. Las bandas se guardan como PNG de 8 bits con su factor de escala
en el JSON acompañante.

| Escena | Producto | Atribución |
|---|---|---|
| **Valle de Viedma · Sentinel-2** | Sentinel-2 MSI, nivel L2A (reflectancia de superficie), tesela 20GMV, 19 de febrero de 2026, 0 % de nubes. Bandas B02, B03, B04, B08 (10 m), B11, B12 (20 m) y la máscara SCL. Obtenida vía **Earth Search** (Element 84) desde el bucket público `sentinel-cogs`. | Contiene datos modificados de Copernicus Sentinel (2026), © ESA. Uso libre con atribución (Copernicus Sentinel Data Terms). |
| **Valle de Viedma · Landsat 8** | Landsat 8 OLI, Collection 2 Level 2 (reflectancia de superficie), enero de 2026. Bandas 2–7 (30 m) y QA_PIXEL. Obtenida vía **Microsoft Planetary Computer**. | *Landsat data courtesy of the U.S. Geological Survey.* Dominio público. |
| **Los Alerces · antes y después** | Sentinel-2 L2A, tesela 18GYT: 20 de enero de 2024 (antes) y 19 de febrero de 2024 (después) del incendio iniciado el 25 de enero de 2024 en el Parque Nacional Los Alerces (Chubut). Mismas bandas que arriba. Vía Earth Search. | Contiene datos modificados de Copernicus Sentinel (2024), © ESA. |

## Referencias metodológicas

- Umbrales de severidad dNBR: USGS / FIREMON (Key & Benson, 2006), usados con fines
  didácticos.
- Fórmulas de índices: NDVI = (NIR − Rojo)/(NIR + Rojo); NBR = (NIR − SWIR2)/(NIR + SWIR2);
  dNBR = NBR antes − NBR después.
- Escalado Landsat C2 L2: reflectancia = DN × 0,0000275 − 0,2. Sentinel-2 L2A: DN/10 000.

## Lo que este laboratorio NO es

No descarga datos, no reproyecta, no ejecuta geoprocesos reales. Cada operación
(buffer, selección por ubicación, superposición, índices) está implementada de
forma simple sobre datos simplificados, para que se entienda **qué hace** cada
etapa. Para trabajar con datos reales, la guía *SIG y Teledetección con QGIS*
(en `materiales-clase/`) indica el equivalente en QGIS de cada paso.
