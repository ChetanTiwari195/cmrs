import { useState } from 'react'
import { toast } from 'sonner'
import { Figure, LoadingRows } from '@/components/Loading'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import api, { errorMessage, useApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDate, formatINR, STATUS_VARIANT, todayISO } from '@/lib/utils'

// Branch managers record deposits here (/deposits); finance settles them (/settlements).
export default function Deposits() {
  const { user } = useAuth()
  const isFinance = user.role === 'FINANCE'
  const [status, setStatus] = useState(isFinance ? 'PENDING' : 'ALL')
  const { data: deposits, loading, error, reload } = useApi(`/deposits/${status === 'ALL' ? '' : `?status=${status}`}`)
  const [dialog, setDialog] = useState(null) // { type: 'settle' | 'fail', deposit }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{isFinance ? 'Settlements' : 'Bank Deposits'}</h1>

      {user.role === 'BRANCH_MANAGER' && <ReadyToDeposit onDeposited={reload} />}

      <div className="space-y-2">
        <Label>Status</Label>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-full sm:w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            {['ALL', 'PENDING', 'SETTLED', 'FAILED'].map((s) => (
              <SelectItem key={s} value={s}>{s === 'ALL' ? 'All statuses' : s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Deposit date</TableHead>
            <TableHead>Branch</TableHead>
            <TableHead>Bank · reference</TableHead>
            <TableHead>Submissions</TableHead>
            <TableHead className="text-right">Deposited</TableHead>
            <TableHead className="text-right">Settled</TableHead>
            <TableHead className="text-right">Difference</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Remarks</TableHead>
            {isFinance && <TableHead />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading && <LoadingRows cols={isFinance ? 10 : 9} />}
          {!loading && deposits?.map((d) => (
            <TableRow key={d.id}>
              <TableCell>{formatDate(d.deposit_date)}</TableCell>
              <TableCell>{d.branch_name}</TableCell>
              <TableCell className="font-medium">{d.bank_name} · {d.reference}</TableCell>
              <TableCell className="min-w-32 whitespace-normal">{d.submission_refs.join(', ')}</TableCell>
              <TableCell className="text-right">{formatINR(d.amount)}</TableCell>
              <TableCell className="text-right">{formatINR(d.settled_amount)}</TableCell>
              <TableCell className={`text-right ${Number(d.difference) ? 'font-medium text-destructive' : ''}`}>{formatINR(d.difference)}</TableCell>
              <TableCell>
                <Badge variant={STATUS_VARIANT[d.status]}>{d.status}</Badge>
                {d.is_delayed && <Badge variant="destructive" className="ml-1">DELAYED</Badge>}
              </TableCell>
              <TableCell className="min-w-48 max-w-80 whitespace-normal break-words">{d.remarks || '—'}</TableCell>
              {isFinance && (
                <TableCell className="space-x-2 text-right whitespace-nowrap">
                  {d.status === 'PENDING' && (
                    <>
                      <Button size="sm" onClick={() => setDialog({ type: 'settle', deposit: d })}>Settle</Button>
                      <Button size="sm" variant="outline" onClick={() => setDialog({ type: 'fail', deposit: d })}>Mark failed</Button>
                    </>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
          {!loading && !deposits?.length && (
            <TableRow>
              <TableCell colSpan={10} className="text-center text-muted-foreground">{error || 'No deposits.'}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {dialog && (
        <SettlementDialog {...dialog} onClose={() => setDialog(null)} onDone={() => { setDialog(null); reload() }} />
      )}
    </div>
  )
}

function ReadyToDeposit({ onDeposited }) {
  const { data, loading, reload } = useApi('/deposits/eligible/')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const { data: deposit } = await api.post('/deposits/', Object.fromEntries(new FormData(e.currentTarget)))
      toast.success(`Deposit ${deposit.reference} recorded.`)
      setOpen(false)
      reload()
      onDeposited()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="md:max-w-md">
      <CardHeader>
        <CardDescription>Reconciled cash ready to deposit · {data?.count ?? 0} submissions</CardDescription>
        <CardTitle className="text-2xl"><Figure loading={loading}>{formatINR(data?.total)}</Figure></CardTitle>
        <Button className="mt-2 w-full sm:w-fit" disabled={!data?.count} onClick={() => { setError(null); setOpen(true) }}>Record bank deposit</Button>
      </CardHeader>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record bank deposit</DialogTitle>
          </DialogHeader>
          <form onSubmit={onSubmit} className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Covers {data?.refs.join(', ')}. The amount must match the reconciled total of {formatINR(data?.total)}.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="bank_name">Bank</Label>
                <Input id="bank_name" name="bank_name" placeholder="HDFC Bank" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reference">Transaction / slip reference</Label>
                <Input id="reference" name="reference" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="amount">Amount deposited (₹)</Label>
                <Input id="amount" name="amount" type="number" min="0.01" step="0.01" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="deposit_date">Deposit date</Label>
                <Input id="deposit_date" name="deposit_date" type="date" max={todayISO()} defaultValue={todayISO()} required />
              </div>
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertTitle>Deposit not recorded</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={saving}>{saving && <Spinner />} Record deposit</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

function SettlementDialog({ type, deposit, onClose, onDone }) {
  const settling = type === 'settle'
  const [saving, setSaving] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post(`/deposits/${deposit.id}/${type}/`, Object.fromEntries(new FormData(e.currentTarget)))
      toast.success(settling ? 'Deposit settled.' : 'Deposit marked as failed. The cash is back with the branch.')
      onDone()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{settling ? 'Confirm settlement' : 'Mark deposit as failed'} · {deposit.reference}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {deposit.branch_name} deposited {formatINR(deposit.amount)} into {deposit.bank_name} on {formatDate(deposit.deposit_date)}.
          </p>
          {settling && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="settled_amount">Amount credited (₹)</Label>
                <Input id="settled_amount" name="settled_amount" type="number" min="0" step="0.01" defaultValue={deposit.amount} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="settled_on">Credited on</Label>
                <Input id="settled_on" name="settled_on" type="date" min={deposit.deposit_date} max={todayISO()} defaultValue={todayISO()} required />
              </div>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="remarks">{settling ? 'Remarks (required if the amount differs)' : 'Reason'}</Label>
            <Textarea id="remarks" name="remarks" required={!settling} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" variant={settling ? 'default' : 'destructive'} disabled={saving}>
              {saving && <Spinner />} {settling ? 'Settle' : 'Mark failed'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
