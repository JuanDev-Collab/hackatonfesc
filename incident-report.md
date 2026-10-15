# Informe de incidentes — Terminal Rescue

## Incidente 1
- **Síntoma:** `docker compose ps -a` muestra `cierre-worker` en `Exited (1)` apenas se levanta el entorno.
- **Diagnóstico:** el log del worker dice `CIE-1107 WORKER_INTERVAL_SECONDS debe ser un entero de segundos; valor recibido: '30s'`. El worker hace `int()` y "30s" no es un número.
- **Comandos:** `docker compose ps -a`, `docker compose logs cierre-worker | tail -3`
- **Solución:** cambiamos `WORKER_INTERVAL_SECONDS=30s` por `WORKER_INTERVAL_SECONDS=30` en `.env.example`, copiamos a `.env` y recreamos el worker con `docker compose up -d --force-recreate cierre-worker`.
- **Evidencia:** evidence/01-worker.txt

## Incidente 2
- **Síntoma:** la API responde `{"error": "base de datos no disponible"}` a cualquier consulta.
- **Diagnóstico:** en los logs aparece `CIE-2210 could not translate host name "cierre-database"`. En `docker-compose.yml` el servicio se llama `cierre-db`, así que ese host no existe dentro de la red de Docker.
- **Comandos:** `curl -s http://localhost:8081/afiliados/1098765432`, `docker compose logs cierre-api | grep CIE-2210`, `grep -c CIE-2210 logs/worker.log`
- **Solución:** `DATABASE_HOST=cierre-db` en `.env.example` y en `.env`, y recreamos `cierre-api` y `cierre-worker`. La API ya responde con los datos del afiliado.
- **Evidencia:** evidence/02-api-conexion.txt

## Incidente 3
- **Síntoma:** `./run.sh` termina con `awk: fatal: cannot open file /opt/cierre/entrada/AFI_MAE.csv: No such file or directory`.
- **Diagnóstico:** `scripts/cierre.sh` leía la entrada de `/opt/cierre/entrada`, una ruta del servidor viejo que no existe en el repositorio. Además los scripts no tenían permiso de ejecución guardado en Git.
- **Comandos:** `./run.sh`, `find . -name AFI_MAE.csv`, `chmod +x run.sh scripts/cierre.sh` (en Git: `git add --chmod=+x`)
- **Solución:** el script ahora lee de `data/` dentro del repositorio, revisa que existan los cinco CSV y los procesa con `scripts/cierre.py`. Les dimos permiso de ejecución a `run.sh`, `reset.sh` y los scripts.
- **Evidencia:** evidence/03-entrada.txt

## Incidente 4
- **Síntoma:** los tres logs tienen miles de líneas y no se sabe cuál es el error principal.
- **Diagnóstico:** contamos los códigos `CIE-####` en las líneas de ERROR de `api.log`, `worker.log` y `database.log`. Los avisos `W-###` no cuentan como error. El más frecuente es `CIE-4012` (lote rechazado por afiliado sin empresa), con 1424 apariciones.
- **Comandos:** `grep -h ERROR logs/*.log | grep -o 'CIE-[0-9]*' | sort | uniq -c | sort -rn`, `wc -l logs/*.log`
- **Solución:** `cierre.py` hace el mismo conteo y escribe `output/top_error.txt` con `codigo_error=CIE-4012` y `ocurrencias=1424`.
- **Evidencia:** evidence/04-top-error.txt

## Incidente 5
- **Síntoma:** AFI_MAE tiene 1520 filas pero solo 1500 documentos distintos, hay afiliados sin empresa, beneficiarios de afiliados que no existen y estados como `Z`, `P`, `9` y `X`.
- **Diagnóstico:** revisamos los datos con psql y con awk. Hay 20 documentos duplicados, 18 activos sin empresa válida, 15 beneficiarios huérfanos y 14 afiliados con código de estado inválido.
- **Comandos:** `docker compose exec -T cierre-db psql -U cierre -d cierre -c "SELECT count(*), count(DISTINCT nro_doc) FROM afi_mae;"`, `cut -d, -f2 output/excepciones.csv | sort | uniq -c`
- **Solución:** `db/init/03_limpieza.sql` borra los duplicados en la base y deja la primera aparición (queda 1500 | 1500). Lo que no se puede arreglar (sin empresa, códigos inválidos y huérfanos) se reporta en `output/excepciones.csv`.
- **Evidencia:** evidence/05-calidad.txt

## Incidente 6
- **Síntoma:** `GET /afiliados/3756530718` responde `500 Internal Server Error`.
- **Diagnóstico:** el afiliado no tiene segundo nombre. `\copy` lo carga como NULL, y en la API `nom1 + " " + nom2` falla al sumar texto con `None`. También fallaba con estados inválidos (`ESTADOS[est_afi]`), y el `JOIN` dejaba por fuera a los afiliados sin empresa.
- **Comandos:** `curl -s -i http://localhost:8081/afiliados/3756530718`, `docker compose logs cierre-api | grep CIE-5003`, `docker compose up -d --build cierre-api`
- **Solución:** en `services/api/app.py` el nombre se arma solo con las partes que existen, el estado se busca con `.get()`, se usa `LEFT JOIN` y `ORDER BY ctid` para tomar la primera aparición. Ahora responde 200, y 404 cuando el documento no existe.
- **Evidencia:** evidence/06-api.txt

## Incidente 7
- **Síntoma:** algunas fechas de afiliación vienen como `01/07/2017` (DD/MM/YYYY), fechas YYYYMMDD, `SIN FECHA`, `N/A`, `2023/02/29` o `15-15-2019`.
- **Diagnóstico:** el formato oficial es `YYYY-MM-DD`, pero el diccionario dice que `DD/MM/YYYY` y `YYYYMMDD` se deben normalizar. Las demás no son fechas reales.
- **Comandos:** `grep -v -E ',[0-9]{4}-[0-9]{2}-[0-9]{2}$' data/AFI_MAE.csv | cut -d, -f1,9`, `grep FECHA_INVALIDA output/excepciones.csv`
- **Solución:** `cierre.py` normaliza los dos formatos válidos y reporta como `FECHA_INVALIDA` las 12 fechas que no se pueden interpretar. Esos afiliados siguen contando en los totales; ninguno se descarta en silencio.
- **Evidencia:** evidence/07-fechas.txt

## Incidente 8
- **Síntoma:** el extracto de Caja Oriente no se puede cruzar directo: usa `;`, otros nombres de columna, documentos de 12 dígitos con ceros a la izquierda y `VIGENTE`/`RETIRADO`.
- **Diagnóstico:** hay que quitar los ceros a la izquierda del documento y convertir `VIGENTE` en `A` y `RETIRADO` en `I` antes de comparar con AFI_MAE.
- **Comandos:** `head -3 data/extracto_caja_oriente.csv`, `grep CRUCE_NO_COINCIDE output/excepciones.csv`, `head -1 output/afiliados_activos.csv`
- **Solución:** `cierre.py` lee el extracto con `;`, normaliza el documento y la situación, y reporta 25 `CRUCE_NO_COINCIDE` (documentos que no existen o con otro estado). El archivo de activos conserva su encabezado original.
- **Evidencia:** evidence/08-cruce.txt

## Incidente 9
- **Síntoma:** el `totales.txt` del script viejo no cuadraba con `control/hoja_control.csv`.
- **Diagnóstico:** contaba filas (1520) en vez de documentos distintos (1500), tomaba como activos a los que no tenían empresa y no excluía los códigos inválidos.
- **Comandos:** `cat output/totales.txt`, `cat control/hoja_control.csv`, `awk -F, 'NR>1 {print $7}' data/AFI_MAE.csv | sort | uniq -c`
- **Solución:** aplicamos las reglas del diccionario. Ahora `total_afiliados=1500`, `activos=1194` e `inactivos=274`, igual que la hoja de control, y `excepciones` es el número de líneas de `excepciones.csv`.
- **Evidencia:** evidence/09-totales.txt

## Incidente 10
- **Síntoma:** el cierre solo funcionaba una vez: la segunda corrida fallaba.
- **Diagnóstico:** el script hacía `mkdir output` (falla si ya existe), movía `AFI_MAE.csv` a `procesados/` y agregaba con `>>` a `totales.txt`.
- **Comandos:** `./run.sh`, `md5sum output/*`, `ls data/`
- **Solución:** el script ya no mueve la entrada; borra y recrea `output/` en cada corrida. Dos corridas seguidas dan archivos idénticos, y también funciona después de `./reset.sh`.
- **Evidencia:** evidence/10-repetible.txt
