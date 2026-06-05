import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// Listener global para sesión expirada
window.addEventListener('co_computing:session_expired', (e) => {
  const event = e as CustomEvent<{ message: string }>
  console.warn('[Auth]', event.detail.message)
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
