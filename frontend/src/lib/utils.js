export { cn } from "cn"

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

// Display only. Amounts arrive from the API as decimal strings; never do math on them here.
export const formatINR = (value) => (value == null ? '—' : inr.format(value))

export const formatDate = (value) => (value ? new Date(value).toLocaleDateString('en-IN', { dateStyle: 'medium' }) : '—')
