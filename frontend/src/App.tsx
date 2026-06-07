import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

import ProtectedRoute from './components/layout/ProtectedRoute'
import Layout from './components/layout/Layout'

import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import TaskListPage from './pages/TaskListPage'
import TaskDetailPage from './pages/TaskDetailPage'
import ProcessingPage from './pages/ProcessingPage'
import WalletPage from './pages/WalletPage'
import ProfilePage from './pages/ProfilePage'
import NotFoundPage from './pages/NotFoundPage'
import JobListPage from './pages/JobListPage'
import NewJobPage from './pages/NewJobPage'
import JobDetailPage from './pages/JobDetailPage'
import JobResultPage from './pages/JobResultPage'

function SessionExpiredHandler() {
  const navigate = useNavigate()

  useEffect(() => {
    const handler = () => {
      navigate('/login', { replace: true })
    }
    window.addEventListener('co_computing:session_expired', handler)
    return () => window.removeEventListener('co_computing:session_expired', handler)
  }, [navigate])

  return null
}

export default function App() {
  return (
    <>
      <SessionExpiredHandler />
      <Routes>
        {/* Rutas públicas */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/registro" element={<RegisterPage />} />

        {/* Rutas protegidas */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/tareas" element={<TaskListPage />} />
            <Route path="/tareas/:id" element={<TaskDetailPage />} />
            <Route path="/procesando/:assignmentId" element={<ProcessingPage />} />
            <Route path="/cartera" element={<WalletPage />} />
            <Route path="/perfil" element={<ProfilePage />} />
            <Route path="/jobs" element={<JobListPage />} />
            <Route path="/jobs/new" element={<NewJobPage />} />
            <Route path="/jobs/:id" element={<JobDetailPage />} />
            <Route path="/jobs/:id/result" element={<JobResultPage />} />
          </Route>
        </Route>

        {/* Redirecciones */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  )
}
