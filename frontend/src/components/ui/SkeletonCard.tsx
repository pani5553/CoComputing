import { clsx } from 'clsx'

interface SkeletonCardProps {
  lines?: number
  className?: string
}

export default function SkeletonCard({ lines = 3, className }: SkeletonCardProps) {
  return (
    <div
      className={clsx(
        'animate-pulse space-y-3 p-5 rounded-xl bg-neutral-900 border border-neutral-700',
        className,
      )}
      aria-hidden="true"
    >
      <div className="h-4 bg-neutral-700 rounded w-1/3" />
      <div className="h-6 bg-neutral-700 rounded w-2/3" />
      {Array.from({ length: Math.max(lines - 2, 1) }).map((_, i) => (
        <div
          key={i}
          className="h-4 bg-neutral-700 rounded"
          style={{ width: `${50 + (i % 3) * 15}%` }}
        />
      ))}
    </div>
  )
}

/** Skeleton para filas de tabla */
export function SkeletonRow() {
  return (
    <tr className="animate-pulse" aria-hidden="true">
      <td className="px-4 py-3.5">
        <div className="h-4 bg-neutral-700 rounded w-20" />
      </td>
      <td className="px-4 py-3.5">
        <div className="h-4 bg-neutral-700 rounded w-24" />
      </td>
      <td className="px-4 py-3.5">
        <div className="h-4 bg-neutral-700 rounded w-40" />
      </td>
      <td className="px-4 py-3.5">
        <div className="h-4 bg-neutral-700 rounded w-16 ml-auto" />
      </td>
      <td className="px-4 py-3.5">
        <div className="h-4 bg-neutral-700 rounded w-16" />
      </td>
    </tr>
  )
}

/** Skeleton para StatCard */
export function SkeletonStat() {
  return (
    <div className="animate-pulse flex flex-col gap-2 p-5 rounded-xl bg-neutral-900 border border-neutral-700" aria-hidden="true">
      <div className="flex items-center gap-2">
        <div className="h-5 w-5 bg-neutral-700 rounded" />
        <div className="h-4 bg-neutral-700 rounded w-24" />
      </div>
      <div className="h-9 bg-neutral-700 rounded w-32 mt-1" />
      <div className="h-4 bg-neutral-700 rounded w-20" />
    </div>
  )
}
