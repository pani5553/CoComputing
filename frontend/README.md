# Co-Computing — Frontend

Interfaz de usuario para la plataforma Co-Computing. Construida con React 18, TypeScript, Tailwind CSS 3 y Vite.

## Requisitos

- Node.js >= 18
- El backend debe estar corriendo en `http://localhost:8000`

## Arrancar en desarrollo

```bash
cd frontend
npm install
npm run dev
```

La app estará disponible en `http://localhost:5173`.

## Variables de entorno

Copia `.env.example` a `.env` y ajusta si necesitas:

```
VITE_API_URL=http://localhost:8000
```

Sin este archivo, la URL por defecto es `http://localhost:8000`.

## Build de produccion

```bash
npm run build
npm run preview
```

## Estructura principal

```
src/
  api/         # Funciones de llamada a la API (auth, tasks, wallet, profile)
  components/
    layout/    # Navbar, Layout, ProtectedRoute
    ui/        # Badge, Button, Card, Input, Modal, ProgressBar, Stepper...
  hooks/       # useAuth, useProgress (polling)
  pages/       # LoginPage, RegisterPage, DashboardPage, TaskListPage,
               #   TaskDetailPage, ProcessingPage, WalletPage, ProfilePage
  store/       # authStore (Zustand), taskStore
  types/       # Todos los tipos TypeScript del dominio
  utils/       # formatCC, formatDate, formatDateTime, timeAgo
```

## Rutas

| Ruta | Acceso | Descripcion |
|------|--------|-------------|
| `/login` | Publico | Formulario de inicio de sesion |
| `/registro` | Publico | Formulario de registro |
| `/dashboard` | Privado | Resumen de estadisticas y actividad reciente |
| `/tareas` | Privado | Listado de tareas con filtros |
| `/tareas/:id` | Privado | Detalle de tarea, boton aceptar/iniciar |
| `/procesando/:assignmentId` | Privado | Barra de progreso, stepper, polling 3s |
| `/cartera` | Privado | Saldos, historial paginado, modal de retiro |
| `/perfil` | Privado | Datos personales, Trust Score, hardware |
