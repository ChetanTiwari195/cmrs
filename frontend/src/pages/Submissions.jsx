import { useState } from 'react'
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import api, { errorMessage, useApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDateTime, formatINR, previewDifference, STATUS_VARIANT } from '@/lib/utils'

export default function Submissions() {
  const { user } = useAuth()
  const isAgent = user.role === 'AGENT'
  const [status, setStatus] = useState(isAgent ? 'ALL' : 'PENDING')
  const { data: submissions, loading, error, reload } = useApi(`/submissions/${status === 'ALL' ? '' : `?status=${status}`}`)
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
            <TableHead>Ref</TableHead>
            <TableHead className="hidden md:table-cell">Submitted</TableHead>
            {!isAgent && <TableHead>Agent</TableHead>}
            <TableHead className="hidden text-right lg:table-cell">Receipts</TableHead>
            <TableHead className="text-right">Expected</TableHead>
            <TableHead className="hidden text-right sm:table-cell">Received</TableHead>
            <TableHead className="hidden text-right sm:table-cell">Difference</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Remarks</TableHead>
            {user.role === 'BRANCH_MANAGER' && <TableHead />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading && <LoadingRows cols={isAgent ? 8 : 10} />}
          {!loading && submissions?.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-medium">{s.ref_no}</TableCell>
              <TableCell className="hidden md:table-cell">{formatDateTime(s.created_at)}</TableCell>
              {!isAgent && <TableCell>{s.agent_name}</TableCell>}
              <TableCell className="hidden text-right lg:table-cell">{s.collection_count}</TableCell>
              <TableCell className="text-right">{formatINR(s.expected_amount)}</TableCell>
              <TableCell className="hidden text-right sm:table-cell">{formatINR(s.received_amount)}</TableCell>
              <TableCell className={`hidden text-right sm:table-cell ${Number(s.difference) ? 'font-medium text-destructive' : ''}`}>{formatINR(s.difference)}</TableCell>
              <TableCell><Badge variant={STATUS_VARIANT[s.status]}>{s.status}</Badge></TableCell>
              <TableCell className="min-w-48 max-w-80 whitespace-normal break-words">{s.remarks || '—'}</TableCell>
              {user.role === 'BRANCH_MANAGER' && (
                <TableCell className="text-right">
                  {s.status === 'PENDING' && <Button size="sm" onClick={() => setReviewing(s)}>Review</Button>}
                </TableCell>
              )}
            </TableRow>
          ))}
          {!loading && !submissions?.length && (
            <TableRow>
              <TableCell colSpan={10} className="text-center text-muted-foreground">{error || 'No submissions.'}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {reviewing && (
        <ReviewDialog submission={reviewing} onClose={() => setReviewing(null)} onDone={() => { setReviewing(null); reload() }} />
      )}
    </div>
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Review {submission.ref_no} · {submission.agent_name}</DialogTitle>
        </DialogHeader>
        <dl className="grid grid-cols-2 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Receipts</dt><dd>{submission.collection_count}</dd>
          <dt className="text-muted-foreground">Expected</dt><dd className="font-medium">{formatINR(submission.expected_amount)}</dd>
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
