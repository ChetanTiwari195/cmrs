import { useState } from 'react'
import { toast } from 'sonner'
import { LoadingRows } from '@/components/Loading'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import api, { errorMessage, useApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function Customers() {
  const { user } = useAuth()
  const isAdmin = user.role === 'ADMIN'
  const { data: customers, loading, error, reload } = useApi('/customers/')
  // null = closed, {} = new, customer = editing
  const [editing, setEditing] = useState(null)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{isAdmin ? 'Customers' : 'My Customers'}</h1>
        {isAdmin && <Button onClick={() => setEditing({})}>Add customer</Button>}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Phone</TableHead>
            <TableHead className="hidden md:table-cell">Address</TableHead>
            <TableHead className="hidden sm:table-cell">Agent</TableHead>
            <TableHead className="hidden md:table-cell">Branch</TableHead>
            {isAdmin && <TableHead />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading && <LoadingRows cols={isAdmin ? 6 : 5} />}
          {!loading && customers?.map((c) => (
            <TableRow key={c.id}>
              <TableCell className="font-medium">{c.name}</TableCell>
              <TableCell>{c.phone}</TableCell>
              <TableCell className="hidden min-w-48 whitespace-normal md:table-cell">{c.address || '—'}</TableCell>
              <TableCell className="hidden sm:table-cell">{c.agent_name}</TableCell>
              <TableCell className="hidden md:table-cell">{c.branch_name}</TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" onClick={() => setEditing(c)}>Edit</Button>
                </TableCell>
              )}
            </TableRow>
          ))}
          {!loading && !customers?.length && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground">{error || 'No customers yet.'}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {isAdmin && (
        <CustomerDialog customer={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload() }} />
      )}
    </div>
  )
}

function CustomerDialog({ customer, onClose, onSaved }) {
  const { data: agents } = useApi('/agents/')
  const isEdit = Boolean(customer?.id)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    const body = Object.fromEntries(new FormData(e.currentTarget))
    setSaving(true)
    try {
      if (isEdit) await api.patch(`/customers/${customer.id}/`, body)
      else await api.post('/customers/', body)
      toast.success(isEdit ? 'Customer updated.' : 'Customer added.')
      onSaved()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={Boolean(customer)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit customer' : 'Add customer'}</DialogTitle>
        </DialogHeader>
        <form key={customer?.id ?? 'new'} onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" name="name" defaultValue={customer?.name} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">Mobile number</Label>
            <Input id="phone" name="phone" inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} defaultValue={customer?.phone} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="address">Address</Label>
            <Textarea id="address" name="address" defaultValue={customer?.address} />
          </div>
          <div className="space-y-2">
            <Label>Assigned agent</Label>
            <Select name="assigned_agent" defaultValue={customer?.assigned_agent?.toString()} required>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select an agent" /></SelectTrigger>
              <SelectContent>
                {agents?.map((a) => (
                  <SelectItem key={a.id} value={a.id.toString()}>{a.name} · {a.branch}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving && <Spinner />} Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
