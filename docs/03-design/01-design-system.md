# Co-Computing — Design System

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** UX/UI Designer
**Stack de implementación:** React 18 + Tailwind CSS 3.4 + @heroicons/react 2.x

---

## 1. Principios de Diseño

1. **Tech-oriented, no frío.** La interfaz es limpia y profesional pero usa calor visual (acentos de color, gradientes sutiles) para que no parezca un panel de administración genérico.
2. **Datos siempre legibles.** Los números (saldo, Trust Score, recompensas) son el contenido principal. La tipografía y el espaciado los destacan por encima de la decoración.
3. **Estados explícitos.** Cada componente tiene aspecto diferente en estado normal, hover, activo, deshabilitado, cargando y error. No existe estado ambiguo.
4. **Rangos como identidad.** Los cuatro rangos del proveedor tienen paleta, icono y lenguaje propios. El proveedor debe sentir que pertenece a un nivel y que puede progresar.
5. **Español y claridad.** Ningún término técnico sin explicación. La UI habla como hablaría un colega, no una documentación de API.

---

## 2. Design Tokens

### 2.1 Paleta de Colores Base

Los valores hexadecimales corresponden a las clases de Tailwind personalizadas configuradas en `tailwind.config.ts`.

#### Neutros (fondos, textos, bordes)

| Token | Hex | Tailwind | Uso |
|---|---|---|---|
| `neutral-950` | `#0A0F1E` | `bg-neutral-950` | Fondo global de la app (modo oscuro) |
| `neutral-900` | `#111827` | `bg-neutral-900` | Fondo de cards, paneles |
| `neutral-800` | `#1F2937` | `bg-neutral-800` | Fondo de inputs, tablas |
| `neutral-700` | `#374151` | `bg-neutral-700` | Bordes principales, separadores |
| `neutral-500` | `#6B7280` | `text-neutral-500` | Texto secundario, labels |
| `neutral-300` | `#D1D5DB` | `text-neutral-300` | Texto de cuerpo |
| `neutral-100` | `#F3F4F6` | `text-neutral-100` | Texto principal, headings |
| `neutral-50`  | `#F9FAFB` | `text-neutral-50`  | Texto de contraste máximo |

#### Acento Principal (Cian tecnológico)

| Token | Hex | Tailwind | Uso |
|---|---|---|---|
| `brand-600` | `#0284C7` | `bg-brand-600` | Botones primarios activos |
| `brand-500` | `#0EA5E9` | `bg-brand-500` | Hover de botón primario, links |
| `brand-400` | `#38BDF8` | `text-brand-400` | Texto de acento, badges activos |
| `brand-300` | `#7DD3FC` | `text-brand-300` | Subrayados, indicadores de progreso |
| `brand-100` | `#E0F2FE` | `bg-brand-100/10` | Fondo sutil de elementos de marca |

#### Semánticos (feedback)

| Token | Hex | Tailwind | Uso |
|---|---|---|---|
| `success-500` | `#22C55E` | `text-success-500` | Ingresos, completado, online |
| `success-900` | `#14532D` | `bg-success-900/50` | Fondo de alert de éxito |
| `warning-500` | `#F59E0B` | `text-warning-500` | Advertencias, pendiente |
| `warning-900` | `#78350F` | `bg-warning-900/50` | Fondo de alert de advertencia |
| `danger-500`  | `#EF4444` | `text-danger-500`  | Errores, egresos, fallos |
| `danger-900`  | `#7F1D1D` | `bg-danger-900/50` | Fondo de alert de error |
| `info-500`    | `#3B82F6` | `text-info-500`    | Información general |
| `info-900`    | `#1E3A5F` | `bg-info-900/50`   | Fondo de alert informativo |

---

### 2.2 Colores de los 4 Rangos

Cada rango tiene una identidad visual de 4 elementos: color primario, color de fondo, icono Heroicon, y texto de descripción.

#### Rango NUEVO (Trust Score: 0 – 49)

| Elemento | Valor |
|---|---|
| Color principal | `#94A3B8` (slate-400) |
| Color de fondo | `rgba(148, 163, 184, 0.12)` |
| Borde del badge | `1px solid #475569` (slate-600) |
| Icono | `UserIcon` (Heroicons Outline) |
| Texto del badge | `Nuevo` |
| Tailwind principal | `text-slate-400` |
| Tailwind fondo | `bg-slate-400/10` |
| Tailwind borde | `border-slate-600` |
| Descripción en UI | "Proveedor en periodo de prueba. Completa tareas para subir de rango." |

#### Rango CONFIABLE (Trust Score: 50 – 74)

| Elemento | Valor |
|---|---|
| Color principal | `#60A5FA` (blue-400) |
| Color de fondo | `rgba(96, 165, 250, 0.12)` |
| Borde del badge | `1px solid #2563EB` (blue-600) |
| Icono | `ShieldCheckIcon` (Heroicons Outline) |
| Texto del badge | `Confiable` |
| Tailwind principal | `text-blue-400` |
| Tailwind fondo | `bg-blue-400/10` |
| Tailwind borde | `border-blue-600` |
| Descripción en UI | "Proveedor con historial positivo. La plataforma confía en tu trabajo." |

#### Rango EXPERTO (Trust Score: 75 – 89)

| Elemento | Valor |
|---|---|
| Color principal | `#34D399` (emerald-400) |
| Color de fondo | `rgba(52, 211, 153, 0.12)` |
| Borde del badge | `1px solid #059669` (emerald-600) |
| Icono | `BoltIcon` (Heroicons Solid) |
| Texto del badge | `Experto` |
| Tailwind principal | `text-emerald-400` |
| Tailwind fondo | `bg-emerald-400/10` |
| Tailwind borde | `border-emerald-600` |
| Descripción en UI | "Proveedor de alto rendimiento. Acceso prioritario a tareas premium." |

#### Rango ÉLITE (Trust Score: 90 – 100)

| Elemento | Valor |
|---|---|
| Color principal | `#FBBF24` (amber-400) |
| Color de fondo | `rgba(251, 191, 36, 0.12)` |
| Borde del badge | `1px solid #D97706` (amber-600) |
| Icono | `StarIcon` (Heroicons Solid) |
| Texto del badge | `Élite` |
| Tailwind principal | `text-amber-400` |
| Tailwind fondo | `bg-amber-400/10` |
| Tailwind borde | `border-amber-600` |
| Descripción en UI | "El nivel más alto de confianza. Eres parte del grupo de élite de Co-Computing." |
| Efecto extra | Gradiente sutil dorado en el borde del card del dashboard: `border-gradient-to-r from-amber-600 to-amber-400` |

---

### 2.3 Tipografía

**Fuente principal:** Inter (Google Fonts). Se importa en el `index.html`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

**Fuente de código / datos técnicos:** JetBrains Mono (para direcciones de wallet, IBANs, hashes).

| Escala | Tailwind | px equiv. | Peso | Uso |
|---|---|---|---|---|
| `text-xs` | `text-xs` | 12px | 400 | Labels de campo, metadatos, timestamps |
| `text-sm` | `text-sm` | 14px | 400/500 | Texto de cuerpo secundario, descripciones de tabla |
| `text-base` | `text-base` | 16px | 400 | Texto de cuerpo principal, párrafos |
| `text-lg` | `text-lg` | 18px | 500 | Subtítulos de sección, nombres de tarea |
| `text-xl` | `text-xl` | 20px | 600 | Títulos de tarjeta, encabezados de sección |
| `text-2xl` | `text-2xl` | 24px | 700 | Títulos de página |
| `text-3xl` | `text-3xl` | 30px | 700 | Trust Score número grande, saldos destacados |
| `text-4xl` | `text-4xl` | 36px | 700 | Porcentaje de progreso en pantalla de procesamiento |

**Pesos de fuente:**
- Regular (400): texto de cuerpo
- Medium (500): labels, metadata
- SemiBold (600): encabezados de sección, botones
- Bold (700): títulos de página, números destacados

**Line-height:** `leading-tight` (1.25) para headings, `leading-relaxed` (1.625) para párrafos descriptivos.

---

### 2.4 Espaciado

El sistema de espaciado usa la escala por defecto de Tailwind (base 4px). Las unidades de uso más frecuentes:

| Token | px | Uso típico |
|---|---|---|
| `p-1` / `gap-1` | 4px | Separación mínima entre icono y texto |
| `p-2` / `gap-2` | 8px | Padding de badges, separación interna de chips |
| `p-3` / `gap-3` | 12px | Padding de botones compactos, celdas de tabla |
| `p-4` / `gap-4` | 16px | Padding de cards pequeñas, gap de grid en mobile |
| `p-5` / `gap-5` | 20px | Padding interno de secciones |
| `p-6` / `gap-6` | 24px | Padding de cards principales, gap de grid en desktop |
| `p-8` / `gap-8` | 32px | Espaciado entre secciones de página |
| `p-12`           | 48px | Padding lateral de página en desktop |
| `p-16`           | 64px | Margen top de page content tras navbar |

**Grid del layout:**
- Mobile (< 768px): 1 columna, padding lateral `px-4`
- Tablet (768px–1024px): 2 columnas, padding lateral `px-6`
- Desktop (> 1024px): hasta 4 columnas, max-width `max-w-7xl`, centrado con `mx-auto`, padding `px-8`

---

### 2.5 Bordes y Radios

| Token | Tailwind | Uso |
|---|---|---|
| Sin borde | — | Separaciones por fondo de color |
| Borde sutil | `border border-neutral-700` | Cards, inputs, tablas |
| Borde de acento | `border border-brand-500/50` | Card de progreso activo, input en focus |
| Radio pequeño | `rounded` (4px) | Badges, chips de filtro |
| Radio mediano | `rounded-lg` (8px) | Botones, inputs, células de tabla |
| Radio grande | `rounded-xl` (12px) | Cards de estadísticas, modales |
| Radio completo | `rounded-full` | Avatares, indicadores de estado online |

---

### 2.6 Sombras

| Token | Tailwind | Uso |
|---|---|---|
| Sin sombra | — | Elementos en fondo oscuro |
| Sombra sutil | `shadow-sm` | Cards en estado hover |
| Sombra de elevación | `shadow-lg shadow-black/30` | Modales, dropdowns |
| Sombra de acento | `shadow-lg shadow-brand-500/20` | Botón primario en hover |
| Sombra de élite | `shadow-lg shadow-amber-500/20` | Card del proveedor en rango élite |

---

### 2.7 Opacidades y Superposiciones

| Uso | Clase |
|---|---|
| Overlay de modal | `bg-black/70 backdrop-blur-sm` |
| Fondo de banner de carga | `bg-neutral-900/90 backdrop-blur-sm` |
| Deshabilitado visual | `opacity-50 cursor-not-allowed` |
| Focus ring | `focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-neutral-900` |

---

### 2.8 Animaciones y Transiciones

| Elemento | Clase Tailwind | Duración |
|---|---|---|
| Hover en botones y cards | `transition-all duration-150 ease-in-out` | 150ms |
| Apertura/cierre de modales | `transition-opacity duration-200` | 200ms |
| Barra de progreso | `transition-all duration-700 ease-out` | 700ms (por paso de polling) |
| Spinner de carga | `animate-spin` | continuo |
| Pulse de elemento en carga | `animate-pulse` | continuo |
| Entrada de página | `animate-fade-in` (clase custom: `@keyframes fadeIn { from { opacity:0; transform: translateY(8px) } to { opacity:1; transform: translateY(0) } }`) | 200ms |

---

## 3. Componentes Reutilizables

### 3.1 Botones

**Variantes:**

#### Botón Primario
```
Tailwind: "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg
           bg-brand-600 hover:bg-brand-500 active:bg-brand-700
           text-white font-semibold text-sm
           transition-all duration-150
           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-neutral-900
           disabled:opacity-50 disabled:cursor-not-allowed"
```
Uso: "Aceptar tarea", "Iniciar procesamiento", "Completar tarea", "Guardar cambios"

#### Botón Secundario
```
Tailwind: "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg
           bg-neutral-800 hover:bg-neutral-700 active:bg-neutral-900
           border border-neutral-700 hover:border-neutral-500
           text-neutral-300 hover:text-neutral-100 font-semibold text-sm
           transition-all duration-150
           focus:outline-none focus:ring-2 focus:ring-neutral-500 focus:ring-offset-2 focus:ring-offset-neutral-900
           disabled:opacity-50 disabled:cursor-not-allowed"
```
Uso: "Cancelar", "Limpiar filtros", "Volver al listado"

#### Botón Peligro
```
Tailwind: "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg
           bg-danger-500/10 hover:bg-danger-500/20
           border border-danger-500/50 hover:border-danger-500
           text-danger-500 hover:text-danger-400 font-semibold text-sm
           transition-all duration-150
           focus:outline-none focus:ring-2 focus:ring-danger-500 focus:ring-offset-2 focus:ring-offset-neutral-900"
```
Uso: "Reportar problema"

#### Botón Ghost / Link
```
Tailwind: "inline-flex items-center gap-1 text-brand-400 hover:text-brand-300
           text-sm font-medium underline-offset-2 hover:underline
           transition-colors duration-150"
```
Uso: "¿Ya tienes cuenta?", "Ver todas las tareas →"

#### Botón de Carga (estado loading)
```
Tailwind: [mismas clases que el botón primario] +
           "cursor-wait" + contenido: <Spinner /> + "Procesando..."
```
El botón se deshabilita y muestra un spinner de 16px a la izquierda del texto.

---

### 3.2 Inputs y Formularios

#### Input de texto estándar
```
Tailwind para <input>:
  "w-full px-4 py-2.5 rounded-lg
   bg-neutral-800 border border-neutral-700
   text-neutral-100 placeholder:text-neutral-500
   text-sm
   focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500
   disabled:opacity-50 disabled:cursor-not-allowed
   transition-colors duration-150"

Tailwind para <label>:
  "block text-sm font-medium text-neutral-300 mb-1.5"

Tailwind para mensaje de error:
  "mt-1.5 text-xs text-danger-500 flex items-center gap-1"
  + <ExclamationCircleIcon className="h-3.5 w-3.5 flex-shrink-0" />
```

#### Input de número (RAM, almacenamiento, monto retiro)
Iguales clases que el input de texto. Atributo `type="number"`, `min="0"`. En inputs de moneda, sufijo de unidad usando un wrapper:
```
Estructura HTML:
<div class="relative">
  <input ... />
  <span class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm">CC</span>
</div>
```

#### Select / Dropdown de filtro
```
Tailwind:
  "w-full px-4 py-2.5 rounded-lg
   bg-neutral-800 border border-neutral-700
   text-neutral-300 text-sm
   focus:outline-none focus:border-brand-500
   cursor-pointer appearance-none"
Con chevron icono absoluto a la derecha (ChevronDownIcon, h-4 w-4, text-neutral-500)
```

#### Toggle (estado online)
```
Estructura:
<button role="switch" aria-checked={isOnline}
  class="relative inline-flex h-6 w-11 items-center rounded-full
         transition-colors duration-200
         [estado OFF]: bg-neutral-700
         [estado ON]:  bg-success-500">
  <span class="inline-block h-4 w-4 transform rounded-full bg-white
               transition-transform duration-200
               [estado OFF]: translate-x-1
               [estado ON]:  translate-x-6" />
</button>
```

---

### 3.3 Badges de Rango

El badge de rango se usa en: navbar, dashboard, perfil, y opcionalmente en tarjetas de tarea completada.

**Estructura genérica:**
```
<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded
             text-xs font-semibold tracking-wide uppercase
             border
             [color classes según rango]">
  <[Icono] class="h-3.5 w-3.5" />
  [Texto del rango]
</span>
```

**Clases por rango:**

| Rango | Clases completas |
|---|---|
| Nuevo | `text-slate-400 bg-slate-400/10 border-slate-600` + `UserIcon` |
| Confiable | `text-blue-400 bg-blue-400/10 border-blue-600` + `ShieldCheckIcon` |
| Experto | `text-emerald-400 bg-emerald-400/10 border-emerald-600` + `BoltIcon` |
| Élite | `text-amber-400 bg-amber-400/10 border-amber-600` + `StarIcon` (solid) |

**Variante grande** (para dashboard y perfil): `px-4 py-2 text-sm rounded-lg` con el icono en `h-5 w-5`.

---

### 3.4 Badges de Estado (tareas y transacciones)

#### Estados de asignación

| Estado | Texto | Clases |
|---|---|---|
| aceptada | Aceptada | `text-info-400 bg-info-400/10 border-info-600` |
| procesando | En proceso | `text-brand-400 bg-brand-400/10 border-brand-600` (con `animate-pulse` en el punto) |
| completada | Completada | `text-success-500 bg-success-500/10 border-success-600` |
| fallida | Fallida | `text-danger-500 bg-danger-500/10 border-danger-600` |
| cancelada | Cancelada | `text-neutral-500 bg-neutral-500/10 border-neutral-600` |

#### Indicador de estado "En proceso" (punto animado)
```
<span class="inline-flex items-center gap-1.5 ...">
  <span class="relative flex h-2 w-2">
    <span class="animate-ping absolute inline-flex h-full w-full rounded-full
                 bg-brand-400 opacity-75" />
    <span class="relative inline-flex rounded-full h-2 w-2 bg-brand-500" />
  </span>
  En proceso
</span>
```

#### Dificultad de tarea

| Dificultad | Texto | Clases |
|---|---|---|
| fácil | Fácil | `text-success-400 bg-success-400/10 border-success-700` |
| medio | Medio | `text-warning-400 bg-warning-400/10 border-warning-700` |
| difícil | Difícil | `text-danger-400 bg-danger-400/10 border-danger-700` |

#### Hardware requerido

| Hardware | Icono | Clases |
|---|---|---|
| cpu | `CpuChipIcon` | `text-neutral-300 bg-neutral-700/50 border-neutral-600` |
| gpu | `RectangleGroupIcon` (o `ComputerDesktopIcon`) | `text-brand-300 bg-brand-300/10 border-brand-700` |
| mixto | `CircleStackIcon` | `text-purple-300 bg-purple-300/10 border-purple-700` |

---

### 3.5 Tarjeta de Tarea (TaskCard)

```
┌─────────────────────────────────────────────────────────────────┐
│  [Tipo badge]                                [Dificultad badge] │
│                                                                 │
│  Título de la tarea (text-lg font-semibold text-neutral-100)    │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ [HW badge]   │  │ 15-30 min    │  │ X plazas           │    │
│  │ cpu/gpu      │  │ estimado     │  │ disponibles        │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│                                                                 │
│  ──────────────────────────────────────────────────────────     │
│                                                  1,50 CC  ▶    │
└─────────────────────────────────────────────────────────────────┘
```

**Clases del contenedor:**
```
"group flex flex-col gap-3 p-5 rounded-xl
 bg-neutral-900 border border-neutral-700
 hover:border-brand-500/50 hover:bg-neutral-800/80
 cursor-pointer transition-all duration-150
 hover:shadow-lg hover:shadow-brand-500/5"
```

**Recompensa (esquina inferior derecha):**
```
"text-xl font-bold text-success-400"
con label: "text-xs text-neutral-500 uppercase tracking-wide"
```

---

### 3.6 Tarjeta de Estadística (StatCard)

Usada en el Dashboard para Trust Score, tareas completadas, ganancias, saldo.

```
┌───────────────────────────────┐
│  [Icono 20px]  Label          │
│                               │
│  Valor grande                 │
│  (opcional) Sub-valor         │
└───────────────────────────────┘
```

**Clases:**
```
"flex flex-col gap-1 p-5 rounded-xl
 bg-neutral-900 border border-neutral-700"
```

- Icono: `h-5 w-5 text-neutral-500`
- Label: `text-xs text-neutral-500 uppercase tracking-wide`
- Valor: `text-3xl font-bold text-neutral-100`
- Sub-valor: `text-sm text-neutral-400`

---

### 3.7 Tabla de Transacciones (TransactionRow)

La tabla de historial de cartera tiene un diseño de lista densa:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FECHA/HORA         TIPO          DESCRIPCIÓN            MONTO   ESTADO  │
├──────────────────────────────────────────────────────────────────────────┤
│  05 jun 2026        pago_tarea    Tarea: Renderizado 3D   +2,50   ✓      │
│  14:32                           "Escena nocturna v3"    CC      Ok      │
├──────────────────────────────────────────────────────────────────────────┤
│  04 jun 2026        retiro        Retiro a PayPal        -10,00   ⏳      │
│  09:15                           user@paypal.com         CC      Pend.   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Clases del contenedor de tabla:**
```
"w-full border border-neutral-700 rounded-xl overflow-hidden"
```

**Cabeceras:**
```
"px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide
 bg-neutral-800 border-b border-neutral-700"
```

**Filas:**
```
"px-4 py-3.5 text-sm border-b border-neutral-800 last:border-0
 hover:bg-neutral-800/50 transition-colors duration-100"
```

**Monto — Ingresos (pago_tarea, bonus):**
```
"text-sm font-semibold text-success-400 tabular-nums"
"+2,50 CC"
```

**Monto — Egresos (retiro, penalizacion):**
```
"text-sm font-semibold text-danger-400 tabular-nums"
"-10,00 CC"
```

**Etiqueta de tipo (chip):**

| Tipo API | Texto visible | Color |
|---|---|---|
| `pago_tarea` | Pago de tarea | `text-success-400 bg-success-400/10` |
| `retiro` | Retiro | `text-info-400 bg-info-400/10` |
| `bonus` | Bono | `text-amber-400 bg-amber-400/10` |
| `penalizacion` | Penalización | `text-danger-400 bg-danger-400/10` |

---

### 3.8 Barra de Progreso

**Barra de progreso lineal (pantalla de procesamiento):**
```
Contenedor:
"w-full h-3 bg-neutral-800 rounded-full overflow-hidden border border-neutral-700"

Relleno:
"h-full rounded-full transition-all duration-700 ease-out
 bg-gradient-to-r from-brand-600 to-brand-400"
style={{ width: `${progress}%` }}
```

**Texto de porcentaje:**
```
"text-4xl font-bold text-neutral-100 tabular-nums"
```

**Barra de progreso de Trust Score (en tarjeta de perfil):**
```
Contenedor: "w-full h-2 bg-neutral-800 rounded-full"
Relleno:    "h-full rounded-full"
  [color dinámico según rango]
  - Nuevo:    "bg-slate-400"
  - Confiable:"bg-blue-400"
  - Experto:  "bg-emerald-400"
  - Élite:    "bg-gradient-to-r from-amber-500 to-amber-300"
```

---

### 3.9 Stepper de Etapas (ProgressStepper)

Componente vertical con estado visual por etapa:

```
● ──── Preparando entorno          [COMPLETADA]  (check verde, texto neutro)
● ──── Descargando recursos        [COMPLETADA]  (check verde, texto neutro)
◉ ──── Procesando datos            [ACTIVA]      (punto pulsante brand, texto blanco, negrita)
○ ──── Validando resultados        [PENDIENTE]   (círculo gris, texto gris)
○ ──── Empaquetando salida         [PENDIENTE]   (círculo gris, texto gris)
```

**Nodo de etapa completada:**
```
"flex h-8 w-8 items-center justify-center rounded-full
 bg-success-500/20 border-2 border-success-500"
+ <CheckIcon className="h-4 w-4 text-success-500" />
```

**Nodo de etapa activa:**
```
"flex h-8 w-8 items-center justify-center rounded-full
 bg-brand-500/20 border-2 border-brand-500 relative"
+ punto pulsante interno (animate-ping, bg-brand-400, h-3 w-3 rounded-full)
```

**Nodo de etapa pendiente:**
```
"flex h-8 w-8 items-center justify-center rounded-full
 bg-neutral-800 border-2 border-neutral-600"
```

**Línea conectora entre nodos:**
```
"absolute left-4 top-8 h-full w-0.5
 [completada→completada]: bg-success-500/50
 [completada→activa]:     bg-gradient-to-b from-success-500/50 to-brand-500/50
 [activa→pendiente]:      bg-neutral-700
 [pendiente→pendiente]:   bg-neutral-700"
```

---

### 3.10 Spinner de Carga

**Spinner inline (dentro de botones):**
```
<svg class="animate-spin h-4 w-4 text-white" xmlns="..." fill="none" viewBox="0 0 24 24">
  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
</svg>
```

**Spinner de página completa (estado de carga inicial):**
```
<div class="flex flex-col items-center justify-center min-h-[400px] gap-4">
  [Spinner grande, h-10 w-10, text-brand-400]
  <p class="text-neutral-500 text-sm animate-pulse">Cargando...</p>
</div>
```

**Skeleton loader (cards en carga):**
```
<div class="animate-pulse space-y-3 p-5 rounded-xl bg-neutral-900 border border-neutral-700">
  <div class="h-4 bg-neutral-700 rounded w-1/3" />
  <div class="h-6 bg-neutral-700 rounded w-2/3" />
  <div class="h-4 bg-neutral-700 rounded w-1/2" />
</div>
```

---

### 3.11 Alertas y Mensajes de Feedback

**Alert de éxito:**
```
"flex items-start gap-3 p-4 rounded-lg
 bg-success-900/50 border border-success-500/30
 text-success-300 text-sm"
+ <CheckCircleIcon className="h-5 w-5 text-success-400 flex-shrink-0 mt-0.5" />
```

**Alert de error:**
```
"flex items-start gap-3 p-4 rounded-lg
 bg-danger-900/50 border border-danger-500/30
 text-danger-300 text-sm"
+ <ExclamationCircleIcon className="h-5 w-5 text-danger-400 flex-shrink-0 mt-0.5" />
```

**Alert de advertencia:**
```
"flex items-start gap-3 p-4 rounded-lg
 bg-warning-900/50 border border-warning-500/30
 text-warning-300 text-sm"
+ <ExclamationTriangleIcon className="h-5 w-5 text-warning-400 flex-shrink-0 mt-0.5" />
```

**Alert informativo:**
```
"flex items-start gap-3 p-4 rounded-lg
 bg-info-900/50 border border-info-500/30
 text-info-300 text-sm"
+ <InformationCircleIcon className="h-5 w-5 text-info-400 flex-shrink-0 mt-0.5" />
```

**Toast (notificación flotante):**
- Posición: esquina inferior derecha, `fixed bottom-6 right-6`
- Z-index: `z-50`
- Animación de entrada: slide desde abajo + fade-in (200ms)
- Auto-dismiss: 4 segundos
- Máximo 3 toasts simultáneos (apilados verticalmente con `gap-3`)

---

### 3.12 Modal

```
Overlay: "fixed inset-0 z-40 flex items-center justify-center p-4
          bg-black/70 backdrop-blur-sm"

Contenedor del modal: "relative w-full max-w-md rounded-xl
                        bg-neutral-900 border border-neutral-700
                        shadow-xl shadow-black/40 p-6
                        animate-fade-in"

Encabezado: "flex items-center justify-between mb-5"
  Título: "text-lg font-semibold text-neutral-100"
  Botón cerrar: "text-neutral-500 hover:text-neutral-300 transition-colors"
  + <XMarkIcon className="h-5 w-5" />

Separador: "border-t border-neutral-700 my-5"

Pie (acciones): "flex justify-end gap-3 mt-6"
```

---

### 3.13 Tarjeta de Saldo (BalanceCard)

```
┌────────────────────────────────────┐
│  [Icono]  Label del saldo          │
│                                    │
│  12,50 CC                          │
│                                    │
│  [Sub-label opcional]              │
└────────────────────────────────────┘
```

Variante destacada (saldo disponible):
```
"p-5 rounded-xl bg-neutral-900 border border-brand-500/30
 shadow-lg shadow-brand-500/5"
```
Con valor en `text-3xl font-bold text-success-400`.

Variantes neutras (pendiente, ganado, retirado):
```
"p-5 rounded-xl bg-neutral-900 border border-neutral-700"
```
Con valor en `text-2xl font-bold text-neutral-100`.

---

## 4. Configuración de Tailwind (tailwind.config.ts)

Para registrar los colores de marca, de rango y semánticos como tokens disponibles en todo el proyecto:

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          100: '#E0F2FE',
          300: '#7DD3FC',
          400: '#38BDF8',
          500: '#0EA5E9',
          600: '#0284C7',
          700: '#0369A1',
        },
        success: {
          300: '#86EFAC',
          400: '#4ADE80',
          500: '#22C55E',
          600: '#16A34A',
          900: '#14532D',
        },
        danger: {
          400: '#F87171',
          500: '#EF4444',
          600: '#DC2626',
          900: '#7F1D1D',
        },
        warning: {
          400: '#FCD34D',
          500: '#F59E0B',
          600: '#D97706',
          900: '#78350F',
        },
        info: {
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          900: '#1E3A5F',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
```

---

## 5. Accesibilidad

| Requisito | Implementación |
|---|---|
| Contraste texto/fondo | Todos los pares texto/fondo verificados en WCAG 2.1 AA (ratio ≥ 4.5:1 para texto normal, ≥ 3:1 para texto grande) |
| Labels de formulario | Todo `<input>` tiene un `<label>` con `htmlFor` asociado. Sin placeholders como sustitutos de label. |
| Botones descriptivos | Todos los botones tienen texto visible. Los iconos solos llevan `aria-label`. |
| Focus visible | El focus ring de brand (`focus:ring-2 focus:ring-brand-500`) es visible en todos los elementos interactivos. No se elimina el outline sin reemplazarlo. |
| Roles ARIA | Toggle de estado online: `role="switch"` con `aria-checked`. Modal: `role="dialog"` con `aria-labelledby`. Alertas: `role="alert"` para mensajes de error críticos. |
| Navegación por teclado | Todos los elementos interactivos son alcanzables con Tab. Los modales capturan el foco (focus trap). |
| Textos de carga | Los spinners incluyen `<span class="sr-only">Cargando...</span>` para lectores de pantalla. |
| Imágenes decorativas | Los iconos puramente decorativos llevan `aria-hidden="true"`. |

---

## 6. Diseño Responsivo

| Breakpoint | Nombre | Ancho mínimo | Cambios principales |
|---|---|---|---|
| Mobile | — | < 640px | Stack vertical, navbar hamburguesa, 1 columna en grids |
| sm | Small | 640px | Algunos elementos en fila, más padding |
| md | Medium / Tablet | 768px | Navbar horizontal, 2 columnas en grids de stats |
| lg | Large / Desktop | 1024px | Layout de sidebar implícito en navbar, 3-4 columnas |
| xl | XL / Wide | 1280px | Max-width aplicado, espaciado aumentado |

**Navbar en mobile:**
- El logo y el botón hamburguesa (Bars3Icon) están en la barra superior
- El menú desplegable ocupa el ancho completo con fondo `bg-neutral-900 border-b border-neutral-700`
- El badge de rango se muestra junto al nombre del proveedor en el menú

**Grids adaptativos:**
- Stats del Dashboard: `grid grid-cols-2 md:grid-cols-4 gap-4`
- Listado de tareas: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`
- Perfil (datos + trust score): `grid grid-cols-1 lg:grid-cols-2 gap-6`
