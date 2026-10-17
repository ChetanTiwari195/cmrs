import { useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import api, { errorMessage, useApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDate, formatINR, STATUS_VARIANT, todayISO } from '@/lib/utils'

export default function Loans() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data: loans, loading, error } = useApi('/loans/')
  const [creating, setCreating] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Loans</h1>
        {user.role === 'ADMIN' && <Button onClick={() => setCreating(true)}>New loan</Button>}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Loan no.</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead>Disbursed</TableHead>
            <TableHead className="text-right">Principal</TableHead>
            <TableHead className="text-right">Total payable</TableHead>
            <TableHead className="text-right">Outstanding</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loans?.map((l) => (
            <TableRow key={l.id} className="cursor-pointer" onClick={() => navigate(`/loans/${l.id}`)}>
              <TableCell className="font-medium">{l.loan_no}</TableCell>
              <TableCell>{l.customer_name}</TableCell>
              <TableCell>{formatDate(l.disbursed_on)}</TableCell>
              <TableCell className="text-right">{formatINR(l.principal)}</TableCell>
              <TableCell className="text-right">{formatINR(l.total_payable)}</TableCell>
              <TableCell className="text-right">{formatINR(l.outstanding)}</TableCell>
              <TableCell><Badge variant={STATUS_VARIANT[l.status]}>{l.status}</Badge></TableCell>
            </TableRow>
          ))}
          {!loading && !loans?.length && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground">{error || 'No loans yet.'}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {creating && (
        <NewLoanDialog onClose={() => setCreating(false)} onSaved={(loan) => navigate(`/loans/${loan.id}`)} />
      )}
    </div>
  )
}

function NewLoanDialog({ onClose, onSaved }) {
  const { data: customers } = useApi('/customers/')
  const today = todayISO()

  async function onSubmit(e) {
    e.preventDefault()
    try {
      const { data } = await api.post('/loans/', Object.fromEntries(new FormData(e.currentTarget)))
      toast.success(`Loan ${data.loan_no} created.`)
      onSaved(data)
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New loan</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Customer</Label>
            <Select name="customer" required>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select a customer" /></SelectTrigger>
              <SelectContent>
                {customers?.map((c) => (
                  <SelectItem key={c.id} value={c.id.toString()}>{c.name} · {c.phone}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="principal">Principal (₹)</Label>
              <Input id="principal" name="principal" type="number" min="1" step="0.01" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="annual_rate">Flat interest (% / year)</Label>
              <Input id="annual_rate" name="annual_rate" type="number" min="0" max="100" step="0.01" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tenure_months">Tenure (months)</Label>
              <Input id="tenure_months" name="tenure_months" type="number" min="1" max="360" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="disbursed_on">Disbursed on</Label>
              <Input id="disbursed_on" name="disbursed_on" type="date" max={today} defaultValue={today} required />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit">Create loan</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
