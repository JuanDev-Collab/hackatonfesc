# Terminal Rescue — David Tamayo y Juan González

## Descripción

Este proyecto repara el cierre mensual de afiliados de la Caja de Compensación. El proceso genera el archivo de afiliados activos que usa el área de Subsidios, una API para consultar un afiliado por documento y un archivo de excepciones para Auditoría. Antes no corría, la API fallaba y los totales no cuadraban con la hoja de control de Operaciones.

## Integrantes

- David Tamayo Villegas
- Juan Andrés González Rodríguez

## Requisitos

- Docker Desktop (o Docker Engine) con Docker Compose v2.
- Bash, Python 3.8 o superior y curl. En Windows usamos Git Bash con WSL 2 activado para Docker.
- Puerto 8081 libre para la API.

## Instalación y ejecución

Desde una copia limpia del repositorio, en la terminal:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
./run.sh
```

`docker compose up` levanta la base, la API y el worker. `./run.sh` ejecuta el cierre y deja los archivos en `output/`. Si algo se daña, `./reset.sh` borra los contenedores y la base y vuelve a levantar todo desde `data/`.

## Configuración

Las variables están en `.env.example`; se copian a `.env`, que no se sube al repositorio.

| Variable | Para qué sirve | Ejemplo |
|---|---|---|
| `POSTGRES_DB` | Nombre de la base que crea el contenedor `cierre-db` | `cierre` |
| `POSTGRES_USER` | Usuario dueño de la base | `cierre` |
| `POSTGRES_PASSWORD` | Clave de ese usuario | `cambiar-esta-clave` |
| `DATABASE_HOST` | Host de la base para la API y el worker; es el nombre del servicio en docker-compose, no `localhost` | `cierre-db` |
| `DATABASE_PORT` | Puerto de PostgreSQL dentro de la red de Docker | `5432` |
| `DATABASE_NAME` | Base a la que se conectan la API y el worker | `cierre` |
| `DATABASE_USER` | Usuario con el que se conectan | `cierre` |
| `DATABASE_PASSWORD` | Clave con la que se conectan; debe ser igual a `POSTGRES_PASSWORD` | `cambiar-esta-clave` |
| `API_PORT` | Puerto del equipo donde se publica la API | `8081` |
| `WORKER_INTERVAL_SECONDS` | Cada cuántos segundos el worker concilia el conteo; debe ser un número entero, sin la "s" | `30` |

## Arquitectura

Son tres servicios definidos en `docker-compose.yml`:

- `cierre-db`: PostgreSQL 16. Al crearse carga los CSV de `data/` con los scripts de `db/init/` y borra los documentos duplicados (`03_limpieza.sql`).
- `cierre-api`: servicio en Python que responde las consultas de afiliados en el puerto 8081. Se conecta a `cierre-db` por la red interna de Docker.
- `cierre-worker`: proceso en Python que cada 30 segundos cuenta los afiliados en `cierre-db` y lo escribe en su log.

El cierre (`run.sh` → `scripts/cierre.sh` → `scripts/cierre.py`) corre fuera de los contenedores con python3. Lee los CSV de `data/` y los logs de `logs/`, y escribe los resultados en `output/`.

## Uso

Consultar un afiliado por documento con `GET /afiliados/{documento}`:

```bash
curl http://localhost:8081/afiliados/1098765432
```

```json
{"documento": "1098765432", "nombre": "JUAN CARLOS PEREZ GOMEZ", "estado": "ACTIVO", "empresa": "EMPRESA ABC"}
```

Si el documento no existe responde `404`.

`./run.sh` genera en `output/`:

- `afiliados_activos.csv`: un afiliado activo con empresa válida por línea, con su número de beneficiarios y su último aporte (`YYYY-MM`).
- `excepciones.csv`: duplicados, afiliados sin empresa, beneficiarios huérfanos, códigos inválidos, fechas inválidas y cruces con Caja Oriente que no coinciden.
- `totales.txt`: `total_afiliados`, `activos`, `inactivos` y `excepciones`.
- `top_error.txt`: el código de error más frecuente en los logs y cuántas veces aparece.

## Pruebas

1. `docker compose ps` debe mostrar `cierre-db`, `cierre-api` y `cierre-worker` en estado running.
2. `curl -i http://localhost:8081/afiliados/3756530718` debe responder 200, y `curl -i http://localhost:8081/afiliados/0000000001` debe responder 404.
3. `./run.sh` y luego `cat output/totales.txt`: debe dar `total_afiliados=1500`, `activos=1194` e `inactivos=274`, igual que `control/hoja_control.csv`.
4. Correr `./run.sh` dos veces y comparar con `md5sum output/*`: los archivos deben salir iguales.
5. `./validator check` corre las pruebas públicas del kit.

## Documentación

- [incident-report.md](incident-report.md): los 10 incidentes con síntoma, diagnóstico, comandos y solución.
- [evidence/](evidence/): la salida de terminal que demuestra cada arreglo.
- [AI_USAGE.md](AI_USAGE.md): cómo usamos inteligencia artificial y qué corregimos.
- [docs/diccionario.md](docs/diccionario.md): reglas del cierre.

## Qué resolvimos

El worker se caía porque el intervalo tenía una "s" y la API apuntaba a un host que no existía; los dos se corrigieron en `.env.example`. La API daba 500 cuando el afiliado no tenía segundo nombre. El script de cierre leía una ruta que no existía y movía el archivo de entrada, así que solo servía una vez; lo rehicimos para que lea `data/`, sea repetible y aplique las reglas de Operaciones: duplicados, empresas, beneficiarios, fechas y cruce con Caja Oriente. Los totales ahora cuadran con la hoja de control.

## Limitaciones y pendientes

- El cierre lee los CSV de `data/` y no la base, así que si alguien corrige un dato directamente en la base no se refleja en `output/` hasta que se corrija también el CSV.
- La clave de `.env.example` es de ejemplo; en un servidor real hay que cambiarla.
- En Windows `./validator check` no puede ejecutar `./run.sh` directamente; lo probamos desde Git Bash.
