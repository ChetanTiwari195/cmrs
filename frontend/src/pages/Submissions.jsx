import { Fragment, useState } from 'react'
import { toast } from 'sonner'
import { Figure, LoadingRows } from '@/components/Loading'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import api, { errorMessage, useApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDateTime, formatINR, previewDifference, STATUS_VARIANT } from '@/lib/utils'

export default function Submissions() {
  const { user } = useAuth()
  const isAgent = user.role === 'AGENT'
  const [status, setStatus] = useState(isAgent ? 'ALL' : 'PENDING')
  const isManager = user.role === 'BRANCH_MANAGER'
  const cols = isManager ? 8 : 7
  const { data, loading, error, reload } = useApi(`/submissions/${status === 'ALL' ? '' : `?status=${status}`}`)
  const [reviewing, setReviewing] = useState(null)

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Cash Submissions</h1>

      {isAgent && <CashInHand onSubmitted={reload} />}

      <div className="space-y-2">
        <Label>Status</Label>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-full sm:w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            {['ALL', 'PENDING', 'APPROVED', 'REJECTED'].map((s) => (
              <SelectItem key={s} value={s}>{s === 'ALL' ? 'All statuses' : s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ref / receipt</TableHead>
            <TableHead className="hidden md:table-cell">Date</TableHead>
            <TableHead className="text-right">Expected</TableHead>
            <TableHead className="hidden text-right sm:table-cell">Received</TableHead>
            <TableHead className="hidden text-right sm:table-cell">Difference</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Remarks</TableHead>
            {isManager && <TableHead />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading && <LoadingRows cols={cols} />}
          {/* Grouped by agent: each submission, its receipts underneath, then the agent's subtotal. */}
          {!loading && data?.by_agent.map((group) => {
            const submissions = data.results.filter((s) => s.agent === group.agent)
            const name = submissions[0].agent_name
            return (
              <Fragment key={group.agent}>
                {!isAgent && (
                  <TableRow className="bg-muted/50 hover:bg-muted/50">
                    <TableCell colSpan={cols} className="font-semibold">{name}</TableCell>
                  </TableRow>
                )}
                {submissions.map((s) => (
                  <Fragment key={s.id}>
                    <TableRow>
                      <TableCell className="font-medium">{s.ref_no}</TableCell>
                      <TableCell className="hidden md:table-cell">{formatDateTime(s.created_at)}</TableCell>
                      <TableCell className="text-right font-medium">{formatINR(s.expected_amount)}</TableCell>
                      <TableCell className="hidden text-right sm:table-cell">{formatINR(s.received_amount)}</TableCell>
                      <DifferenceCell value={s.difference} />
                      <TableCell><Badge variant={STATUS_VARIANT[s.status]}>{s.status}</Badge></TableCell>
                      <TableCell className="min-w-48 max-w-80 whitespace-normal break-words">{s.remarks || '—'}</TableCell>
                      {isManager && (
                        <TableCell className="text-right">
                          {s.status === 'PENDING' && <Button size="sm" onClick={() => setReviewing(s)}>Review</Button>}
                        </TableCell>
                      )}
                    </TableRow>
                    {s.receipts.map((r) => (
                      <TableRow key={r.id} className="text-muted-foreground">
                        <TableCell className="pl-6">
                          {r.receipt_no}
                          <div className="text-xs">{r.customer_name} · {r.loan_no}</div>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">{formatDateTime(r.collected_at)}</TableCell>
                        <TableCell className="text-right">{formatINR(r.amount)}</TableCell>
                        <TableCell className="hidden sm:table-cell" />
                        <TableCell className="hidden sm:table-cell" />
                        <TableCell colSpan={isManager ? 3 : 2} />
                      </TableRow>
                    ))}
                  </Fragment>
                ))}
                <TotalRow label={`${isAgent ? 'Total' : `${name} total`} · ${group.receipts} receipts`} totals={group} cols={cols} />
              </Fragment>
            )
          })}
          {!loading && !data?.results.length && (
            <TableRow>
              <TableCell colSpan={cols} className="text-center text-muted-foreground">{error || 'No submissions.'}</TableCell>
            </TableRow>
          )}
        </TableBody>
        {!isAgent && !loading && data?.results.length > 0 && (
          <TableFooter>
            <TotalRow label={`${user.branch?.name ?? 'All branches'} total · ${data.total.receipts} receipts`} totals={data.total} cols={cols} />
          </TableFooter>
        )}
      </Table>

      {reviewing && (
        <ReviewDialog submission={reviewing} onClose={() => setReviewing(null)} onDone={() => { setReviewing(null); reload() }} />
      )}
    </div>
  )
}

function DifferenceCell({ value }) {
  // Positive = cash short, negative = excess. Number() only decides the colour.
  return (
    <TableCell className={`hidden text-right sm:table-cell ${Number(value) ? 'font-medium text-destructive' : ''}`}>
      {formatINR(value)}
    </TableCell>
  )
}

function TotalRow({ label, totals, cols }) {
  return (
    <TableRow className="font-semibold">
      <TableCell>{label}</TableCell>
      <TableCell className="hidden md:table-cell" />
      <TableCell className="text-right">{formatINR(totals.expected)}</TableCell>
      <TableCell className="hidden text-right sm:table-cell">{formatINR(totals.received)}</TableCell>
      <DifferenceCell value={totals.difference} />
      <TableCell colSpan={cols - 5} />
    </TableRow>
  )
}

function CashInHand({ onSubmitted }) {
  const { data, loading, reload } = useApi('/collections/?status=COLLECTED')
  const [submitting, setSubmitting] = useState(false)

  async function submit() {
    setSubmitting(true)
    try {
      const { data: submission } = await api.post('/submissions/')
      toast.success(`Submitted ${formatINR(submission.expected_amount)} to the branch (${submission.ref_no}).`)
      reload()
      onSubmitted()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="md:max-w-md">
      <CardHeader>
        <CardDescription>Cash in hand · {data?.count ?? 0} receipts</CardDescription>
        <CardTitle className="text-2xl"><Figure loading={loading}>{formatINR(data?.total)}</Figure></CardTitle>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button className="mt-2 w-full sm:w-fit" disabled={!data?.count || submitting}>
              {submitting && <Spinner />} Submit cash to branch
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Submit {formatINR(data?.total)} to the branch?</AlertDialogTitle>
              <AlertDialogDescription>
                All {data?.count} receipts you hold will be handed over. The branch manager will count the cash and approve or reject it.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={submit}>Submit</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardHeader>
    </Card>
  )
}

function ReviewDialog({ submission, onClose, onDone }) {
  const [received, setReceived] = useState(submission.expected_amount)
  const [remarks, setRemarks] = useState('')
  const [busy, setBusy] = useState(false)
  const difference = received === '' ? null : previewDifference(submission.expected_amount, received)

  async function act(action) {
    setBusy(true)
    try {
      const body = action === 'approve' ? { received_amount: received, remarks } : { remarks }
      await api.post(`/submissions/${submission.id}/${action}/`, body)
      toast.success(action === 'approve' ? 'Cash approved.' : 'Submission rejected and returned to the agent.')
      onDone()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Review {submission.ref_no} · {submission.agent_name}</DialogTitle>
        </DialogHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Receipt</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {submission.receipts.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.receipt_no}</TableCell>
                <TableCell className="whitespace-normal">{r.customer_name} · {r.loan_no}</TableCell>
                <TableCell className="text-right">{formatINR(r.amount)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell colSpan={2}>Expected total · {submission.collection_count} receipts</TableCell>
              <TableCell className="text-right">{formatINR(submission.expected_amount)}</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
        <dl className="grid grid-cols-2 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Difference</dt>
          <dd className={difference ? 'font-medium text-destructive' : ''}>
            {difference == null ? '—' : `${formatINR(Math.abs(difference))} ${difference > 0 ? 'short' : difference < 0 ? 'excess' : ''}`}
          </dd>
        </dl>
        <div className="space-y-2">
          <Label htmlFor="received">Cash received (₹)</Label>
          <Input id="received" type="number" min="0" step="0.01" value={received} onChange={(e) => setReceived(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="remarks">Remarks {difference ? '(required)' : ''}</Label>
          <Textarea id="remarks" value={remarks} onChange={(e) => setRemarks(e.target.value)} placeholder="Required if the amounts differ or you reject" />
        </div>
        <DialogFooter>
          <Button variant="destructive" disabled={busy} onClick={() => act('reject')}>Reject</Button>
          <Button disabled={busy || received === ''} onClick={() => act('approve')}>{busy && <Spinner />} Approve</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
