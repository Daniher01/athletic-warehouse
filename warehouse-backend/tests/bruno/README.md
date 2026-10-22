# Athletic Warehouse - Bruno API Collection

Esta carpeta contiene la colección de pruebas API para [Bruno](https://www.usebruno.com/) (cliente API Git-friendly y open-source).

## Estructura de la Colección

```
tests/bruno/
├── bruno.json                      # Manifiesto de la colección Bruno
├── collection.bru                  # Variables pre-request por defecto (baseUrl: http://localhost:8000)
├── environments/
│   └── Local.bru                   # Entorno local (baseUrl: http://localhost:8000)
├── health.bru                      # GET /api/v1/health
├── ingest-tableflow.bru            # POST /api/v1/ingest/tableflow (Caso exitoso)
├── ingest-tableflow-invalid.bru    # POST /api/v1/ingest/tableflow (Rechazo 422 por player_id faltante)
└── list-wellness.bru               # GET /api/v1/wellness?limit=50
```

## Cómo Usar con Bruno GUI

1. Abre la aplicación de escritorio de **Bruno**.
2. Selecciona **Open Collection** y apunta a la carpeta:
   `warehouse-backend/tests/bruno`
3. En la esquina superior derecha, selecciona el entorno `Local` (o déjalo sin seleccionar, ya que `collection.bru` define `baseUrl = http://localhost:8000` por defecto).
4. Ejecuta cualquiera de las peticiones haciendo clic en **Send**.

## Cómo Usar con Bruno CLI (Opcional)

Si tienes instalado el CLI oficial de Bruno (`@usebruno/cli`):

```bash
cd warehouse-backend/tests/bruno
bru run --env Local
```
