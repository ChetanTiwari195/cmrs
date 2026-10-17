import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import api, { errorMessage, useApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDate, formatDateTime, formatINR, label, STATUS_VARIANT } from '@/lib/utils'

export default function LoanDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const { data: loan, error, reload } = useApi(`/loans/${id}/`)
  const { data: history, reload: reloadHistory } = useApi(`/collections/?loan=${id}`)
  const [collecting, setCollecting] = useState(false)

  if (error) return <p className="text-muted-foreground">{error}</p>
  if (!loan) return null

  const stats = [
    ['Principal', loan.principal],
    ['Interest', loan.total_interest],
    ['Total payable', loan.total_payable],
    ['Paid', loan.amount_paid],
    ['Outstanding', loan.outstanding],
  ]

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/loans"><ArrowLeft /> Loans</Link>
        </Button>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-semibold">{loan.loan_no} · {loan.customer_name}</h1>
            <p className="text-sm text-muted-foreground">
              {loan.annual_rate}% flat · {loan.tenure_months} months · disbursed {formatDate(loan.disbursed_on)} ·{' '}
              <Badge variant={STATUS_VARIANT[loan.status]}>{loan.status}</Badge>
            </p>
          </div>
          {user.role === 'AGENT' && loan.status === 'ACTIVE' && (
            <Button onClick={() => setCollecting(true)}>Collect payment</Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {stats.map(([name, value]) => (
          <Card key={name}>
            <CardHeader>
              <CardDescription>{name}</CardDescription>
              <CardTitle className="text-lg">{formatINR(value)}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <section>
        <h2 className="mb-2 font-medium">Repayment schedule</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Due date</TableHead>
              <TableHead className="text-right">Amount due</TableHead>
              <TableHead className="text-right">Paid</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loan.installments.map((i) => (
              <TableRow key={i.id}>
                <TableCell>{i.seq}</TableCell>
                <TableCell>{formatDate(i.due_date)}</TableCell>
                <TableCell className="text-right">{formatINR(i.amount_due)}</TableCell>
                <TableCell className="text-right">{formatINR(i.amount_paid)}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[i.status]}>{i.status}</Badge>
                  {i.is_overdue && <Badge variant="destructive" className="ml-1">OVERDUE</Badge>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>

      <section>
        <h2 className="mb-2 font-medium">Repayment history</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Receipt</TableHead>
              <TableHead>Collected at</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {history?.results.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.receipt_no}</TableCell>
                <TableCell>{formatDateTime(c.collected_at)}</TableCell>
                <TableCell>{c.agent_name}</TableCell>
                <TableCell className="text-right">{formatINR(c.amount)}</TableCell>
                <TableCell><Badge variant={STATUS_VARIANT[c.status]}>{label(c.status)}</Badge></TableCell>
              </TableRow>
            ))}
            {history && !history.results.length && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">No repayments yet.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>

      {collecting && (
        <CollectDialog
          loan={loan}
          onClose={() => setCollecting(false)}
          onCollected={() => { reload(); reloadHistory() }}
        />
      )}
    </div>
  )
}

function CollectDialog({ loan, onClose, onCollected }) {
  // One key per opened form: a double-click or retry returns the same receipt instead of a second payment.
  const [idempotencyKey] = useState(() => crypto.randomUUID())
  const [error, setError] = useState(null)
  const [receipt, setReceipt] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const nextEmi = loan.installments.find((i) => i.status !== 'PAID')

  async function onSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const amount = new FormData(e.currentTarget).get('amount')
      const { data } = await api.post('/collections/', { loan: loan.id, amount, idempotency_key: idempotencyKey })
      setReceipt(data)
      onCollected()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{receipt ? 'Payment recorded' : `Collect payment · ${loan.customer_name}`}</DialogTitle>
        </DialogHeader>

        {receipt ? (
          <>
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-muted-foreground">Receipt no.</dt><dd className="font-medium">{receipt.receipt_no}</dd>
              <dt className="text-muted-foreground">Amount</dt><dd className="font-medium">{formatINR(receipt.amount)}</dd>
              <dt className="text-muted-foreground">Customer</dt><dd>{receipt.customer_name}</dd>
              <dt className="text-muted-foreground">Loan</dt><dd>{receipt.loan_no}</dd>
              <dt className="text-muted-foreground">Collected at</dt><dd>{formatDateTime(receipt.collected_at)}</dd>
            </dl>
            <DialogFooter>
              <Button onClick={onClose}>Done</Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <dl className="grid grid-cols-2 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Outstanding</dt><dd className="font-medium">{formatINR(loan.outstanding)}</dd>
              {nextEmi && (
                <>
                  <dt className="text-muted-foreground">Next EMI (#{nextEmi.seq})</dt>
                  <dd>{formatINR(nextEmi.amount_due)} · paid {formatINR(nextEmi.amount_paid)}</dd>
                </>
              )}
            </dl>
            <div className="space-y-2">
              <Label htmlFor="amount">Amount received (₹)</Label>
              <Input id="amount" name="amount" type="number" min="0.01" step="0.01" required autoFocus />
              <p className="text-xs text-muted-foreground">Anything above the current EMI is applied to the next EMIs.</p>
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertTitle>Payment not recorded</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={submitting}>{submitting ? 'Saving…' : 'Record payment'}</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
