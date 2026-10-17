import { useState } from 'react'
import { Figure, LoadingRows } from '@/components/Loading'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/lib/auth'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApi } from '@/lib/api'
import { formatDateTime, formatINR, label, STATUS_VARIANT, todayISO } from '@/lib/utils'

const STATUSES = ['COLLECTED', 'SUBMITTED', 'BRANCH_RECEIVED', 'DEPOSITED', 'SETTLED']

export default function Collections() {
  const { user } = useAuth()
  const isAgent = user.role === 'AGENT'
  const [filters, setFilters] = useState({ date_from: todayISO(), date_to: todayISO(), status: 'ALL' })
  const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v && v !== 'ALL'))
  const { data, loading, error } = useApi(`/collections/?${params}`)
  const set = (key) => (value) => setFilters((f) => ({ ...f, [key]: value?.target ? value.target.value : value }))

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Collections</h1>

      <div className="grid grid-cols-2 items-end gap-3 sm:flex sm:flex-wrap sm:gap-4">
        <div className="space-y-2">
          <Label htmlFor="date_from">From</Label>
          <Input id="date_from" type="date" value={filters.date_from} onChange={set('date_from')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="date_to">To</Label>
          <Input id="date_to" type="date" value={filters.date_to} onChange={set('date_to')} />
        </div>
        <div className="col-span-2 space-y-2">
          <Label>Status</Label>
          <Select value={filters.status} onValueChange={set('status')}>
            <SelectTrigger className="w-full sm:w-44"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All statuses</SelectItem>
              {STATUSES.map((s) => <SelectItem key={s} value={s}>{label(s)}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:max-w-md md:gap-4">
        <Card>
          <CardHeader>
            <CardDescription>Total collected</CardDescription>
            <CardTitle className="text-lg"><Figure loading={loading}>{formatINR(data?.total)}</Figure></CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Receipts</CardDescription>
            <CardTitle className="text-lg"><Figure loading={loading}>{data?.count ?? '—'}</Figure></CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Receipt</TableHead>
            <TableHead className="hidden md:table-cell">Collected at</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead className="hidden lg:table-cell">Loan</TableHead>
            {!isAgent && <TableHead className="hidden md:table-cell">Agent</TableHead>}
            <TableHead className="text-right">Amount</TableHead>
            <TableHead className="hidden sm:table-cell">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading && <LoadingRows cols={isAgent ? 6 : 7} />}
          {!loading && data?.results.map((c) => (
            <TableRow key={c.id}>
              <TableCell className="font-medium">{c.receipt_no}</TableCell>
              <TableCell className="hidden md:table-cell">{formatDateTime(c.collected_at)}</TableCell>
              <TableCell>{c.customer_name}</TableCell>
              <TableCell className="hidden lg:table-cell">{c.loan_no}</TableCell>
              {!isAgent && <TableCell className="hidden md:table-cell">{c.agent_name}</TableCell>}
              <TableCell className="text-right">{formatINR(c.amount)}</TableCell>
              <TableCell className="hidden sm:table-cell"><Badge variant={STATUS_VARIANT[c.status]}>{label(c.status)}</Badge></TableCell>
            </TableRow>
          ))}
          {!loading && !data?.results.length && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground">{error || 'No collections for these filters.'}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
