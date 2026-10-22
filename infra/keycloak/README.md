# Keycloak IAM & RBAC Infrastructure

Esta infraestructura gestiona el control de acceso basado en roles (**RBAC**), Single Sign-On (**SSO**) e identidades departamentales para **Athletic Warehouse** (`warehouse-backend`, `tableflow` y `metabase`).

---

## 1. Principios de Diseño: Cero Hardcoding y Realm Parametrizable

1. **Agnóstico al Club:** La configuración por defecto utiliza el realm genérico `sports-club`. No existen nombres de entidades deportivas quemadas en el código, configuraciones fijas o fixtures.
2. **Parametrización por Entorno:** Todo el comportamiento se gobierna mediante variables de entorno en `.env`:
   - `KEYCLOAK_REALM`: Nombre del realm (default: `sports-club`).
   - `KEYCLOAK_BASE_URL`: URL pública de Keycloak (default: `http://localhost:8080`).
   - `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`: Credenciales de administración global.
3. **Fuente de Verdad Declarativa:** El archivo [realm-export.json](file:///infra/keycloak/realm-export.json) se importa automáticamente al levantar el contenedor con `--import-realm`.

---

## 2. Topología de Roles, Grupos y Clientes

### Jerarquía de Grupos Departamentales
Cada grupo inyecta el atributo `department_id` en las reclamaciones del token:

- `/Departamentos/Medico` (`department_id=medico`)
- `/Departamentos/Preparacion-Fisica` (`department_id=preparacion-fisica`)
- `/Departamentos/Scouting` (`department_id=scouting`)
- `/Departamentos/Cantera` (`department_id=cantera`)
- `/Departamentos/Direccion-Deportiva` (`department_id=direccion-deportiva`)

### Roles de Realm
- **`dept_admin`**: Administrador de departamento (gestión de plantillas, auditoría y accesos).
- **`dept_ingestor`**: Ingestor de datos (carga de archivos en Tableflow y ejecución de webhooks hacia `/api/v1/ingest/tableflow`).
- **`dept_analyst`**: Analista departamental (consumo de dashboards en Metabase y endpoints `/api/v1/wellness`).

### Clientes OIDC Configurados

| Client ID | Tipo | Flujo OIDC | Propósito |
| :--- | :--- | :--- | :--- |
| `warehouse-backend-api` | Confidencial / Resource Server | Bearer JWT / JWKS | Validación de tokens en FastAPI con RS256 |
| `tableflow-app` | Público | Auth Code + PKCE (`S256`) | Interfaz web de Tableflow con SSO y aislamiento de Workspaces |
| `tableflow-service-m2m` | Confidencial | Client Credentials (M2M) | Ingesta automatizada y entrega segura de webhooks |
| `metabase-app` | Confidencial | Auth Code / SSO | Visualización de Business Intelligence y sincronización de grupos |

---

## 3. Usuarios de Prueba (Fixtures Locales)

Todos los usuarios de desarrollo comparten la contraseña: `test_password_123`

| Usuario | Departamento | Roles Asignados | Correo |
| :--- | :--- | :--- | :--- |
| `dr_garcia` | `/Departamentos/Medico` | `dept_ingestor` | `garcia@sportsclub.internal` |
| `coach_mikel` | `/Departamentos/Preparacion-Fisica` | `dept_analyst` | `mikel@sportsclub.internal` |
| `admin_user` | `/Departamentos/Direccion-Deportiva` | `dept_admin`, `dept_ingestor`, `dept_analyst` | `admin@sportsclub.internal` |

---

## 4. Guía Operativa de Despliegue

### Levantar el Servicio Keycloak
```bash
docker compose up -d keycloak
```

Para verificar el estado y los logs de inicialización:
```bash
docker compose logs -f keycloak
```

Una vez levantado, la consola de administración estará disponible en:
- **URL:** [http://localhost:8080](http://localhost:8080)
- **Usuario Admin:** `admin` (o valor de `${KEYCLOAK_ADMIN}`)
- **Password Admin:** `admin_password` (o valor de `${KEYCLOAK_ADMIN_PASSWORD}`)

---

## 5. Ejemplos de Obtención de Tokens (`curl`)

### A. Token de Usuario (Resource Owner Password Credentials)
Útil para pruebas directas en desarrollo:
```bash
curl -s -X POST "http://localhost:8080/realms/sports-club/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=warehouse-backend-api" \
  -d "client_secret=backend-api-secret-123" \
  -d "username=dr_garcia" \
  -d "password=test_password_123" \
  -d "grant_type=password" | jq .access_token
```

### B. Token Servicio M2M (Client Credentials Grant)
Utilizado por Tableflow o pipelines automatizados:
```bash
curl -s -X POST "http://localhost:8080/realms/sports-club/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=tableflow-service-m2m" \
  -d "client_secret=tableflow-m2m-secret-xyz" \
  -d "grant_type=client_credentials" | jq .access_token
```

### C. Consumir Endpoints de `warehouse-backend` con Bearer Token
```bash
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/sports-club/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=warehouse-backend-api" \
  -d "client_secret=backend-api-secret-123" \
  -d "username=dr_garcia" \
  -d "password=test_password_123" \
  -d "grant_type=password" | jq -r .access_token)

# Consultar identidad y claims verificados
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
```

---

## 6. Exportar y Persistir Cambios del Realm

Si realizas modificaciones en la interfaz de Keycloak y deseas persistirlas en el repositorio:
```bash
docker exec -it athletic-keycloak /opt/keycloak/bin/kc.sh export \
  --realm sports-club \
  --file /opt/keycloak/data/import/realm-export.json
```
Esto mantendrá [realm-export.json](file:///infra/keycloak/realm-export.json) como la única fuente de verdad versionada.
