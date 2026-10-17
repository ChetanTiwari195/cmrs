export { cn } from "cn"

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

// Display only. Amounts arrive from the API as decimal strings; never do math on them here.
export const formatINR = (value) => (value == null ? '—' : inr.format(value))

export const formatDate = (value) => (value ? new Date(value).toLocaleDateString('en-IN', { dateStyle: 'medium' }) : '—')

export const formatDateTime = (value) => (value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—')

// YYYY-MM-DD in local time, for <input type="date"> and API filters.
export const todayISO = () => new Date().toLocaleDateString('en-CA')

export const STATUS_VARIANT = {
  ACTIVE: 'default', CLOSED: 'secondary',
  PAID: 'default', PARTIAL: 'secondary', PENDING: 'outline',
  COLLECTED: 'outline', SUBMITTED: 'secondary', BRANCH_RECEIVED: 'secondary', DEPOSITED: 'secondary', SETTLED: 'default',
}

export const label = (status) => status.replaceAll('_', ' ')

Object.assign(STATUS_VARIANT, { APPROVED: 'default', REJECTED: 'destructive', OPEN: 'destructive', RESOLVED: 'secondary' })

// Display-only preview of expected − received while the manager types; the API computes and stores the real figure.
export const previewDifference = (expected, received) => (Math.round(expected * 100) - Math.round(received * 100)) / 100

Object.assign(STATUS_VARIANT, { FAILED: 'destructive' })
