import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  BarChart3, 
  Users, 
  Settings, 
  RefreshCw, 
  DollarSign,
  Clock,
  TrendingUp,
  Database
} from 'lucide-react'
import { clsx } from 'clsx'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: BarChart3 },
  { name: 'Admin', href: '/admin', icon: Settings },
  { name: 'Settings', href: '/settings', icon: Database },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg">
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center justify-center border-b border-gray-200 px-4">
            <div className="flex items-center space-x-2">
              <div className="flex h-8 w-8 items-center justify-center rounded bg-primary-500">
                <Clock className="h-5 w-5 text-white" />
              </div>
              <div className="text-lg font-semibold text-gray-900">
                Toggl Reports
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 px-4 py-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'group flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-500'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  )}
                >
                  <item.icon
                    className={clsx(
                      'mr-3 h-5 w-5 flex-shrink-0',
                      isActive ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'
                    )}
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="border-t border-gray-200 p-4">
            <div className="text-xs text-gray-500">
              <div className="flex items-center justify-between">
                <span>Version 2.0.0</span>
                <div className="flex items-center space-x-1">
                  <div className="h-2 w-2 rounded-full bg-green-400"></div>
                  <span>Online</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        {/* Top header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">
                  {getPageTitle(location.pathname)}
                </h1>
                <p className="mt-1 text-sm text-gray-500">
                  {getPageDescription(location.pathname)}
                </p>
              </div>
              
              <div className="flex items-center space-x-4">
                {/* Quick stats */}
                <div className="hidden md:flex items-center space-x-6 text-sm text-gray-500">
                  <div className="flex items-center space-x-1">
                    <TrendingUp className="h-4 w-4" />
                    <span>Live Data</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <DollarSign className="h-4 w-4" />
                    <span>USD/EUR</span>
                  </div>
                </div>

                {/* Action buttons */}
                <button className="btn btn-outline btn-sm">
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Sync
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

function getPageTitle(pathname: string): string {
  if (pathname === '/') return 'Dashboard'
  if (pathname.startsWith('/client/')) return 'Client Report'
  if (pathname.startsWith('/member/')) return 'Member Report'
  if (pathname === '/admin') return 'Administration'
  if (pathname === '/settings') return 'Settings'
  return 'Toggl Reports'
}

function getPageDescription(pathname: string): string {
  if (pathname === '/') return 'Overview of client performance and team productivity'
  if (pathname.startsWith('/client/')) return 'Detailed analysis of client work and earnings'
  if (pathname.startsWith('/member/')) return 'Individual team member performance metrics'
  if (pathname === '/admin') return 'Manage rates and team settings'
  if (pathname === '/settings') return 'Application configuration and data management'
  return 'Professional time tracking and client billing reports'
}