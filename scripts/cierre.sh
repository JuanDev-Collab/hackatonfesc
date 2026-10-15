#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Cierre mensual de afiliados activos.
# Antes leía de /opt/cierre/entrada (ruta que no existe), fallaba con `mkdir output`
# en la segunda corrida y movía AFI_MAE.csv a procesados/, así que solo servía una vez.
# Ahora lee data/ del repositorio sin modificarla y regenera output/ en cada corrida.
# Las reglas del cierre están en scripts/cierre.py (ver docs/diccionario.md).
# ---------------------------------------------------------------------------
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ENTRADA="$RAIZ/data"
SALIDA="$RAIZ/output"

for archivo in AFI_MAE.csv AFI_BEN.csv EMPRESA.csv APORTES.csv extracto_caja_oriente.csv; do
    if [ ! -r "$ENTRADA/$archivo" ]; then
        echo "ERROR: no se puede leer $ENTRADA/$archivo" >&2
        exit 1
    fi
done

rm -rf "$SALIDA"
mkdir -p "$SALIDA"

echo "Leyendo afiliados desde $ENTRADA/AFI_MAE.csv"
python3 "$RAIZ/scripts/cierre.py" "$RAIZ"

echo "Cierre terminado"
