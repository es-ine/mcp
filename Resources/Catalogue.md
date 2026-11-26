# Operations catalogue and reference

This page lists the INE statistical operations
the server knows about, which ones already return data, and a short glossary of the
terms you will meet while using the five tools.

## Contents

- [Operations at a glance](#operations-at-a-glance)
- [Available now](#available-now)
- [Coming soon](#coming-soon)
- [Glossary](#glossary)
- [Source](#source)

## Operations at a glance

| Status | Operations |
| --- | ---: |
| Available now (tables published) | 110 |
| Coming soon (no tables yet) | 56 |
| **Total in the catalogue** | **166** |

How to read the tables:

- **ID** is the operation identifier used by the INE API.
- **Code** is INE's short acronym for the operation.
- **IOE code** is the code in the *Inventario de Operaciones Estadísticas*; it is empty (–) for some operations.
- Operation names are shown in Spanish, as INE publishes them.

> Use `ine_select_operation` with the name, the acronym or the ID to start from any operation below.

## Available now

Operations that have tables published, so the full five-step flow works for them.

| ID | Code | Operation | IOE code |
| ---: | --- | --- | ---: |
| 6 | `ICLA` | Índice de Coste Laboral Armonizado | 30211 |
| 7 | `ETDP` | Estadística de Transmisión de Derechos de la Propiedad | 30168 |
| 8 | `CENSOPV` | Censos de Población y Viviendas | 30243 |
| 10 | `UA` | Indicadores Urbanos | 30256 |
| 14 | `IPS` | Índices de Precios del Sector Servicios | 30182 |
| 15 | `IPV` | Índice de Precios de la Vivienda (IPV) | 30457 |
| 18 | `IPCA` | Índice de Precios de Consumo Armonizado (IPCA) | 30180 |
| 22 | `DPOP` | Cifras Oficiales de Población de los Municipios Españoles: Revisión del Padrón Municipal | 30245 |
| 23 | `ECM` | Estadística de Defunciones según la Causa de Muerte | 30417 |
| 24 | `EEE:IND` | Estadística Estructural de Empresas: Sector Industrial | 30048 |
| 25 | `IPC` | Índice de Precios de Consumo (IPC) | 30138 |
| 26 | `IPI` | Índices de Producción Industrial | 30050 |
| 27 | `IPRI` | Índices de Precios Industriales | 30051 |
| 31 | `IAS` | Indicadores de Actividad del Sector Servicios | 30183 |
| 32 | `ICM` | Índices de Comercio al por Menor | 30103 |
| 33 | `IDB` | Indicadores Demográficos Básicos | 30264 |
| 40 | `HPT` | Estadística de Hipotecas | 30149 |
| 42 | `ICN` | Índices de Cifras de Negocios en la Industria | 30052 |
| 43 | `DIR` | Explotación Estadística del Directorio Central de Empresas | 30203 |
| 44 | `ICES` | Encuesta sobre Comercio Internacional de Servicios y otras Operaciones Internacionales | 30198 |
| 48 | `IPRX-M` | Índices de Precios de Exportación y de Importación de Productos Industriales | 30071 |
| 61 | `IPAP` | Índice de Precios de Apartamentos Turísticos | 30222 |
| 62 | `IPAC` | Índice de Precios de Camping | 30223 |
| 63 | `IPTR` | Índice de Precios de Alojamientos de Turismo Rural | 30229 |
| 66 | `ENSD` | Estadística de Nulidades, Separaciones y Divorcios | 30463 |
| 70 | `PROH` | Proyección de Hogares | 30276 |
| 71 | `EM` | Estadística de Migraciones | 30277 |
| 93 | `EIAP` | Encuesta Industrial Anual de Productos | 30049 |
| 100 | `I+D:AP` | Estadística sobre Actividades en I+D en el Sector Administración Pública | 30058 |
| 104 | `IMM` | Índices de Precios de Materiales y Energía e Índices Nacionales de la Mano de Obra | 30062 |
| 121 | `EAES:Q` | Encuesta Cuatrienal de Estructura Salarial | 30133 |
| 125 | `SM` | Estadística de Sociedades Mercantiles | 30151 |
| 130 | `EEE:SER` | Estadística Estructural de Empresas: Sector Servicios | 30177 |
| 132 | `IPH` | Índice de Precios Hoteleros | 30179 |
| 137 | `IPT` | Índice de Precios del Trabajo | 30185 |
| 139 | `EACL` | Encuesta Anual de Coste Laboral | 30188 |
| 140 | `EAES` | Encuesta Anual de Estructura Salarial | 30189 |
| 153 | `TICH` | Encuesta sobre Equipamiento y Uso de Tecnologías de Información y Comunicación en los Hogares | 30450 |
| 155 | `ECV` | Encuesta de Condiciones de Vida (ECV) | 30453 |
| 163 | `ICE` | Indicadores de Confianza Empresarial | 30199 |
| 171 | `TF` | Estadística sobre Transporte Ferroviario | 30221 |
| 177 | `EEPG` | Estadística de Empresas según su pertenencia a grupos | 30227 |
| 180 | `IRSH` | Indicadores de Rentabilidad del Sector Hotelero | 30230 |
| 197 | `TM` | Tablas de Mortalidad | 30271 |
| 205 | `EFPA` | Flujos de la Población Activa | 30310 |
| 213 | `CONA` | Estadística de la Población Condenada Adulta | 30466 |
| 214 | `CONM` | Estadística de la Población Condenada Menor de Edad | 30467 |
| 215 | `VGD` | Estadística de Violencia Doméstica y Violencia de Género | 30468 |
| 230 | `PERE` | Estadística del Padrón de la Población Española Residente en el Extranjero | 85001 |
| 234 | `EMLG` | Estadística de Movilidad Laboral y Geográfica | 30209 |
| 236 | `ICV` | Indicadores de Calidad de Vida | 30471 |
| 237 | `CNTR2010` | Contabilidad Nacional Trimestral de España: Principales Agregados | 30024 |
| 238 | `EOH` | Encuesta de Ocupación Hotelera | 30235 |
| 239 | `EOAP` | Encuesta de Ocupación en Apartamentos Turísticos | 30236 |
| 240 | `EOAC` | Encuesta de Ocupación en Campings | 30237 |
| 241 | `EOTR` | Encuesta de Ocupación en Alojamientos de Turismo Rural | 30238 |
| 246 | `CTNFSI` | Cuentas Trimestrales no Financieras de los Sectores Institucionales | 30026 |
| 249 | `ECSE` | Encuesta Coyuntural sobre Stocks y Existencias | 30063 |
| 250 | `IPSS` | Índice de Producción del Sector Servicios | 30234 |
| 254 | `IIH` | Índice de ingresos hoteleros | 30220 |
| 256 | `EEE:COM` | Estadística Estructural de Empresas: Sector Comercio | 30232 |
| 257 | `CRE` | Contabilidad Regional de España | 30025 |
| 258 | `ICNE` | Índice de Cifra de Negocios Empresarial | 30083 |
| 259 | `EH` | Estadística sobre Ejecuciones Hipotecarias | 30153 |
| 293 | `EPA` | Encuesta de Población Activa (EPA) | 30308 |
| 297 | `TV` | Estadística de Transporte de Personas | 30163 |
| 303 | `ETCL` | Encuesta Trimestral de Coste Laboral (ETCL) | 30187 |
| 305 | `MNPM` | MNP Estadística de Matrimonios | 30302 |
| 306 | `MNP_PAR` | MNP Estadística de Partos | 30303 |
| 307 | `MNPN` | MNP Estadística de Nacimientos | 30304 |
| 308 | `MNP_MFT` | MNP Estadística de Muertes Fetales Tardías | – |
| 309 | `MNPD` | MNP Estadística de Defunciones | 30306 |
| 314 | `EPF` | Encuesta de Presupuestos Familiares (EPF) | 30458 |
| 326 | `PROP` | Proyecciones de Población | 30278 |
| 328 | `EOA` | Encuesta de Ocupación en Albergues | 30239 |
| 329 | `EG` | Encuesta de Gasto Turístico | 16029 |
| 330 | `FR` | Movimientos Turísticos en Fronteras | 16028 |
| 331 | `IGC` | Índice de Garantía de la Competitividad | – |
| 333 | `MYH` | Mujeres y Hombres en España | 30456 |
| 334 | `ETR` | Encuesta de turismo de residentes | 16023 |
| 336 | `ANES` | Estadística de Adquisiciones de Nacionalidad Española de Residentes | 30279 |
| 340 | `EF` | Encuesta de Fecundidad | 30317 |
| 345 | `CNEAG` | Contabilidad nacional anual de España: agregados por rama de actividad | 30030 |
| 353 | `ADRH` | Atlas de distribución de renta de los hogares | 30325 |
| 406 | `EDES` | Estimacion del numero de defunciones semanales (EDeS) | 30324 |
| 410 | `VTE` | Viviendas turísticas en España | – |
| 412 | `GDVE` | Distribución del gasto en destino realizado por los visitantes extranjeros en sus visitas a España | – |
| 424 | `EMN` | Estimación Mensual de Nacimientos | 30323 |
| 425 | `CDMGE` | Comercio diario al por menor de grandes empresas | – |
| 426 | `CODEM` | Coyuntura demográfica de empresas | – |
| 429 | `OAT` | Ocupación en alojamientos turísticos | – |
| 432 | `IPVA` | Índice de Precios de Vivienda en Alquiler | – |
| 436 | `TMOV_R` | Medición del turismo receptor a partir de la posición de los teléfonos móviles | – |
| 437 | `TMOV_E` | Medición del turismo emisor a partir de la posición de los teléfonos móviles | – |
| 438 | `TMOV_I` | Medición del turismo interno interprovincial a partir de la posición de los teléfonos móviles | – |
| 450 | `ECP` | Estadística Continua de Población | 30282 |
| 452 | `GDRE` | Distribución del gasto realizado por los residentes en sus visitas al Extranjero según país de destino | – |
| 455 | `EMCR` | Estadística de Migraciones y Cambios de Residencia | 30283 |
| 463 | `CENSOP` | Censo de Población | 30281 |
| 464 | `MOS` | Comercio Internacional de Servicios por Modos de Suministro (MoS) | 30098 |
| 465 | `STEC` | Comercio Internacional de Servicios por Características de las Empresas (STEC) | 30240 |
| 468 | `IMA` | Panel de Indicadores Medioambientales | 30206 |
| 472 | `CSES` | Cuenta satélite de la economía social | 30092 |
| 473 | `EEECN` | Estadística estructural de empresas: Sector Construcción | 30292 |
| 474 | `ECVG` | Estadística sobre Cadenas de Valor Globales | 30099 |
| 476 | `CMEA:T` | Cuentas de Emisiones a la Atmósfera Trimestrales | – |
| 481 | `IRAV` | Índice de Referencia de Arrendamientos de Vivienda | – |
| 482 | `TIVA` | Panel de Indicadores de Comercio Internacional de Valor Añadido | 30801 |
| 486 | `IPCO` | Índice de Producción de la Construcción | 30293 |
| 490 | `OCE` | Cifras del censo electoral | – |

## Coming soon

Operations that exist in the catalogue but do not expose tables yet. They can be
found with `ine_select_operation`, but `ine_select_multiple_tables` will not have
tables to return until INE publishes them and the catalogue is refreshed.

| ID | Code | Operation | IOE code |
| ---: | --- | --- | ---: |
| 16 | `TNOM` | Distribución de Nombres | – |
| 20 | `CNTR2000` | Contabilidad Nacional Trimestral de España. Base 2000 | 30013 |
| 39 | `EOT` | Encuesta de Ocupación en Alojamientos Turísticos | 30162 |
| 49 | `APEL` | Distribución de Apellidos | – |
| 67 | `EPSC` | Estadística de Productos en el Sector Comercio | 30233 |
| 79 | `IRIVA` | Índices de Reparto Regional del IVA y los Impuestos Especiales sobre la Cerveza, sobre el Alcohol y Bebidas Derivadas y sobre Productos Intermedios | 30015 |
| 86 | `CTNFSI` | Cuentas Trimestrales no Financieras de los Sectores Institucionales. Base 2008 | 30021 |
| 91 | `EEA` | Encuesta sobre la Estructura de las Explotaciones Agrícolas | 30044 |
| 99 | `I+D:E` | Estadística sobre Actividades en I+D en el Sector Empresas | 30057 |
| 101 | `I+D:ISFL` | Estadística sobre Actividades en I+D en el Sector Instituciones Privadas sin Fines de Lucro | 30059 |
| 102 | `I+D:ES` | Estadística sobre Actividades en I+D en el Sector Enseñanza Superior | 30060 |
| 103 | `PITEC` | Encuesta sobre Innovación en las Empresas | 30061 |
| 107 | `EAPM` | Estadísticas sobre las Actividades de Protección Medioambiental | 30066 |
| 110 | `ECE` | Encuesta de Consumos Energéticos | 30070 |
| 115 | `ITIC` | Indicadores del Sector de Tecnologías de la Información y las Comunicaciones (TIC) | 30081 |
| 116 | `FILEXT` | Estadística de Filiales de Empresas Españolas en el Exterior | 30082 |
| 129 | `ETICCE` | Encuesta sobre el Uso de Tecnologías de la Información y las Comunicaciones y del Comercio Electrónico en las Empresas | 30169 |
| 141 | `IAT` | Indicadores de Alta Tecnología | 30197 |
| 142 | `EPD` | Discapacidad en el mercado laboral: empleo | 30320 |
| 147 | `EMH` | Encuesta de Morbilidad Hospitalaria | 30414 |
| 148 | `EPS` | Estadística de Profesionales Sanitarios Colegiados | 30416 |
| 150 | `EDAD` | Encuesta de Discapacidad, Autonomía Personal y Situaciones de Dependencia | 30418 |
| 161 | `EGHE` | Encuesta de Gasto de los Hogares en Educación | 30460 |
| 166 | `DAE` | Demografía Armonizada de Empresas | 30204 |
| 174 | `BIOT` | Estadística sobre el Uso de Biotecnología | 30224 |
| 178 | `EPSS` | Estadística de Productos en el Sector Servicios | 30228 |
| 189 | `NOM` | Nomenclátor: Población del Padrón Continuo por Unidad Poblacional | 30261 |
| 216 | `APSH` | Encuesta de Centros y Servicios de Atención a las Personas Sin Hogar y en Exclusión Residencial | 30469 |
| 229 | `EES` | Encuesta Europea de Salud | 54088 |
| 233 | `ENSE` | Encuesta Nacional de Salud (ENSE) | 54009 |
| 248 | `CSTE` | Cuenta Satélite del Turismo de España | 30027 |
| 252 | `SPD` | Discapacidad en el mercado laboral: salarios | 30331 |
| 285 | `SSA` | Estadísticas sobre el Suministro y Saneamiento del Agua | 30077 |
| 286 | `EGR` | Estadísticas sobre Generación de Residuos | 30078 |
| 287 | `RTR` | Estadísticas sobre Recogida y Tratamiento de Residuos | 30079 |
| 288 | `CMEA:A` | Cuentas Medioambientales: Cuenta de Emisiones a la Atmósfera | 30084 |
| 289 | `CIAMB` | Cuentas Medioambientales: Cuenta de Impuestos Ambientales | 30085 |
| 290 | `CFM` | Cuentas Medioambientales: Cuenta de Flujos de Materiales | 30086 |
| 311 | `MNP_RP` | Movimiento Natural de la Población (Resultados Provisionales) | 30301 |
| 338 | `CGPM` | Cuentas medioambientales: Cuenta de gasto en protección medioambiental | 30088 |
| 339 | `CFFE` | Cuentas medioambientales: Cuenta de flujos físicos de la energía | 30090 |
| 342 | `BSA` | Cuentas Medioambientales: Cuenta de Bienes y Servicios Ambientales | 30089 |
| 343 | `ODS` | Indicadores de la Agenda 2030 para el Desarrollo Sostenible | 30800 |
| 344 | `CNE` | Contabilidad nacional anual de España: principales agregados | 30029 |
| 346 | `CNFSI` | Cuentas anuales no financieras de los sectores institucionales | 30031 |
| 348 | `CNE:TOD` | Contabilidad nacional anual de España: tablas de Origen y Destino | 30032 |
| 349 | `CNE:TIO` | Contabilidad nacional anual de España: tablas Input-Output | 30033 |
| 371 | `CRS` | Cuentas Medioambientales: Cuenta de los Residuos | 30095 |
| 407 | `EAES:Q` | Encuesta Cuatrienal de Estructural Salarial | – |
| 409 | `VLPD` | Discapacidad en el mercado laboral: vida laboral | 30332 |
| 433 | `IMCV` | Indicador Multidimensional de Calidad de Vida | – |
| 470 | `EDSE` | Encuesta de Salud de España | 30473 |
| 484 | `VIME` | Visualizador de multilocalización empresarial (VIME) | – |
| 485 | `CSMOT` | Cuentas Medioambientales: Cuenta de Subvenciones Medioambientales y Otras Transferencias Similares | 30284 |
| 489 | `ELEC` | Procesos electorales | – |
| 495 | `OCE` | Cifras de electores. Publicación mensual | – |

## Glossary

| Term | Meaning |
| --- | --- |
| **Operation** | A statistical survey or product, such as the CPI or the Labour Force Survey. Step 1. |
| **Table** | A published dataset belonging to an operation. Step 2. |
| **Group / variable** | A dimension that structures a table: sex, province, age group, period… Step 3 (`group_id`). |
| **Value** | One category of a variable, such as *Murcia* or *Hombres*. Step 4 (`FK_Variable` and `Id`). |
| **Period** | The time range requested in step 5, for example the last four quarters. |

## Source

Operations with tables are listed as available; the rest are listed as coming soon. Official data and metadata: [INE](https://www.ine.es).
