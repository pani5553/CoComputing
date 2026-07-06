# Co-Computing — Backlog de User Stories (MVP)

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** Product Owner
**Referencias:** `docs/02-requisitos.md`, `docs/00-vision.md`, `docs/01-stack.md`

---

## Convenciones

### Priorización MoSCoW

| Prioridad | Significado |
|-----------|-------------|
| **Must Have** | Imprescindible para el MVP. Sin esta historia el producto no es demostrable ni viable. |
| **Should Have** | Importante para la calidad y completitud. No bloquea el flujo core pero es necesario para producción. |
| **Could Have** | Deseable. Añade valor pero puede posponerse sin romper el producto. |
| **Won't Have** | Excluido del MVP. Documentado para el backlog futuro. |

### Estimación de Complejidad (tallas de camiseta)

| Talla | Puntos de historia | Descripción |
|-------|-------------------|-------------|
| XS | 1 | Cambio trivial o lectura simple de un campo |
| S | 2 | Endpoint CRUD simple o componente de presentación |
| M | 3 | Flujo con lógica de negocio moderada |
| L | 5 | Flujo complejo, múltiples entidades o lógica de negocio avanzada |
| XL | 8 | Módulo completo con múltiples estados, efectos secundarios y tests |

---

## Épicas

| ID | Épica | Descripción |
|----|-------|-------------|
| E-01 | Autenticación | Registro, login y gestión de sesión del proveedor |
| E-02 | Dashboard | Pantalla principal con métricas y resumen de actividad |
| E-03 | Exploración de Tareas | Listado, filtros y detalle de tareas disponibles |
| E-04 | Ciclo de Vida de Tarea | Aceptar, iniciar, completar y fallar asignaciones |
| E-05 | Procesamiento | Pantalla de progreso simulado por etapas |
| E-06 | Cartera | Saldos, historial de transacciones y solicitud de retiro |
| E-07 | Perfil | Datos personales, hardware y estado online |
| E-08 | Trust Score | Cálculo, desglose y visualización del sistema de reputación |
| E-09 | Infraestructura y Calidad | Seed, tests, seguridad, README y configuración de entornos |

---

## Backlog Priorizado

---

### E-01: Autenticación

---

#### US-01 — Registro de nuevo proveedor

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-01

**Historia:**
Como persona con hardware potente que quiere ingresos pasivos,
quiero registrarme en Co-Computing con mi email, nombre y contraseña,
para crear mi cuenta de proveedor y acceder a la plataforma.

**Criterios de aceptación:**

1. **Registro exitoso:** Dado un nombre válido, email no registrado previamente y contraseña de al menos 8 caracteres, cuando envío el formulario de registro, entonces el sistema crea mi cuenta, inicializa mi cartera a cero, establece mi Trust Score en 0 y mi rango en "nuevo", y me redirige al dashboard.

2. **Email duplicado:** Dado un email que ya existe en el sistema, cuando intento registrarme, entonces el sistema muestra el mensaje "Este email ya está registrado" y no crea ningún registro duplicado.

3. **Contraseña corta:** Dado una contraseña de menos de 8 caracteres, cuando intento registrarme, entonces el sistema muestra el mensaje "La contraseña debe tener al menos 8 caracteres" antes de enviar el formulario.

4. **Email inválido:** Dado un email con formato incorrecto (sin @, sin dominio), cuando intento registrarme, entonces el sistema muestra error de validación en el campo email.

5. **Nombre vacío:** Dado un formulario con el campo nombre vacío, cuando intento enviar, entonces el sistema muestra error de campo requerido.

6. **Seguridad de password:** El password no aparece en ningún log, respuesta de API ni almacenado en texto plano en base de datos; se almacena su hash bcrypt.

7. **Estado de carga:** Mientras se procesa el registro, el botón de envío muestra estado de carga y no permite doble envío.

---

#### US-02 — Inicio de sesión

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-01

**Historia:**
Como proveedor registrado,
quiero iniciar sesión con mi email y contraseña,
para acceder a mi cuenta y comenzar a procesar tareas.

**Criterios de aceptación:**

1. **Login exitoso:** Dado mi email y contraseña correctos, cuando inicio sesión, entonces el sistema me devuelve un JWT válido (duración 7 días) y me redirige al dashboard con mis datos cargados.

2. **Credenciales incorrectas:** Dado un email correcto con contraseña incorrecta, cuando intento iniciar sesión, entonces el sistema muestra "Credenciales incorrectas" sin revelar si el email existe.

3. **Email no registrado:** Dado un email no registrado, cuando intento iniciar sesión, entonces el sistema muestra el mismo mensaje genérico "Credenciales incorrectas".

4. **Token persistido:** Después de iniciar sesión, si recargo la página, mi sesión se mantiene activa hasta que el token expire o cierre sesión manualmente.

5. **Redirección de rutas protegidas:** Si intento acceder a `/dashboard` sin sesión activa, el sistema me redirige a la página de login.

6. **Estado de carga:** Mientras se procesa el login, el botón muestra estado de carga y no permite doble envío.

---

#### US-03 — Cierre de sesión

**Prioridad:** Must Have
**Estimación:** XS (1 punto)
**Épica:** E-01

**Historia:**
Como proveedor autenticado,
quiero poder cerrar mi sesión,
para proteger mi cuenta cuando termino de usar la plataforma.

**Criterios de aceptación:**

1. **Logout inmediato:** Dado que estoy autenticado, cuando pulso "Cerrar sesión", entonces el token se elimina del almacenamiento local, el store de Zustand se limpia y soy redirigido a la pantalla de login.

2. **Protección post-logout:** Después de cerrar sesión, si intento acceder a `/dashboard` u otra ruta protegida, el sistema me redirige a login.

3. **Sin datos residuales:** Tras el logout, ningún dato sensible (nombre, saldo, tareas) es accesible sin autenticarse de nuevo.

---

### E-02: Dashboard

---

#### US-04 — Visualización del dashboard principal

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-02

**Historia:**
Como proveedor autenticado,
quiero ver mi dashboard con mi estado actual y actividad reciente,
para tener una visión inmediata de mi progreso y motivación para continuar.

**Criterios de aceptación:**

1. **Métricas visibles:** El dashboard muestra correctamente: Trust Score actual, rango (nuevo/confiable/experto/élite), número de tareas completadas y ganancias totales acumuladas.

2. **Saldo de cartera:** El dashboard muestra el saldo disponible de mi cartera con dos decimales.

3. **Tareas recientes:** El dashboard lista las últimas 5 asignaciones del proveedor con título de tarea, estado de la asignación y recompensa ganada (o 0 si falló).

4. **Dashboard vacío:** Si no tengo ninguna asignación previa, el listado de tareas recientes muestra el mensaje "Aún no has procesado ninguna tarea. ¡Explora las tareas disponibles!" con un enlace al listado.

5. **Datos actualizados:** Cada vez que navego al dashboard, los datos se recargan desde el backend para reflejar el estado más reciente.

6. **Estado de carga:** Mientras se obtienen los datos, se muestra un indicador de carga. Si la petición falla, se muestra mensaje de error con opción de reintentar.

7. **Navegación rápida:** El dashboard tiene acceso directo (enlace o botón) al listado de tareas disponibles.

---

### E-03: Exploración de Tareas

---

#### US-05 — Listado de tareas disponibles

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-03

**Historia:**
Como proveedor autenticado,
quiero ver un listado de todas las tareas disponibles para procesar,
para descubrir oportunidades de ingresos adaptadas a mi hardware.

**Criterios de aceptación:**

1. **Listado completo:** Sin filtros activos, el sistema muestra todas las tareas con estado "disponible" y al menos 1 plaza disponible.

2. **Información visible en tarjeta:** Cada tarea en el listado muestra: título, tipo, dificultad, hardware requerido, recompensa y plazas disponibles.

3. **Estado de carga:** Se muestra indicador de carga mientras se obtienen las tareas del backend.

4. **Listado vacío:** Si no hay tareas disponibles (sin filtros), se muestra "No hay tareas disponibles en este momento. Vuelve pronto."

5. **Acceso al detalle:** Al pulsar en una tarea, navego a la pantalla de detalle de esa tarea.

6. **Error de red:** Si la petición falla, se muestra mensaje de error con opción de reintentar.

---

#### US-06 — Filtrado de tareas por dificultad y hardware

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-03

**Historia:**
Como proveedor autenticado,
quiero filtrar las tareas por dificultad y tipo de hardware requerido,
para encontrar rápidamente tareas compatibles con mis capacidades.

**Criterios de aceptación:**

1. **Filtro por dificultad:** Puedo seleccionar uno o varios niveles de dificultad (fácil, medio, difícil). El listado se actualiza mostrando solo las tareas que coinciden.

2. **Filtro por hardware:** Puedo seleccionar uno o varios tipos de hardware (cpu, gpu, mixto). El listado se actualiza mostrando solo las coincidentes.

3. **Filtros combinados:** Al activar filtros de dificultad Y hardware simultáneamente, el listado muestra solo las tareas que cumplen ambos criterios (intersección).

4. **Limpiar filtros:** Existe un botón "Limpiar filtros" que restablece todos los filtros y vuelve al listado completo.

5. **Sin resultados:** Si la combinación de filtros no devuelve ninguna tarea, se muestra "No hay tareas disponibles con estos filtros."

6. **Filtros persistentes en la sesión:** Si navego al detalle de una tarea y vuelvo al listado, los filtros activos se mantienen.

---

#### US-07 — Filtrado de tareas por tipo y recompensa mínima

**Prioridad:** Should Have
**Estimación:** S (2 puntos)
**Épica:** E-03

**Historia:**
Como proveedor autenticado,
quiero filtrar las tareas por tipo de tarea y recompensa mínima,
para encontrar tareas de mi especialidad que valgan la pena económicamente.

**Criterios de aceptación:**

1. **Filtro por tipo:** Puedo seleccionar un tipo de tarea de la lista de tipos disponibles (renderizado 3D, entrenamiento ML, etc.). El listado se actualiza con las coincidentes.

2. **Filtro por recompensa mínima:** Puedo introducir un valor numérico. Solo aparecen tareas con recompensa mayor o igual a ese valor. El campo solo acepta números positivos.

3. **Combinación con otros filtros:** Los filtros de tipo y recompensa mínima son acumulativos con los filtros de dificultad y hardware.

4. **Recompensa inválida:** Si introduzco un valor no numérico o negativo, el sistema no aplica ese filtro y muestra una indicación de que el valor es inválido.

---

#### US-08 — Detalle de tarea

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-03

**Historia:**
Como proveedor autenticado,
quiero ver toda la información de una tarea antes de aceptarla,
para tomar una decisión informada sobre si tengo el hardware y tiempo necesarios.

**Criterios de aceptación:**

1. **Información completa:** La pantalla muestra: título, descripción completa, tipo, dificultad, hardware requerido, recompensa, duración estimada (min-max en minutos), plazas disponibles y nombre del solicitante.

2. **Etapas de procesamiento:** Se muestra la lista de etapas que se ejecutarán al iniciar la tarea.

3. **Tarea no encontrada:** Si el ID de la URL no corresponde a ninguna tarea, se muestra mensaje "Tarea no encontrada" con enlace al listado.

4. **Botón de aceptar activo:** Si la tarea tiene plazas disponibles y el proveedor no tiene ya una asignación activa para esta tarea, aparece el botón "Aceptar tarea" activo.

5. **Sin plazas disponibles:** Si `slots_left` es 0, el botón aparece deshabilitado con texto "Sin plazas disponibles".

6. **Asignación activa existente:** Si el proveedor ya tiene esta tarea en estado "aceptada" o "procesando", aparece el botón "Continuar procesamiento" que navega a la pantalla de progreso de esa asignación.

7. **Estado de carga:** Se muestra indicador mientras se obtienen los datos de la tarea.

---

### E-04: Ciclo de Vida de Tarea

---

#### US-09 — Aceptar una tarea

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-04

**Historia:**
Como proveedor autenticado,
quiero aceptar una tarea disponible,
para reservar mi plaza y comenzar el proceso de obtener esa recompensa.

**Criterios de aceptación:**

1. **Aceptación exitosa:** Al pulsar "Aceptar tarea" en el detalle, el sistema crea una asignación con estado "aceptada", decrementa las plazas disponibles de la tarea y navega a la pantalla de detalle o a una pantalla de confirmación.

2. **Sin plazas en el momento de aceptar:** Si entre que cargué el detalle y pulsé aceptar ya no quedan plazas, el sistema muestra "No quedan plazas disponibles para esta tarea" y no crea la asignación.

3. **Doble aceptación bloqueada:** Si ya tengo esta tarea en estado "aceptada" o "procesando", el backend devuelve error y la UI muestra "Ya tienes esta tarea activa".

4. **Confirmación visual:** Tras aceptar exitosamente, se muestra un mensaje de éxito "Tarea aceptada correctamente" y un botón "Iniciar procesamiento".

5. **Estado de carga:** Mientras se procesa la aceptación, el botón muestra estado de carga y no permite doble clic.

---

#### US-10 — Iniciar el procesamiento de una tarea

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-04

**Historia:**
Como proveedor autenticado con una tarea aceptada,
quiero iniciar el procesamiento de esa tarea,
para que comience a ejecutarse y pueda ganar la recompensa.

**Criterios de aceptación:**

1. **Inicio exitoso:** Al pulsar "Iniciar procesamiento", el sistema transiciona la asignación a estado "procesando", registra `started_at` y navega a la pantalla de progreso `/processing/{assignmentId}`.

2. **Solo el dueño puede iniciar:** Si otro proveedor intentase llamar al endpoint con el ID de mi asignación, recibe error 403.

3. **Estado inválido:** Si la asignación no está en estado "aceptada", el sistema devuelve error con mensaje claro y no realiza la transición.

4. **Datos de etapas disponibles:** La respuesta del endpoint incluye el número de etapas y sus nombres para que la pantalla de progreso los muestre correctamente.

---

#### US-11 — Completar una tarea

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-04

**Historia:**
Como proveedor que ha procesado una tarea,
quiero marcar la tarea como completada,
para recibir mi recompensa en la cartera y que mi Trust Score mejore.

**Criterios de aceptación:**

1. **Completar desde procesando:** Al pulsar "Completar tarea" desde la pantalla de progreso, el sistema transiciona la asignación a "completada", registra `completed_at` y acredita la recompensa en el saldo disponible de mi cartera.

2. **Transacción creada:** En el historial de la cartera aparece una nueva transacción de tipo "pago_tarea" con el monto de la recompensa y descripción del nombre de la tarea.

3. **Trust Score actualizado:** El Trust Score del proveedor se recalcula inmediatamente tras completar. El campo `trust_delta` de la asignación registra el cambio producido.

4. **Tareas completadas incrementadas:** El contador `tasks_completed` del proveedor aumenta en 1.

5. **Redirección exitosa:** Tras completar, el sistema muestra una pantalla o modal de éxito con el monto ganado y redirige al dashboard o al historial de cartera.

6. **Estado inválido:** Si la asignación no está en estado "procesando", el endpoint devuelve error y no realiza ninguna operación.

7. **Solo el dueño puede completar:** Cualquier intento de otro proveedor recibe error 403.

---

#### US-12 — Reportar fallo en una tarea

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-04

**Historia:**
Como proveedor que tiene problemas durante el procesamiento,
quiero reportar que no puedo completar la tarea,
para ser transparente con la plataforma y liberar mi estado para aceptar otras tareas.

**Criterios de aceptación:**

1. **Fallo exitoso:** Al pulsar "Reportar problema" desde la pantalla de progreso, el sistema transiciona la asignación a "fallida", registra el timestamp de fallo y no acredita ninguna recompensa.

2. **Trust Score penalizado:** El Trust Score del proveedor se recalcula con el impacto negativo del fallo. El `trust_delta` de la asignación refleja el valor negativo.

3. **Confirmación requerida:** Antes de confirmar el fallo, el sistema muestra un diálogo de confirmación: "¿Seguro que quieres reportar que no puedes completar esta tarea? Esto puede afectar negativamente tu Trust Score."

4. **Redirección post-fallo:** Tras confirmar el fallo, el sistema muestra mensaje informativo y redirige al listado de tareas disponibles.

5. **Estado inválido:** Si la asignación no está en estado "procesando", el endpoint devuelve error.

---

### E-05: Procesamiento

---

#### US-13 — Pantalla de progreso de procesamiento

**Prioridad:** Must Have
**Estimación:** XL (8 puntos)
**Épica:** E-05

**Historia:**
Como proveedor que está procesando una tarea,
quiero ver el progreso actualizado de la tarea en tiempo real con las etapas por las que pasa,
para tener feedback tranquilizador de que algo está ocurriendo y saber cuándo puedo completarla.

**Criterios de aceptación:**

1. **Actualización automática:** El progreso se consulta al backend cada 3 segundos. La barra o indicador visual se actualiza sin recargar la página.

2. **Porcentaje visible:** Se muestra el porcentaje de progreso actual (0%-99%).

3. **Etapas con estado:** La lista de etapas muestra visualmente cuáles están completadas, cuál está en curso y cuáles están pendientes.

4. **Techo del 99%:** El progreso nunca supera automáticamente el 99%. El indicador se detiene en 99% hasta que el proveedor pulsa "Completar tarea".

5. **Habilitación del botón completar:** El botón "Completar tarea" aparece deshabilitado hasta que el progreso alcanza el 80%, momento en que se activa.

6. **Botón reportar problema:** El botón "Reportar problema" está disponible en todo momento desde que el procesamiento está en curso, independientemente del progreso.

7. **Recuperación de estado:** Si navego fuera de la pantalla y regreso con la URL `/processing/{assignmentId}`, la pantalla carga el estado actual de la asignación (si sigue en "procesando") y reanuda el polling sin reiniciar el progreso.

8. **Redireccion por estado externo:** Si al cargar o consultar el progreso la asignación ya está en estado "completada" o "fallida", la pantalla redirige automáticamente a la sección correspondiente (dashboard si completada, listado de tareas si fallida).

9. **Limpieza del polling:** Al salir de la pantalla, el intervalo de polling se cancela para no generar peticiones innecesarias en segundo plano.

10. **Nombre de tarea visible:** La pantalla muestra el título de la tarea que se está procesando de forma prominente.

---

#### US-14 — Endpoint de consulta de progreso

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-05

**Historia:**
Como sistema frontend que muestra el progreso de procesamiento,
quiero consultar el estado actualizado de una asignación en procesamiento,
para mostrar al proveedor el avance real calculado en el backend.

**Criterios de aceptación:**

1. **Cálculo correcto:** El endpoint calcula el progreso como `min((tiempo_transcurrido_segundos / duracion_estimada_segundos) * 100, 99)` y devuelve el valor redondeado a un decimal.

2. **Etapa activa derivada:** La respuesta incluye el índice de la etapa activa calculado en función del porcentaje de progreso y el número total de etapas.

3. **Solo el dueño:** Si un proveedor diferente al dueño de la asignación consulta el progreso, recibe error 403.

4. **Estado no procesando:** Si la asignación no está en estado "procesando", el endpoint devuelve el estado actual y el porcentaje correspondiente (0 si aceptada, 100 si completada, null si fallida) para que el frontend pueda redirigir correctamente.

5. **Respuesta rápida:** El endpoint responde en menos de 200ms.

---

### E-06: Cartera

---

#### US-15 — Visualización de saldos de cartera

**Prioridad:** Must Have
**Estimación:** S (2 puntos)
**Épica:** E-06

**Historia:**
Como proveedor autenticado,
quiero ver mi cartera con todos mis saldos,
para saber cuánto he ganado, cuánto tengo disponible para retirar y cuánto he retirado.

**Criterios de aceptación:**

1. **Cuatro saldos visibles:** La pantalla muestra saldo disponible, saldo pendiente, total ganado y total retirado, todos con dos decimales y la unidad de moneda.

2. **Datos actualizados:** Los saldos se cargan desde el backend al entrar a la pantalla y reflejan las últimas operaciones.

3. **Estado de carga:** Se muestra indicador mientras se obtienen los datos. Si falla, se muestra error con opción de reintentar.

4. **Saldos a cero:** Si no hay ninguna actividad aún, todos los saldos se muestran como "0,00" sin errores.

---

#### US-16 — Historial de transacciones

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-06

**Historia:**
Como proveedor autenticado,
quiero ver el historial completo de mis transacciones ordenado de más reciente a más antiguo,
para tener trazabilidad de cada ingreso, retiro y penalización.

**Criterios de aceptación:**

1. **Lista ordenada:** Las transacciones aparecen ordenadas de más reciente a más antigua.

2. **Datos por transacción:** Cada transacción muestra: fecha y hora, tipo (pago_tarea / retiro / bonus / penalizacion), descripción en español, monto y estado.

3. **Color por tipo:** Los ingresos (pago_tarea, bonus) muestran el monto en color verde o positivo. Los egresos (retiro, penalizacion) en color rojo o negativo.

4. **Sin transacciones:** Si no hay historial, se muestra "No tienes transacciones aún".

5. **Límite de visualización:** Se muestran hasta 50 transacciones. Si hay más de 50, se muestran las 50 más recientes con una nota informativa.

---

#### US-17 — Solicitud de retiro de fondos

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-06

**Historia:**
Como proveedor con saldo disponible,
quiero solicitar el retiro de mis ganancias eligiendo el método de pago,
para transformar mis puntos de cómputo en dinero real.

**Criterios de aceptación:**

1. **Tres métodos disponibles:** Puedo elegir entre transferencia bancaria (campo IBAN), PayPal (campo email) y criptomoneda (campo dirección de wallet).

2. **Monto válido:** El campo de monto solo acepta números positivos con hasta 2 decimales.

3. **Límite de saldo:** Si el monto solicitado supera el saldo disponible, el sistema muestra "El monto supera tu saldo disponible (X,XX)" y no procesa el retiro.

4. **Monto mínimo:** Si el monto es inferior a 10, el sistema muestra "El monto mínimo de retiro es 10,00".

5. **Retiro exitoso:** Con monto válido y datos de destino correctos, el sistema registra la solicitud de retiro, deduce el monto del saldo disponible, crea la transacción de tipo "retiro" con estado "pendiente" y muestra confirmación "Solicitud de retiro registrada. Te contactaremos cuando se procese."

6. **Historial actualizado:** La nueva transacción de retiro aparece inmediatamente en el historial.

7. **Campo de destino obligatorio:** No se puede enviar el formulario sin haber completado el campo de destino del método seleccionado.

8. **Confirmación previa:** Antes de procesar, se muestra un resumen (monto, método, destino) y se solicita confirmación al usuario.

---

### E-07: Perfil

---

#### US-18 — Visualización y edición del perfil

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-07

**Historia:**
Como proveedor autenticado,
quiero ver y editar mi información de perfil,
para mantener mis datos actualizados y gestionar mi estado de disponibilidad.

**Criterios de aceptación:**

1. **Datos del perfil visibles:** La pantalla muestra nombre completo (editable), email (solo lectura), fecha de registro, tasa de éxito y estado online.

2. **Edición de nombre:** Puedo cambiar mi nombre completo. Al guardar, el cambio se persiste y se refleja inmediatamente en la UI (navbar, dashboard).

3. **Email no editable:** El campo email aparece como solo lectura; no hay forma de modificarlo desde la UI.

4. **Toggle de estado online:** El toggle de estado online actualiza el campo `is_online` en el backend al cambiar de posición. Muestra estado de carga durante la actualización.

5. **Tasa de éxito calculada:** La tasa de éxito se muestra como porcentaje con un decimal (ej. "85,3%") calculada en el backend.

6. **Estado de carga y error:** Mientras se cargan o guardan los datos, se muestran los estados correspondientes.

---

#### US-19 — Gestión del hardware registrado

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-07

**Historia:**
Como proveedor autenticado,
quiero registrar o actualizar las especificaciones de mi hardware,
para que la plataforma pueda mostrarme tareas compatibles y los clientes sepan con qué recursos cuento.

**Criterios de aceptación:**

1. **Formulario de hardware:** Los campos CPU (texto, obligatorio), GPU (texto, opcional), RAM en GB (número entero positivo, obligatorio) y almacenamiento en GB (número entero positivo, obligatorio) son accesibles y editables.

2. **Validación de campos numéricos:** RAM y almacenamiento solo aceptan enteros mayores que cero. Un valor de 0 o negativo muestra error de validación.

3. **GPU opcional:** El campo GPU puede guardarse vacío sin errores. Se muestra como "No especificado" cuando está vacío.

4. **Guardar exitoso:** Al guardar, los datos se persisten y se muestran actualizados sin necesidad de recargar la página.

5. **Primer registro:** Si el proveedor nunca ha registrado hardware, el formulario aparece vacío pero funcional.

---

#### US-20 — Trust Score con desglose en el perfil

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-07

**Historia:**
Como proveedor autenticado,
quiero ver mi Trust Score con el desglose de cada componente de la fórmula,
para entender exactamente por qué tengo esa puntuación y qué puedo hacer para mejorarla.

**Criterios de aceptación:**

1. **Puntuación total visible:** Se muestra el Trust Score total (0-100) de forma prominente junto al rango actual.

2. **Desglose de componentes:** Se muestran los cuatro componentes con su nombre, valor actual y peso en la fórmula: Tasa de completado (40%), Precisión (30%), Tiempo de respuesta (20%), Valoración de cliente (10%).

3. **Coherencia matemática:** La suma ponderada de los cuatro componentes iguala el Trust Score total mostrado (tolerancia ±0.01 por redondeo).

4. **Rango siguiente:** Si el proveedor no está en rango "élite", se muestra el rango siguiente y cuántos puntos le faltan para alcanzarlo.

5. **Descripción de rangos:** Se muestra una descripción breve de cada rango (nuevo: 0-49, confiable: 50-74, experto: 75-89, élite: 90-100) para contextualizar la posición del proveedor.

---

### E-08: Trust Score

---

#### US-21 — Cálculo y actualización del Trust Score

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-08

**Historia:**
Como sistema de reputación de Co-Computing,
quiero calcular y actualizar el Trust Score de un proveedor cada vez que completa o falla una tarea,
para mantener una puntuación de confianza actualizada y coherente con su historial real.

**Criterios de aceptación:**

1. **Fórmula correcta:** El Trust Score se calcula como `(completion_rate * 0.40) + (accuracy * 0.30) + (response_time * 0.20) + (client_rating * 0.10)`. Los tests del servicio validan la fórmula con al menos 5 escenarios de valores conocidos.

2. **Actualización al completar:** Cuando una asignación transiciona a "completada", el Trust Score del proveedor se recalcula y persiste inmediatamente.

3. **Actualización al fallar:** Cuando una asignación transiciona a "fallida", el Trust Score del proveedor se recalcula y persiste inmediatamente.

4. **Trust Delta registrado:** El campo `trust_delta` de la asignación almacena la diferencia entre el Trust Score antes y después del recálculo (puede ser positivo, negativo o cero).

5. **Rango actualizado:** Después de cada recálculo, el campo `rank` del proveedor se actualiza según la tabla de rangos: 0-49 = nuevo, 50-74 = confiable, 75-89 = experto, 90-100 = élite.

6. **Límites respetados:** El Trust Score nunca supera 100 ni baja de 0 independientemente de los valores de los componentes.

7. **Componentes de accuracy y response_time ajustados:** `accuracy` aumenta 2 puntos al completar y baja 5 al fallar, con límites 0-100. `response_time` sube 5 si el inicio fue en menos de 10 minutos desde la aceptación y baja 5 si tardó más de 60 minutos.

---

#### US-22 — Visualización de rango en el dashboard y navbar

**Prioridad:** Should Have
**Estimación:** S (2 puntos)
**Épica:** E-08

**Historia:**
Como proveedor autenticado,
quiero ver mi rango actual de forma visible en el dashboard y en la navegación principal,
para sentir la progresión y motivación de mejorar mi posición en la plataforma.

**Criterios de aceptación:**

1. **Rango en el dashboard:** El dashboard muestra el rango actual con su nombre (nuevo / confiable / experto / élite) diferenciado visualmente (badge con color o icono propio por rango).

2. **Rango en la navegación:** El nombre del proveedor en la navbar o menú incluye el rango o un badge de rango visible.

3. **Actualización inmediata:** Si el proveedor sube de rango tras completar una tarea, el rango se actualiza al volver al dashboard sin necesidad de cerrar y volver a abrir sesión.

---

### E-09: Infraestructura y Calidad

---

#### US-23 — Tests del backend: módulo de autenticación

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-09

**Historia:**
Como desarrollador responsable de la calidad del backend,
quiero tener tests automatizados que cubran todos los endpoints de autenticación,
para garantizar que el registro, login y validación de token funcionan correctamente y no se rompen con cambios futuros.

**Criterios de aceptación:**

1. **Test de registro exitoso:** Verifica que `POST /auth/register` con datos válidos devuelve 201 y los datos del proveedor creado.

2. **Test de email duplicado:** Verifica que `POST /auth/register` con email existente devuelve 400 con mensaje de error apropiado.

3. **Test de contraseña corta:** Verifica que `POST /auth/register` con contraseña < 8 caracteres devuelve 422.

4. **Test de login exitoso:** Verifica que `POST /auth/login` con credenciales correctas devuelve 200 con un JWT y datos del proveedor.

5. **Test de credenciales incorrectas:** Verifica que `POST /auth/login` con password incorrecto devuelve 401.

6. **Test de perfil autenticado:** Verifica que `GET /auth/me` con JWT válido devuelve 200 con datos del proveedor.

7. **Test de token inválido:** Verifica que `GET /auth/me` con JWT malformado o expirado devuelve 401.

---

#### US-24 — Tests del backend: módulo de tareas

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-09

**Historia:**
Como desarrollador responsable de la calidad del backend,
quiero tests automatizados para todos los endpoints de tareas y su ciclo de vida,
para garantizar que el flujo core del producto funciona correctamente.

**Criterios de aceptación:**

1. **Listado de tareas:** `GET /tasks/` sin filtros devuelve 200 con lista de tareas disponibles.

2. **Listado con filtros:** `GET /tasks/?difficulty=facil&hardware=gpu` devuelve solo las tareas que cumplen los filtros.

3. **Detalle de tarea:** `GET /tasks/{id}` con ID válido devuelve 200 con todos los campos. Con ID inexistente devuelve 404.

4. **Aceptar tarea:** `POST /tasks/{id}/accept` con tarea disponible devuelve 201. Sin plazas devuelve 400. Sin autenticación devuelve 401.

5. **Iniciar tarea:** `POST /tasks/{id}/start` desde estado "aceptada" devuelve 200 con datos de progreso. Desde otro estado devuelve 400.

6. **Completar tarea:** `POST /tasks/{id}/complete` desde "procesando" devuelve 200, actualiza cartera y Trust Score. Desde otro estado devuelve 400.

7. **Fallar tarea:** `POST /tasks/{id}/fail` desde "procesando" devuelve 200 y penaliza Trust Score.

8. **Historial del proveedor:** `GET /tasks/my/history` devuelve las asignaciones del proveedor autenticado.

9. **Aislamiento por proveedor:** Un proveedor no puede completar o fallar la asignación de otro proveedor; devuelve 403.

---

#### US-25 — Tests del backend: módulo de cartera

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-09

**Historia:**
Como desarrollador responsable de la calidad del backend,
quiero tests automatizados para los endpoints de la cartera,
para garantizar que los saldos, transacciones y retiros funcionan correctamente.

**Criterios de aceptación:**

1. **Saldo de cartera:** `GET /wallet/` con token válido devuelve 200 con los cuatro saldos.

2. **Historial de transacciones:** `GET /wallet/transactions` devuelve 200 con la lista de transacciones ordenadas.

3. **Retiro exitoso:** `POST /wallet/withdraw` con monto válido y saldo suficiente devuelve 200 y crea la transacción.

4. **Saldo insuficiente:** `POST /wallet/withdraw` con monto mayor al disponible devuelve 400.

5. **Monto mínimo no alcanzado:** `POST /wallet/withdraw` con monto < 10 devuelve 400 con mensaje de mínimo.

6. **Sin autenticación:** Todos los endpoints de wallet sin token devuelven 401.

---

#### US-26 — Tests del backend: módulo de perfil

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-09

**Historia:**
Como desarrollador responsable de la calidad del backend,
quiero tests automatizados para los endpoints de perfil,
para garantizar que las estadísticas, hardware y estado online funcionan correctamente.

**Criterios de aceptación:**

1. **Estadísticas de perfil:** `GET /profile/stats` devuelve 200 con Trust Score, rango, tasa de éxito y hardware.

2. **Actualización de hardware:** `PUT /profile/hardware` con datos válidos devuelve 200 y persiste los cambios. Con RAM = 0 devuelve 422.

3. **Toggle online:** `PATCH /profile/online` actualiza el campo `is_online` y devuelve el estado actual.

4. **Sin autenticación:** Todos los endpoints de perfil sin token devuelven 401.

---

#### US-27 — Seed de tareas representativas

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-09

**Historia:**
Como desarrollador que configura el entorno local o de demostración,
quiero ejecutar un script de seed que pueble la base de datos con tareas representativas,
para que la plataforma sea demostrable sin necesidad de insertar datos manualmente.

**Criterios de aceptación:**

1. **Cobertura de tipos:** El seed incluye al menos 15 tareas con variedad de tipos: renderizado 3D, entrenamiento ML, transcodificación de video, análisis de datos y simulación física.

2. **Variedad de dificultad y hardware:** El seed incluye tareas de las tres dificultades (fácil, medio, difícil) y los tres tipos de hardware (cpu, gpu, mixto).

3. **Idempotente:** Ejecutar el script varias veces no duplica los registros (usa `INSERT ... ON CONFLICT DO NOTHING` o equivalente).

4. **Ejecutable en menos de 30 segundos:** El script completa en menos de 30 segundos en una conexión estándar a Supabase Cloud.

5. **Documentado en README:** El README incluye el comando exacto para ejecutar el seed como paso obligatorio del arranque local.

---

#### US-28 — Schema SQL y políticas RLS

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-09

**Historia:**
Como desarrollador que configura el entorno desde cero,
quiero tener ficheros SQL ejecutables que creen el schema completo y las políticas de Row Level Security,
para poder reproducir el entorno de base de datos sin configuración manual.

**Criterios de aceptación:**

1. **Schema completo:** El fichero `backend/app/db/schema.sql` crea todas las tablas: `providers`, `tasks`, `task_assignments`, `wallets`, `transactions`, con todos sus campos, tipos, restricciones y relaciones de clave foránea.

2. **Políticas RLS:** El fichero `backend/app/db/rls_policies.sql` activa RLS en todas las tablas y define políticas que garantizan: cada proveedor solo ve sus propios registros de `task_assignments`, `wallets` y `transactions`; `tasks` tiene lectura pública para proveedores autenticados.

3. **Ejecutable en SQL editor de Supabase:** Ambos ficheros se pueden pegar y ejecutar directamente en el SQL editor de Supabase sin modificaciones.

4. **Idempotente:** Los ficheros usan `CREATE TABLE IF NOT EXISTS` y `CREATE POLICY IF NOT EXISTS` para poder ejecutarse múltiples veces sin errores.

---

#### US-29 — README y arranque local en menos de 5 minutos

**Prioridad:** Must Have
**Estimación:** S (2 puntos)
**Épica:** E-09

**Historia:**
Como nuevo desarrollador que se une al proyecto,
quiero un README claro que me permita arrancar el proyecto completo en menos de 5 minutos,
para poder empezar a contribuir sin perder tiempo en configuración.

**Criterios de aceptación:**

1. **Pasos secuenciales y completos:** El README lista todos los pasos de arranque local en orden, sin dar por supuesto conocimientos específicos del proyecto.

2. **Comandos exactos y copiables:** Cada paso incluye el comando exacto a ejecutar, sin ambigüedad.

3. **Variables de entorno documentadas:** Existe `.env.example` en `backend/` y `frontend/` con todas las variables requeridas, una descripción por línea de qué es cada variable y un valor de ejemplo o indicación de dónde obtenerlo.

4. **Tiempo verificado:** Siguiendo el README paso a paso con conexión a internet estable, el entorno arranca en menos de 5 minutos.

5. **Requisitos previos declarados:** El README lista los requisitos previos (Python 3.12+, Node 20+, cuenta en Supabase) al inicio.

---

#### US-30 — Configuración de CORS y seguridad de API

**Prioridad:** Must Have
**Estimación:** S (2 puntos)
**Épica:** E-09

**Historia:**
Como desarrollador responsable de la seguridad del backend,
quiero que el CORS esté configurado para aceptar solo el origen del frontend y que los headers de seguridad estén presentes,
para que la API no sea accesible desde orígenes no autorizados.

**Criterios de aceptación:**

1. **CORS restrictivo:** El backend solo acepta peticiones desde el valor de `FRONTEND_URL` en la variable de entorno. Una petición desde `http://malicious.com` recibe error CORS.

2. **Sin wildcard en producción:** El código no contiene `allow_origins=["*"]` en ninguna configuración que afecte al entorno de producción.

3. **Headers de seguridad:** Las respuestas del backend incluyen `X-Content-Type-Options: nosniff` y `X-Frame-Options: DENY`.

4. **JWT validado en todos los endpoints protegidos:** Todos los endpoints que no son `POST /auth/register` y `POST /auth/login` requieren un JWT válido y devuelven 401 sin él.

---

## Resumen del Backlog

### Distribución por prioridad

| Prioridad | Cantidad de stories | Puntos totales |
|-----------|--------------------|--------------:|
| Must Have | 26 | 87 |
| Should Have | 2 | 4 |
| Could Have | 0 | 0 |
| Won't Have (MVP) | — | — |
| **Total** | **28** | **91** |

### Stories por épica

| Épica | Stories | Puntos |
|-------|---------|-------:|
| E-01: Autenticación | US-01, US-02, US-03 | 7 |
| E-02: Dashboard | US-04 | 5 |
| E-03: Exploración de Tareas | US-05, US-06, US-07, US-08 | 13 |
| E-04: Ciclo de Vida de Tarea | US-09, US-10, US-11, US-12 | 14 |
| E-05: Procesamiento | US-13, US-14 | 11 |
| E-06: Cartera | US-15, US-16, US-17 | 10 |
| E-07: Perfil | US-18, US-19, US-20 | 9 |
| E-08: Trust Score | US-21, US-22 | 7 |
| E-09: Infraestructura y Calidad | US-23 a US-30 | 24 |

### Secuencia de entrega sugerida (por dependencias)

**Sprint 1 — Fundación:**
US-28 (Schema SQL) → US-23 (Tests auth) → US-01, US-02, US-03 (Autenticación) → US-30 (CORS/Seguridad)

**Sprint 2 — Descubrimiento de Tareas:**
US-27 (Seed) → US-05, US-06, US-07, US-08 (Listado y detalle de tareas) → US-24 (Tests tareas parcial)

**Sprint 3 — Flujo Core:**
US-09, US-10, US-11, US-12 (Ciclo de vida) → US-13, US-14 (Procesamiento) → US-24 (Tests tareas completo)

**Sprint 4 — Financiero y Reputación:**
US-15, US-16, US-17 (Cartera) → US-21 (Trust Score) → US-25 (Tests wallet) → US-26 (Tests perfil)

**Sprint 5 — Perfil, Dashboard y Cierre:**
US-04 (Dashboard) → US-18, US-19, US-20 (Perfil) → US-22 (Rango en navegación) → US-29 (README)

---

## Historias Won't Have (backlog futuro)

Las siguientes historias han sido identificadas durante el análisis pero quedan explícitamente excluidas del MVP:

| ID futuro | Título | Motivo de exclusión |
|-----------|--------|---------------------|
| US-F01 | Integración con Stripe para retiros reales | Complejidad regulatoria y de integración. Fase 2. |
| US-F02 | Detección automática de hardware del proveedor | Requiere agente local fuera del alcance web. Fase 2. |
| US-F03 | Notificaciones en tiempo real (WebSocket) | Requiere infraestructura de WebSockets. Fase 2. |
| US-F04 | Panel del cliente que sube tareas | Duplica la superficie de producto; se valida primero el lado proveedor. |
| US-F05 | Valoraciones explícitas de clientes | Depende del panel de cliente (US-F04). |
| US-F06 | Notificaciones por email | Fuera de alcance del MVP. Fase 2. |
| US-F07 | Sistema de heartbeat para estado online | Requiere WebSockets. Fase 2. |
| US-F08 | Panel de administración back-office | No necesario para validación. Se gestiona directamente en Supabase. |
| US-F09 | Internacionalización multiidioma | La plataforma se lanza en español. Expansión futura condicionada al éxito del MVP. |
| US-F10 | Aplicación móvil nativa (iOS / Android) | Segunda fase condicionada al éxito del MVP web. |

---

## Feature: Cómputo Real Distribuido

**Versión:** 1.1
**Fecha:** 2026-06-07
**Referencia:** `briefs/02-computo-real.md`, `migrations/004_compute.sql`

Esta sección extiende el backlog con las user stories de la feature de cómputo distribuido real. El sistema de autenticación (JWT via `/auth/login`), la cartera (`wallet_service`), el `trust_score`, los componentes UI (Card, Button, ProgressBar) y los stores Zustand ya existen y se reutilizan. Las tablas nuevas (`jobs`, `chunks`, `chunk_results`) están definidas en `migrations/004_compute.sql`.

---

### Épicas nuevas

| ID | Épica | Descripción |
|----|-------|-------------|
| E-10 | Cómputo Distribuido - Cliente | Flujo completo del cliente para enviar un job de datos, seguir su progreso real y obtener el resultado consolidado |
| E-11 | Cómputo Distribuido - Worker/Proveedor | Worker CLI que reclama y procesa chunks reales; pantalla del proveedor con progreso basado en chunks; consenso y pago automático |

---

### E-10: Cómputo Distribuido - Cliente

---

#### US-31 — Crear un nuevo job de procesamiento de datos

**Prioridad:** Must Have
**Estimación:** XL (8 puntos)
**Épica:** E-10

**Historia:**
Como usuario autenticado que actúa como cliente,
quiero subir un archivo CSV y elegir una operación (media, suma, min, max, conteo) sobre una o varias columnas,
para enviar un trabajo de cómputo real al sistema distribuido y recibir el resultado procesado.

**Criterios de aceptación:**

1. **Acceso al formulario:** Existe una pantalla "Nuevo trabajo" accesible desde la navegación principal. Reutiliza los componentes Button y Card existentes.

2. **Subida de CSV:** El formulario acepta un archivo `.csv` de hasta 50 MB. Si el archivo supera ese tamaño, se muestra el mensaje "El archivo no puede superar 50 MB" y no se envía.

3. **Formato válido:** Si el archivo subido no es un CSV válido (no tiene cabecera, está vacío o contiene filas malformadas), el backend devuelve 422 con descripción del problema y la UI lo muestra al usuario.

4. **Selección de operación:** El formulario permite elegir la operación: `mean`, `sum`, `min`, `max`, `count`. La selección es obligatoria; sin ella el botón "Enviar" permanece deshabilitado.

5. **Selección de columnas:** Tras cargar el CSV en el frontend, se muestran las columnas detectadas para que el usuario seleccione sobre cuáles aplicar la operación. Al menos una columna debe estar seleccionada.

6. **Envío exitoso:** Al confirmar, el sistema llama a `POST /jobs` (multipart/form-data o JSON con datos del CSV) con `job_type: "data-processing"` y los `params` correspondientes. Si el backend devuelve 201, la UI navega automáticamente a la pantalla "Mis trabajos" y muestra un mensaje de confirmación "Trabajo enviado correctamente".

7. **Troceado en background:** El backend divide el dataset por filas en N chunks (mínimo 2, máximo configurable) y persiste los registros en la tabla `chunks`. El job pasa de `pending` a `splitting` y luego a `processing` de forma automática sin intervención del usuario.

8. **Recompensa informativa:** El formulario muestra una estimación de la recompensa total del job (en CC) calculada por el backend según el tamaño del dataset, antes de confirmar el envío.

9. **Estado de carga:** Mientras se procesa el envío, el botón muestra estado de carga y no permite doble envío.

10. **Sin autenticación:** Un usuario no autenticado que acceda a la pantalla es redirigido al login.

---

#### US-32 — Listado de mis trabajos (cliente)

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-10

**Historia:**
Como cliente autenticado,
quiero ver una lista de todos mis trabajos enviados con su estado actual y progreso,
para saber en qué punto se encuentra cada uno sin tener que preguntar al sistema manualmente.

**Criterios de aceptación:**

1. **Listado propio:** La pantalla "Mis trabajos" llama a `GET /jobs` y muestra únicamente los jobs del cliente autenticado. Un cliente nunca ve los jobs de otro cliente.

2. **Información por fila:** Cada job en la lista muestra: identificador corto (primeros 8 caracteres del UUID), fecha de creación, operación y columnas solicitadas (extraídas de `params`), estado actual con badge de color (pending=gris, processing=azul, validating=amarillo, completed=verde, failed=rojo) y progreso en porcentaje (`completed_chunks / total_chunks * 100`, redondeado a entero).

3. **Barra de progreso real:** Se reutiliza el componente ProgressBar existente. El porcentaje refleja chunks validados sobre total, no tiempo transcurrido.

4. **Lista vacía:** Si el cliente no tiene ningún job, se muestra "Aún no has enviado ningún trabajo. Pulsa 'Nuevo trabajo' para empezar." con enlace al formulario.

5. **Actualización periódica:** La lista se refresca automáticamente cada 5 segundos mientras haya algún job en estado diferente de `completed` o `failed`. Si todos los jobs están en estado terminal, el polling se detiene.

6. **Acceso al detalle:** Al pulsar sobre un job se navega a la pantalla de detalle de ese job (US-33).

7. **Estado de carga y error:** Se muestra indicador de carga en la primera carga. Si la petición falla, se muestra error con opción de reintentar.

---

#### US-33 — Detalle y progreso real de un job

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-10

**Historia:**
Como cliente autenticado,
quiero ver el estado detallado de un job concreto con el progreso real basado en chunks completados,
para tener visibilidad del trabajo distribuido y saber cuándo estará listo el resultado.

**Criterios de aceptación:**

1. **Datos del job:** La pantalla llama a `GET /jobs/{id}` y muestra: estado, porcentaje de progreso (`completed_chunks / total_chunks * 100`), número de chunks total y completados, fecha de creación, operación y columnas.

2. **Progreso real, no simulado:** El porcentaje mostrado se calcula exclusivamente a partir de `completed_chunks` y `total_chunks` devueltos por el backend. No existe lógica de simulación por tiempo transcurrido en esta pantalla.

3. **Polling activo:** Si el job no está en estado terminal (`completed` o `failed`), la pantalla consulta `GET /jobs/{id}` cada 5 segundos y actualiza los datos sin recargar la página. Al alcanzar el estado terminal, el polling se detiene.

4. **Transición a completado:** Cuando el job pasa a `completed`, la pantalla muestra automáticamente un banner "Trabajo completado" con un botón "Ver resultado" que lleva a la pantalla de resultado (US-34), sin que el usuario tenga que recargar manualmente.

5. **Job fallido:** Si el job pasa a `failed`, la pantalla muestra un mensaje "El trabajo ha fallado. Puedes intentarlo de nuevo." con botón que lleva al formulario de nuevo job precargado con los mismos parámetros.

6. **Acceso no autorizado:** Si el job no pertenece al cliente autenticado, el backend devuelve 403 y la UI muestra "No tienes acceso a este trabajo."

7. **Job no encontrado:** Si el ID no existe, el backend devuelve 404 y la UI muestra "Trabajo no encontrado" con enlace a "Mis trabajos".

8. **Limpieza del polling:** Al salir de la pantalla, el intervalo de polling se cancela.

---

#### US-34 — Ver el resultado final de un job completado

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-10

**Historia:**
Como cliente autenticado cuyo job ha sido completado,
quiero ver el resultado consolidado del procesamiento de mis datos,
para obtener el valor por el que envié el trabajo y poder usarlo.

**Criterios de aceptación:**

1. **Endpoint correcto:** La pantalla llama a `GET /jobs/{id}/result`. Si el job no está en estado `completed`, el backend devuelve 409 y la UI muestra "El resultado aún no está disponible."

2. **Resultado visible:** El resultado se presenta en formato tabular o JSON legible: columna, operación aplicada, valor calculado (ej. `{"col1": {"mean": 42.3}, "col2": {"mean": 17.1}}`).

3. **Descarga:** Existe un botón "Descargar resultado (JSON)" que descarga el campo `result` del job como archivo `.json` con nombre `resultado_{job_id_corto}.json`.

4. **Metadatos del job:** La pantalla muestra también: fecha de completado, número de chunks procesados, número de proveedores que participaron y recompensa total pagada.

5. **Acceso restringido:** Solo el cliente propietario del job puede ver el resultado. Cualquier otro usuario autenticado recibe 403.

6. **Estado de carga:** Se muestra indicador mientras se obtienen los datos del resultado.

---

### E-11: Cómputo Distribuido - Worker/Proveedor

---

#### US-35 — Worker CLI: autenticación y bucle de claim/process/submit

**Prioridad:** Must Have
**Estimación:** XL (8 puntos)
**Épica:** E-11

**Historia:**
Como proveedor que quiere contribuir recursos de cómputo,
quiero ejecutar el worker CLI para que mi máquina procese chunks reales de forma autónoma,
para ganar recompensas en CC sin intervención manual en cada tarea.

**Criterios de aceptación:**

1. **Arranque por CLI:** El worker se lanza con `python -m app.worker --api <url> --email <email> --password <password>`. Los tres argumentos son obligatorios; sin alguno el proceso termina con mensaje de error claro.

2. **Autenticación reutilizada:** El worker usa exactamente el endpoint `POST /auth/login` existente para obtener el JWT. No implementa autenticación propia. Si las credenciales son incorrectas, el proceso termina con mensaje "Credenciales incorrectas. Verifica email y contraseña."

3. **Claim atómico:** El worker llama a `POST /work/claim` para reclamar hasta N chunks `pending` (N configurable, por defecto 1). El backend asigna los chunks de forma atómica: si dos workers llaman simultáneamente, cada uno recibe chunks distintos sin colisiones.

4. **Procesamiento real con polars:** Para `job_type: "data-processing"`, el worker ejecuta la operación indicada en `params` sobre las filas del chunk usando polars (o pandas como fallback). El resultado es el valor numérico calculado de verdad, no un valor aleatorio ni simulado.

5. **Arquitectura de plugin:** La lógica de procesamiento está encapsulada en una clase `WorkerTask` con interfaz `process(payload: dict) -> dict`. El worker principal no contiene lógica de negocio del cómputo; solo orquesta claim, dispatch al plugin y submit.

6. **Submit del resultado:** Tras procesar, el worker llama a `POST /work/{chunk_id}/submit` con el resultado y `duration_ms`. Si el backend devuelve 200, el worker registra en log "Chunk {chunk_id} enviado correctamente". Si devuelve error, lo registra y continúa con el siguiente chunk.

7. **Polling continuo:** Si no hay chunks disponibles (`POST /work/claim` devuelve lista vacía), el worker espera 5 segundos y reintenta. El bucle continúa hasta que se interrumpe con Ctrl+C.

8. **Log estructurado:** Cada operación relevante (login, claim, inicio de cómputo, submit, error) se registra en stdout con timestamp ISO 8601 y nivel (INFO, WARNING, ERROR). No se registran datos sensibles (passwords, contenido de chunks en crudo).

9. **Script multi-worker:** Existe un script `scripts/run_workers.sh` (o `.ps1`) que lanza N instancias del worker en paralelo para demostrar la distribución. N es configurable como argumento.

10. **Tests del worker:** Existe al menos un test de integración que crea un job con 2 chunks, lanza 2 instancias del worker, verifica que ambos chunks quedan en estado `done` y que el job pasa a `validating` o `completed`.

---

#### US-36 — Backend: endpoints de claim y submit para workers

**Prioridad:** Must Have
**Estimación:** XL (8 puntos)
**Épica:** E-11

**Historia:**
Como worker Python autenticado,
quiero poder reclamar chunks pendientes y entregar mis resultados a través de la API,
para que el backend registre mi trabajo y pueda validarlo por consenso.

**Criterios de aceptación:**

1. **POST /work/claim — claim atómico:** El endpoint selecciona hasta N chunks en estado `pending` de entre todos los jobs en estado `processing`, los marca como `assigned`, registra `assigned_to = provider_id` del JWT, incrementa `attempts` y los devuelve en la respuesta. La operación es atómica (usa SELECT ... FOR UPDATE SKIP LOCKED o equivalente). Dos llamadas concurrentes nunca devuelven el mismo chunk.

2. **Respeto a replicas_needed:** Un mismo chunk puede ser reclamado por hasta `replicas_needed` proveedores distintos. Si un chunk ya tiene `replicas_needed` resultados en `chunk_results`, no se incluye en futuros claims aunque su estado sea `assigned`.

3. **POST /work/{chunk_id}/submit — entrega de resultado:** El endpoint acepta `result` (jsonb) y `duration_ms` (entero positivo). Crea un registro en `chunk_results`. Si `duration_ms <= 0`, devuelve 422. Si el proveedor ya entregó resultado para ese chunk, devuelve 409.

4. **Activación de consenso tras submit:** Cada vez que se recibe un submit, el backend comprueba cuántos resultados existen ya para ese chunk. Si hay `replicas_needed` resultados, dispara la lógica de validación por consenso (US-38) de forma síncrona o asíncrona antes de responder.

5. **Solo proveedores autenticados:** Ambos endpoints requieren JWT válido y devuelven 401 sin él. El proveedor solo puede hacer submit del chunk que tiene asignado; en caso contrario, 403.

6. **Sin chunks disponibles:** Si `POST /work/claim` no encuentra chunks `pending` elegibles, devuelve 200 con lista vacía (no 404).

7. **Tests:** Tests unitarios e integración que verifían: claim concurrente sin colisiones, submit correcto, submit duplicado (409), submit con duration_ms = 0 (422), claim sin chunks disponibles.

---

#### US-37 — Pantalla del proveedor: progreso basado en chunks reales

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-11

**Historia:**
Como proveedor autenticado que está procesando una tarea (en el sentido del sistema existente) o que contribuye como worker,
quiero que la pantalla de procesamiento muestre el avance real basado en chunks completados y no en tiempo transcurrido simulado,
para tener feedback auténtico de mi contribución al cómputo distribuido.

**Criterios de aceptación:**

1. **Integración con pantalla existente:** La pantalla de procesamiento existente (`/processing/{assignmentId}`) se amplía o coexiste con una nueva vista de chunks. No se elimina ni se rompe el flujo de asignaciones existente (US-13 sigue funcionando tal como está).

2. **Indicador de chunks:** Si la asignación en curso corresponde a un job del pipeline distribuido, la pantalla muestra adicionalmente: número de chunks reclamados por el proveedor, cuántos han sido enviados, y cuántos han sido validados como correctos.

3. **Sin progreso simulado para jobs reales:** Para jobs del tipo `data-processing`, el porcentaje de progreso mostrado en la ProgressBar se calcula como `chunks_submitted / chunks_claimed * 100`. No se usa la fórmula de tiempo transcurrido de `progress_service.py` para estos jobs.

4. **Compatibilidad backward:** Las asignaciones de tipo tarea clásica (que no están vinculadas a un job distribuido) siguen mostrando el progreso simulado exactamente igual que antes. Ningún test de US-13 falla.

5. **Actualización reactiva:** El indicador de chunks se actualiza cada vez que el worker CLI hace un submit exitoso (reflejado en el próximo ciclo de polling de la pantalla, que ya existe en 3 segundos).

6. **Estado de validación visible:** Cuando un chunk del proveedor pasa a `is_valid = true` o `is_valid = false` tras el consenso, la pantalla lo refleja con una indicación visual (ej. checkmark verde o cruz roja junto al chunk).

---

#### US-38 — Validación por consenso y cierre del job

**Prioridad:** Must Have
**Estimación:** XL (8 puntos)
**Épica:** E-11

**Historia:**
Como sistema de cómputo distribuido,
quiero validar automáticamente los resultados de cada chunk comparando los resultados de múltiples proveedores,
para garantizar que solo se consolidan resultados correctos y se pagan únicamente los proveedores que computaron de forma honesta.

**Criterios de aceptación:**

1. **Activación del consenso:** Cuando un chunk tiene exactamente `replicas_needed` resultados en `chunk_results`, el servicio de consenso se ejecuta automáticamente para ese chunk.

2. **Consenso por coincidencia exacta:** Si los `replicas_needed` resultados son idénticos (comparación de los valores numéricos con tolerancia de ±0.0001 para floats), todos los `chunk_results` se marcan `is_valid = true` y el chunk pasa a estado `done`.

3. **Desempate por 3er proveedor:** Si los resultados no coinciden, el chunk se reasigna a un tercer proveedor distinto (no puede ser ninguno de los dos anteriores). El sistema elige al proveedor con mayor `trust_score` disponible en ese momento. La lógica de claim estándar (US-36) incluye este caso sin crear un endpoint separado.

4. **Resolución por mayoría (3 resultados):** Con 3 resultados, el valor que aparece en mayoría (al menos 2 de 3) se considera correcto. Los `chunk_results` coincidentes con la mayoría se marcan `is_valid = true`; el discrepante se marca `is_valid = false`.

5. **Avance del job:** Cada vez que un chunk pasa a `done`, el campo `completed_chunks` del job se incrementa en 1 de forma atómica. Cuando `completed_chunks == total_chunks`, el job pasa a estado `completed` y se ejecuta la consolidación del resultado final.

6. **Consolidación del resultado final:** El servicio de consolidación reduce los resultados parciales válidos de todos los chunks (operación de reduce apropiada para la operación solicitada: suma de sumas, media ponderada por número de filas, min global, max global, conteo total) y persiste el resultado en `jobs.result`.

7. **Job marcado como completed:** El campo `jobs.completed_at` se registra con el timestamp de finalización. El estado pasa a `completed`.

8. **Fallo por reintentos excesivos:** Si un chunk supera 5 intentos sin alcanzar consenso, su estado pasa a `rejected` y el job entero pasa a `failed`, con `completed_at` registrado.

9. **Tests de consenso:** Existen tests que verifican los tres escenarios: (a) dos resultados iguales → ambos válidos, chunk done; (b) dos resultados distintos → se asigna un tercero; (c) tres resultados con mayoría de 2 → el discordante queda inválido.

---

#### US-39 — Pago a proveedores válidos y actualización de trust score tras consenso

**Prioridad:** Must Have
**Estimación:** L (5 puntos)
**Épica:** E-11

**Historia:**
Como proveedor que ha procesado chunks de forma correcta,
quiero recibir automáticamente el pago en CC en mi cartera y ver mi trust score actualizado,
para que mi contribución tenga recompensa económica y de reputación sin intervención manual.

**Criterios de aceptación:**

1. **Pago solo por resultados válidos:** Al completarse un job, el servicio de pago itera sobre todos los `chunk_results` con `is_valid = true`. Solo estos reciben pago. Los `chunk_results` con `is_valid = false` no reciben ningún abono.

2. **Distribución proporcional:** La recompensa del job (`jobs.reward_total`) se distribuye entre los proveedores con resultados válidos en proporción al número de chunks válidos que cada uno procesó. Si un proveedor procesó 3 de 10 chunks válidos totales, recibe el 30% de `reward_total`.

3. **Reutilización de wallet_service:** El pago se realiza llamando al `wallet_service` y `transactions` existentes. Se crea una transacción de tipo `pago_tarea` por cada proveedor pagado, con descripción "Pago por job {job_id_corto} — {n} chunks válidos". El saldo `balance_available` del proveedor se incrementa.

4. **Trust score subida por resultado válido:** Por cada `chunk_result` marcado `is_valid = true`, el `trust_score` del proveedor se recalcula inmediatamente usando el `trust_service` existente. La componente `accuracy` sube 2 puntos (con techo en 100).

5. **Trust score penalizado por resultado inválido:** Por cada `chunk_result` marcado `is_valid = false`, la componente `accuracy` del proveedor baja 5 puntos (con suelo en 0) y el `trust_score` se recalcula.

6. **Transacciones visibles en cartera:** Las nuevas transacciones de pago aparecen en `GET /wallet/transactions` del proveedor inmediatamente después del cierre del job, sin necesidad de recargar la app manualmente (el polling de la cartera, si existe, las recoge; si no, aparecen en la siguiente visita a la pantalla de cartera).

7. **Idempotencia del pago:** Si el servicio de cierre se ejecuta dos veces por cualquier motivo (reintentos, fallos de red), no se generan transacciones duplicadas. El sistema verifica que no existe ya una transacción `pago_tarea` para ese job y ese proveedor antes de crear una nueva.

8. **Tests de pago:** Existen tests que verifican: (a) proveedor con 2 chunks válidos recibe el porcentaje correcto de la recompensa; (b) proveedor con 0 chunks válidos no recibe ningún pago ni transacción; (c) el trust score sube para resultados válidos y baja para inválidos; (d) la idempotencia del pago (doble ejecución no duplica transacciones).

---

#### US-40 — Tests de integración end-to-end del pipeline de cómputo

**Prioridad:** Must Have
**Estimación:** XL (8 puntos)
**Épica:** E-11

**Historia:**
Como desarrollador responsable de la calidad del pipeline de cómputo distribuido,
quiero tests de integración que ejerciten el flujo completo desde la creación del job hasta el pago,
para garantizar que todos los componentes funcionan juntos de forma correcta y que los bugs del pasado (progreso simulado) no vuelven a introducirse.

**Criterios de aceptación:**

1. **Test flujo feliz completo:** El test crea un job con un CSV de prueba de 100 filas y operación `mean`, simula 2 workers que reclaman y procesan todos los chunks con resultados coincidentes, y verifica que: el job pasa a `completed`, `jobs.result` contiene el valor correcto de la media, los proveedores reciben pago y sus trust scores suben.

2. **Test de consenso con discrepancia:** El test simula 2 workers con resultados distintos para el mismo chunk, verifica que el chunk no pasa a `done` y que se asigna a un 3er proveedor, y que la resolución por mayoría funciona correctamente.

3. **Test de claim concurrente:** El test lanza 5 peticiones simultáneas a `POST /work/claim` para un job con 3 chunks y verifica que no hay solapamiento: la suma de chunks reclamados no supera 3 y cada chunk aparece asignado a un único proveedor.

4. **Test de idempotencia de pago:** El test llama al servicio de cierre del job dos veces y verifica que el número de transacciones en `wallet.transactions` no se duplica.

5. **Test de no-regresión del progreso simulado:** El test verifica que `GET /tasks/{assignmentId}/progress` (endpoint existente de US-14) sigue funcionando correctamente para asignaciones de tipo tarea clásica y devuelve el progreso basado en tiempo, sin verse afectado por el nuevo código del pipeline.

6. **Tests del worker:** Los tests del worker son reales: instancian la clase del plugin `WorkerTask` con un payload de datos real y verifican que el resultado calculado es correcto (no un mock del cómputo).

7. **Build del frontend:** El pipeline de CI verifica que `tsc --noEmit` pasa sin errores después de añadir los tipos TypeScript para las entidades `Job`, `Chunk` y `ChunkResult`.

8. **No se rompen los tests existentes:** Todos los tests de US-23 a US-30 continúan pasando sin modificaciones.

---

#### US-41 — Migración de base de datos y schema para cómputo distribuido

**Prioridad:** Must Have
**Estimación:** M (3 puntos)
**Épica:** E-11

**Historia:**
Como desarrollador que configura el entorno para la feature de cómputo,
quiero ejecutar la migración `migrations/004_compute.sql` para crear las tablas y políticas RLS necesarias,
para que el pipeline de cómputo distribuido tenga soporte de persistencia desde el primer arranque.

**Criterios de aceptación:**

1. **Migración idempotente:** El fichero `migrations/004_compute.sql` puede ejecutarse múltiples veces sin errores ni datos duplicados (usa `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `DROP POLICY IF EXISTS`).

2. **Tablas creadas correctamente:** Tras ejecutar la migración, existen las tablas `jobs`, `chunks` y `chunk_results` con todos los campos, tipos, constraints y claves foráneas definidos en el brief.

3. **RLS activado:** Las tres tablas tienen RLS habilitado. El backend (que usa service_role key) puede leer y escribir en todas ellas. Un usuario sin service_role no puede acceder directamente desde el cliente.

4. **Orden de ejecución documentado:** El encabezado del fichero SQL indica explícitamente que debe ejecutarse después de `001_schema.sql`, `002_rls.sql` y `003_seed.sql`.

5. **README actualizado:** El README incluye `migrations/004_compute.sql` en la secuencia de configuración del entorno local, inmediatamente después de las migraciones existentes.

6. **Sin impacto en tablas existentes:** La ejecución de la migración no modifica, elimina ni añade columnas a las tablas `providers`, `tasks`, `task_assignments`, `wallets` ni `transactions`.

---

## Resumen actualizado del Backlog

### Distribución por prioridad

| Prioridad | Cantidad de stories | Puntos totales |
|-----------|--------------------|--------------:|
| Must Have | 37 | 141 |
| Should Have | 2 | 4 |
| Could Have | 0 | 0 |
| Won't Have (MVP) | — | — |
| **Total** | **39** | **145** |

### Stories por épica (completo)

| Épica | Stories | Puntos |
|-------|---------|-------:|
| E-01: Autenticación | US-01, US-02, US-03 | 7 |
| E-02: Dashboard | US-04 | 5 |
| E-03: Exploración de Tareas | US-05, US-06, US-07, US-08 | 13 |
| E-04: Ciclo de Vida de Tarea | US-09, US-10, US-11, US-12 | 14 |
| E-05: Procesamiento | US-13, US-14 | 11 |
| E-06: Cartera | US-15, US-16, US-17 | 10 |
| E-07: Perfil | US-18, US-19, US-20 | 9 |
| E-08: Trust Score | US-21, US-22 | 7 |
| E-09: Infraestructura y Calidad | US-23 a US-30 | 24 |
| E-10: Cómputo Distribuido - Cliente | US-31, US-32, US-33, US-34 | 19 |
| E-11: Cómputo Distribuido - Worker/Proveedor | US-35, US-36, US-37, US-38, US-39, US-40, US-41 | 45 |
| **Total** | **US-01 a US-41** | **164** |

> Nota: el total de puntos de la tabla por épica (164) difiere del total por prioridad (145) porque US-07 y US-22 son Should Have (4 puntos) y están excluidos del Must Have. La fila "Total" de la tabla por épica suma todos los puntos independientemente de la prioridad.

### Secuencia de entrega sugerida para la feature (sprints adicionales)

**Sprint 6 — Fundación de cómputo:**
US-41 (Migración 004) → US-36 (Endpoints claim/submit) → US-35 (Worker CLI base + plugin polars)

**Sprint 7 — Flujo cliente:**
US-31 (Crear job) → US-32 (Listado de jobs) → US-33 (Detalle y progreso real) → US-34 (Resultado final)

**Sprint 8 — Consenso y pago:**
US-38 (Validación por consenso) → US-39 (Pago y trust score) → US-37 (Pantalla proveedor con chunks reales)

**Sprint 9 — Calidad y cierre:**
US-40 (Tests E2E del pipeline) → validación de no-regresión → build TypeScript limpio

---

## Ampliación: Verificación de Despliegue y Placeholder de Créditos

**Versión:** 1.2
**Fecha:** 2026-07-06
**Referencia:** `briefs/05-vercel-creditos.md`

Esta sección añade al backlog dos elementos puntuales derivados del encargo de verificación de despliegue en Vercel/Railway: una user story de UI para el botón "Añadir créditos" en la cartera del proveedor (placeholder sin funcionalidad real), y una entrada de tipo chore/infraestructura para la verificación de que el proyecto sigue listo para publicarse. Ninguno de los dos introduce alcance de producto adicional al aquí descrito; no se crean épicas nuevas.

---

#### US-42 — Botón "Añadir créditos" en la cartera (placeholder)

**Prioridad:** Could Have
**Estimación:** XS (1 punto)
**Épica:** E-06 (Cartera)

**Historia:**
Como proveedor autenticado que consulta su cartera,
quiero ver un botón "Añadir créditos" junto al botón de solicitud de retiro,
para saber que en el futuro podré recargar saldo directamente, aunque hoy la función todavía no esté disponible.

**Criterios de aceptación:**

1. **Botón visible:** En la pantalla de cartera del proveedor (`WalletPage`), junto al botón "Solicitar retiro", aparece un botón "Añadir créditos" con el mismo estilo visual que el resto de acciones de la pantalla.

2. **Apertura de modal informativo:** Al pulsar el botón, se abre una ventana modal (reutilizando el componente `Modal` existente) con un mensaje que indica claramente que la función está en construcción (p. ej. "Muy pronto podrás comprar créditos. Función en construcción.") y una acción para cerrarla.

3. **Sin llamada a backend:** Pulsar el botón o interactuar con el modal no genera ninguna petición HTTP a la API. No existe ningún endpoint nuevo asociado a esta acción.

4. **Sin persistencia de estado:** No se crea, modifica ni simula ningún saldo, transacción o registro de cartera como resultado de esta interacción. Cerrar y reabrir el modal, o recargar la página, no deja rastro alguno de la interacción.

5. **No interfiere con flujos existentes:** El botón y su modal son independientes del flujo de recarga real del cliente (`POST /wallet/deposit`, brief `03-lado-cliente.md`) y del flujo de retiro del proveedor (US-17). Ninguno de los dos se ve alterado por esta historia.

6. **Cierre limpio del modal:** Tras cerrar el modal, la pantalla de cartera permanece en un estado consistente: saldos e historial de transacciones se muestran exactamente igual que antes de abrirlo.

7. **Fuera de alcance explícito:** Esta historia no incluye integración con ningún medio de pago real, backend ni persistencia. La compra real de créditos queda como funcionalidad futura, fuera de este alcance.

---

#### CH-01 — Verificación de preparación para despliegue en Vercel/Railway

**Tipo:** Chore técnico / infraestructura (no es una feature de producto)
**Prioridad:** Must Have (bloqueante para autorizar la publicación)
**Referencia:** `DEPLOY.md`, `frontend/vercel.json`, brief `04-deploy-landing.md`, brief `05-vercel-creditos.md`

**Descripción:**
Como equipo responsable de la publicación de Co-Computing,
queremos confirmar que la documentación y configuración de despliegue siguen reflejando fielmente el estado actual del producto tras las features de cómputo real y lado cliente,
para que el usuario pueda publicar en Vercel/Railway siguiendo `DEPLOY.md` sin pasos desactualizados ni sorpresas.

**Criterios de aceptación (verificación, no desarrollo nuevo):**

1. **Checklist de rutas actualizado:** El checklist final de `DEPLOY.md` incluye todas las rutas de la aplicación vigentes, incluyendo las añadidas por las features de cómputo (`/jobs/*`) y lado cliente (`/cliente/*`), no solo las del MVP original.

2. **Variables de entorno completas:** La lista de variables de entorno de Railway en `DEPLOY.md` sigue incluyendo todas las necesarias para el funcionamiento actual del backend, en particular `SUPABASE_DB_URL`, con indicación visible de qué falla si se omite.

3. **Migraciones listadas en orden:** El checklist de despliegue lista explícitamente todas las migraciones necesarias (001 a 005) en el orden correcto de ejecución.

4. **Sin bloqueantes de producto:** Ningún requisito funcional o no funcional de `docs/02-requisitos.md` impide la publicación del producto tal como está definido (MVP + ampliaciones).

5. **Confirmación explícita registrada:** Product Owner y Architect dejan constancia de que no hay nada bloqueante para publicar o, si lo hubiera, documentan el hallazgo concreto encontrado.

**Nota del Product Owner:** desde el punto de vista de requisitos de producto, no hay ningún requisito funcional o no funcional pendiente que bloquee la publicación en Vercel/Railway. Las exclusiones de alcance ya declaradas (pagos reales, WebSockets, apps móviles, panel de administración, etc.) siguen vigentes desde el MVP original y no son condición de publicación.
