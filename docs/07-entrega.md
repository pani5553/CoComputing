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
| ~~Sin timeout de chunks asignados~~ | **RESUELTO 2026-07-07.** TTL de 10 minutos vía reclamo perezoso en `POST /work/claim` (`migrations/006_chunk_ttl.sql`) + rechazo automatico tras 5 intentos, ya activo. Ver "Proximos pasos sugeridos para v3" (puntos 1 y 3) y `docs/04-arquitectura.md` §14.2. La migracion no hizo backfill automatico, pero se comprobo manualmente contra produccion el 2026-07-08 y no habia ningun chunk `assigned` preexistente que necesitara limpieza (ver entrada de cierre de ciclo 2026-07-08). |
| Sin rate limiting en `/work/claim` | Un proveedor autenticado puede reclamar chunks de forma agresiva sin limitacion. No hay proteccion contra acaparamiento de trabajo. |
| Credenciales del worker en linea de comandos | El argumento `--password` expone la contrasena en el historial de shell y en `ps aux`. En produccion, usar variables de entorno o un gestor de secretos. |
| Sin deteccion de ataques Sybil | Un mismo operador puede registrar multiples cuentas y procesar el mismo chunk dos veces, garantizando consenso artificialmente. La unica proteccion es `UNIQUE (chunk_id, provider_id)` que bloquea el doble submit con la misma cuenta. |
| ~~Operaciones de wallet no completamente atomicas~~ | **RESUELTO 2026-07-07**, de forma mas completa de lo pedido: `wallet_queries.credit_reward_and_update_trust` aplica pago de recompensa + actualizacion de trust score en una unica transaccion psycopg2 con `FOR UPDATE`. Ver "Proximos pasos sugeridos para v3" (punto 2) y `docs/04-arquitectura.md` §14.3. El codigo antiguo (`wallet_service.credit_reward`, no-atomico) quedo huerfano sin llamadores (V3-MAYOR-02 en `docs/05-review.md`) y ya se elimino el 2026-07-08. |
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

1. ~~TTL para chunks asignados.~~ **RESUELTO (2026-07-07).** Implementado como "reclamo perezoso" dentro del propio `POST /work/claim` (sin scheduler externo), con TTL de 10 minutos vía la nueva columna `chunks.assigned_at` (`migrations/006_chunk_ttl.sql`, ya aplicada a produccion). Diseño en `docs/04-arquitectura.md` §14.2; revisado sin bloqueantes en `docs/05-review.md` (seccion 2026-07-07); `docs/06-security.md` marca **SEC-22 → RESUELTO** (seccion 2026-07-07). Detalle de deuda residual (falta de backfill para chunks ya atascados antes del despliegue, V3-MAYOR-01) en la entrada de cierre de ciclo mas abajo.
2. ~~Operacion atomica en `credit_reward`.~~ **RESUELTO (2026-07-07), de forma mas completa de lo pedido.** No solo el credito de wallet quedo atomico: pago de recompensa + actualizacion de trust score ahora se ejecutan en la MISMA transaccion psycopg2 (nueva funcion `wallet_queries.credit_reward_and_update_trust`, con `SELECT ... FOR UPDATE` sobre el proveedor para evitar carreras entre chunks liquidados casi simultaneamente). Diseño en `docs/04-arquitectura.md` §14.3; `docs/06-security.md` marca **SEC-24 → RESUELTO** (seccion 2026-07-07).
3. ~~Rechazo automatico de chunks con mas de 5 intentos~~ (US-38 CA-8; ver R2-A-04 en `docs/05-review.md`). **RESUELTO (2026-07-07).** La logica (`MAX_CHUNK_ATTEMPTS = 5`) ya existia en el codigo pero era, en la practica, casi inalcanzable sin TTL (nada devolvia un chunk de `assigned` a `pending` salvo el propio flujo de consenso). Al activar el TTL del punto 1, este mecanismo pasa a ser plenamente alcanzable en la misma llamada a `/work/claim`. Ver `docs/04-arquitectura.md` §14.0.2 y §14.2.5. Nota: esta misma activacion abrio un hallazgo de seguridad nuevo (SEC-36, ya cerrado) — ver la entrada de cierre de ciclo mas abajo.
4. Transaccionalidad en la creacion de job + chunks para evitar jobs fantasma en estado `splitting` si falla la insercion de chunks (R2-A-05). **Sigue pendiente** — fuera del alcance del ciclo 2026-07-07/08.

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

---

# Co-Computing — Resumen de Entrega: Publicacion Vercel/Railway + Boton "Anadir creditos"

**Fecha:** 2026-07-06
**Autor:** Technical Writer
**Version del producto:** 1.1.0 (sin incremento de version — ciclo de retoques puntuales, no una feature nueva)
**Referencia:** `briefs/05-vercel-creditos.md`, `docs/05-review.md` (seccion fechada 2026-07-06), `docs/06-security.md` (seccion fechada 2026-07-06)

---

## Que se entrego

Este ciclo era, por diseno, pequeno: dos retoques puntuales sobre un proyecto que ya funciona en local y ya tenia documentacion de despliegue completa (no una feature nueva, ver `briefs/05-vercel-creditos.md`).

**Frontend:**

- Boton **"Anadir creditos"** en la cartera del proveedor (`frontend/src/pages/WalletPage.tsx`), junto a "Solicitar retiro". Abre un `Modal` (componente reutilizado) con el mensaje "Muy pronto podras comprar creditos (CC) con tarjeta o PayPal. Esta funcion esta en construccion." Es un placeholder puramente visual: un unico `useState<boolean>` nuevo, sin llamada a API, sin endpoint nuevo y sin tocar el flujo de recarga ya funcional del lado cliente (`frontend/src/pages/client/DepositPage.tsx`, `POST /wallet/deposit`).
- Confirmado que `npm run build` compila sin errores en todas las pantallas existentes (dashboard, tareas, computo, cliente).

**Verificacion de preparacion para desplegar (sin cambios de arquitectura):**

- DevOps repaso `DEPLOY.md` y `frontend/vercel.json` contra el estado actual del codigo y actualizo el checklist final con las rutas nuevas a probar (`/cliente/*`, `/jobs/*`), ademas de anadir una nota de riesgo sobre el hallazgo critico descrito abajo.
- Backend Dev confirmo que `ENVIRONMENT=production` sigue desactivando `/docs`/`/redoc` y que CORS no tiene nada hardcodeado a `localhost` en el camino de produccion.
- QA verifico manualmente el boton (abre y cierra el modal sin romper el resto de la pantalla) y que el build de frontend y la imagen Docker del backend construyen sin errores. No se anadieron tests automaticos nuevos (no hacian falta segun el encargo).
- Product Owner, Architect, Database Engineer y Security confirmaron, cada uno desde su angulo, que no hay nada bloqueante para publicar: los requisitos y la arquitectura no tienen huecos, las 5 migraciones (`001` a `005`) estan listadas correctamente en el checklist de despliegue de `DEPLOY.md`, y `docs/06-security.md` sigue vigente.

## Como probar lo nuevo

1. Arrancar el frontend (`cd frontend && npm run dev`) e iniciar sesion como proveedor.
2. Ir a "Cartera". Junto a "Solicitar retiro" debe aparecer el boton "Anadir creditos".
3. Pulsarlo: se abre un modal con el aviso de funcion en construccion. Cerrarlo (boton "Entendido" o cerrar el modal) no deja ningun efecto secundario ni dispara llamadas de red (comprobable en la pestana de red del navegador).
4. Confirmar que el resto de la pantalla de cartera (saldos, historial de transacciones, retiro de fondos) sigue funcionando exactamente igual que antes.
5. Opcional: `cd frontend && npm run build` para confirmar que la build de produccion sigue compilando sin errores.

## Hallazgo critico pendiente — NO resuelto en este ciclo

Durante la verificacion de este ciclo, el Code Reviewer y el Security Auditor encontraron —de forma independiente el primero y confirmando/ampliando el segundo, ambos con reproduccion propia, no solo lectura— un problema **ajeno a este brief** pero presente sin commitear en el mismo arbol de trabajo: una migracion a medias del acceso a datos, de psycopg2 directo a la API REST de Supabase. Concretamente:

- `backend/app/db/supabase_client.py` (fichero nuevo, sin trackear en git) construye el cliente Supabase en tiempo de import usando `os.getenv` crudo. Si las credenciales solo estan en `.env` (el flujo normal que describe este mismo README) y nadie las ha exportado como variables de entorno reales del proceso, el import de `app.main` falla con `SupabaseException: supabase_url is required`. Como `conftest.py` importa `app.main` a nivel de modulo, esto **rompe la recoleccion de los 71 tests del backend al completo**, no solo algunos.
- `backend/app/core/config.py`: el campo `supabase_db_url` paso de obligatorio a opcional (`Optional[str] = None`), eliminando el fail-fast de arranque para todo el codigo que sigue dependiendo de psycopg2 directo — escrow del cliente, jobs de computo real y, segun amplio el Security Auditor, tambien el pago de recompensas a proveedores (`wallet_queries.py`).
- `backend/app/db/queries/task_queries.py`: modificado como parte del mismo WIP, con manejo de errores que oculta fallos de infraestructura como si fueran resultados de negocio normales.

Esto **no es una regresion introducida por el brief de este ciclo** — ni el brief 04 (despliegue) ni el 05 (Vercel/creditos) pidieron esta migracion — pero convive sin commitear en el mismo arbol de trabajo y bloquea cualquier `pytest` o arranque local que no tenga las variables de entorno exportadas manualmente.

**Esta documentado en detalle, con reproduccion independiente por dos roles distintos, en:**

- `docs/05-review.md`, seccion fechada 2026-07-06 ("Revision — Publicacion Vercel + Boton 'Anadir creditos'"): hallazgos R3-CRIT-01 y R3-CRIT-02 (los dos criticos), mas R3-MAYOR-01 y R3-MAYOR-02 sobre la causa raiz.
- `docs/06-security.md`, seccion fechada 2026-07-06 ("Auditoria — Publicacion Vercel + Boton 'Anadir creditos'"): hallazgos SEC-33 a SEC-35, que confirman que no hay fuga de credenciales pero si deuda de higiene de logging/secretos, y que el radio de impacto alcanza tambien el pago a proveedores.
- Una nota de riesgo equivalente, mas breve, en `DEPLOY.md`, seccion "5 · Checklist final antes de publicar".

**La decision de revertir este WIP o completarlo queda pendiente del usuario o del equipo humano.** Ambos documentos plantean dos opciones concretas: (A) revertir `backend/app/core/config.py` y `backend/app/db/queries/task_queries.py` a `git HEAD` y borrar `backend/app/db/supabase_client.py`; o (B) conservar la migracion a REST pero corrigiendo antes los hallazgos criticos. Ninguna de las dos se ha aplicado todavia. **Este WIP no debe considerarse listo para produccion ni desplegarse tal cual** hasta que se tome esa decision.

La parte que si es responsabilidad de este brief —el boton placeholder y la verificacion de despliegue— esta completa y sin hallazgos de fondo, confirmado de forma independiente por el Code Reviewer (lectura completa + `npm run build` real) y el Security Auditor (grep de secretos + lectura linea a linea).

## Documentacion entregada en este ciclo

| Fichero | Descripcion |
|---------|-------------|
| `README.md` | Nota sobre el placeholder "Anadir creditos" en una nueva seccion "Placeholders conocidos"; corregido el checklist de migraciones desactualizado (ahora referencia `DEPLOY.md` como fuente unica en vez de listar solo 001→002) |
| `docs/07-entrega.md` | Esta entrada |

---

# Co-Computing — Cierre de ciclo: Estabilidad v3 (TTL de chunks + transaccion pago/trust) + SEC-36

**Fecha:** 2026-07-08
**Autor:** Technical Writer
**Version del producto:** 1.1.0 (sin incremento de version — ciclo de fiabilidad interna, no una feature de producto)
**Referencia:** `docs/04-arquitectura.md` §14, `docs/05-review.md` (secciones fechadas 2026-07-07), `docs/06-security.md` (secciones fechadas 2026-07-07 y 2026-07-08)

## Que se entrego

Este ciclo resolvio dos de los "Proximos pasos sugeridos para v3" identificados al cierre del ciclo anterior (ver mas arriba en este mismo documento), y en el proceso se encontro y cerro un hallazgo de seguridad nuevo.

**1. TTL de chunks asignados + rechazo automatico por intentos (puntos 1 y 3 de "Proximos pasos").** Un chunk que queda `assigned` sin submit durante mas de 10 minutos se devuelve automaticamente a `pending` mediante un reclamo perezoso dentro del propio `POST /work/claim` (sin scheduler externo, sin dependencia nueva). Esto activa de verdad la logica de rechazo tras 5 intentos (`MAX_CHUNK_ATTEMPTS`), que ya existia en el codigo pero era casi inalcanzable antes de este cambio. Diseño completo en `docs/04-arquitectura.md` §14.2; verificado por el Code Reviewer (sin bloqueantes, 3 hallazgos MAYOR no bloqueantes) y por el Security Auditor (**SEC-22 → RESUELTO**).

**2. Transaccion atomica de pago + trust score (punto 2 de "Proximos pasos"), resuelta de forma mas completa de lo pedido.** El encargo original pedia solo que el credito de wallet fuese atomico. Se entrego mas: la nueva funcion `wallet_queries.credit_reward_and_update_trust` aplica pago de recompensa, registro de transaccion y actualizacion de trust score (con `SELECT ... FOR UPDATE` sobre el proveedor) en una **unica** transaccion psycopg2 — todo o nada. Diseño en `docs/04-arquitectura.md` §14.3; el Security Auditor confirma **SEC-24 → RESUELTO** (ventana de carrera cerrada, verificado a nivel de esquema, no solo de codigo).

**3. Migraciones nuevas — ambas ya aplicadas a produccion, no son pendientes:**

| Migracion | Contenido | Estado |
|-----------|-----------|--------|
| `migrations/006_chunk_ttl.sql` | Añade `chunks.assigned_at timestamptz` + indice parcial `idx_chunks_assigned_at ON chunks(assigned_at) WHERE status='assigned'`. Sin backfill automatico (V3-MAYOR-01 en `docs/05-review.md`): los chunks que ya estuvieran `assigned` antes del despliegue habrian quedado con `assigned_at IS NULL`, sin ser reclamados retroactivamente por el TTL. Verificado manualmente contra produccion el 2026-07-08: 0 chunks en estado `assigned` en ese momento, por lo que no hizo falta limpieza. | Aplicada a produccion |
| `migrations/007_chunk_abandon_tracking.sql` | Añade `chunks.abandoned_by uuid[]`, usada por `claim_chunks_atomic` para impedir que un proveedor vuelva a reclamar un chunk que el mismo abandono via TTL. Cierra SEC-36 (ver abajo). | Aplicada a produccion |

**4. Hallazgo de seguridad nuevo, encontrado y cerrado en el mismo ciclo: SEC-36.** Al activar el TTL, el Security Auditor detecto (2026-07-07) que un unico proveedor — sin necesidad de multiples cuentas (Sybil) — podia forzar el rechazo permanente de cualquier chunk objetivo reclamandolo y dejandolo expirar repetidamente (cada expiracion cuenta como un intento; tras 5, el chunk se rechaza para siempre, sin ninguna penalizacion de trust score porque el camino de penalizacion solo se dispara para resultados efectivamente entregados). El Backend Dev implemento la mitigacion (exclusion de auto-reclamo via `chunks.abandoned_by`, migracion 007) y el Security Auditor la verifico de forma independiente el 2026-07-08, leyendo el codigo actual: **SEC-36 → RESUELTO** para el vector que lo hacia explotable por un actor unico.

## Lo que queda explicitamente fuera de este ciclo

- **SEC-23 (ataque Sybil en consenso) y SEC-21 (sin rate limiting en `/work/claim`) siguen SIN RESOLVER.** La propia verificacion de cierre de SEC-36 (`docs/06-security.md`, seccion 2026-07-08) confirma que el riesgo residual — varias cuentas repartiendose el abandono de un mismo chunk para evadir la exclusion por-proveedor que cierra SEC-36 — queda subsumido en SEC-23, no resuelto por este ciclo. Los tres hallazgos (SEC-36 cerrado, SEC-21 y SEC-23 pendientes) comparten la misma causa raiz de fondo: `/work/claim` no tiene ningun control de identidad o comportamiento por proveedor mas alla de la validez del JWT. `docs/06-security.md` recomienda explicitamente abordar SEC-21 y SEC-23 en el mismo esfuerzo de diseño, no por separado.
- La segunda mitigacion sugerida para SEC-36 (penalizar `accuracy`/`completion_rate` cuando un proveedor abandona un chunk via TTL) **no se implemento** — abandonar un chunk sigue sin costar nada en reputacion. Queda como hardening de defensa en profundidad en el backlog, no bloqueante.
- El punto 4 original de "Proximos pasos sugeridos para v3" (transaccionalidad en la creacion de job + chunks, R2-A-05) **sigue sin resolver** — no formaba parte del alcance de este ciclo.
- `docs/05-review.md` señalo tres hallazgos MAYOR, los tres ya cerrados el 2026-07-08: **V3-MAYOR-01** (falta de backfill en la migracion 006) — confirmado operativamente que no hacia falta, 0 chunks `assigned` en produccion en el momento de la verificacion; **V3-MAYOR-02** (`wallet_service.credit_reward` como codigo muerto) — funcion eliminada; **V3-MAYOR-03** (la sentencia de reclamo TTL no usaba `FOR UPDATE SKIP LOCKED` como las otras dos sentencias de `claim_chunks_atomic`) — corregido, ahora las tres sentencias usan el mismo patron. Queda pendiente, eso si, un test de concurrencia real (multi-hilo/multi-proceso) que ejercite `claim_chunks_atomic` bajo carga simultanea genuina — lo existente son tests de integracion secuenciales contra una BD real, no concurrencia de verdad.
- El patron no-transaccional de pago + trust en `task_lifecycle.py` (flujo de tareas clasicas, distinto del pipeline de computo) **no se toco** — es un problema analogo y documentado como deuda diferida para v4, no una regresion de este ciclo.

## Documentacion entregada en este ciclo

| Fichero | Descripcion |
|---------|-------------|
| `docs/04-arquitectura.md` | Seccion 14 nueva: diseño del TTL de chunks asignados y de la transaccion pago + trust |
| `docs/05-review.md` | Revision del ciclo (seccion 2026-07-07): 0 hallazgos criticos, 3 mayores, 2 menores, 1 informativo |
| `docs/06-security.md` | Auditoria del ciclo (seccion 2026-07-07: SEC-22 y SEC-24 resueltos, SEC-36 nuevo) y verificacion de cierre de SEC-36 (seccion 2026-07-08) |
| `README.md` | (Sin seccion "Limitaciones conocidas del MVP" propia — esa tabla vive en este documento) sin cambios adicionales de contenido tecnico en este ciclo mas alla de los ya vigentes |
| `docs/07-entrega.md` | Marcados como RESUELTOS los puntos 1-3 de "Proximos pasos sugeridos para v3" y las dos filas correspondientes de "Limitaciones conocidas del MVP" (mas arriba en este documento); esta entrada de cierre de ciclo |
