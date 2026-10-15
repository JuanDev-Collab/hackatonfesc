-- Limpieza de calidad de datos después de la carga (incidente 5).
-- Duplicados: se conserva la primera aparición de cada documento (regla 1 del diccionario).
-- Lo irreparable (sin empresa, códigos inválidos, huérfanos) no se borra: lo reporta
-- ./run.sh en output/excepciones.csv.
DELETE FROM afi_mae a
USING afi_mae b
WHERE a.nro_doc = b.nro_doc
  AND a.ctid > b.ctid;

UPDATE afi_mae SET est_afi = trim(est_afi), cod_emp = trim(cod_emp);
