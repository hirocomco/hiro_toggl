import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import Dashboard from '@/pages/Dashboard'
import ClientDetail from '@/pages/ClientDetail'
import MemberDetail from '@/pages/MemberDetail'
import Admin from '@/pages/Admin'
import Settings from '@/pages/Settings'
import NotFound from '@/pages/NotFound'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/client/:clientId" element={<ClientDetail />} />
        <Route path="/member/:memberId" element={<MemberDetail />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  )
}

export default App