# Athletic Warehouse - Bruno API Collection

Esta carpeta contiene la colección de pruebas API para [Bruno](https://www.usebruno.com/) (cliente API Git-friendly y open-source).

## Estructura de la Colección

```
tests/bruno/
├── bruno.json                      # Manifiesto de la colección Bruno
├── collection.bru                  # Variables pre-request por defecto (baseUrl: http://localhost:8000)
├── environments/
│   └── Local.bru                   # Entorno local (baseUrl, keycloakUrl, tableflowSecret, authToken)
├── health.bru                      # GET /api/v1/health (Health check sin auth)
├── auth-me.bru                     # GET /api/v1/auth/me (Perfil y RBAC del usuario)
├── ingest-tableflow.bru            # POST /api/v1/ingest/tableflow (Caso exitoso con X-Tableflow-Secret / HMAC)
├── ingest-tableflow-slug.bru       # POST /api/v1/ingest/tableflow (Ingesta por player_slug determinista)
├── ingest-tableflow-invalid.bru    # POST /api/v1/ingest/tableflow (Rechazo 422 por player_id faltante)
├── list-wellness.bru               # GET /api/v1/wellness?limit=50 (Requiere rol dept_analyst)
└── keycloak-token.bru              # POST /realms/sports-club/.../token (Obtención de token en Keycloak)
```

## Cómo Usar con Bruno GUI

1. Abre la aplicación de escritorio de **Bruno**.
2. Selecciona **Open Collection** y apunta a la carpeta:
   `warehouse-backend/tests/bruno`
3. En la esquina superior derecha, selecciona el entorno `Local`.
4. Para obtener un token JWT:
   - Ejecuta la petición `keycloak-token.bru` (con usuario `coach_mikel` o `dr_garcia` o `admin_user`).
   - Copia el `access_token` devuelto y pégalo en la variable `authToken` del entorno `Local`.
5. Ejecuta `auth-me.bru` o `list-wellness.bru` con tu token activo.
6. `ingest-tableflow.bru` ya incluye el header `X-Tableflow-Secret` preconfigurado en `Local.bru`.

## Cómo Usar con Bruno CLI (Opcional)

Si tienes instalado el CLI oficial de Bruno (`@usebruno/cli`):

```bash
cd warehouse-backend/tests/bruno
bru run --env Local
```
