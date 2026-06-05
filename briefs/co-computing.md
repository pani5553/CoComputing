# Encargo del cliente: Co-Computing

## Resumen
Construir **Co-Computing**, una plataforma web de **computación distribuida
descentralizada**: permite a personas con ordenadores potentes (gamers,
workstations) monetizar su CPU/GPU ociosa procesando tareas distribuidas. La
propuesta de valor es una experiencia **radicalmente sencilla**: sin
conocimientos de cloud, blockchain ni DevOps.

## Usuario objetivo
El **Proveedor de Cómputo**: persona con conocimientos técnicos básicos que
quiere ingresos pasivos con su hardware infrautilizado. Sensible a la confianza,
prefiere feedback claro y comportamiento predecible.

## Stack OBLIGATORIO (respetar)
- **Frontend:** React (SPA) + Vite. Internacionalización en **español**.
- **Backend:** FastAPI (Python) + Uvicorn.
- **Base de datos y Auth:** Supabase (PostgreSQL). Autenticación JWT HS256,
  expiración 7 días.
- **Comunicación:** API REST JSON entre frontend y backend.

## Funcionalidades del MVP (todas obligatorias)

1. **Registro** — el proveedor se registra (email, password ≥8, nombre).
2. **Login seguro** — devuelve JWT.
3. **Panel principal (Dashboard)** — estado del proveedor: trust score, rango
   (nuevo/confiable/experto/élite), nº tareas completadas, ganancias totales,
   tareas recientes.
4. **Listado de tareas disponibles** — con filtros: dificultad
   (fácil/medio/difícil), hardware (cpu/gpu/mixto), tipo, recompensa mínima.
5. **Detalle de tarea** — título, descripción, recompensa, duración estimada,
   dificultad, hardware requerido, plazas disponibles, datos del solicitante.
6. **Aceptar / iniciar / completar / fallar una tarea** — ciclo de vida de la
   asignación del proveedor.
7. **Procesamiento con progreso** — pantalla que muestra el progreso de la tarea
   en curso (puede simularse con barra animada por etapas).
8. **Cartera (wallet)** — saldo disponible, pendiente, total ganado, total
   retirado; historial de transacciones; solicitud de retiro
   (transferencia/paypal/cripto).
9. **Perfil** — datos del proveedor, trust score con desglose, hardware
   registrado (CPU, GPU, RAM, almacenamiento), tasa de éxito, estado online.
10. **Sistema de Trust Score** — fórmula ponderada:
    `trust = completion_rate*0.40 + accuracy*0.30 + response_time*0.20 + client_rating*0.10`
    Rangos: 0-49 nuevo, 50-74 confiable, 75-89 experto, 90-100 élite.

## Modelo de datos (orientativo, el arquitecto lo detalla)
- **providers**: id, email, full_name, trust_score, rank, tasks_completed,
  success_rate, total_earned, cpu_model, gpu_model, ram_gb, storage_gb,
  is_online, timestamps.
- **tasks**: id, title, task_type, description, reward, duration_min/max,
  difficulty, hardware_required, total_slots, slots_left, datos del solicitante,
  status (disponible/en_progreso/completada/cancelada).
- **task_assignments**: id, task_id, provider_id, status
  (aceptada/procesando/completada/fallida/cancelada), timestamps, reward_paid,
  trust_delta.
- **wallets**: provider_id, available_balance, pending_balance, total_earned,
  total_withdrawn.
- **transactions**: id, provider_id, task_id, amount, tx_type
  (pago_tarea/retiro/bonus/penalizacion), status, description.

## Endpoints orientativos
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET /tasks/` (con filtros), `GET /tasks/{id}`
- `POST /tasks/{id}/accept|start|complete|fail`
- `GET /tasks/my/history`
- `GET /wallet/`, `GET /wallet/transactions`, `POST /wallet/withdraw`
- `GET /profile/stats`

## Requisitos de calidad
- Código de **producción**: completo, sin TODOs ni placeholders.
- Seguridad: passwords hasheadas, JWT bien validado, CORS correcto, Row Level
  Security en Supabase, sin secretos hardcodeados (usar variables de entorno).
- UI fiel a un diseño limpio y profesional, en español, con estados claros
  (cargando, éxito, error).
- Tests del backend que cubran los endpoints principales.
- Todo debe poder arrancar localmente con instrucciones claras en el README.

## Fuera de alcance (MVP)
- Integración de pagos reales (Stripe) — solo simular la solicitud de retiro.
- Ejecución real de cómputo distribuido — el procesamiento puede simularse.
- App móvil nativa.
- Lado "cliente que sube tareas" — solo el lado **Proveedor**.
