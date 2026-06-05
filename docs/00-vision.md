# Co-Computing — Visión del Producto

**Versión:** 1.0  
**Fecha:** 2026-06-05  
**Autor:** CEO / Definición de Producto

---

## 1. Propuesta de Valor

Co-Computing convierte el hardware doméstico infrautilizado en una fuente de ingresos pasivos, eliminando por completo la fricción técnica que hoy aleja a personas no especializadas de los mercados de cómputo distribuido.

Un proveedor con una workstation o un PC gamer potente puede unirse a la red, elegir tareas según su capacidad de hardware y cobrar por el trabajo completado, todo desde una interfaz web en español que no exige ningún conocimiento de cloud, blockchain ni DevOps. La confianza es el activo central: un Trust Score transparente y un sistema de rangos progresivo (Nuevo → Confiable → Experto → Elite) premian la fiabilidad y dan al proveedor una trayectoria de crecimiento visible.

**El problema que resolvemos:** existe una enorme capacidad de cómputo ociosa en hogares y estudios que hoy no puede monetizarse porque las plataformas existentes son técnicamente hostiles o exigen infraestructura especializada.

**La solución diferenciadora:** experiencia radicalmente sencilla, feedback inmediato, reputación cuantificada y cartera de ganancias gestionable desde el navegador.

---

## 2. Usuarios Objetivo y sus Motivaciones

### Usuario principal del MVP: el Proveedor de Cómputo

| Perfil | Descripción |
|--------|-------------|
| Arquetipo | Persona con PC gamer, workstation de diseño o servidor casero que permanece encendido muchas horas al día con capacidad ociosa. |
| Conocimiento técnico | Básico-medio: sabe instalar software, entiende conceptos como CPU/GPU/RAM, pero no administra servidores ni usa APIs. |
| Motivación principal | Ingresos pasivos sin esfuerzo continuo: "mi hardware trabaja mientras yo no lo uso." |
| Motivación secundaria | Reconocimiento y progresión: el sistema de rangos satisface el deseo de ser valorado por la comunidad. |
| Sensibilidad clave | Confianza y transparencia. Necesita saber exactamente cuánto ha ganado, cuánto está pendiente y por qué su puntuación sube o baja. |
| Barrera de entrada a eliminar | Cualquier requisito de configuración técnica compleja o jerga de infraestructura. |

### Usuario fuera de alcance en el MVP

El lado "cliente que sube tareas" (empresas o desarrolladores que demandan cómputo) queda completamente fuera del MVP. Las tareas disponibles en la plataforma serán creadas directamente en la base de datos para las pruebas y la demostración.

---

## 3. Principios de Producto (máximo 5)

1. **Simplicidad ante todo.** Cada pantalla debe poder ser usada por alguien que nunca ha oído hablar de computación distribuida. Si una acción requiere explicación, la interfaz está mal diseñada.

2. **Confianza basada en datos, no en promesas.** El Trust Score y el historial de transacciones son siempre visibles, auditables y explicados con lenguaje llano. El proveedor nunca debe preguntarse "¿por qué cambió mi puntuación?".

3. **Progresión visible y motivadora.** El sistema de rangos y el historial de tareas deben hacer que el proveedor sienta que está construyendo algo: una reputación, un historial, un ingreso creciente. El gamification es una herramienta de retención, no decoración.

4. **Estados claros en todo momento.** La UI nunca deja al usuario en la duda: cada operación tiene un estado de carga, un estado de éxito y un estado de error bien comunicado. El procesamiento de tareas muestra progreso real (o simulado convincentemente) en lugar de una pantalla en blanco.

5. **Seguridad no negociable, invisible para el usuario.** Passwords hasheadas, tokens JWT correctamente validados, Row Level Security activado en Supabase. La seguridad no puede degradarse para simplificar el desarrollo.

---

## 4. Alcance del MVP

El MVP valida la hipótesis central: **un proveedor de cómputo puede registrarse, descubrir tareas, ejecutarlas y cobrar por ellas en una experiencia end-to-end sin fricción técnica.**

### Funcionalidades incluidas

| # | Funcionalidad | Valor que aporta |
|---|---------------|-----------------|
| 1 | Registro e inicio de sesión con JWT | Identidad segura del proveedor |
| 2 | Dashboard con métricas personales | Visión inmediata del estado y progreso |
| 3 | Listado de tareas con filtros (dificultad, hardware, tipo, recompensa mínima) | Descubrimiento de oportunidades adaptadas al hardware propio |
| 4 | Detalle de tarea con todos los metadatos | Toma de decisión informada antes de aceptar |
| 5 | Ciclo de vida completo de asignación (aceptar / iniciar / completar / fallar) | Flujo de trabajo funcional de principio a fin |
| 6 | Pantalla de procesamiento con progreso por etapas | Feedback tranquilizador durante la ejecución |
| 7 | Cartera con saldo, historial y solicitud de retiro | Monetización visible y gestionable |
| 8 | Perfil con desglose del Trust Score y hardware registrado | Transparencia de reputación y autogestión de recursos |
| 9 | Sistema de Trust Score con fórmula ponderada y rangos | Motor de confianza y retención a largo plazo |

### Flujo end-to-end del MVP

```
Registro → Login → Dashboard → Explorar tareas → Ver detalle → Aceptar tarea
→ Iniciar procesamiento → Completar tarea → Ver ganancia en cartera → Solicitar retiro
```

---

## 5. Métricas de Éxito del MVP

Las siguientes métricas determinan si el MVP ha cumplido su objetivo antes de escalar.

| Métrica | Umbral mínimo de éxito | Razón |
|---------|------------------------|-------|
| Tasa de registro completado | 90% de usuarios que inician el formulario lo completan | Valida que el onboarding no tiene fricción |
| Tasa de primera tarea aceptada | 70% de usuarios registrados aceptan al menos una tarea en las primeras 48h | Valida que el descubrimiento de tareas funciona |
| Tasa de tarea completada vs. aceptada | Mayor del 80% | Valida que el ciclo de vida técnico es robusto y la UX no abandona al usuario a mitad del flujo |
| Cobertura de tests de backend | 100% de endpoints principales cubiertos | No es negociable como requisito de calidad de producción |
| Tiempo de arranque local (cold start) | Menos de 5 minutos siguiendo el README | Valida que el onboarding de desarrollo es real, no teórico |
| Ausencia de errores de seguridad críticos | 0 vulnerabilidades críticas detectadas en revisión (secrets expuestos, JWT sin validar, CORS abierto) | Umbral no negociable |

---

## 6. Fuera del Alcance del MVP

Los siguientes elementos quedan explícitamente excluidos del MVP. Incluirlos introduciría complejidad que no está validada por la hipótesis central.

| Elemento | Motivo de exclusión |
|----------|---------------------|
| Integración de pagos reales (Stripe u otro procesador) | Complejidad regulatoria y de integración desproporcionada para el MVP. Los retiros se registran como solicitudes sin ejecutar transferencia real. |
| Ejecución real de cómputo distribuido | Requiere infraestructura de orquestación (agentes locales, sandboxing, monitorización de recursos) fuera del alcance de esta fase. El procesamiento se simula con animación por etapas. |
| Aplicación móvil nativa (iOS / Android) | La validación inicial se hace en web. La app móvil es una segunda fase condicionada al éxito del MVP web. |
| Panel del lado "cliente que sube tareas" | El MVP valida únicamente el lado proveedor. Incorporar el lado demandante duplicaría la superficie de producto sin validar primero la oferta. |
| Sistema de pagos automáticos o liquidación periódica | Depende de la integración de pagos reales, que está fuera de alcance. |
| Notificaciones push o por email | Fuera de alcance en esta iteración. Pueden añadirse en la siguiente fase si el engagement lo justifica. |
| Administración back-office (panel de administrador) | No es necesario para la validación. La gestión de datos de prueba se hace directamente en Supabase. |
| Internacionalización multiidioma | La plataforma se lanza en español. Otros idiomas son una decisión de expansión futura. |

---

## 7. Decisiones y Supuestos Notables

Las siguientes decisiones se tomaron ante ambigüedades del brief. Se documentan para que el Product Owner las valide antes de que el equipo de desarrollo las implemente.

- **Las tareas del MVP son datos de seed, no creadas por usuarios.** El brief excluye el lado cliente, por lo que el equipo de backend debe poblar la tabla `tasks` con datos de muestra representativos para que el flujo del proveedor sea demostrable. Se asume que esto es responsabilidad del equipo de desarrollo como parte del arranque local.

- **El "hardware registrado" en el perfil es autodeclarado.** El brief no menciona detección automática de hardware. Se asume entrada manual por el proveedor en su perfil. Si en el futuro se requiere detección automática, necesitará un agente local fuera del alcance actual.

- **La simulación de procesamiento debe ser convincente, no trivial.** Una barra de progreso instantánea no aporta valor de UX. Se asume que el progreso debe avanzar por etapas con duraciones mínimas realistas (por ejemplo, 3-5 segundos entre etapas) para que el proveedor sienta que algo está ocurriendo.

- **El Trust Score se actualiza al completar o fallar una tarea.** El brief especifica la fórmula pero no el momento de recálculo. Se asume que el recálculo ocurre en cada transición de estado de la asignación.

- **El estado "online" del proveedor es autodeclarado (toggle manual).** No existe un mecanismo de heartbeat en el MVP. Un sistema de presencia real requeriría WebSockets, lo cual está fuera de alcance.

---

*Documento de visión aprobado para trasladar al CTO para definición de arquitectura técnica y stack de infraestructura.*
