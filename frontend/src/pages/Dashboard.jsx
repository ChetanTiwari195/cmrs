import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Figure, LoadingRows } from '@/components/Loading'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import api, { errorMessage, useApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatINR, todayISO } from '@/lib/utils'

const monthStart = () => todayISO().slice(0, 8) + '01'

// [key, label, hint, roles that see it (all if omitted)]
const METRICS = [
  ['expected', 'Expected collections', 'EMIs due in the period'],
  ['collected', 'Total collected', 'Cash collected by agents'],
  ['with_agents', 'Cash held by agents', 'Collected, not yet received by the branch'],
  ['received_at_branch', 'Received at branches', 'Cash counted and approved by managers', ['ADMIN', 'FINANCE', 'BRANCH_MANAGER']],
  ['deposited', 'Bank deposits', 'Pending and settled deposits', ['ADMIN', 'FINANCE', 'BRANCH_MANAGER']],
  ['settled', 'Settled amount', 'Confirmed credited by the bank', ['ADMIN', 'FINANCE', 'BRANCH_MANAGER']],
  ['outstanding', 'Outstanding (now)', 'Unpaid balance on active loans'],
]

export default function Dashboard() {
  const { user } = useAuth()
  const seesAll = ['ADMIN', 'FINANCE'].includes(user.role)
  const [filters, setFilters] = useState({ date_from: monthStart(), date_to: todayISO(), branch: 'ALL', agent: 'ALL' })
  const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v && v !== 'ALL'))
  const { data, loading, error } = useApi(`/dashboard/?${params}`)
  const [addingAgent, setAddingAgent] = useState(false)
  const [agentsVersion, setAgentsVersion] = useState(0) // remounts the agent filter so a new agent shows up
  const set = (key) => (value) => setFilters((f) => ({ ...f, [key]: value?.target ? value.target.value : value }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        {user.role === 'ADMIN' && (
          <Button onClick={() => setAddingAgent(true)}><UserPlus /> Add agent</Button>
        )}
      </div>

      {addingAgent && (
        <AddAgentDialog onClose={() => setAddingAgent(false)} onAdded={() => { setAddingAgent(false); setAgentsVersion((v) => v + 1) }} />
      )}

      <div className="grid grid-cols-2 items-end gap-3 sm:flex sm:flex-wrap sm:gap-4">
        <div className="space-y-2">
          <Label htmlFor="date_from">From</Label>
          <Input id="date_from" type="date" value={filters.date_from} onChange={set('date_from')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="date_to">To</Label>
          <Input id="date_to" type="date" value={filters.date_to} onChange={set('date_to')} />
        </div>
        {seesAll && <BranchFilter value={filters.branch} onChange={set('branch')} />}
        {user.role !== 'AGENT' && <AgentFilter key={agentsVersion} value={filters.agent} onChange={set('agent')} />}
      </div>

      {error && <p className="text-destructive">{error}</p>}

      <div className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-4">
        {METRICS.filter(([, , , roles]) => !roles || roles.includes(user.role)).map(([key, title, hint]) => (
          <Card key={key}>
            <CardHeader>
              <CardDescription>{title}</CardDescription>
              <CardTitle className="text-lg md:text-2xl"><Figure loading={loading}>{formatINR(data?.[key])}</Figure></CardTitle>
              <p className="hidden text-xs text-muted-foreground sm:block">{hint}</p>
            </CardHeader>
          </Card>
        ))}
        <Card>
          <CardHeader>
            <CardDescription>Open discrepancies (now)</CardDescription>
            <CardTitle className="text-lg md:text-2xl"><Figure loading={loading}>{data?.open_discrepancies ?? '—'}</Figure></CardTitle>
            <p className="hidden text-xs text-muted-foreground sm:block">Net difference {formatINR(data?.open_discrepancy_amount)} (positive = money missing)</p>
          </CardHeader>
        </Card>
        {user.role !== 'AGENT' && (
          <Card>
            <CardHeader>
              <CardDescription>Deposits awaiting settlement (now)</CardDescription>
              <CardTitle className="text-lg md:text-2xl"><Figure loading={loading}>{data?.pending_deposits ?? '—'}</Figure></CardTitle>
            </CardHeader>
          </Card>
        )}
      </div>

      {user.role !== 'AGENT' && <section>
        <h2 className="mb-2 font-medium">Collections by agent</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Agent</TableHead>
              <TableHead className="hidden md:table-cell">Branch</TableHead>
              <TableHead className="hidden text-right sm:table-cell">Receipts</TableHead>
              <TableHead className="text-right">Collected</TableHead>
              <TableHead className="text-right">Still with agent</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && <LoadingRows cols={5} />}
            {!loading && data?.by_agent.map((a) => (
              <TableRow key={a.agent}>
                <TableCell className="font-medium">{a.name}</TableCell>
                <TableCell className="hidden md:table-cell">{a.branch}</TableCell>
                <TableCell className="hidden text-right sm:table-cell">{a.receipts}</TableCell>
                <TableCell className="text-right">{formatINR(a.collected)}</TableCell>
                <TableCell className="text-right">{formatINR(a.held)}</TableCell>
              </TableRow>
            ))}
            {!loading && data && !data.by_agent.length && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">No collections in this period.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>}
    </div>
  )
}

function BranchFilter({ value, onChange }) {
  const { data: branches } = useApi('/branches/')
  return (
    <div className="col-span-2 space-y-2 sm:col-span-1">
      <Label>Branch</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full sm:w-48"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All branches</SelectItem>
          {branches?.map((b) => <SelectItem key={b.id} value={b.id.toString()}>{b.name}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  )
}

function AgentFilter({ value, onChange }) {
  const { data: agents } = useApi('/agents/')
  return (
    <div className="col-span-2 space-y-2 sm:col-span-1">
      <Label>Agent</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full sm:w-48"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All agents</SelectItem>
          {agents?.map((a) => <SelectItem key={a.id} value={a.id.toString()}>{a.name} · {a.branch}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  )
}

function AddAgentDialog({ onClose, onAdded }) {
  const { data: branches } = useApi('/branches/')
  const [saving, setSaving] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setSaving(true)
    try {
      const { data: agent } = await api.post('/agents/', Object.fromEntries(new FormData(e.currentTarget)))
      toast.success(`${agent.name} added to ${agent.branch}. They can log in now.`)
      onAdded()
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
          <DialogTitle>Add collection agent</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="first_name">First name</Label>
              <Input id="first_name" name="first_name" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">Last name</Label>
              <Input id="last_name" name="last_name" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input id="username" name="username" autoComplete="off" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" name="password" type="password" autoComplete="new-password" minLength={8} required />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Branch</Label>
            <Select name="branch" required>
              <SelectTrigger className="w-full"><SelectValue placeholder="Select a branch" /></SelectTrigger>
              <SelectContent>
                {branches?.map((b) => <SelectItem key={b.id} value={b.id.toString()}>{b.code} · {b.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <p className="text-xs text-muted-foreground">At least 8 characters, not too common and not all numbers.</p>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving && <Spinner />} Add agent</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
