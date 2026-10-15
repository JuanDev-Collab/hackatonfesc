# Uso de inteligencia artificial

## Uso 1
- Herramienta: Claude (Claude Code)
- Para qué se usó: diagnosticar por qué cierre-worker quedaba en Exited (1) y la API no conectaba a la base
- Prompt principal (resumido): "guíame para dejar funcionando el kit Terminal Rescue: worker caído, API sin base, cierre que no corre"
- Qué produjo: identificó WORKER_INTERVAL_SECONDS=30s y DATABASE_HOST=cierre-database en .env.example y propuso 30 y cierre-db
- Qué modificó o corrigió el equipo: probamos cada cambio en Docker antes de aceptarlo y guardamos la salida real del antes y el después en evidence/ para el informe

## Uso 2
- Herramienta: Claude (Claude Code)
- Para qué se usó: reescribir el script de cierre con las reglas de docs/diccionario.md
- Prompt principal (resumido): "el cierre lee /opt/cierre/entrada, solo funciona una vez y los totales no cuadran con la hoja de control"
- Qué produjo: un cierre.sh que lee data/ y un cierre.py que calcula activos, excepciones, totales y el error más frecuente de los logs, todo de una vez
- Qué modificó o corrigió el equipo: pedimos que fuera más sencillo y que se separara por incidente, para subir un commit por arreglo entre los dos y poder explicar cada parte

## Uso 3
- Herramienta: Claude (Claude Code)
- Para qué se usó: hacer funcionar Docker Desktop en Windows
- Prompt principal (resumido): "Docker Desktop is unable to start"
- Qué produjo: primero sugirió reiniciar el PC; después, revisando el log de Docker, encontró que faltaba WSL.
- Qué modificó o corrigió el equipo: Instalar WSL; además ya teníamos el repositorio creado con el kit dentro de fesc-tecnico/, así que lo movimos a la raíz para que el calificador encuentre run.sh
