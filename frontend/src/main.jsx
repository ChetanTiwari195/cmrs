import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/lib/auth'
import App from './App.jsx'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <TooltipProvider>
      <AuthProvider>
        <App />
        <Toaster richColors />
      </AuthProvider>
    </TooltipProvider>
  </StrictMode>,
)
