import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import AppLayout from '@/components/AppLayout'
import { PageLoader } from '@/components/Loading'
import { useAuth } from '@/lib/auth'
import { NAV } from '@/lib/nav'
import Collections from '@/pages/Collections'
import Customers from '@/pages/Customers'
import Dashboard from '@/pages/Dashboard'
import Deposits from '@/pages/Deposits'
import Discrepancies from '@/pages/Discrepancies'
import LoanDetail from '@/pages/LoanDetail'
import Loans from '@/pages/Loans'
import Login from '@/pages/Login'
import Submissions from '@/pages/Submissions'

const PAGES = {
  '/dashboard': Dashboard,
  '/customers': Customers,
  '/loans': Loans,
  '/collections': Collections,
  '/submissions': Submissions,
  '/discrepancies': Discrepancies,
  '/deposits': Deposits,
  '/settlements': Deposits,
}

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return <PageLoader fullScreen />

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        {user ? (
          <Route element={<AppLayout />}>
            {/* Only the current role's pages are registered, so other URLs fall through to the redirect. */}
            {NAV[user.role].map(({ path }) => {
              const Page = PAGES[path]
              return <Route key={path} path={path} element={<Page />} />
            })}
            <Route path="/loans/:id" element={<LoanDetail />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        ) : (
          <Route path="*" element={<Navigate to="/login" replace />} />
        )}
      </Routes>
    </BrowserRouter>
  )
}
