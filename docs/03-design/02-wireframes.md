# Co-Computing — Wireframes de Pantallas Principales

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** UX/UI Designer
**Referencias:** `docs/03-design/00-mapa-navegacion.md`, `docs/03-design/01-design-system.md`

**Leyenda de wireframes:**
```
[...]      → Botón o elemento interactivo
(...)      → Texto de etiqueta o valor de dato
{...}      → Icono
═══        → Borde / separador fuerte
───        → Separador sutil
░░░        → Área con skeleton loader (estado cargando)
▓▓▓        → Contenido con error (fondo de alert de error)
│           → Borde vertical
█           → Elemento completamente sólido (relleno)
```

---

## 1. Navbar / Layout Compartido

El layout es idéntico en todas las pantallas privadas. La navbar ocupa la parte superior, el contenido de página va debajo con padding.

### Estado: Normal (Desktop ≥ 1024px)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  NAVBAR  — altura 64px, bg-neutral-900, border-b border-neutral-700             ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │  {Bolt}  Co-Computing          Tareas   Cartera   Perfil                 │   ║
║  │                                                                          │   ║
║  │  (logo: text-brand-400 font-bold)  (nav links: text-neutral-300         │   ║
║  │                                     hover:text-neutral-100)              │   ║
║  │                                                        ┌──────────────┐  │   ║
║  │                                                        │ {Star}Élite  │  │   ║
║  │                                                        │  Ana García▾ │  │   ║
║  │                                                        └──────┬───────┘  │   ║
║  └─────────────────────────────────────────────────────────────── ┼ ───────┘   ║
║                                                   Dropdown ▼     │             ║
║                                          ┌────────────────────────┘             ║
║                                          │ ┌──────────────────────────┐         ║
║                                          │ │  {UserCircle} Mi perfil  │         ║
║                                          │ │  ─────────────────────── │         ║
║                                          │ │  {ArrowRightOnRect}      │         ║
║                                          │ │  Cerrar sesión           │         ║
║                                          │ └──────────────────────────┘         ║
╚══════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  PAGE CONTENT AREA                                                               │
│  max-w-7xl mx-auto px-8 py-8                                                     │
│  bg-neutral-950 min-h-screen                                                     │
│                                                                                  │
│  [contenido de la pantalla activa]                                               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Estado: Mobile (< 768px)

```
╔══════════════════════════════════════════════════════════════════╗
║  NAVBAR MOBILE — altura 56px                                     ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │  {Bolt} Co-Computing                         {Bars3}     │   ║
║  └──────────────────────────────────────────────────────────┘   ║
║                                                                  ║
║  [Menú abierto — overlay desde arriba]                           ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │  {Star} Élite · Ana García                               │   ║
║  │  ────────────────────────────────────────────────────    │   ║
║  │  {HomeIcon}      Dashboard                               │   ║
║  │  {BriefcaseIcon} Tareas disponibles                      │   ║
║  │  {WalletIcon}    Cartera                                 │   ║
║  │  {UserIcon}      Mi perfil                               │   ║
║  │  ────────────────────────────────────────────────────    │   ║
║  │  {ArrowRight}    Cerrar sesión                           │   ║
║  └──────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════╝
```

**Nota de implementación:** El enlace activo en la navbar recibe `text-brand-400 font-semibold` con un indicador inferior `border-b-2 border-brand-400` en desktop. En mobile, recibe `bg-neutral-800 rounded-lg`.

---

## 2. Pantalla de Login

**Ruta:** `/login`

### Estado: Datos (formulario vacío)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  PÁGINA PÚBLICA — bg-neutral-950 min-h-screen                                   ║
║                                                                                  ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │                    [cabecera pública sin nav links]                       │   ║
║  │   {Bolt}  Co-Computing                                                    │   ║
║  └──────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                  ║
║            ┌──────────────────────────────────────────────────────┐             ║
║            │                                                      │             ║
║            │       {Bolt}  Co-Computing                           │             ║
║            │       (text-brand-400, text-2xl, font-bold)          │             ║
║            │                                                      │             ║
║            │  ══════════════════════════════════════════════════  │             ║
║            │                                                      │             ║
║            │   Inicia sesión                                      │             ║
║            │   (text-2xl font-bold text-neutral-100)              │             ║
║            │   Bienvenido de nuevo a la plataforma                │             ║
║            │   (text-sm text-neutral-500)                         │             ║
║            │                                                      │             ║
║            │   Correo electrónico                                 │             ║
║            │   ┌──────────────────────────────────────────────┐  │             ║
║            │   │  tu@email.com                                │  │             ║
║            │   └──────────────────────────────────────────────┘  │             ║
║            │                                                      │             ║
║            │   Contraseña                                         │             ║
║            │   ┌──────────────────────────────────────┬────────┐ │             ║
║            │   │  ••••••••                             │ {Eye}  │ │             ║
║            │   └──────────────────────────────────────┴────────┘ │             ║
║            │                                                      │             ║
║            │   [         Iniciar sesión          ]                │             ║
║            │   (botón primario, w-full)                           │             ║
║            │                                                      │             ║
║            │   ────────────────────────────────────────────────  │             ║
║            │                                                      │             ║
║            │   ¿Aún no tienes cuenta?                             │             ║
║            │   [Regístrate aquí]  (link ghost brand)              │             ║
║            │                                                      │             ║
║            └──────────────────────────────────────────────────────┘             ║
║            max-w-md mx-auto mt-16, card con bg-neutral-900 rounded-xl p-8       ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

### Estado: Cargando (tras enviar formulario)

```
            ┌──────────────────────────────────────────────────────┐
            │   [campos del formulario — deshabilitados y opacidad] │
            │                                                      │
            │   [  {Spinner}  Iniciando sesión...  ]               │
            │   (botón primario + estado loading, deshabilitado)    │
            └──────────────────────────────────────────────────────┘
```

### Estado: Error

```
            ┌──────────────────────────────────────────────────────┐
            │                                                      │
            │   ┌──────────────────────────────────────────────┐  │
            │   │ {ExclamationCircle} Credenciales incorrectas. │  │
            │   │ Comprueba tu email y contraseña.              │  │
            │   └──────────────────────────────────────────────┘  │
            │   (alert de error, bg-danger-900/50 border-danger)   │
            │                                                      │
            │   Correo electrónico                                 │
            │   ┌──────────────────────────────────────────────┐  │
            │   │  tu@email.com                       [borde   │  │
            │   └──────────────────────────────────── rojo]────┘  │
            │                                                      │
            │   [         Iniciar sesión          ]                │
            └──────────────────────────────────────────────────────┘
```

---

## 3. Pantalla de Registro

**Ruta:** `/registro`

### Estado: Datos (formulario vacío)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║            ┌──────────────────────────────────────────────────────┐             ║
║            │                                                      │             ║
║            │       {Bolt}  Co-Computing                           │             ║
║            │                                                      │             ║
║            │  ══════════════════════════════════════════════════  │             ║
║            │                                                      │             ║
║            │   Crea tu cuenta                                     │             ║
║            │   Empieza a monetizar tu hardware hoy                │             ║
║            │                                                      │             ║
║            │   Nombre completo                                    │             ║
║            │   ┌──────────────────────────────────────────────┐  │             ║
║            │   │  Tu nombre                                   │  │             ║
║            │   └──────────────────────────────────────────────┘  │             ║
║            │                                                      │             ║
║            │   Correo electrónico                                 │             ║
║            │   ┌──────────────────────────────────────────────┐  │             ║
║            │   │  tu@email.com                                │  │             ║
║            │   └──────────────────────────────────────────────┘  │             ║
║            │                                                      │             ║
║            │   Contraseña  (mínimo 8 caracteres)                  │             ║
║            │   ┌──────────────────────────────────────┬────────┐ │             ║
║            │   │  ••••••••                             │ {Eye}  │ │             ║
║            │   └──────────────────────────────────────┴────────┘ │             ║
║            │                                                      │             ║
║            │   [         Crear cuenta          ]                  │             ║
║            │   (botón primario, w-full)                           │             ║
║            │                                                      │             ║
║            │   ────────────────────────────────────────────────  │             ║
║            │                                                      │             ║
║            │   ¿Ya tienes cuenta?                                 │             ║
║            │   [Inicia sesión]  (link ghost brand)                │             ║
║            │                                                      │             ║
║            └──────────────────────────────────────────────────────┘             ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

### Estado: Error de validación en campos

```
            │   Nombre completo                                    │
            │   ┌──────────────────────────────────── borde rojo ─┐│
            │   │                                                  ││
            │   └──────────────────────────────────────────────────┘│
            │   {ExclamationCircle} Este campo es obligatorio        │
            │   (text-xs text-danger-500)                            │
            │                                                        │
            │   Contraseña                                           │
            │   ┌──────────────────────────────────── borde rojo ─┐ │
            │   │  ••••••                                          │ │
            │   └──────────────────────────────────────────────────┘ │
            │   {ExclamationCircle} Mínimo 8 caracteres               │
```

### Estado: Cargando

```
            │   [  {Spinner}  Creando tu cuenta...  ]
            │   (botón loading, deshabilitado)
```

---

## 4. Dashboard

**Ruta:** `/dashboard`

### Estado: Datos (proveedor con actividad)

```
╔════ NAVBAR ════════════════════════════════════════════════════════════════════╗
╚════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  Bienvenido, Ana  (text-2xl font-bold text-neutral-100)                          │
│  Viernes, 5 de junio de 2026  (text-sm text-neutral-500)                        │
│                                                                                  │
│  ┌─────────────────────┬─────────────────────┬──────────────────────────────┐   │
│  │  {ChartBar}         │  {CheckCircle}       │  {BankNotes}                 │   │
│  │  Trust Score        │  Tareas              │  Ganancias totales           │   │
│  │                     │  completadas         │                              │   │
│  │  78,40              │  24                  │  48,75 CC                    │   │
│  │  (text-3xl bold     │  (text-3xl bold       │  (text-3xl bold             │   │
│  │   text-neutral-100) │   text-neutral-100)   │   text-success-400)        │   │
│  │                     │                      │                              │   │
│  │  {BoltIcon}         │                      │                              │   │
│  │  [badge Experto]    │  Tasa de éxito: 91,7% │  Disponible: 12,50 CC      │   │
│  │  text-emerald-400   │  (text-sm neutral-500)│  (text-sm success-500)     │   │
│  └─────────────────────┴─────────────────────┴──────────────────────────────┘   │
│  grid grid-cols-1 md:grid-cols-3 gap-4                                           │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────   │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ Saldo  │
│  │  {Wallet}  Cartera                       [Ir a mi cartera →]        │ card   │
│  │  ────────────────────────────────────────────────────────────────   │        │
│  │  Saldo disponible     12,50 CC   (text-success-400 text-2xl bold)   │        │
│  │  Saldo pendiente       0,00 CC   (text-neutral-400)                 │        │
│  └─────────────────────────────────────────────────────────────────────┘        │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────   │
│                                                                                  │
│  Actividad reciente  (text-xl font-semibold text-neutral-100)                    │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │  TAREA                       ESTADO             RECOMPENSA  FECHA         │  │
│  │  ──────────────────────────────────────────────────────────────────────── │  │
│  │  Renderizado 3D — Escena v3  {Check} Completada  +2,50 CC   04 jun        │  │
│  │  Entrenamiento ML ResNet-50  {Check} Completada  +5,00 CC   03 jun        │  │
│  │  Transcodificación 4K        ● En proceso        ——         hoy           │  │
│  │  Análisis de datos CSV       {X} Fallida          0,00 CC   02 jun        │  │
│  │  Simulación física fluidos   {Check} Completada  +3,00 CC   01 jun        │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  [Explorar todas las tareas disponibles  →]                                      │
│  (botón secundario o link)                                                       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Estado: Vacío (proveedor recién registrado, sin actividad)

```
│  ─────────────────────────────────────────────────────────────────────────────   │
│                                                                                  │
│  Actividad reciente                                                              │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                            │  │
│  │              {BriefcaseIcon}  (h-12 w-12 text-neutral-700)                │  │
│  │                                                                            │  │
│  │          Aún no has procesado ninguna tarea.                               │  │
│  │          (text-neutral-400)                                                │  │
│  │                                                                            │  │
│  │  [  Explorar tareas disponibles  ]  (botón primario)                       │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
```

### Estado: Cargando

```
│  ┌────────░░░░░░░░░░░░─┬───────░░░░░░░░░─┬────░░░░░░░░░░░░────┐  │
│  │  ░░░░░░░░░░░░░░░░░  │  ░░░░░░░░░░░░░  │  ░░░░░░░░░░░░░░░   │  │
│  │  ░░░░░              │  ░░░░░           │  ░░░░░              │  │
│  │  ░░░░░░░░░░         │  ░░░            │  ░░░░░░░░           │  │
│  └─────────────────────┴─────────────────┴────────────────────┘  │
│  [tres StatCards con animate-pulse skeleton]                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  [5 filas de skeleton para tareas recientes]                       │
```

---

## 5. Listado de Tareas con Filtros

**Ruta:** `/tareas`

### Estado: Datos (con y sin filtros activos)

```
╔════ NAVBAR ════════════════════════════════════════════════════════════════════╗
╚════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  Tareas disponibles  (text-2xl font-bold)                                        │
│  18 tareas encontradas  (text-sm text-neutral-500)                               │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  FILTROS                                                                  │   │
│  │                                                                          │   │
│  │  Dificultad                 Hardware              Tipo de tarea          │   │
│  │  ┌──────────────────┐       ┌──────────────────┐  ┌──────────────────┐   │   │
│  │  │ [✓] Fácil        │       │ [✓] CPU          │  │ Todos los tipos ▾│   │   │
│  │  │ [✓] Medio        │       │ [ ] GPU          │  └──────────────────┘   │   │
│  │  │ [ ] Difícil      │       │ [ ] Mixto        │                          │   │
│  │  └──────────────────┘       └──────────────────┘  Recompensa mínima      │   │
│  │                                                    ┌────────────────┐     │   │
│  │  [Limpiar filtros]  (botón ghost, visible solo     │ 0,00        CC │     │   │
│  │   cuando hay filtros activos)                      └────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│  bg-neutral-900 rounded-xl border border-neutral-700 p-4 mb-6                   │
│                                                                                  │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌─────────────────────┐│
│  │ [Fácil] [CPU]          │  │ [Medio] [GPU]           │  │ [Fácil] [Mixto]     ││
│  │                        │  │                         │  │                     ││
│  │ Análisis de datos CSV  │  │ Entrenamiento ML        │  │ Simulación fluidos  ││
│  │                        │  │ ResNet-50               │  │                     ││
│  │ [CPU]  15-25 min       │  │ [GPU]  45-90 min        │  │ [Mixto] 20-40 min   ││
│  │ {Users} 5 plazas       │  │ {Users} 2 plazas        │  │ {Users} 8 plazas    ││
│  │ ────────────────────   │  │ ─────────────────────── │  │ ──────────────────  ││
│  │                 1,50 CC│  │                  5,00 CC│  │              2,75 CC││
│  └────────────────────────┘  └────────────────────────┘  └─────────────────────┘│
│  grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4                            │
│                                                                                  │
│  [más tarjetas...]                                                               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Filtros activos (chips visuales):**
Cuando hay filtros seleccionados, se muestran chips encima del grid:
```
│  Filtros activos:  [Fácil ×]  [CPU ×]  [Limpiar todo]          │
│  (chips pequeños con border brand-500, text-brand-400)          │
```

### Estado: Vacío (sin resultados para los filtros)

```
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │          {FunnelIcon}  (h-12 w-12 text-neutral-700)        │  │
│  │                                                            │  │
│  │     No hay tareas disponibles con estos filtros.           │  │
│  │                                                            │  │
│  │  [  Limpiar filtros  ]  (botón secundario)                  │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
```

### Estado: Cargando

```
│  ┌──────────░░░░─┐  ┌──────────░░░░─┐  ┌──────────░░░░─┐        │
│  │ ░░░ ░░░░░░░   │  │ ░░░ ░░░░░░░   │  │ ░░░ ░░░░░░░   │        │
│  │ ░░░░░░░░░░░░░ │  │ ░░░░░░░░░░░░░ │  │ ░░░░░░░░░░░░░ │        │
│  │ ░░░░░░░       │  │ ░░░░░░░       │  │ ░░░░░░░       │        │
│  │ ░░░ ░░░ ░░░   │  │ ░░░ ░░░ ░░░   │  │ ░░░ ░░░ ░░░   │        │
│  │ ─────────── ░ │  │ ─────────── ░ │  │ ─────────── ░ │        │
│  └───────────────┘  └───────────────┘  └───────────────┘        │
│  [6 TaskCard skeleton, animate-pulse]                             │
```

---

## 6. Detalle de Tarea

**Ruta:** `/tareas/:id`

### Estado: Datos (tarea disponible, sin asignación previa)

```
╔════ NAVBAR ════════════════════════════════════════════════════════════════════╗
╚════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  [← Volver al listado]  (link ghost, ChevronLeftIcon)                            │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  [Renderizado 3D]  [Difícil]              [GPU]  {CpuChipIcon}           │   │
│  │  (badge tipo)     (badge dificultad rojo) (badge hardware brand)         │   │
│  │                                                                          │   │
│  │  Renderizado de escena nocturna 4K con iluminación volumétrica            │   │
│  │  (text-2xl font-bold text-neutral-100)                                   │   │
│  │                                                                          │   │
│  │  Solicitante: StudioFX Digital  (text-sm text-neutral-400)               │   │
│  │                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌───────────────────────────────────────────┐  ┌────────────────────────────┐  │
│  │  DESCRIPCIÓN                              │  │  DETALLES                  │  │
│  │  ─────────────────────────────────────── │  │  ─────────────────────────  │  │
│  │  Renderizado completo de una escena       │  │                            │  │
│  │  3D de alta complejidad con Cycles.       │  │  Recompensa                │  │
│  │  Se proporcionará el fichero .blend       │  │  5,00 CC                   │  │
│  │  comprimido. Se requiere GPU con          │  │  (text-2xl success-400     │  │
│  │  mínimo 8GB VRAM para tiempos             │  │   font-bold)               │  │
│  │  aceptables.                              │  │                            │  │
│  │  (text-sm text-neutral-300 leading-       │  │  ── ── ── ── ── ── ──      │  │
│  │   relaxed)                                │  │                            │  │
│  │                                           │  │  {Clock} Duración est.     │  │
│  │                                           │  │  45 – 90 minutos           │  │
│  │                                           │  │                            │  │
│  │                                           │  │  {UserGroup} Plazas        │  │
│  │                                           │  │  3 de 5 disponibles        │  │
│  │                                           │  │  [███░░] (barra neutral)   │  │
│  │                                           │  │                            │  │
│  │                                           │  │  {CpuChip} Hardware        │  │
│  │                                           │  │  GPU requerida             │  │
│  └───────────────────────────────────────────┘  └────────────────────────────┘  │
│  grid grid-cols-1 lg:grid-cols-3 (desc: col-span-2, detalles: col-span-1)        │
│                                                                                  │
│  ETAPAS DE PROCESAMIENTO                                                         │
│  ─────────────────────────────────────────────────────────────────────────────  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  1. Preparando entorno       2. Descargando recursos    3. Renderizando  │   │
│  │  4. Validando salida         5. Empaquetando resultado                   │   │
│  │  (chips con número + nombre, bg-neutral-800 border-neutral-700)          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  [           Aceptar tarea           ]  (botón primario, w-full md:w-auto│   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Variación de Botón según estado:

```
[Estado A] Tarea disponible, sin asignación:
  [           Aceptar tarea           ]   ← botón primario activo

[Estado B] Asignación activa (aceptada o procesando):
  [       Continuar procesamiento      ]  ← botón primario activo (link a /procesando/:id)

[Estado C] Sin plazas (slots_left = 0):
  [         Sin plazas disponibles     ]  ← botón primario disabled + opacity-50
  + nota: "Esta tarea ya no tiene plazas disponibles." (text-xs warning-500 text-center)
```

**Tras pulsar "Aceptar tarea" — feedback inline:**
```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  {CheckCircle} ¡Tarea aceptada correctamente!                            │
  │  (alert de éxito)                                                        │
  └──────────────────────────────────────────────────────────────────────────┘

  [       Iniciar procesamiento       ]   ← botón primario activo
  [  Volver al listado  ]                 ← botón secundario
```

### Estado: Cargando

```
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ░░░ ░░░          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                                  │  │
│  │                                                                        │  │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                                       │  │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░         │  │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
```

### Estado: Error 404

```
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │          {ExclamationTriangle}  (h-12 w-12 text-neutral-600)           │  │
│  │                                                                        │  │
│  │              Tarea no encontrada                                       │  │
│  │     Esta tarea no existe o ya no está disponible.                      │  │
│  │                                                                        │  │
│  │    [  ← Ver todas las tareas  ]  (botón secundario)                    │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
```

---

## 7. Pantalla de Progreso de Procesamiento

**Ruta:** `/procesando/:assignmentId`

Esta es la pantalla más importante en términos de UX. Debe ser tranquilizadora, mostrar progreso claro y transmitir que el sistema está trabajando.

### Estado: Datos (procesamiento en curso, progreso 45%)

```
╔════ NAVBAR ════════════════════════════════════════════════════════════════════╗
╚════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │   ● En proceso  (badge animado con punto pulsante brand-400)             │   │
│  │                                                                          │   │
│  │   Renderizado de escena nocturna 4K                                      │   │
│  │   (text-2xl font-bold text-neutral-100)                                  │   │
│  │                                                                          │   │
│  │   Solicitante: StudioFX Digital · GPU · Difícil                          │   │
│  │   (text-sm text-neutral-500)                                             │   │
│  │                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│  bg-neutral-900 rounded-xl border border-brand-500/30 p-6 mb-6                  │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  ┌───────────┐  │
│  │  PROGRESO ACTUAL                                           │  │  ETAPAS   │  │
│  │  ──────────────────────────────────────────────────────── │  │           │  │
│  │                                                            │  │  ✓ Prep.  │  │
│  │               45%                                         │  │    entorno│  │
│  │         (text-4xl font-bold text-neutral-100               │  │           │  │
│  │          tabular-nums, centrado)                           │  │  ✓ Descarg│  │
│  │                                                            │  │    recurs.│  │
│  │  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░       │  │           │  │
│  │  (barra: h-3 rounded-full, gradient brand-600→brand-400)  │  │  ◉ Render │  │
│  │  (fondo: bg-neutral-800)                                  │  │    izando │  │
│  │                                                            │  │  (ACTIVA) │  │
│  │  Iniciado a las 14:23 · Actualizado hace 2s                │  │           │  │
│  │  (text-xs text-neutral-500 text-center mt-2)               │  │  ○ Valida │  │
│  │                                                            │  │    ndo    │  │
│  │  ────────────────────────────────────────────────────────  │  │           │  │
│  │                                                            │  │  ○ Empaq. │  │
│  │  El botón "Completar" se habilitará al alcanzar el 80%.    │  │    result.│  │
│  │  (text-xs text-neutral-500 italic)                         │  │           │  │
│  │                                                            │  └───────────┘  │
│  │  [  {Spinner}  Actualizando progreso...  ]                  │                 │
│  │  (text-xs text-neutral-600, icono h-3 w-3)                │                 │
│  └────────────────────────────────────────────────────────────┘                 │
│  grid grid-cols-1 lg:grid-cols-3 (progreso: col-span-2, etapas: col-span-1)     │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  [ Completar tarea ]  (botón primario — DESHABILITADO, opacity-50)       │   │
│  │  [ Reportar problema ]  (botón peligro — SIEMPRE ACTIVO)                 │   │
│  │                                                                          │   │
│  │  El botón "Completar tarea" se activará cuando el progreso               │   │
│  │  alcance el 80%.  (text-xs text-neutral-600, visible si < 80%)           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Variación: Progreso ≥ 80% (botón completar activo)

```
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  [ ✓  Completar tarea  ]  (botón primario — ACTIVO, éxito inminente)    │   │
│  │  [ Reportar problema ]  (botón peligro — ACTIVO)                        │   │
│  │                                                                          │   │
│  │  La tarea está casi lista. Pulsa "Completar" cuando confirmes            │   │
│  │  que el procesamiento ha terminado.                                      │   │
│  │  (text-xs text-neutral-400, visible cuando prog ≥ 80%)                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
```

### Modal de Confirmación de Completar:

```
╔══════════════════════════════════════════════════════╗
║  MODAL — "Completar tarea"                           ║
║  ────────────────────────────────────────────────── ║
║                                                      ║
║  {CheckCircleIcon}  (h-10 w-10 text-success-400)    ║
║                                                      ║
║  ¿Completar esta tarea?                              ║
║  (text-lg font-semibold)                             ║
║                                                      ║
║  Confirmas que el procesamiento ha finalizado        ║
║  correctamente. Recibirás 5,00 CC en tu cartera.     ║
║  (text-sm text-neutral-400)                          ║
║                                                      ║
║  ──────────────────────────────────────────────────  ║
║                                                      ║
║  [  Cancelar  ]     [  Confirmar y cobrar  ]         ║
║  (botón sec.)        (botón primario)                ║
╚══════════════════════════════════════════════════════╝
```

### Modal de Confirmación de Reporte de Problema:

```
╔══════════════════════════════════════════════════════╗
║  MODAL — "Reportar problema"                         ║
║  ────────────────────────────────────────────────── ║
║                                                      ║
║  {ExclamationTriangleIcon}  (h-10 w-10 text-warning) ║
║                                                      ║
║  ¿Reportar que no puedes completar esta tarea?       ║
║  (text-lg font-semibold)                             ║
║                                                      ║
║  Esta acción registra que no has podido finalizar    ║
║  el procesamiento. No recibirás la recompensa y      ║
║  tu Trust Score puede verse afectado.                ║
║  (text-sm text-neutral-400)                          ║
║                                                      ║
║  ──────────────────────────────────────────────────  ║
║                                                      ║
║  [  Cancelar  ]     [  Reportar problema  ]          ║
║  (botón sec.)        (botón peligro)                 ║
╚══════════════════════════════════════════════════════╝
```

### Estado: Cargando inicial (al entrar a la página)

```
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  (título skeleton)          │   │
│  │       ░░░░░░░░░░░░░░░░  (subtítulo skeleton)                             │   │
│  │                                                                          │   │
│  │              {AnimateSpin}  (Spinner grande, text-brand-400, h-8 w-8)    │   │
│  │         Cargando estado de la tarea...  (text-neutral-500)               │   │
│  │                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
```

### Estado: Error de conexión (polling falla)

```
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  {WifiIcon} No se puede actualizar el progreso.                          │   │
│  │  Comprobando la conexión...  (alert informativo, auto-reintento)         │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│  [El stepper y la barra muestran el último valor conocido]                       │
```

---

## 8. Cartera (Wallet)

**Ruta:** `/cartera`

### Estado: Datos

```
╔════ NAVBAR ════════════════════════════════════════════════════════════════════╗
╚════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  Mi cartera  (text-2xl font-bold)                                                │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  SALDOS                                                                  │   │
│  │  ────────────────────────────────────────────────────────────────────── │   │
│  │                                                                          │   │
│  │  ┌──────────────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐  │   │
│  │  │  {BankNotes}         │  │  {Clock}      │  │  {Arrow  │  │  {Arrow │  │   │
│  │  │  Saldo disponible    │  │  Pendiente    │  │  Up}     │  │  Down}  │  │   │
│  │  │                      │  │               │  │  Total   │  │  Total  │  │   │
│  │  │  12,50 CC            │  │   0,00 CC     │  │  ganado  │  │ retirado│  │   │
│  │  │  (text-3xl           │  │   (text-2xl   │  │          │  │         │  │   │
│  │  │   success-400 bold)  │  │    neutral)   │  │ 48,75 CC │  │ 36,25 CC│  │   │
│  │  │                      │  │               │  │ (text-2xl│  │ (text-2xl│  │   │
│  │  │  Listo para retirar  │  │  En proceso   │  │  neutral)│  │  neutral)│  │   │
│  │  └──────────────────────┘  └──────────────┘  └──────────┘  └─────────┘  │   │
│  │  grid grid-cols-2 md:grid-cols-4 gap-4                                   │   │
│  │                                                                          │   │
│  │  [  Solicitar retiro  ]  (botón primario)                                │   │
│  │  (Saldo mínimo para retirar: 10,00 CC)                                   │   │
│  │  (text-xs text-neutral-500)                                              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  Historial de transacciones  (text-xl font-semibold)                             │
│  Últimas 50 transacciones                                                        │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │  FECHA          TIPO              DESCRIPCIÓN              MONTO   ESTADO  │  │
│  │  ──────────────────────────────────────────────────────────────────────── │  │
│  │  05 jun 14:32   [Pago de tarea]   Tarea: Rend. 3D          +5,00   ✓ Ok   │  │
│  │  05 jun 10:15   [Penalización]    Tarea fallida: Simul.    -0,80   ✓ Ok   │  │
│  │  04 jun 09:00   [Retiro]          Retiro PayPal            -10,00  ⏳Pend  │  │
│  │  03 jun 18:45   [Pago de tarea]   Tarea: Entrena. ML       +5,00   ✓ Ok   │  │
│  │  03 jun 11:30   [Bono]            Bono por primer rango    +1,00   ✓ Ok   │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│  border border-neutral-700 rounded-xl overflow-hidden                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Modal de Solicitud de Retiro:

```
╔═══════════════════════════════════════════════════════════════╗
║  MODAL — Solicitar retiro  ×                                  ║
║  ─────────────────────────────────────────────────────────── ║
║                                                               ║
║  Saldo disponible: 12,50 CC                                   ║
║  (text-sm text-neutral-400, destacado)                        ║
║                                                               ║
║  Método de retiro                                             ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │  ○ Transferencia bancaria                               │  ║
║  │  ● PayPal                                               │  ║
║  │  ○ Criptomoneda                                         │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  Email de PayPal                                              ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │  tu@paypal.com                                          │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  Monto a retirar (CC)                                         ║
║  ┌───────────────────────────────────────────────────────┐    ║
║  │  10,00                                           CC   │    ║
║  └───────────────────────────────────────────────────────┘    ║
║  Mínimo: 10,00 CC · Máximo: 12,50 CC                          ║
║  (text-xs text-neutral-500)                                   ║
║                                                               ║
║  ─────────────────────────────────────────────────────────── ║
║                                                               ║
║  [  Cancelar  ]          [  Confirmar retiro  ]               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Paso 2 del modal (confirmación antes de enviar):**
```
╔═══════════════════════════════════════════════════════════════╗
║  Confirma tu solicitud de retiro                              ║
║  ─────────────────────────────────────────────────────────── ║
║                                                               ║
║  Monto:    10,00 CC                                           ║
║  Método:   PayPal                                             ║
║  Destino:  tu@paypal.com                                      ║
║                                                               ║
║  Te contactaremos cuando se procese el retiro.                ║
║  (text-sm text-neutral-400)                                   ║
║                                                               ║
║  ─────────────────────────────────────────────────────────── ║
║                                                               ║
║  [  ← Volver  ]          [  Confirmar  ]                      ║
╚═══════════════════════════════════════════════════════════════╝
```

### Estado: Sin transacciones

```
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │         {DocumentTextIcon}  (h-12 w-12 text-neutral-700)               │  │
│  │                                                                        │  │
│  │              No tienes transacciones aún.                              │  │
│  │      Cuando completes tu primera tarea, aparecerá aquí.                │  │
│  │                                                                        │  │
│  │   [  Explorar tareas disponibles  ]  (botón secundario)                │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
```

### Estado: Cargando

```
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ┌──────────────░░┐ ┌───────░░┐ ┌──────────░░┐ ┌─────────░░┐       │   │
│  │  │ ░░░░░░░░░░░░░  │ │ ░░░░░░ │ │ ░░░░░░░░░░ │ │ ░░░░░░░░ │       │   │
│  │  │ ░░░░░░░░░░     │ │ ░░░░░  │ │ ░░░░░░░░   │ │ ░░░░░░░  │       │   │
│  │  └────────────────┘ └────────┘ └────────────┘ └──────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  [skeleton de 4 BalanceCards + 5 filas de tabla]                            │
```

---

## 9. Perfil del Proveedor

**Ruta:** `/perfil`

### Estado: Datos

```
╔════ NAVBAR ════════════════════════════════════════════════════════════════════╗
╚════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│  Mi perfil  (text-2xl font-bold)                                                 │
│                                                                                  │
│  ┌────────────────────────────────────────────┐  ┌────────────────────────────┐ │
│  │  DATOS PERSONALES                          │  │  TRUST SCORE               │ │
│  │  ────────────────────────────────────────  │  │  ─────────────────────────  │ │
│  │                                            │  │                            │ │
│  │  ┌────────────────────────────────────┐   │  │  78,40                     │ │
│  │  │  {UserCircle}  (h-16 w-16          │   │  │  (text-4xl bold neutral-100)│ │
│  │  │   text-neutral-600)                │   │  │                            │ │
│  │  │  Ana García                        │   │  │  {Bolt}  [badge Experto]    │ │
│  │  │  (text-xl font-semibold)           │   │  │  (emerald-400)             │ │
│  │  └────────────────────────────────────┘   │  │                            │ │
│  │                                            │  │  ────────────────────────  │ │
│  │  Nombre completo                           │  │                            │ │
│  │  ┌────────────────────────────────────┐   │  │  Tasa de completado  40%   │ │
│  │  │  Ana García                        │   │  │  ███████████░░░░░░░░  87   │ │
│  │  └────────────────────────────────────┘   │  │                            │ │
│  │                                            │  │  Precisión          30%    │ │
│  │  Correo electrónico                        │  │  █████████░░░░░░░░░  82   │ │
│  │  ┌────────────────────────────────────┐   │  │                            │ │
│  │  │  ana@email.com    {LockClosed}     │   │  │  Tiempo de respuesta 20%   │ │
│  │  │  (solo lectura, text-neutral-500)  │   │  │  ████████░░░░░░░░░░░  70   │ │
│  │  └────────────────────────────────────┘   │  │                            │ │
│  │                                            │  │  Valoración cliente  10%   │ │
│  │  Miembro desde  01 ene 2026               │  │  ████████░░░░░░░░░░░  70   │ │
│  │  (text-sm text-neutral-500)               │  │                            │ │
│  │                                            │  │  ────────────────────────  │ │
│  │  Estado de disponibilidad                  │  │                            │ │
│  │  ┌──────────────────────────────────┐     │  │  Siguiente rango: Élite    │ │
│  │  │  Online  [██ toggle ON]          │     │  │  Te faltan 11,6 puntos     │ │
│  │  │  (success-500 cuando activo)     │     │  │  para llegar a Élite.      │ │
│  │  └──────────────────────────────────┘     │  │  (text-sm text-neutral-400)│ │
│  │                                            │  │                            │ │
│  │  Tasa de éxito: 91,7%                     │  │  [Ver desglose completo ▾] │ │
│  │  (text-sm neutral-500)                    │  │                            │ │
│  │                                            │  └────────────────────────────┘ │
│  │  [  Guardar cambios  ]  (botón primario)  │                                  │
│  └────────────────────────────────────────────┘                                  │
│  grid grid-cols-1 lg:grid-cols-2 gap-6                                           │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  Hardware registrado  (text-xl font-semibold)                                    │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  ┌──────────────────────────────┐  ┌────────────────────────────────┐   │   │
│  │  │  {CpuChipIcon}               │  │  {RectangleGroup}               │   │   │
│  │  │  Modelo de CPU *             │  │  Modelo de GPU  (opcional)      │   │   │
│  │  │  ┌──────────────────────┐   │  │  ┌──────────────────────────┐   │   │   │
│  │  │  │ AMD Ryzen 9 5950X    │   │  │  │ NVIDIA RTX 4090          │   │   │   │
│  │  │  └──────────────────────┘   │  │  └──────────────────────────┘   │   │   │
│  │  └──────────────────────────────┘  └────────────────────────────────┘   │   │
│  │                                                                          │   │
│  │  ┌──────────────────────────────┐  ┌────────────────────────────────┐   │   │
│  │  │  {CircleStack}               │  │  {ArchiveBox}                   │   │   │
│  │  │  RAM (GB) *                  │  │  Almacenamiento (GB) *          │   │   │
│  │  │  ┌──────────────────────┐   │  │  ┌──────────────────────────┐   │   │   │
│  │  │  │  64                  │   │  │  │  2000                    │   │   │   │
│  │  │  └──────────────────────┘   │  │  └──────────────────────────┘   │   │   │
│  │  └──────────────────────────────┘  └────────────────────────────────┘   │   │
│  │  grid grid-cols-1 sm:grid-cols-2 gap-4                                   │   │
│  │                                                                          │   │
│  │  [  Guardar hardware  ]  (botón primario)                                │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Descripción de rangos (panel expandible en Trust Score):**
```
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  RANGOS DE CO-COMPUTING                                    │  │
│  │                                                            │  │
│  │  {User}   Nuevo       0–49     Proveedor en prueba        │  │
│  │  {Shield} Confiable   50–74    Historial positivo         │  │
│  │  {Bolt}   Experto     75–89    Alto rendimiento    ← TÚ   │  │
│  │  {Star}   Élite       90–100   Máxima confianza           │  │
│  └────────────────────────────────────────────────────────────┘  │
```

### Estado: Cargando

```
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ░░░░░░░░  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  │
│  │  ░░░░░░░░░░░░░░░░                                          │  │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░  ░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░    ░░░░░░░░░░░░░░░░░░░░░░░░░░   │  │
│  └────────────────────────────────────────────────────────────┘  │
│  [skeleton del formulario de perfil + trust score card]           │
```

### Estado: Error (fallo al cargar datos del perfil)

```
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  {ExclamationCircle}  No se pudieron cargar los datos        │  │
│  │  de tu perfil. Comprueba tu conexión e inténtalo de nuevo.  │  │
│  │                                                              │  │
│  │  [  Reintentar  ]  (botón secundario)                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  (alert de error centrado en la pantalla)                           │
```

---

## 10. Pantalla de Éxito Post-Completar (Modal sobre Dashboard)

Esta no es una ruta independiente, sino un modal que aparece sobre el dashboard inmediatamente después de completar una tarea. Se cierra manualmente o tras 5 segundos.

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     {CheckCircleIcon}                                         ║
║     (h-16 w-16 text-success-400, centrado)                   ║
║                                                               ║
║     ¡Tarea completada!                                        ║
║     (text-2xl font-bold text-neutral-100, centrado)           ║
║                                                               ║
║     Has ganado                                                ║
║     5,00 CC                                                   ║
║     (text-4xl font-bold text-success-400, centrado)           ║
║                                                               ║
║     por "Renderizado de escena nocturna 4K"                   ║
║     (text-sm text-neutral-400, centrado)                      ║
║                                                               ║
║     Tu saldo disponible ha sido actualizado.                  ║
║                                                               ║
║  ──────────────────────────────────────────────────────────  ║
║                                                               ║
║  [  Ver mi cartera  ]      [  Volver al dashboard  ]          ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 11. Pantalla de Estado Vacío Global (404 de ruta)

Para rutas no existentes (`*` en React Router):

```
╔════ NAVBAR ════════════════════════════════════════════════════════════════════╗
╚════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                                                                                  │
│                    {ExclamationCircleIcon}                                       │
│                    (h-20 w-20 text-neutral-700)                                  │
│                                                                                  │
│                         Página no encontrada                                     │
│                     (text-2xl font-bold text-neutral-300)                        │
│                                                                                  │
│             La dirección a la que intentas acceder no existe.                    │
│                     (text-sm text-neutral-500)                                   │
│                                                                                  │
│                    [  ← Volver al dashboard  ]                                   │
│                    (botón primario, centrado)                                    │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Notas de Implementación para el Frontend Developer

### Comportamiento de datos sensibles al rango en la UI

El componente `RankBadge` recibe `rank: 'nuevo' | 'confiable' | 'experto' | 'elite'` y devuelve el badge completo con icono, color y texto. Debe usarse en:
- `DashboardPage.tsx` — junto al Trust Score
- `Navbar` (componente de layout) — junto al nombre
- `ProfilePage.tsx` — en la sección de Trust Score
- Historial de tareas recientes (opcional, subtexto)

### Barra de progreso (ProgressStepper)

El componente recibe:
```typescript
interface ProgressStepperProps {
  stages: string[]           // nombres de las etapas
  currentStageIndex: number  // índice de la etapa activa (0-based)
  progress: number           // porcentaje 0-99
}
```
La etapa activa se calcula: `currentStageIndex = Math.floor((progress / 100) * stages.length)` (el backend lo devuelve, el frontend lo usa directamente).

### Trust Score Breakdown

El componente `TrustScoreBreakdown` recibe los cuatro componentes y el rango:
```typescript
interface TrustScoreBreakdownProps {
  total: number
  completionRate: number  // 0-100, peso 40%
  accuracy: number        // 0-100, peso 30%
  responseTime: number    // 0-100, peso 20%
  clientRating: number    // 0-100, peso 10%
  rank: string
  nextRank: string | null
  pointsToNextRank: number | null
}
```

### Polling en ProcessingPage

El hook `useTaskProgress` gestiona:
1. `setInterval` de 3000ms llamando a `GET /tasks/assignments/:id/progress`
2. Limpieza en `useEffect` return (cleanup)
3. Si la respuesta devuelve `status: 'completada'` o `status: 'fallida'`, navega automáticamente
4. Si falla 3 veces consecutivas, muestra el banner de error de conexión pero no detiene el polling (lo reintenta)

### Accesibilidad de la barra de progreso

```html
<div role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={99}
     aria-label="Progreso de la tarea">
  ...
</div>
```

### Moneda del sistema

Todos los montos se muestran con el sufijo `CC` (Co-Computing Credits) con dos decimales. El formato numérico usa coma decimal en español: `1.234,56 CC`. Usar la función de utilidad `formatCC(amount: number): string` que aplica `toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' CC'`.
