/**
 * Formatea un monto en Co-Computing Credits con notación española.
 * Ejemplo: 1234.56 → "1.234,56 CC"
 */
export function formatCC(amount: number): string {
  return (
    amount.toLocaleString('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) + ' CC'
  )
}

/**
 * Formatea una fecha ISO en formato "05 jun 2026"
 */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

/**
 * Formatea una fecha ISO con hora: "05 jun 2026 · 14:32"
 */
export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  const date = d.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
  const time = d.toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  })
  return `${date} · ${time}`
}

/**
 * Devuelve "hace X segundos / minutos / horas"
 */
export function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return `hace ${diff}s`
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`
  return `hace ${Math.floor(diff / 3600)} h`
}
