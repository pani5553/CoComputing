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
