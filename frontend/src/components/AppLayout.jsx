import { LogOut } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarHeader, SidebarInset,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarProvider, SidebarTrigger,
} from '@/components/ui/sidebar'
import { useAuth } from '@/lib/auth'
import { NAV, ROLE_LABELS } from '@/lib/nav'

export default function AppLayout() {
  const { user, logout } = useAuth()

  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="px-4 py-3 text-lg font-semibold">CMRS</SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarMenu>
              {NAV[user.role].map(({ path, label, icon: Icon }) => (
                <SidebarMenuItem key={path}>
                  <NavLink to={path}>
                    {({ isActive }) => (
                      <SidebarMenuButton isActive={isActive}>
                        <Icon /> {label}
                      </SidebarMenuButton>
                    )}
                  </NavLink>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter className="p-4 text-sm">
          <div className="font-medium">{user.first_name || user.username}</div>
          <div className="text-muted-foreground">
            {ROLE_LABELS[user.role]}{user.branch && ` · ${user.branch.name}`}
          </div>
          <Button variant="outline" size="sm" className="mt-2" onClick={logout}>
            <LogOut /> Log out
          </Button>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset>
        <header className="flex h-12 items-center border-b px-4">
          <SidebarTrigger />
        </header>
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
