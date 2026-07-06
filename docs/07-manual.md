# Co-Computing — Manual de Uso

**Version:** 1.1
**Fecha:** 2026-06-07
**Audiencia:** Usuarios finales de la plataforma (proveedores y clientes)

---

## Que es Co-Computing

Co-Computing es una plataforma web de computacion distribuida. Cualquier persona con hardware disponible puede registrarse como proveedor, aceptar tareas de procesamiento y cobrar recompensas en CC (Co-Computing Credits). A partir de la version 1.1, los clientes tambien pueden enviar trabajos de procesamiento de datos reales (CSV + operacion) que se distribuyen entre los proveedores de la red.

---

## Registro e inicio de sesion

### Registrarse

1. Abrir la plataforma en el navegador.
2. Pulsar "Crear cuenta" en la pantalla de bienvenida.
3. Rellenar nombre completo, email y contrasena (minimo 8 caracteres).
4. Pulsar "Registrarse". Si el registro es correcto, la plataforma redirige al dashboard.

Si el email ya esta registrado, aparece el mensaje "Este email ya esta registrado".
Si la contrasena tiene menos de 8 caracteres, el formulario lo indica antes de enviar.

### Iniciar sesion

1. Introducir email y contrasena en la pantalla de login.
2. Pulsar "Iniciar sesion".
3. La sesion dura 7 dias. Al recargar la pagina, la sesion se mantiene activa.

### Cerrar sesion

Pulsar el boton de cerrar sesion en la barra de navegacion. El token se elimina y la sesion queda invalidada en el dispositivo actual.

---

## Dashboard

El dashboard es la pantalla principal tras el login. Muestra:

- **Trust Score actual** y rango (nuevo, confiable, experto, elite).
- **Tareas completadas** (contador acumulado).
- **Ganancias totales** en CC.
- **Saldo disponible** de la cartera.
- **Ultimas 5 asignaciones** con su estado y recompensa.
- Enlace rapido al listado de tareas disponibles.

Los datos se recargan cada vez que se navega al dashboard.

---

## Tareas (flujo de proveedor)

### Explorar tareas disponibles

Navegar a "Tareas" en el menu. Se muestran todas las tareas con plazas disponibles, ordenadas por recompensa descendente.

**Filtros disponibles:**

| Filtro | Valores |
|--------|---------|
| Dificultad | facil, medio, dificil |
| Hardware requerido | cpu, gpu, mixto |
| Tipo de tarea | renderizado_3d, entrenamiento_ml, transcodificacion_video, analisis_datos, simulacion_fisica |
| Recompensa minima | numero positivo en CC |

Los filtros se combinan. Para quitar todos los filtros, pulsar "Limpiar filtros".

### Ver detalle de una tarea

Pulsar sobre cualquier tarea del listado. El detalle muestra titulo, descripcion completa, tipo, dificultad, hardware requerido, recompensa, duracion estimada, plazas disponibles, nombre del solicitante y lista de etapas de procesamiento.

### Aceptar una tarea

En el detalle, pulsar "Aceptar tarea". El sistema reserva una plaza. Si ya no quedan plazas, el boton aparece deshabilitado.

Solo se puede tener una asignacion activa por tarea al mismo tiempo. Si ya tienes la tarea aceptada o en procesamiento, el boton muestra "Continuar procesamiento".

### Procesar una tarea

Tras aceptar, pulsar "Iniciar procesamiento". La plataforma muestra una pantalla de progreso con:

- Barra de progreso (0 % a 99 %).
- Etapas de procesamiento con indicacion de cual esta activa.
- Boton "Completar tarea" (se activa cuando el progreso supera el 80 %).
- Boton "Reportar problema" (disponible en todo momento).

El progreso se actualiza automaticamente cada 3 segundos. Si sales de la pantalla y vuelves a `/procesando/<id>`, el estado se recupera correctamente.

### Completar una tarea

Cuando el boton "Completar tarea" esta activo, pulsarlo abre una confirmacion. Al confirmar:

- La recompensa se acredita en el saldo disponible de la cartera.
- El Trust Score se recalcula.
- Se redirige al dashboard o a la cartera.

### Reportar un problema

Pulsar "Reportar problema" en la pantalla de procesamiento. El sistema pide confirmacion e informa de que el Trust Score puede verse afectado negativamente. Al confirmar, la asignacion pasa a "fallida" y se puede volver al listado de tareas.

---

## Cartera

### Ver saldos

Navegar a "Cartera" en el menu. Se muestran cuatro saldos:

| Campo | Descripcion |
|-------|-------------|
| Saldo disponible | Listo para retirar. Se incrementa al completar tareas y al recibir pagos por chunks validos. |
| Saldo pendiente | En proceso (no activo en el MVP; siempre es 0). |
| Total ganado | Suma historica de todas las recompensas recibidas. |
| Total retirado | Suma historica de todos los retiros procesados. |

### Historial de transacciones

En la misma pantalla de cartera, debajo de los saldos. Muestra las 50 transacciones mas recientes ordenadas de mas reciente a mas antigua. Cada fila incluye fecha, tipo, descripcion, monto y estado.

Tipos de transaccion:

| Tipo | Color | Descripcion |
|------|-------|-------------|
| pago_tarea | Verde | Recompensa por completar una tarea o por chunks validos en un job distribuido |
| retiro | Rojo | Solicitud de retiro de fondos |
| bonus | Verde | Bonus aplicado manualmente |
| penalizacion | Rojo | Penalizacion aplicada manualmente |

### Solicitar un retiro

1. Pulsar "Retirar fondos" en la pantalla de cartera.
2. Introducir el monto (minimo 10 CC, no puede superar el saldo disponible).
3. Elegir el metodo de pago: transferencia bancaria (IBAN), PayPal (email) o criptomoneda (direccion de wallet).
4. Introducir el destino correspondiente al metodo elegido.
5. Revisar el resumen y confirmar.

La solicitud queda registrada con estado "pendiente". El equipo de Co-Computing la procesara y enviara el pago al destino indicado. El monto se deduce inmediatamente del saldo disponible.

### Anadir creditos (proximamente)

Junto a "Retirar fondos" hay un boton "Anadir creditos". Por ahora solo muestra un aviso informativo: la compra de creditos con tarjeta o PayPal todavia no esta disponible. Mientras tanto, el saldo solo se incrementa completando tareas o chunks del pipeline distribuido.

---

## Perfil

### Ver y editar el perfil

Navegar a "Perfil" en el menu. La pantalla muestra:

- Nombre completo (editable).
- Email (solo lectura).
- Fecha de registro.
- Tasa de exito (% de tareas completadas sobre el total de tareas finalizadas).
- Estado online (toggle).

Para editar el nombre, modificar el campo y pulsar "Guardar cambios".

### Toggle de estado online

El toggle "Disponible" en la pantalla de perfil actualiza el campo `is_online` en el backend. Cambiar el estado indica a la plataforma si estas disponible para recibir tareas. El cambio se refleja inmediatamente.

### Hardware registrado

En la misma pantalla de perfil, debajo de los datos personales. Campos:

- CPU (texto, obligatorio): modelo de CPU.
- GPU (texto, opcional): modelo de GPU. Si no tienes GPU dedicada, dejar vacio.
- RAM en GB (numero entero, obligatorio): minimo 1.
- Almacenamiento en GB (numero entero, obligatorio): minimo 1.

Pulsar "Guardar hardware" para persistir los cambios.

---

## Trust Score

El Trust Score es la puntuacion de confianza del proveedor. Se calcula con la formula:

```
trust_score = (completion_rate * 0.40) + (accuracy * 0.30)
            + (response_time_score * 0.20) + (client_rating * 0.10)
```

Todos los componentes tienen rango 0-100. El resultado se limita a 0-100.

### Rangos

| Rango | Trust Score |
|-------|-------------|
| nuevo | 0 a 49 |
| confiable | 50 a 74 |
| experto | 75 a 89 |
| elite | 90 a 100 |

### Como sube el Trust Score

- Completar una tarea: `accuracy` sube 2 puntos. Si iniciaste la tarea en menos de 10 minutos desde la aceptacion, `response_time_score` sube 5 puntos.
- Chunk valido (pipeline distribuido): `accuracy` sube 2 puntos.

### Como baja el Trust Score

- Fallar una tarea: `accuracy` baja 5 puntos. Si tardaste mas de 60 minutos en iniciar desde la aceptacion, `response_time_score` baja 5 puntos.
- Chunk invalido (resultado rechazado por consenso): `accuracy` baja 5 puntos.

El desglose completo de cada componente y el rango siguiente se muestran en la seccion "Trust Score" del perfil.

---

## Computo Real Distribuido (Jobs)

Esta funcionalidad permite enviar trabajos de procesamiento de datos que son ejecutados de forma real y distribuida por los proveedores de la red.

### Enviar un nuevo trabajo

1. Navegar a "Mis trabajos" en el menu y pulsar "Nuevo trabajo", o acceder directamente a `/jobs/new`.
2. Subir un archivo CSV (hasta 10 MB). El archivo debe tener cabecera en la primera fila.
3. Seleccionar la operacion a aplicar: `mean` (media), `sum` (suma), `min`, `max` o `count`.
4. Seleccionar las columnas sobre las que aplicar la operacion. Al menos una columna debe estar seleccionada.
5. Revisar la estimacion de recompensa total (0,10 CC por chunk).
6. Pulsar "Enviar trabajo".

Si el envio es correcto, la plataforma redirige a "Mis trabajos" con un mensaje de confirmacion.

Errores posibles:

| Error | Causa |
|-------|-------|
| "El archivo CSV no contiene datos validos" | El CSV esta vacio, no tiene cabecera o las filas estan malformadas |
| "El archivo CSV no puede superar 10 MB" | El archivo es demasiado grande |
| "Tipo de job no soportado" | Solo se acepta `data-processing` en el MVP |

### Ver mis trabajos

Navegar a "Mis trabajos" (`/jobs`). La lista muestra todos los trabajos enviados, con:

- Identificador corto (primeros 8 caracteres del UUID).
- Fecha de creacion.
- Operacion y columnas solicitadas.
- Estado con badge de color.
- Barra de progreso real (chunks validados / total).

El estado de la lista se actualiza automaticamente cada 5 segundos mientras haya algun trabajo en curso. Al alcanzar el estado terminal (`completed` o `failed`), el polling se detiene.

**Estados posibles:**

| Estado | Badge | Significado |
|--------|-------|-------------|
| pending | Gris | El job fue recibido pero aun no se ha trocedo |
| splitting | Naranja | El backend esta dividiendo el CSV en chunks |
| processing | Azul | Los workers estan procesando los chunks |
| validating | Amarillo | Los resultados estan siendo validados por consenso |
| completed | Verde | Todos los chunks estan validados; resultado disponible |
| failed | Rojo | El job no pudo completarse |

Pulsar sobre cualquier trabajo lleva al detalle.

### Ver el detalle de un trabajo

La pantalla de detalle (`/jobs/:id`) muestra:

- Estado actual y porcentaje de progreso.
- Numero de chunks completados y total.
- Fecha de creacion y operacion solicitada.

El progreso se actualiza cada 5 segundos mientras el job no esta en estado terminal. Cuando el job pasa a `completed`, aparece automaticamente un banner con el boton "Ver resultado". Si el job pasa a `failed`, aparece un mensaje con la opcion de crear un nuevo trabajo con los mismos parametros.

### Ver el resultado

La pantalla de resultado (`/jobs/:id/result`) muestra:

- Tabla con los valores calculados por columna.
- Metadatos: fecha de completado, numero de chunks procesados, numero de proveedores participantes y recompensa total pagada.
- Boton "Descargar resultado (JSON)" que descarga el fichero `resultado_<id_corto>.json`.

El resultado solo esta disponible cuando el job tiene estado `completed`. Si se accede antes, la plataforma muestra "El resultado aun no esta disponible".

---

## Uso como proveedor de computo (Worker CLI)

Si quieres contribuir capacidad de computo al pipeline distribuido y ganar recompensas por procesar chunks, puedes lanzar el worker desde la linea de comandos.

### Requisitos

- Python 3.12 o superior con el entorno virtual del backend activado.
- Dependencia `polars` instalada (incluida en `requirements.txt` del backend).
- Una cuenta de proveedor registrada en la plataforma.

### Arrancar el worker

```bash
cd backend
python -m app.worker --api http://localhost:8000 --email tu@email.com --password tupassword
```

El worker realiza las siguientes operaciones de forma continua hasta que se detiene con `Ctrl+C`:

1. Se autentica con `POST /auth/login` usando las credenciales indicadas.
2. Llama a `POST /work/claim` para reclamar chunks pendientes.
3. Procesa cada chunk con polars segun la operacion indicada en el payload.
4. Envia el resultado con `POST /work/{chunk_id}/submit`.
5. Si no hay chunks disponibles, espera 5 segundos y reintenta.

El worker registra en la consola cada operacion relevante con timestamp ISO 8601 y nivel de log (INFO, WARNING, ERROR). Las contrasenas y el contenido de los chunks no se registran.

### Lanzar multiples workers

Para la demo de distribucion, el script `scripts/run_workers.sh` lanza varias instancias en paralelo. Editar el script para configurar las credenciales y el numero de instancias.

```bash
bash scripts/run_workers.sh
```

### Recompensas del worker

Cada chunk validado como correcto por consenso acredita `reward_per_chunk = reward_total / total_chunks` CC en la cartera del proveedor. Los chunks cuyo resultado es rechazado (discrepante con la mayoria) no generan pago y reducen el `accuracy` del trust score.

Las recompensas aparecen en el historial de transacciones de la cartera con descripcion "Pago por job <id_corto> - N chunks validos".

### Advertencia de seguridad

El worker ejecuta computo sobre payloads recibidos de la API sin aislamiento de seguridad. No ejecutar el worker conectado a una API de origen desconocido. Ver la nota de seguridad en el README del repositorio.

---

## Preguntas frecuentes

**No veo ninguna tarea disponible.**
Asegurate de no tener filtros activos. Pulsa "Limpiar filtros". Si el problema persiste, puede que no haya tareas disponibles en este momento o que el seed de tareas no se haya ejecutado en el entorno.

**Mi barra de progreso llego al 99 % y no avanza.**
El progreso se detiene en 99 % hasta que pulsas "Completar tarea". Esto es intencionado: el sistema requiere confirmacion manual para registrar la tarea como completada y acreditar la recompensa.

**El job aparece en estado "processing" pero no avanza.**
Es necesario que al menos un worker este activo y conectado al mismo backend. Arranca el worker CLI con tus credenciales de proveedor.

**Un chunk queda en estado "assigned" y el job no progresa.**
Si el worker que reclamo ese chunk se desconecto antes de enviar el resultado, el chunk queda bloqueado. Workaround: actualizar el `status` del chunk a `pending` directamente en el SQL Editor de Supabase para que otro worker pueda reclamarlo.

**No veo el resultado en /jobs/:id/result aunque el job dice "completed".**
Asegurate de estar autenticado con la misma cuenta que creo el job. El endpoint devuelve 403 si accedes con otra cuenta.

**Quiero retirar mis fondos pero el boton esta desactivado.**
El monto minimo de retiro es 10 CC. Asegurate de tener al menos ese saldo disponible.
