#!/usr/bin/env python3
"""Cierre mensual de afiliados activos.

Lee los CSV de data/ (solo lectura, nunca los mueve ni los modifica), aplica las reglas
de docs/diccionario.md y genera en output/:
  afiliados_activos.csv, excepciones.csv, totales.txt y top_error.txt

Es repetible: cada ejecución reescribe output/ desde cero y produce el mismo resultado.
Uso: python3 scripts/cierre.py [carpeta_del_kit]
"""

import csv
import os
import re
import sys
from collections import Counter

BASE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA = os.path.join(BASE, "data")
LOGS = os.path.join(BASE, "logs")
SALIDA = os.path.join(BASE, "output")

ESTADOS = {"A": "ACTIVO", "I": "INACTIVO"}
CODIGO_ERROR = re.compile(r"CIE-\d{4}")


def leer_csv(nombre, separador=","):
    with open(os.path.join(DATA, nombre), encoding="utf-8-sig", newline="") as archivo:
        filas = []
        for fila in csv.DictReader(archivo, delimiter=separador):
            filas.append({k.strip(): (v or "").strip() for k, v in fila.items() if k is not None})
        return filas


def top_error():
    """Código CIE-#### más frecuente entre las líneas de error de los tres logs."""
    conteo = Counter()
    for nombre in ("api.log", "worker.log", "database.log"):
        ruta = os.path.join(LOGS, nombre)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8", errors="replace") as archivo:
            for linea in archivo:
                if "ERROR" in linea:
                    conteo.update(CODIGO_ERROR.findall(linea))
    if not conteo:
        return "", 0
    # Mayor conteo; en empate, el código menor (orden estable).
    return sorted(conteo.items(), key=lambda par: (-par[1], par[0]))[0]


def main():
    afiliados = leer_csv("AFI_MAE.csv")
    empresas = {e["COD_EMP"]: e["NOM_EMP"] for e in leer_csv("EMPRESA.csv")}
    beneficiarios = leer_csv("AFI_BEN.csv")
    aportes = leer_csv("APORTES.csv")

    excepciones = []

    # Regla 1: universo = documentos distintos; se conserva la primera aparición.
    universo, orden, duplicados = {}, [], []
    for fila in afiliados:
        doc = fila["NRO_DOC"]
        if doc in universo:
            if doc not in duplicados:
                duplicados.append(doc)
            continue
        universo[doc] = fila
        orden.append(doc)
    for doc in duplicados:
        excepciones.append((doc, "DUPLICADO", "documento repetido en AFI_MAE; se conserva la primera aparición"))

    # Beneficiarios por afiliado (regla 4: huérfanos).
    conteo_ben = Counter()
    for ben in beneficiarios:
        if ben["NRO_DOC_AFI"] in universo:
            conteo_ben[ben["NRO_DOC_AFI"]] += 1
        else:
            excepciones.append((ben["NRO_DOC_BEN"], "BENEFICIARIO_HUERFANO",
                                "afiliado {0} no existe en AFI_MAE".format(ben["NRO_DOC_AFI"])))

    # Último periodo pagado por afiliado (regla 7).
    ultimo_aporte = {}
    for aporte in aportes:
        periodo = aporte["PERIODO"]
        if re.fullmatch(r"\d{4}-\d{2}", periodo) and periodo > ultimo_aporte.get(aporte["NRO_DOC"], ""):
            ultimo_aporte[aporte["NRO_DOC"]] = periodo

    activos, inactivos = [], 0
    for doc in orden:
        fila = universo[doc]
        estado = fila["EST_AFI"]

        # Regla 2: solo A e I son códigos válidos.
        if estado not in ESTADOS:
            excepciones.append((doc, "CODIGO_INVALIDO", "EST_AFI='{0}' no es A ni I".format(estado)))
            continue
        if estado == "I":
            inactivos += 1
            continue

        # Regla 3: activo sin empresa válida.
        cod_emp = fila["COD_EMP"]
        if cod_emp not in empresas:
            excepciones.append((doc, "SIN_EMPRESA", "COD_EMP='{0}' vacío o inexistente en EMPRESA".format(cod_emp)))
            continue

        nombre = " ".join(p for p in (fila["NOM1"], fila["NOM2"], fila["APE1"], fila["APE2"]) if p)
        activos.append([doc, nombre, "ACTIVO", cod_emp, empresas[cod_emp], str(conteo_ben[doc]), ultimo_aporte.get(doc, "")])

    codigo, ocurrencias = top_error()

    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "afiliados_activos.csv"), "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(["documento", "nombre", "estado", "cod_empresa", "empresa", "beneficiarios", "ultimo_aporte"])
        escritor.writerows(activos)
    with open(os.path.join(SALIDA, "excepciones.csv"), "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(["documento", "tipo", "detalle"])
        escritor.writerows(excepciones)
    with open(os.path.join(SALIDA, "totales.txt"), "w", encoding="utf-8", newline="\n") as archivo:
        archivo.write("total_afiliados={0}\n".format(len(universo)))
        archivo.write("activos={0}\n".format(len(activos)))
        archivo.write("inactivos={0}\n".format(inactivos))
        archivo.write("excepciones={0}\n".format(len(excepciones)))
    with open(os.path.join(SALIDA, "top_error.txt"), "w", encoding="utf-8", newline="\n") as archivo:
        archivo.write("codigo_error={0}\n".format(codigo))
        archivo.write("ocurrencias={0}\n".format(ocurrencias))

    print("total_afiliados={0} activos={1} inactivos={2} excepciones={3}".format(len(universo), len(activos), inactivos, len(excepciones)))
    print("top_error {0} = {1}".format(codigo, ocurrencias))


if __name__ == "__main__":
    main()
