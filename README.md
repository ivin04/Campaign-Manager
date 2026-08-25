# D&D Campaign Manager

Gestor local de memoria para una campaña de D&D 5e 2014.

## Instalación

Abre CMD en esta carpeta:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt

## Arranque

    .venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8765

Luego abre:

    http://127.0.0.1:8765/docs

La base de datos se crea automáticamente en:

    data\campaign.db

## Comprobación

Abre:

    http://127.0.0.1:8765/health

Debe aparecer:

    {"ok":true}

## Importante

Esta primera versión crea la base y una API local. La integración automática con SillyTavern (guardar recuerdos y recuperar contexto antes de cada respuesta) será el siguiente paso.
