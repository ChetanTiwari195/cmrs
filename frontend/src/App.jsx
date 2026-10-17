import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import AppLayout from '@/components/AppLayout'
import { useAuth } from '@/lib/auth'
import { NAV } from '@/lib/nav'
import Login from '@/pages/Login'
import Placeholder from '@/pages/Placeholder'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return null

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        {user ? (
          <Route element={<AppLayout />}>
            {/* Only the current role's pages are registered, so other URLs fall through to the redirect. */}
            {NAV[user.role].map(({ path, label }) => (
              <Route key={path} path={path} element={<Placeholder title={label} />} />
            ))}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        ) : (
          <Route path="*" element={<Navigate to="/login" replace />} />
        )}
      </Routes>
    </BrowserRouter>
  )
}
