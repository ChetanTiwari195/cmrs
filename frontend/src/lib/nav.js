import { AlertTriangle, Banknote, FileText, Landmark, LayoutDashboard, Send, Users, Wallet } from 'lucide-react'

const dashboard = { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }
const discrepancies = { path: '/discrepancies', label: 'Discrepancies', icon: AlertTriangle }

// Sidebar items per role. Pages are filled in by later PRs.
export const NAV = {
  ADMIN: [dashboard, { path: '/customers', label: 'Customers', icon: Users }, { path: '/loans', label: 'Loans', icon: FileText }],
  AGENT: [
    dashboard,
    { path: '/customers', label: 'My Customers', icon: Users },
    { path: '/collections', label: 'Collections', icon: Wallet },
    { path: '/submissions', label: 'Cash Submissions', icon: Send },
  ],
  BRANCH_MANAGER: [
    dashboard,
    { path: '/submissions', label: 'Cash Submissions', icon: Send },
    { path: '/deposits', label: 'Bank Deposits', icon: Landmark },
    discrepancies,
  ],
  FINANCE: [dashboard, { path: '/settlements', label: 'Settlements', icon: Banknote }, discrepancies],
}

export const ROLE_LABELS = {
  ADMIN: 'Admin',
  FINANCE: 'Finance',
  BRANCH_MANAGER: 'Branch Manager',
  AGENT: 'Collection Agent',
}
