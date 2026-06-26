# Guion de vídeo demo — Co-Computing

**Duración objetivo:** 90 segundos  
**Público:** Reclutadores, profesores, compañeros de portafolio  
**Objetivo:** Mostrar el flujo completo de la plataforma de forma clara y rápida

---

## Estructura (90 s)

| Segmento | Tiempo | Qué mostrar |
|----------|--------|-------------|
| Intro + landing | 0–10 s | Portada animada y landing pública |
| Registro | 10–22 s | Formulario de registro → dashboard |
| Catálogo de tareas | 22–38 s | Lista de tareas → aceptar una tarea |
| Procesando | 38–55 s | Pantalla de progreso del worker |
| Cartera | 55–70 s | Saldo, historial de transacciones |
| Publicar tarea (cliente) | 70–83 s | Formulario de publicación + escrow |
| Cierre | 83–90 s | Stack técnico en pantalla |

---

## Guion detallado

### [0–10 s] Intro y landing

**Pantalla:** Landing pública en `/`

> "Co-Computing es una plataforma de cómputo distribuido donde cualquier persona puede
> monetizar su CPU o GPU procesando tareas reales."

**Acción:** Desplaza lentamente la landing mostrando el hero, los tres pasos y la sección de beneficios.

---

### [10–22 s] Registro rápido

**Pantalla:** `/registro`

> "El registro es inmediato."

**Acción:** Rellena el formulario con datos de demo (nombre, email, contraseña) y pulsa **Registrarse**.
Muestra cómo aparece el dashboard tras el registro con el saldo inicial.

---

### [22–38 s] Catálogo y aceptar tarea

**Pantalla:** `/tareas`

> "El catálogo muestra las tareas disponibles con su recompensa, dificultad y hardware requerido."

**Acción:** Haz clic en una tarea de tipo *Análisis de datos* o *Entrenamiento ML*.
Muestra la página de detalle. Pulsa **Aceptar tarea**.

> "Al aceptar, la tarea pasa a estado 'En progreso' y el worker comienza a procesar."

---

### [38–55 s] Progreso del worker

**Pantalla:** `/procesando/:assignmentId`

> "La pantalla de progreso muestra en tiempo real los pasos que ejecuta el worker distribuido."

**Acción:** Deja que la barra de progreso avance por los stages. Muestra el log de pasos completados.
Cuando llega al 100 %, aparece la confirmación de tarea completada.

> "Tarea completada. La recompensa se acredita automáticamente."

---

### [55–70 s] Cartera

**Pantalla:** `/cartera`

> "En la cartera vemos el saldo acumulado y el historial de transacciones."

**Acción:** Muestra el saldo disponible, el botón de **Retirar fondos** y la última transacción
de tipo *Pago de tarea* con el importe recién cobrado.

---

### [70–83 s] Publicar tarea como cliente

**Pantalla:** `/cliente/publicar`

> "Los usuarios también pueden actuar como clientes: publicar tareas y que la red las procese."

**Acción:** Muestra el formulario de publicación. Introduce título, tipo de tarea, recompensa por plaza
y número de plazas. El panel lateral muestra el **escrow total** que se bloqueará.
Pulsa **Publicar tarea** y muestra la confirmación con el nuevo saldo disponible.

---

### [83–90 s] Cierre

**Pantalla:** Diapositiva con el stack técnico (o la landing)

> "Co-Computing: backend en FastAPI + Supabase, frontend en React 18 con TypeScript y Tailwind,
> desplegado en Railway y Vercel. Código en GitHub."

**Acción:** Muestra el enlace al repositorio o el QR del portafolio.

---

## Consejos de grabación

- **Resolución:** 1920 × 1080 a 30 fps
- **Herramienta:** OBS Studio, Loom o QuickTime
- **Cursor:** Activa el resaltado de cursor para que los clics sean visibles
- **Datos de demo:** Usa el usuario seed (`demo@co-computing.io`) o crea uno de prueba
  con saldo suficiente para no bloquear el flujo por fondos insuficientes
- **Velocidad:** Habla despacio; es mejor quedar en 95 s que en 80 s con voz acelerada
- **Música de fondo:** Opcional, volumen bajo (−20 dB respecto a la voz)
