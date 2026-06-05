# Co-Computing — Requisitos del Producto (MVP)

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** Product Owner
**Referencias:** `docs/00-vision.md`, `docs/01-stack.md`, `briefs/co-computing.md`

---

## 1. Introducción y Alcance

Este documento describe los requisitos funcionales y no funcionales del MVP de Co-Computing. Define qué debe hacer el sistema y cómo se sabe que cada funcionalidad está correctamente implementada. No prescribe tecnologías ni decisiones de diseño visual: esas responsabilidades pertenecen al CTO y al UX/UI Designer respectivamente.

El usuario objetivo es el **Proveedor de Cómputo**: persona con hardware potente infrautilizado que quiere ingresos pasivos sin conocimientos técnicos avanzados. Cada requisito debe poder ser evaluado directamente frente a las necesidades de este perfil.

---

## 2. Requisitos Funcionales

### RF-01: Registro de Proveedor

**Descripción:** El sistema permite a una persona nueva crear una cuenta de proveedor proporcionando nombre completo, dirección de email y contraseña.

**Reglas de negocio:**
- El email debe ser único en el sistema. No pueden existir dos cuentas con el mismo email.
- La contraseña debe tener un mínimo de 8 caracteres.
- Al registrarse, se crea automáticamente un registro de proveedor con Trust Score inicial de 0, rango "nuevo", tareas completadas = 0, y ganancias = 0.
- Se crea automáticamente una cartera (wallet) asociada con todos los saldos a cero.
- El estado `is_online` inicial es `false`.
- No se envía email de verificación en el MVP. El registro es inmediato y operativo.

**Criterios de aceptación:**
- Dado un email no registrado, nombre válido y contraseña de 8 o más caracteres, el sistema crea la cuenta y devuelve confirmación de éxito.
- Dado un email ya registrado, el sistema devuelve un error claro indicando que el email ya existe, sin crear duplicados.
- Dada una contraseña de menos de 8 caracteres, el sistema rechaza el registro con un mensaje de error que indica el requisito mínimo.
- Dado un email con formato inválido (sin @, sin dominio), el sistema rechaza el registro con error de validación.
- Dado un nombre vacío, el sistema rechaza el registro.
- El password nunca se almacena en texto plano; se almacena su hash bcrypt.

---

### RF-02: Inicio de Sesión

**Descripción:** El proveedor registrado puede autenticarse con su email y contraseña para obtener acceso a la plataforma.

**Reglas de negocio:**
- La autenticación devuelve un JSON Web Token (JWT) firmado con HS256 y expiración de 7 días.
- El token contiene el identificador del proveedor como claim `sub`.
- No existe mecanismo de "recordar sesión" diferenciado: todos los tokens duran 7 días.
- No existe límite de intentos fallidos en el MVP, pero los errores no revelan si el email existe o no.

**Criterios de aceptación:**
- Dado un email y contraseña correctos, el sistema devuelve un JWT válido y los datos básicos del proveedor (nombre, email, trust_score, rango).
- Dado un email correcto con contraseña incorrecta, el sistema devuelve error 401 con mensaje genérico "Credenciales incorrectas".
- Dado un email no registrado, el sistema devuelve error 401 con el mismo mensaje genérico (no revela si el email existe).
- El token devuelto puede usarse en las siguientes 7 días para acceder a todos los endpoints protegidos.
- Un token expirado o manipulado es rechazado con error 401 en cualquier endpoint protegido.

---

### RF-03: Consulta del Proveedor Autenticado

**Descripción:** El sistema expone un endpoint que devuelve los datos del proveedor actualmente autenticado a partir de su token JWT.

**Reglas de negocio:**
- Solo accesible con token válido.
- Devuelve todos los datos del perfil del proveedor: identificador, nombre, email, trust_score, rango, tareas_completadas, tasa_de_exito, hardware registrado, estado online.

**Criterios de aceptación:**
- Con token válido, el sistema devuelve los datos actualizados del proveedor autenticado.
- Con token inválido o ausente, el sistema devuelve 401.

---

### RF-04: Dashboard del Proveedor

**Descripción:** Pantalla principal del proveedor autenticado que muestra un resumen de su estado actual y actividad reciente.

**Datos a mostrar:**
- Trust Score actual (número de 0 a 100).
- Rango actual (nuevo / confiable / experto / élite).
- Número total de tareas completadas.
- Ganancias totales acumuladas (en la moneda del sistema, con dos decimales).
- Saldo disponible en cartera.
- Listado de las 5 tareas más recientes procesadas por el proveedor (las últimas asignaciones con sus estados).

**Reglas de negocio:**
- Los datos del dashboard se obtienen en tiempo real desde el backend al cargar la pantalla.
- Si el proveedor no tiene ninguna tarea procesada, el listado de tareas recientes aparece vacío con un mensaje orientativo.

**Criterios de aceptación:**
- El dashboard muestra el Trust Score, rango, número de tareas completadas y ganancias totales del proveedor autenticado.
- El dashboard muestra el saldo disponible de la cartera.
- El dashboard muestra las últimas 5 asignaciones del proveedor con título de tarea, estado de la asignación y recompensa.
- Si no existen asignaciones previas, el listado muestra un mensaje del tipo "Aún no has procesado ninguna tarea".
- La pantalla tiene estado de carga visible mientras se obtienen los datos.
- Si la llamada al backend falla, se muestra un mensaje de error sin dejar la pantalla en blanco.

---

### RF-05: Listado de Tareas Disponibles

**Descripción:** El proveedor puede explorar el catálogo de tareas disponibles en la plataforma aplicando filtros para encontrar las que se adaptan a su hardware y preferencias.

**Datos a mostrar por tarea en el listado:**
- Título de la tarea.
- Tipo de tarea (renderizado 3D, entrenamiento ML, transcodificación de video, análisis de datos, simulación física u otros).
- Dificultad (fácil / medio / difícil).
- Hardware requerido (cpu / gpu / mixto).
- Recompensa en la moneda del sistema.
- Duración estimada (rango en minutos).
- Plazas disponibles restantes.

**Filtros disponibles:**
- **Dificultad:** fácil / medio / difícil (selección única o múltiple).
- **Hardware requerido:** cpu / gpu / mixto (selección única o múltiple).
- **Tipo de tarea:** lista de tipos únicos presentes en la base de datos.
- **Recompensa mínima:** valor numérico introducido por el proveedor; filtra tareas con recompensa mayor o igual al valor indicado.

**Reglas de negocio:**
- Solo se muestran tareas con estado "disponible" y plazas mayores que cero.
- Los filtros son acumulativos (AND entre filtros distintos).
- Sin ningún filtro activo, se muestran todas las tareas disponibles.
- El listado no tiene paginación en el MVP si el número de tareas seed es manejable (hasta 20 tareas); si se supera ese número, se puede limitar a las 50 primeras ordenadas por recompensa descendente.

**Criterios de aceptación:**
- El listado muestra todas las tareas con estado "disponible" y plazas > 0 cuando no hay filtros activos.
- Al aplicar filtro de dificultad "fácil", solo aparecen tareas con dificultad "fácil".
- Al aplicar filtro de hardware "gpu", solo aparecen tareas que requieren gpu.
- Al aplicar una recompensa mínima de 5, solo aparecen tareas con recompensa >= 5.
- Los filtros se pueden combinar y el resultado es la intersección de todos los activos.
- Existe un botón o acción para limpiar todos los filtros y volver al listado completo.
- Si no hay tareas que cumplan los filtros, se muestra un mensaje indicativo (no una pantalla en blanco).
- La pantalla tiene estado de carga visible durante la obtención de datos.
- Si la llamada falla, se muestra mensaje de error.

---

### RF-06: Detalle de Tarea

**Descripción:** El proveedor puede ver toda la información de una tarea específica antes de decidir aceptarla.

**Datos a mostrar:**
- Título.
- Descripción completa.
- Tipo de tarea.
- Dificultad.
- Hardware requerido.
- Recompensa exacta.
- Duración estimada (mínima y máxima en minutos).
- Plazas disponibles totales y restantes.
- Nombre o alias del solicitante (empresa o persona que publicó la tarea; dato de la tabla `tasks`).
- Estado de la tarea.
- Etapas de procesamiento (lista de nombres de etapas que se ejecutarán).

**Reglas de negocio:**
- Si la tarea no existe o no está disponible, se muestra error 404 con mensaje claro.
- Si el proveedor ya tiene esta tarea en estado "aceptada" o "procesando", el botón de acción muestra "Ir a procesamiento" en lugar de "Aceptar".
- Si la tarea no tiene plazas disponibles (slots_left = 0), el botón de aceptar aparece deshabilitado con un mensaje "Sin plazas disponibles".

**Criterios de aceptación:**
- Dado un ID de tarea válida y disponible, la pantalla muestra todos los campos descritos.
- Dado un ID inexistente, la pantalla muestra un mensaje de error 404.
- Si la tarea tiene plazas disponibles, aparece el botón "Aceptar tarea" activo.
- Si la tarea no tiene plazas disponibles, el botón aparece deshabilitado con indicación de "Sin plazas".
- Si el proveedor ya tiene esta tarea aceptada o en progreso, se muestra el botón "Continuar" o "Ir a procesamiento".

---

### RF-07: Ciclo de Vida de Asignación de Tarea

**Descripción:** El proveedor puede realizar todas las transiciones del ciclo de vida de una asignación: aceptar, iniciar, completar y reportar fallo.

**Estados de la asignación y transiciones válidas:**
```
[Sin asignación] → aceptada → procesando → completada
                                          → fallida
              → cancelada (desde aceptada, antes de iniciar)
```

**RF-07a: Aceptar tarea**
- Crea una nueva asignación con estado "aceptada".
- Decrementa en 1 el campo `slots_left` de la tarea.
- Si `slots_left` ya era 0, devuelve error 400 "No quedan plazas disponibles".
- Un proveedor no puede aceptar la misma tarea dos veces si ya tiene una asignación activa (aceptada o procesando).

**RF-07b: Iniciar tarea**
- Transiciona la asignación de "aceptada" a "procesando".
- Registra el timestamp `started_at` en la asignación.
- Devuelve el número de etapas simuladas para esa tarea y el identificador de la asignación.
- Solo el proveedor dueño de la asignación puede iniciarla.

**RF-07c: Completar tarea**
- Transiciona la asignación de "procesando" a "completada".
- Registra el timestamp `completed_at`.
- Acredita la recompensa de la tarea en el saldo disponible de la cartera del proveedor.
- Crea una transacción de tipo "pago_tarea" en el historial de la cartera.
- Incrementa en 1 el contador `tasks_completed` del proveedor.
- Recalcula el Trust Score del proveedor aplicando la fórmula ponderada.
- Actualiza el rango del proveedor según el nuevo Trust Score.

**RF-07d: Reportar fallo**
- Transiciona la asignación de "procesando" a "fallida".
- Registra el timestamp de fallo.
- No acredita recompensa.
- Puede aplicar una penalización al Trust Score (trust_delta negativo).
- Recalcula el Trust Score y el rango del proveedor.

**Criterios de aceptación:**
- Un proveedor autenticado puede aceptar una tarea disponible con plazas; el sistema responde con los datos de la asignación creada.
- Intentar aceptar una tarea sin plazas devuelve error 400.
- Un proveedor no puede aceptar la misma tarea si ya tiene una asignación activa para ella.
- Iniciar una asignación aceptada cambia el estado a "procesando" y registra `started_at`.
- Solo el proveedor dueño puede ejecutar las transiciones de su asignación; otro proveedor recibe 403.
- Completar una asignación en estado "procesando" acredita la recompensa en la cartera y actualiza `tasks_completed` y el Trust Score.
- Fallar una asignación en estado "procesando" no acredita recompensa y puede reducir el Trust Score.
- No se puede completar o fallar una asignación que no está en estado "procesando".
- No se pueden realizar transiciones desde estados terminales (completada, fallida, cancelada).

---

### RF-08: Pantalla de Progreso de Procesamiento

**Descripción:** Mientras una asignación está en estado "procesando", el proveedor ve una pantalla que muestra el progreso por etapas de forma visual y actualizada.

**Comportamiento:**
- El progreso se actualiza automáticamente cada 3 segundos mediante polling al backend.
- El backend calcula el porcentaje de progreso en función del tiempo transcurrido desde `started_at` y la duración estimada de la tarea: `progreso = min((tiempo_transcurrido / duracion_estimada_segundos) * 100, 99)`.
- El progreso nunca alcanza el 100% automáticamente. Se detiene en 99% esperando la acción del proveedor.
- Las etapas de procesamiento se derivan del porcentaje de progreso y los nombres de etapas definidos en la tarea.
- El proveedor puede pulsar "Completar tarea" cuando considere que el proceso ha terminado. El botón aparece habilitado una vez que el progreso supera el 80%.
- El proveedor puede reportar un fallo mediante un botón "Reportar problema" disponible en todo momento.
- Al abandonar la pantalla (navegación) y volver, el sistema recupera el estado actual del progreso.

**Criterios de aceptación:**
- La pantalla muestra el nombre de la tarea en proceso y el porcentaje de progreso actual.
- La barra de progreso o indicador visual se actualiza cada 3 segundos sin recargar la página.
- Las etapas de procesamiento se muestran en orden con indicación de cuál está activa, cuáles han completado y cuáles están pendientes.
- El progreso nunca supera el 99% de forma automática.
- El botón "Completar tarea" aparece habilitado cuando el progreso alcanza o supera el 80%.
- Pulsar "Completar tarea" llama al endpoint de completar, actualiza la cartera y redirige al dashboard o pantalla de éxito.
- Pulsar "Reportar problema" llama al endpoint de fallo y redirige con mensaje informativo.
- Si se abandona la pantalla y se regresa con la asignación aún en progreso, la pantalla retoma el progreso actual sin reiniciarlo.
- Si la asignación ya fue completada o falló (procesada en otra pestaña), la pantalla redirige correctamente.

---

### RF-09: Cartera (Wallet)

**Descripción:** El proveedor tiene acceso a su cartera donde puede consultar sus saldos y el historial completo de transacciones, y solicitar el retiro de fondos disponibles.

#### RF-09a: Consulta de Saldos

**Datos a mostrar:**
- Saldo disponible: fondos listos para retirar.
- Saldo pendiente: fondos de tareas completadas en proceso de liquidación (puede ser 0 en el MVP simplificado).
- Total ganado: suma histórica de todos los pagos recibidos.
- Total retirado: suma histórica de todos los retiros solicitados.

**Criterios de aceptación:**
- La cartera muestra los cuatro saldos con dos decimales.
- Los saldos reflejan las operaciones recientes sin necesidad de recargar manualmente.

#### RF-09b: Historial de Transacciones

**Datos a mostrar por transacción:**
- Fecha y hora.
- Tipo (pago_tarea / retiro / bonus / penalizacion).
- Descripción legible en español.
- Monto (positivo para ingresos, negativo para retiros/penalizaciones).
- Estado de la transacción.

**Reglas de negocio:**
- Las transacciones se ordenan de más reciente a más antigua.
- El historial muestra un máximo de 50 transacciones en el MVP. Si hay más, se muestran las 50 más recientes.

**Criterios de aceptación:**
- El historial muestra todas las transacciones del proveedor autenticado en orden cronológico inverso.
- Cada transacción muestra tipo, descripción, monto y fecha.
- Si no hay transacciones, se muestra mensaje "No tienes transacciones aún".

#### RF-09c: Solicitud de Retiro

**Descripción:** El proveedor puede solicitar el retiro del saldo disponible eligiendo el método de destino.

**Métodos disponibles:**
- Transferencia bancaria (requiere IBAN o número de cuenta).
- PayPal (requiere email de PayPal).
- Criptomoneda (requiere dirección de wallet).

**Reglas de negocio:**
- El monto de retiro no puede superar el saldo disponible.
- El monto mínimo de retiro es 10 unidades de moneda.
- Al confirmar el retiro, se crea una transacción de tipo "retiro" con estado "pendiente".
- El saldo disponible se reduce en el monto solicitado inmediatamente al confirmar.
- El retiro no se ejecuta realmente (MVP); queda registrado como solicitud pendiente.

**Criterios de aceptación:**
- El proveedor puede seleccionar un método de retiro y especificar el destino.
- Si el monto solicitado supera el saldo disponible, el sistema rechaza la solicitud con mensaje claro.
- Si el monto es inferior al mínimo (10 unidades), el sistema rechaza con mensaje de mínimo requerido.
- Una solicitud válida crea la transacción de retiro, reduce el saldo disponible y muestra confirmación de solicitud registrada.
- El historial de transacciones refleja inmediatamente la nueva solicitud de retiro.

---

### RF-10: Perfil del Proveedor

**Descripción:** El proveedor puede consultar y editar su perfil, ver el desglose de su Trust Score, gestionar su hardware registrado y cambiar su estado de disponibilidad.

#### RF-10a: Datos del Perfil

**Datos a mostrar:**
- Nombre completo (editable).
- Email (solo lectura).
- Fecha de registro.
- Estado online (toggle editable).
- Tasa de éxito (porcentaje de tareas completadas sobre total aceptadas).

**Criterios de aceptación:**
- El proveedor puede actualizar su nombre completo. El cambio se persiste.
- El email no es editable.
- El toggle de estado online actualiza el campo `is_online` en base de datos inmediatamente.
- La tasa de éxito se calcula y muestra con un decimal de precisión.

#### RF-10b: Hardware Registrado

**Descripción:** El proveedor puede registrar o actualizar las especificaciones de su hardware.

**Campos:**
- Modelo de CPU (texto libre, obligatorio).
- Modelo de GPU (texto libre, opcional).
- RAM en GB (número entero positivo, obligatorio).
- Almacenamiento en GB (número entero positivo, obligatorio).

**Criterios de aceptación:**
- El proveedor puede rellenar o actualizar todos los campos de hardware.
- El campo RAM y almacenamiento solo aceptan números enteros mayores que cero.
- Al guardar, los datos se persisten y se muestran actualizados al recargar el perfil.
- El modelo de GPU puede estar vacío (proveedor solo con CPU).

#### RF-10c: Trust Score con Desglose

**Descripción:** El perfil muestra el Trust Score actual del proveedor con el desglose de cada componente de la fórmula.

**Datos a mostrar:**
- Trust Score total (0-100).
- Rango actual con descripción del rango.
- Valor de cada componente:
  - Tasa de completado (`completion_rate`, peso 40%).
  - Precisión (`accuracy`, peso 30%).
  - Tiempo de respuesta (`response_time`, peso 20%).
  - Valoración de cliente (`client_rating`, peso 10%).
- Indicación del rango siguiente y puntos necesarios para alcanzarlo (si no es élite).

**Criterios de aceptación:**
- Los cuatro componentes del Trust Score se muestran con su valor y peso porcentual.
- La suma ponderada de los componentes coincide con el Trust Score total mostrado (tolerancia ±0.01).
- Se muestra el rango actual y, si no es élite, el rango siguiente con el delta necesario.

---

### RF-11: Sistema de Trust Score

**Descripción:** El sistema calcula y mantiene actualizado el Trust Score de cada proveedor usando una fórmula ponderada.

**Fórmula:**
```
trust_score = (completion_rate * 0.40) + (accuracy * 0.30) + (response_time * 0.20) + (client_rating * 0.10)
```

Todos los componentes son valores entre 0 y 100.

**Rangos:**
| Rango | Rango de puntuación |
|-------|---------------------|
| nuevo | 0 – 49 |
| confiable | 50 – 74 |
| experto | 75 – 89 |
| élite | 90 – 100 |

**Definición de componentes:**
- `completion_rate`: porcentaje de asignaciones completadas sobre el total de asignaciones finalizadas (completadas + fallidas). Si no hay asignaciones finalizadas, vale 0.
- `accuracy`: en el MVP, se inicializa a 80 y se reduce en 5 puntos por cada asignación fallida y se incrementa en 2 puntos por cada asignación completada, con un techo de 100 y un suelo de 0.
- `response_time`: tiempo medio de respuesta desde que se acepta una tarea hasta que se inicia. Cuanto menor el tiempo, mayor la puntuación. En el MVP se inicializa a 70 y se ajusta en ±5 según si el inicio fue rápido (< 10 minutos) o tardío (> 60 minutos).
- `client_rating`: en el MVP, sin valoraciones explícitas de clientes, se inicializa a 70 y no cambia hasta que exista el módulo de valoraciones.

**Reglas de negocio:**
- El Trust Score se recalcula cada vez que una asignación transiciona a estado "completada" o "fallida".
- El Trust Score se almacena con dos decimales.
- El rango se actualiza automáticamente al recalcular el Trust Score.
- El campo `trust_delta` en `task_assignments` registra el cambio en Trust Score producido por esa asignación (positivo o negativo).

**Criterios de aceptación:**
- Al completar una tarea, el Trust Score del proveedor aumenta de forma consistente con la fórmula.
- Al fallar una tarea, el Trust Score del proveedor puede disminuir de forma consistente con la fórmula.
- Un proveedor que completa suficientes tareas pasa de rango "nuevo" a "confiable" y el sistema lo refleja en su perfil y dashboard.
- El Trust Score nunca supera 100 ni baja de 0.
- El trust_delta de cada asignación refleja la diferencia real entre el Trust Score antes y después del recálculo.
- Los tests del servicio `trust_score.py` validan la fórmula con valores conocidos y comprueban que la suma ponderada es correcta.

---

## 3. Requisitos No Funcionales

### RNF-01: Seguridad

| Aspecto | Requisito |
|---------|-----------|
| Contraseñas | Almacenadas exclusivamente como hash bcrypt con cost factor >= 12. Nunca en texto plano, nunca en logs. |
| JWT | HS256, firmado con clave secreta de mínimo 32 caracteres. Expiración de 7 días. Validado en todos los endpoints protegidos mediante dependencia de FastAPI. |
| CORS | El origen permitido es exclusivamente el valor de la variable de entorno `FRONTEND_URL`. Nunca `"*"` en producción. |
| Row Level Security | RLS activado en todas las tablas de Supabase. Cada proveedor solo accede a sus propios registros de `task_assignments`, `wallets` y `transactions`. Las tareas son de lectura pública para proveedores autenticados. |
| Secretos | Ninguna credencial, clave de API ni secret en el código fuente o ficheros commiteados. Todo via variables de entorno gestionadas con `pydantic-settings`. |
| Validación de inputs | Todos los request bodies validados con Pydantic v2. Ningún parámetro de query sin tipado. |
| SQL injection | Cero interpolación directa de strings en queries. Uso exclusivo de parámetros del SDK de Supabase o queries parametrizadas de psycopg2. |
| Headers de seguridad | `X-Content-Type-Options: nosniff` y `X-Frame-Options: DENY` presentes en todas las respuestas del backend. |

**Criterio de aceptación de bloque:** La revisión de seguridad detecta 0 vulnerabilidades críticas (secretos expuestos, JWT sin validar, CORS abierto, SQL injection).

---

### RNF-02: Rendimiento

| Aspecto | Requisito |
|---------|-----------|
| Tiempo de respuesta | El 95% de las peticiones a endpoints de lectura responden en menos de 500ms bajo carga normal (un solo usuario en desarrollo local). |
| Polling de progreso | El endpoint `GET /tasks/assignments/{id}/progress` responde en menos de 200ms para no degradar la experiencia de la pantalla de procesamiento. |
| Cold start local | El proyecto completo (backend + frontend + seed) arranca en menos de 5 minutos siguiendo el README. |

---

### RNF-03: Usabilidad

| Aspecto | Requisito |
|---------|-----------|
| Idioma | Toda la interfaz de usuario en español. Ningún texto visible en inglés, incluyendo mensajes de error, estados y etiquetas. |
| Estados de interfaz | Toda operación asíncrona expone tres estados: cargando, éxito y error. Ninguna pantalla puede quedar en blanco sin feedback. |
| Mensajes de error | Los errores se muestran en lenguaje llano y orientado al usuario, sin códigos de error técnicos ni stack traces. |
| Accesibilidad mínima | Los formularios tienen etiquetas (`label`) asociadas a sus inputs. Los botones tienen texto descriptivo o `aria-label`. El contraste de texto sobre fondo cumple WCAG 2.1 nivel AA. |

---

### RNF-04: Mantenibilidad y Calidad de Código

| Aspecto | Requisito |
|---------|-----------|
| Tests de backend | 100% de los endpoints principales cubiertos por tests automatizados (pytest). Cobertura mínima de líneas del 80% sobre `app/`. |
| Tests de frontend | Los hooks `useAuth` y `useTaskProgress`, los stores de Zustand y los componentes `TrustScoreBreakdown`, `TaskFilters` y `ProgressStepper` tienen tests con Vitest. |
| Linting | El código Python pasa `ruff check` sin errores. El código TypeScript/React pasa ESLint sin errores ni warnings. |
| Sin placeholders | No existe ningún `TODO`, `FIXME`, `pass` sin implementar, ni dato hardcodeado que debería ser dinámico en el código entregado. |
| Tipos | El backend usa type hints en todas las funciones. El frontend usa TypeScript estricto (`strict: true`) sin ningún `any` explícito. |

---

### RNF-05: Operabilidad

| Aspecto | Requisito |
|---------|-----------|
| README | Contiene instrucciones completas de arranque local ejecutables en menos de 5 minutos. |
| Variables de entorno | Existe `.env.example` documentado en `backend/` y `frontend/` con todas las variables requeridas y descripción de cada una. |
| Seed | El script `python backend/scripts/seed.py` es idempotente y puebla la tabla `tasks` con 15-20 tareas representativas. |
| Schema | Existen ficheros `backend/app/db/schema.sql` y `backend/app/db/rls_policies.sql` ejecutables en el SQL editor de Supabase. |

---

## 4. Restricciones y Fuera de Alcance

Las siguientes funcionalidades están explícitamente fuera del MVP y no deben ser desarrolladas ni parcialmente implementadas:

- Integración de pagos reales (Stripe o cualquier procesador). Los retiros se registran como solicitudes sin ejecutar ninguna transferencia real.
- Ejecución real de cómputo distribuido. El procesamiento se simula con cálculo de progreso basado en tiempo transcurrido.
- Aplicación móvil nativa (iOS / Android).
- Panel de administración back-office.
- Sistema de notificaciones push o por email.
- Lado "cliente que sube tareas". Las tareas existen únicamente como datos de seed.
- Internacionalización a idiomas distintos del español.
- Detección automática de hardware del proveedor (el hardware es autodeclarado).
- Sistema de heartbeat para estado online (el estado es un toggle manual).
- Valoraciones explícitas de clientes (el componente `client_rating` del Trust Score es fijo en 70 en el MVP).

---

## 5. Glosario

| Término | Definición |
|---------|-----------|
| Proveedor | Usuario registrado que procesa tareas y cobra recompensas. |
| Tarea | Unidad de trabajo de cómputo disponible para ser aceptada por proveedores. |
| Asignación | Relación entre un proveedor y una tarea específica en un estado determinado. |
| Trust Score | Puntuación de confianza del proveedor (0-100) calculada mediante fórmula ponderada. |
| Rango | Categoría del proveedor derivada del Trust Score: nuevo / confiable / experto / élite. |
| Cartera (Wallet) | Registro financiero del proveedor con saldos y movimientos. |
| Seed | Datos iniciales de prueba insertados en base de datos para hacer la plataforma demostrable. |
| Slot | Plaza disponible en una tarea. Cada proveedor que acepta una tarea consume un slot. |
