# Co-Computing — Mapa de Pantallas y Flujo de Navegación

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** UX/UI Designer
**Referencias:** `docs/00-vision.md`, `docs/02-requisitos.md`, `docs/02-backlog.md`

---

## 1. Árbol de Rutas

```
/                           → Redirige a /dashboard si autenticado, a /login si no
│
├── /login                  → Pantalla de inicio de sesión
├── /registro               → Pantalla de registro de nuevo proveedor
│
└── [Rutas protegidas — requieren JWT válido]
    │
    ├── /dashboard          → Panel principal del proveedor
    │
    ├── /tareas             → Listado de tareas disponibles con filtros
    │   └── /tareas/:id     → Detalle de una tarea concreta
    │
    ├── /procesando/:assignmentId  → Pantalla de progreso de procesamiento
    │
    ├── /cartera            → Cartera: saldos + historial de transacciones
    │
    └── /perfil             → Perfil del proveedor: datos, hardware, Trust Score
```

---

## 2. Mapa de Pantallas Completo

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ZONA PÚBLICA (sin autenticación)                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────────┐   "¿No tienes cuenta?"   ┌──────────────────┐               │
│   │   /login     │ ─────────────────────── ▶│   /registro      │               │
│   │  Inicio de   │                          │  Nuevo proveedor │               │
│   │  sesión      │ ◀───────────────────────  │                  │               │
│   └──────┬───────┘   "¿Ya tienes cuenta?"   └────────┬─────────┘               │
│          │ Login OK + JWT                            │ Registro OK + JWT        │
└──────────┼────────────────────────────────────────── ┼─────────────────────────┘
           │                                           │
           ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ZONA PRIVADA (requiere JWT en cabecera)                     │
│                                                                                 │
│  ╔══════════════════════════════════════════════════════════════════════╗       │
│  ║  NAVBAR PERSISTENTE (en todas las pantallas privadas)               ║       │
│  ║  Logo · Tareas · Cartera · Perfil · [Rango badge] Nombre · Salir   ║       │
│  ╚══════════════════════════════════════════════════════════════════════╝       │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────┐         │
│   │  /dashboard  — Panel Principal                                   │         │
│   │                                                                  │         │
│   │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │         │
│   │  │  Trust Score    │  │  Tareas          │  │  Ganancias     │  │         │
│   │  │  + Rango badge  │  │  completadas     │  │  totales       │  │         │
│   │  └─────────────────┘  └──────────────────┘  └────────────────┘  │         │
│   │                                                                  │         │
│   │  ┌────────────────────────────────────────────────────────────┐  │         │
│   │  │  Tareas recientes (últimas 5 asignaciones)                 │  │         │
│   │  │  [Ver todas las tareas disponibles →]                      │  │         │
│   │  └────────────────────────────────────────────────────────────┘  │         │
│   └──────────────────────────────────────────────────────────────────┘         │
│                    │                                                            │
│                    │ Click "Ver tareas"                                         │
│                    ▼                                                            │
│   ┌──────────────────────────────────────────────────────────────────┐         │
│   │  /tareas  — Listado de Tareas con Filtros                        │         │
│   │                                                                  │         │
│   │  [Filtros: Dificultad · Hardware · Tipo · Recompensa mínima]     │         │
│   │  [Limpiar filtros]                                               │         │
│   │                                                                  │         │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │         │
│   │  │ TaskCard │ │ TaskCard │ │ TaskCard │ │ TaskCard │ ...         │         │
│   │  └────┬─────┘ └──────────┘ └──────────┘ └──────────┘            │         │
│   └────── ┼ ───────────────────────────────────────────────────────┘         │
│            │ Click en tarjeta                                                  │
│            ▼                                                                    │
│   ┌──────────────────────────────────────────────────────────────────┐         │
│   │  /tareas/:id  — Detalle de Tarea                                 │         │
│   │                                                                  │         │
│   │  Título · Descripción · Metadatos · Etapas de procesamiento      │         │
│   │                                                                  │         │
│   │  [Estado A] Sin asignación activa:   [Aceptar tarea]  ──────┐   │         │
│   │  [Estado B] Ya aceptada/procesando:  [Continuar procesam.]─┐ │   │         │
│   │  [Estado C] Sin plazas:              [Sin plazas — disabled] │ │   │         │
│   └──────────────────────────────────────────────────────────── ┼─┼─┘         │
│                                          Aceptar OK              │ │            │
│                                                                   │ │            │
│                              ┌────────────────────────────────────┘ │            │
│                              │                                       │            │
│                              ▼          Continuar procesam.         │            │
│   ┌──────────────────────────────────────────────────────────────────┐         │
│   │  /procesando/:assignmentId  — Progreso de Procesamiento         │ ◀────────┘│
│   │                                                                  │           │
│   │  Nombre tarea · Porcentaje · Barra animada                       │           │
│   │  Stepper de etapas (completada / activa / pendiente)             │           │
│   │                                                                  │           │
│   │  [Reportar problema]  (siempre visible)                          │           │
│   │  [Completar tarea]    (visible desde progreso ≥ 80%)             │           │
│   └───────────────────┬─────────────────────────┬────────────────────┘           │
│                       │ Completar OK             │ Reportar problema OK          │
│                       ▼                          ▼                               │
│              Pantalla de éxito           Confirmación de fallo                  │
│              (modal sobre dashboard)     (modal de confirmación)                 │
│              → redirige /dashboard       → redirige /tareas                     │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────┐           │
│   │  /cartera  — Cartera del Proveedor                               │           │
│   │                                                                  │           │
│   │  ┌────────────────┐ ┌─────────────┐ ┌───────────┐ ┌──────────┐  │           │
│   │  │ Saldo          │ │ Pendiente   │ │ Ganado    │ │ Retirado │  │           │
│   │  │ disponible     │ │             │ │ total     │ │ total    │  │           │
│   │  └────────────────┘ └─────────────┘ └───────────┘ └──────────┘  │           │
│   │                                                                  │           │
│   │  [Solicitar retiro]                                              │           │
│   │                                                                  │           │
│   │  Historial de transacciones                                      │           │
│   │  ─────────────────────────────────────────────────────────────  │           │
│   │  Fecha · Tipo · Descripción · Monto · Estado                     │           │
│   └──────────────────────────────────────────────────────────────────┘           │
│                    │ Click "Solicitar retiro"                                    │
│                    ▼                                                              │
│              Modal de retiro                                                     │
│              Método · Destino · Monto · [Confirmar]                              │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────┐           │
│   │  /perfil  — Perfil del Proveedor                                 │           │
│   │                                                                  │           │
│   │  ┌──────────────────────────┐  ┌─────────────────────────────┐  │           │
│   │  │  Datos personales        │  │  Trust Score + Desglose      │  │           │
│   │  │  Nombre (editable)       │  │  Barra por componente        │  │           │
│   │  │  Email (solo lectura)    │  │  Rango actual + siguiente    │  │           │
│   │  │  Estado online [toggle]  │  └─────────────────────────────┘  │           │
│   │  │  Tasa de éxito           │                                    │           │
│   │  └──────────────────────────┘                                    │           │
│   │                                                                  │           │
│   │  ┌────────────────────────────────────────────────────────────┐  │           │
│   │  │  Hardware registrado                                       │  │           │
│   │  │  CPU · GPU · RAM · Almacenamiento · [Guardar cambios]      │  │           │
│   │  └────────────────────────────────────────────────────────────┘  │           │
│   └──────────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Flujo Completo End-to-End (happy path)

```
  1. Usuario nuevo visita la plataforma
         │
         ▼
  2. /registro — Introduce nombre, email, contraseña
         │  OK: cuenta creada, JWT generado, cartera inicializada
         ▼
  3. /dashboard — Primera vista (pantalla vacía con onboarding)
         │  Click "Explorar tareas disponibles"
         ▼
  4. /tareas — Listado completo de tareas del seed
         │  [Opcional] Aplica filtros de dificultad / hardware
         │  Click en una tarjeta de tarea
         ▼
  5. /tareas/:id — Lee descripción, recompensa, etapas
         │  Click "Aceptar tarea"
         │  [Spinner] POST /tasks/{id}/accept → asignación creada
         │  Click "Iniciar procesamiento"
         │  [Spinner] POST /tasks/{id}/start → estado: procesando
         ▼
  6. /procesando/:assignmentId — Progreso en tiempo real
         │  Polling cada 3s: GET /tasks/assignments/:id/progress
         │  Barra avanza 0% → 99%
         │  A partir de 80%: botón "Completar tarea" se activa
         │  Click "Completar tarea"
         │  [Spinner] POST /tasks/{id}/complete → recompensa acreditada
         ▼
  7. Modal de éxito: "¡Tarea completada! Has ganado X,XX CC"
         │  Click "Ver mi cartera" o cierre automático en 3s
         ▼
  8. /cartera — Saldo disponible actualizado, transacción visible
         │  [Opcional] Click "Solicitar retiro"
         │  Modal retiro → método → destino → monto → confirmar
         ▼
  9. /perfil — Trust Score actualizado, tareas completadas +1
         │  [Opcional] Actualizar hardware registrado
         ▼
  10. /dashboard — Métricas actualizadas, tarea aparece en "recientes"
```

---

## 4. Flujo de Error: Reporte de Problema

```
  /procesando/:assignmentId
         │  Click "Reportar problema"
         ▼
  Modal de confirmación:
  "¿Seguro que quieres reportar que no puedes completar esta tarea?
   Esto puede afectar negativamente tu Trust Score."
         │  [Cancelar] → cierra modal, vuelve a procesando
         │  [Confirmar] → POST /tasks/{id}/fail
         ▼
  Toast de información: "Tarea reportada. Tu Trust Score ha sido ajustado."
         │
         ▼
  Redirige a /tareas (listado de disponibles)
```

---

## 5. Flujo de Autenticación y Protección de Rutas

```
  Acceso a ruta protegida (/dashboard, /tareas, /cartera, /perfil, /procesando/*)
         │
         ▼
  ¿Existe token JWT en localStorage y no está expirado?
         │
         ├── NO → Redirige a /login (con parámetro returnUrl)
         │         Tras login exitoso → redirige a la ruta original
         │
         └── SÍ → Carga la página normalmente
                   Si el backend devuelve 401 (token expirado mid-session)
                   → Limpia authStore → Redirige a /login con aviso
                   "Tu sesión ha expirado. Inicia sesión de nuevo."
```

---

## 6. Transiciones de Estado de Asignación en la UI

```
  Estado de asignación        Pantalla activa               Acción disponible
  ─────────────────────       ───────────────────────────   ──────────────────────────
  Sin asignación              /tareas/:id                   [Aceptar tarea]
  aceptada                    /tareas/:id                   [Iniciar procesamiento]
                              o /procesando/:id (si navega)
  procesando                  /procesando/:id               [Completar] (si prog ≥ 80%)
                                                            [Reportar problema]
  completada                  /dashboard (redirigido)       —
  fallida                     /tareas (redirigido)          —
  cancelada                   /tareas                       —
```

---

## 7. Jerarquía de Navegación (Navbar)

La navbar es visible en todas las pantallas privadas y contiene acceso directo a los 4 módulos principales:

```
  [Co-Computing Logo]   Tareas   Cartera   Perfil        [Badge Rango] Nombre ▾
                                                          ─────────────────────
                                                          [Cerrar sesión]
```

El badge de rango en la navbar tiene color según el rango actual del proveedor:
- Nuevo: gris
- Confiable: azul
- Experto: verde
- Élite: dorado

En mobile (< 768px), la navbar colapsa en un menú hamburguesa que despliega los mismos elementos en vertical.

---

## 8. Gestión de Errores Globales

| Situación | Respuesta de la UI |
|---|---|
| 401 en cualquier endpoint protegido | Limpia sesión → redirige a /login con mensaje de sesión expirada |
| 403 en una operación | Toast de error: "No tienes permiso para realizar esta acción" |
| 404 en detalle de tarea | Pantalla de error inline con enlace a /tareas |
| 500 del servidor | Toast de error: "Ha ocurrido un error inesperado. Inténtalo de nuevo." |
| Sin conexión a internet | Banner informativo: "Comprueba tu conexión a internet" |
| Polling de progreso falla 3 veces consecutivas | Banner en la pantalla de procesamiento: "No se puede actualizar el progreso. Comprobando conexión..." |
