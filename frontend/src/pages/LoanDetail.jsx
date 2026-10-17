import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApi } from '@/lib/api'
import { formatDate, formatINR } from '@/lib/utils'

const STATUS_VARIANT = { PAID: 'default', PARTIAL: 'secondary', PENDING: 'outline' }

export default function LoanDetail() {
  const { id } = useParams()
  const { data: loan, error } = useApi(`/loans/${id}/`)

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
        <h1 className="mt-2 text-xl font-semibold">{loan.loan_no} · {loan.customer_name}</h1>
        <p className="text-sm text-muted-foreground">
          {loan.annual_rate}% flat · {loan.tenure_months} months · disbursed {formatDate(loan.disbursed_on)} · <Badge variant="outline">{loan.status}</Badge>
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {stats.map(([label, value]) => (
          <Card key={label}>
            <CardHeader>
              <CardDescription>{label}</CardDescription>
              <CardTitle className="text-lg">{formatINR(value)}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div>
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
      </div>
    </div>
  )
}
