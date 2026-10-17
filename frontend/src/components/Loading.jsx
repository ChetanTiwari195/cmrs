import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { TableCell, TableRow } from '@/components/ui/table'

export function PageLoader({ fullScreen = false }) {
  return (
    <div className={`flex items-center justify-center ${fullScreen ? 'min-h-svh' : 'py-24'}`}>
      <Spinner className="size-8 text-muted-foreground" />
    </div>
  )
}

export function LoadingRows({ cols, rows = 4 }) {
  return Array.from({ length: rows }, (_, r) => (
    <TableRow key={r}>
      {Array.from({ length: cols }, (_, c) => (
        <TableCell key={c}><Skeleton className="h-4 w-full min-w-12" /></TableCell>
      ))}
    </TableRow>
  ))
}

// Shows a skeleton in place of a card figure until it loads.
export function Figure({ loading, children }) {
  return loading ? <Skeleton className="h-7 w-28" /> : children
}
