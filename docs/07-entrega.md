# Co-Computing — Resumen de Entrega: Feature Computo Real Distribuido (v2)

**Fecha:** 2026-06-07
**Autor:** Technical Writer
**Version del producto:** 1.1.0
**Referencia:** `briefs/02-computo-real.md`, `docs/02-backlog.md` (US-31 a US-41)

---

## Que se anadio

### Archivos nuevos

**Backend:**

| Archivo | Contenido |
|---------|-----------|
| `backend/app/routers/compute.py` | Router `/jobs`: POST /jobs, GET /jobs, GET /jobs/{id}, GET /jobs/{id}/result |
| `backend/app/routers/work.py` | Router `/work`: POST /work/claim, POST /work/{chunk_id}/submit |
| `backend/app/services/compute_service.py` | Logica de creacion de jobs, splitting de CSV, finalizacion y consolidacion de resultados |
| `backend/app/services/consensus_service.py` | Validacion por consenso: comparacion canonica de resultados, logica de desempate, pago y actualizacion de trust score |
| `backend/app/db/queries/compute_queries.py` | Queries de BD para jobs, chunks y chunk_results; `claim_chunks_atomic` con `FOR UPDATE SKIP LOCKED` via psycopg2 |
| `backend/app/models/compute.py` | Modelos Pydantic: `JobCreateRequest`, `JobPublic`, `JobListResponse`, `ClaimResponse`, `ChunkWithPayload`, `SubmitRequest`, `SubmitResponse` |
| `backend/app/worker/__init__.py` | Paquete del worker |
| `backend/app/worker/main.py` | Entry point del worker CLI: autenticacion, bucle claim-process-submit, logging estructurado |
| `backend/app/worker/plugins/__init__.py` | Registro de plugins: `PLUGINS = {"data-processing": DataProcessingPlugin}` |
| `backend/app/worker/plugins/base.py` | Clase abstracta `WorkerPlugin` con interfaz `process(payload: dict) -> dict` |
| `backend/app/worker/plugins/data_processing.py` | `DataProcessingPlugin`: implementacion real con polars para mean/sum/min/max/count |
| `backend/tests/test_compute.py` | Tests de integracion de los endpoints de jobs (casos C-01 a C-05) |
| `backend/tests/test_consensus.py` | Tests de consenso (casos K-01 a K-07) |

**Frontend:**

| Archivo | Contenido |
|---------|-----------|
| `frontend/src/types/compute.ts` | Tipos TypeScript: `Job`, `JobStatus`, `ChunkWithPayload`, `ClaimResponse`, `SubmitRequest`, `SubmitResponse`, `JobCreateRequest` |
| `frontend/src/pages/NewJobPage.tsx` | Formulario para subir CSV, previsualizar columnas y enviar job |
| `frontend/src/pages/JobListPage.tsx` | Lista de jobs con estado real, barra de progreso y polling cada 5 segundos |
| `frontend/src/pages/JobDetailPage.tsx` | Detalle del job con progreso real y transicion automatica a completado |
| `frontend/src/pages/JobResultPage.tsx` | Visualizacion y descarga del resultado consolidado |

**Infraestructura y scripts:**

| Archivo | Contenido |
|---------|-----------|
| `migrations/004_compute.sql` | Crea tablas `jobs`, `chunks`, `chunk_results` con constraints, indices y politicas RLS. Idempotente. |
| `scripts/run_workers.sh` | Lanza multiples instancias del worker en paralelo para demo de distribucion |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `backend/app/main.py` | Registra los routers `compute` y `work` con los prefijos `/jobs` y `/work` |
| `backend/app/services/wallet_service.py` | Anade la funcion `credit_reward(provider_id, amount, description)` para acreditar recompensas por chunks validos |
| `frontend/src/App.tsx` | Anade las rutas `/jobs`, `/jobs/new`, `/jobs/:id`, `/jobs/:id/result` al router |
| `docs/02-backlog.md` | Extiende el backlog con US-31 a US-41 y las epicas E-10 y E-11 |
| `docs/04-arquitectura.md` | Anade la seccion 12 con el diagrama de flujo del pipeline, estructura de directorios, claim atomico, logica de consenso y notas de seguridad |
| `docs/04-api-contracts.md` | Anade la seccion 6 con los contratos completos de la Compute API |
| `README.md` | Anade la seccion "Computo Real Distribuido (feature v2)" |

---

## Como probar la feature end-to-end

### Requisitos previos

- Backend arrancado en `http://localhost:8000` (ver README, seccion "Arranque local sin Docker").
- Frontend arrancado en `http://localhost:5173`.
- Migracion `004_compute.sql` aplicada en Supabase.
- Al menos dos cuentas de proveedor registradas (pueden ser la cuenta demo mas otra creada manualmente).

### Pasos

**1. Registrar o usar cuentas de proveedor**

Si tienes aplicado el seed de demo:
- Cliente: `demo@co-computing.io` / `demo1234`
- Para los workers necesitas al menos una cuenta adicional. Registra una desde `/registro`.

**2. Crear un job como cliente**

```
1. Iniciar sesion con la cuenta cliente en http://localhost:5173
2. Navegar a /jobs/new
3. Subir un archivo CSV con datos numericos (ejemplo minimo: dos columnas, 20 filas)
4. Seleccionar operacion "mean" y elegir las columnas numericas
5. Pulsar "Enviar trabajo"
6. El sistema redirige a /jobs donde el job aparece en estado "processing"
```

Si no tienes un CSV a mano, genera uno de prueba:

```python
import csv, random
with open('test.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['precio', 'cantidad'])
    for _ in range(50):
        w.writerow([round(random.uniform(1, 100), 2), random.randint(1, 50)])
```

**3. Levantar dos workers**

Abrir dos terminales separadas:

```bash
cd backend

# Terminal 1
python -m app.worker --api http://localhost:8000 --email proveedorA@example.com --password passA

# Terminal 2
python -m app.worker --api http://localhost:8000 --email proveedorB@example.com --password passB
```

O usar el script de demo:

```bash
bash scripts/run_workers.sh
```

Los workers mostraran en stdout mensajes como:

```
2026-06-07T10:01:15Z INFO  Login exitoso como proveedorA@example.com
2026-06-07T10:01:16Z INFO  Chunk chunk-uuid-0 reclamado
2026-06-07T10:01:16Z INFO  Procesando chunk 0 (data-processing, mean)
2026-06-07T10:01:16Z INFO  Chunk chunk-uuid-0 enviado correctamente
```

**4. Seguir el progreso en el frontend**

```
1. Recargar /jobs o esperar el polling automatico (cada 5 segundos)
2. La barra de progreso avanza a medida que los chunks se validan
3. Cuando todos los chunks estan validados, el job pasa a "completed"
4. Aparece el boton "Ver resultado" que lleva a /jobs/:id/result
```

**5. Ver y descargar el resultado**

La pagina de resultado muestra los valores calculados por columna. El boton "Descargar resultado (JSON)" descarga el fichero `resultado_<id_corto>.json`.

---

## Limitaciones conocidas del MVP

| Limitacion | Descripcion |
|------------|-------------|
| Sin sandboxing del worker | El worker ejecuta polars sobre payloads de la API sin aislamiento. Solo usar en entornos de confianza. Ver nota de seguridad en el README. |
| Sin timeout de chunks asignados | Si un worker reclama un chunk y desaparece, el chunk queda en estado `assigned` indefinidamente. No hay TTL ni scheduler que lo devuelva a `pending`. El job queda atascado. Workaround manual: actualizar el estado directamente en Supabase. |
| Sin rate limiting en `/work/claim` | Un proveedor autenticado puede reclamar chunks de forma agresiva sin limitacion. No hay proteccion contra acaparamiento de trabajo. |
| Credenciales del worker en linea de comandos | El argumento `--password` expone la contrasena en el historial de shell y en `ps aux`. En produccion, usar variables de entorno o un gestor de secretos. |
| Sin deteccion de ataques Sybil | Un mismo operador puede registrar multiples cuentas y procesar el mismo chunk dos veces, garantizando consenso artificialmente. La unica proteccion es `UNIQUE (chunk_id, provider_id)` que bloquea el doble submit con la misma cuenta. |
| Operaciones de wallet no completamente atomicas | `credit_reward` hereda el patron read-modify-write de `update_wallet_on_task_complete`. Con chunks validados de forma muy concurrente, podria perderse alguna recompensa. Fix pendiente (R2-C-02 en `docs/05-review.md`). |
| Tipo de job unico | Solo `data-processing` esta implementado. La arquitectura de plugin esta preparada para tipos adicionales (`transcription`, `rendering`, etc.) pero no implementados. |
| Sin endpoint DELETE /jobs | Un job en estado `splitting` o `failed` no puede eliminarse desde la API. Debe gestionarse directamente en Supabase. |

---

## Decisiones clave de diseno

**Claim atomico con psycopg2.** El SDK de Supabase no expone `FOR UPDATE SKIP LOCKED`. Sin ese hint, dos workers concurrentes podrian reclamar el mismo chunk. La solucion usa psycopg2 directamente con `BEGIN/COMMIT` explicito para garantizar que cada chunk va a exactamente un worker por reclamo. La misma variable de entorno `SUPABASE_DB_URL` ya configurada en el proyecto se reutiliza.

**Validacion por consenso canonica.** Los resultados JSON de dos workers se comparan serializando con `json.dumps(result, sort_keys=True)`. Esto garantiza que `{"a":1,"b":2}` y `{"b":2,"a":1}` se traten como identicos, evitando falsos desacuerdos por orden de claves.

**Plugin WorkerPlugin.** El worker no contiene logica de negocio del computo. Solo orquesta: claim, dispatch al plugin, submit. Anadir un nuevo tipo de job requiere crear una clase que herede de `WorkerPlugin`, implementar `process(payload: dict) -> dict`, y registrarla en `plugins/__init__.py`. No se toca el nucleo del worker.

**Progreso real, no simulado.** El campo `progress` del job es `completed_chunks / total_chunks * 100`, calculado en el backend. El frontend deja de usar `progress_service.py` (que calcula por tiempo transcurrido) para los jobs del pipeline distribuido. El progreso simulado sigue funcionando sin cambios para las asignaciones clasicas de tareas.

**Reutilizacion de servicios existentes.** `wallet_service.credit_reward` (nueva funcion anadida), `trust_score.update_accuracy_on_complete` y `trust_score.update_accuracy_on_fail` son las unicas interfaces entre el pipeline nuevo y el codigo existente. Los endpoints de auth, el mecanismo JWT y los componentes UI (Card, Button, ProgressBar) se reutilizan sin modificacion.

---

## Proximos pasos sugeridos para v3

**Estabilidad y correccion (prioridad alta):**

1. TTL para chunks asignados. Un scheduler debe devolver a `pending` los chunks con `status = assigned` que lleven mas de N minutos sin recibir submit. Valor sugerido: 10 minutos.
2. Operacion atomica en `credit_reward`: `UPDATE wallets SET available_balance = available_balance + %s WHERE provider_id = %s RETURNING *` sin doble lectura.
3. Rechazo automatico de chunks con mas de 5 intentos (US-38 CA-8, actualmente no implementado; ver R2-A-04 en `docs/05-review.md`).
4. Transaccionalidad en la creacion de job + chunks para evitar jobs fantasma en estado `splitting` si falla la insercion de chunks (R2-A-05).

**Seguridad:**

5. Sandboxing del worker: contenedor Docker con `--network none`, sin acceso al filesystem del host, con limites de CPU y memoria. Firmado HMAC del payload.
6. Inyeccion de credenciales del worker por variable de entorno o secret manager en lugar de argumentos CLI.
7. Rate limiting en `POST /work/claim`.
8. Deteccion de cuentas Sybil: limitar participacion de workers por IP o requerir verificacion.

**Funcionalidad:**

9. Nuevos tipos de job: `hashing` (SHA-256 de ficheros), `transcription` (audio con Whisper local). El sistema de plugins ya esta preparado.
10. Panel de administracion con vista de jobs activos, chunks atascados y metricas por proveedor.
11. Notificaciones en tiempo real (WebSocket) al cliente cuando su job se completa.
12. Retiro de fondos reales (Stripe o SEPA) una vez validada la plataforma con CC internos.

---

## Estado del proyecto al cierre de v1.1

### Deuda tecnica conocida

Los siguientes items fueron identificados por el Code Reviewer (`docs/05-review.md`) y deben resolverse antes de desplegar v1.1 en produccion:

| ID | Severidad | Descripcion |
|----|-----------|-------------|
| R2-C-01 | CRITICO | `JobListPage.tsx` no compilaba por imports faltantes (`Link`, `Button`). Verificar que esta corregido antes del build. |
| R2-C-02 | CRITICO | `credit_reward` hereda el patron no-atomico de `update_wallet_on_task_complete`. |
| R2-C-03 | CRITICO | `_pay_and_update_trust` no es transaccional: si el pago tiene exito y el trust falla, el proveedor queda con saldo correcto pero trust desactualizado. |
| R2-A-04 | ALTO | Chunk con >5 intentos no se marca como `rejected` automaticamente. |
| R2-A-05 | ALTO | `create_job_with_chunks` no hace rollback si falla la insercion de chunks. |
| R2-A-06 | ALTO | `claim_chunks_atomic` no permite que el segundo proveedor reclame un chunk ya `assigned` con replicas pendientes. La feature de consenso con `replicas_needed=2` no puede completarse sin este fix. |
| R2-M-05 | MEDIO | `JobResultPage.tsx` asumia una estructura de resultado distinta a la generada por `finalize_job`. La tabla de resultados mostraba "No hay datos disponibles" siempre. |

Los blockers marcados como CRITICO y los R2-A-06 / R2-M-05 son bloqueantes: la feature central del consenso distribuido y la visualizacion de resultados no funcionan correctamente sin ellos.

### Documentacion entregada en este ciclo

| Fichero | Descripcion |
|---------|-------------|
| `README.md` | Seccion "Computo Real Distribuido (feature v2)" anadida al README principal del repositorio |
| `docs/07-entrega.md` | Este documento: lista de archivos, guia de prueba end-to-end, limitaciones, decisiones de diseno y proximos pasos |
