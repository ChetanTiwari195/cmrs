import { LogOut } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar'
import { useAuth } from '@/lib/auth'
import { NAV, ROLE_LABELS } from '@/lib/nav'

export default function AppLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-12 items-center border-b px-4">
          <SidebarTrigger />
          <span className="ml-2 font-semibold md:hidden">CMRS</span>
        </header>
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

function AppSidebar() {
  const { user, logout } = useAuth()
  // On phones the sidebar is a slide-over sheet; close it once a page is picked.
  const { setOpenMobile } = useSidebar()

  return (
    <Sidebar>
      <SidebarHeader className="px-4 py-3 text-lg font-semibold">CMRS</SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarMenu>
            {NAV[user.role].map(({ path, label, icon: Icon }) => (
              <SidebarMenuItem key={path}>
                <NavLink to={path} onClick={() => setOpenMobile(false)}>
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
          {ROLE_LABELS[user.role]}
          {user.branch && ` · ${user.branch.name}`}
        </div>
        <Button variant="outline" size="sm" className="mt-2" onClick={logout}>
          <LogOut /> Log out
        </Button>
      </SidebarFooter>
    </Sidebar>
  )
}
