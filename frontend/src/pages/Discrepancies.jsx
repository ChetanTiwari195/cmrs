import { useState } from 'react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import api, { errorMessage, useApi } from '@/lib/api'
import { formatDateTime, formatINR, label, STATUS_VARIANT } from '@/lib/utils'

export default function Discrepancies() {
  const [status, setStatus] = useState('OPEN')
  const { data, loading, error, reload } = useApi(`/discrepancies/${status === 'ALL' ? '' : `?status=${status}`}`)
  const [resolving, setResolving] = useState(null)

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Discrepancies</h1>

      <div className="space-y-2">
        <Label>Status</Label>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="OPEN">Open</SelectItem>
            <SelectItem value="RESOLVED">Resolved</SelectItem>
            <SelectItem value="ALL">All</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Raised</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Branch</TableHead>
            <TableHead>Reference</TableHead>
            <TableHead className="text-right">Expected</TableHead>
            <TableHead className="text-right">Actual</TableHead>
            <TableHead className="text-right">Difference</TableHead>
            <TableHead>Note</TableHead>
            <TableHead>Status</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.map((d) => (
            <TableRow key={d.id}>
              <TableCell>{formatDateTime(d.created_at)}</TableCell>
              <TableCell><Badge variant="outline">{label(d.type)}</Badge></TableCell>
              <TableCell>{d.branch_name}</TableCell>
              <TableCell>{d.reference || '—'}</TableCell>
              <TableCell className="text-right">{formatINR(d.expected)}</TableCell>
              <TableCell className="text-right">{formatINR(d.actual)}</TableCell>
              <TableCell className="text-right font-medium text-destructive">{formatINR(d.difference)}</TableCell>
              <TableCell className="max-w-56 truncate" title={d.resolution_note || d.note}>{d.resolution_note || d.note}</TableCell>
              <TableCell><Badge variant={STATUS_VARIANT[d.status]}>{d.status}</Badge></TableCell>
              <TableCell className="text-right">
                {d.status === 'OPEN' && <Button size="sm" variant="outline" onClick={() => setResolving(d)}>Resolve</Button>}
              </TableCell>
            </TableRow>
          ))}
          {!loading && !data?.length && (
            <TableRow>
              <TableCell colSpan={10} className="text-center text-muted-foreground">{error || 'No discrepancies.'}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {resolving && <ResolveDialog discrepancy={resolving} onClose={() => setResolving(null)} onDone={() => { setResolving(null); reload() }} />}
    </div>
  )
}

function ResolveDialog({ discrepancy, onClose, onDone }) {
  async function onSubmit(e) {
    e.preventDefault()
    try {
      await api.post(`/discrepancies/${discrepancy.id}/resolve/`, Object.fromEntries(new FormData(e.currentTarget)))
      toast.success('Discrepancy resolved.')
      onDone()
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Resolve {label(discrepancy.type).toLowerCase()} of {formatINR(discrepancy.difference)}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <p className="text-sm text-muted-foreground">Raised with: {discrepancy.note}</p>
          <div className="space-y-2">
            <Label htmlFor="resolution_note">How was it resolved?</Label>
            <Textarea id="resolution_note" name="resolution_note" required />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit">Mark resolved</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
