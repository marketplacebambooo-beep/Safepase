import { useEffect, useState } from 'react'

import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'

import { api, clearToken, getToken, getUser, setUser } from './api'

import Layout from './components/Layout'

import Login from './pages/Login'

import ForgotPassword from './pages/ForgotPassword'

import ClinicDashboard from './pages/ClinicDashboard'

import HospitalPanel from './pages/HospitalPanel'

import PatientDetail from './pages/PatientDetail'

import Notifications from './pages/Notifications'

import AdminPanel from './pages/AdminPanel'



function homeForRole(role) {

  if (role === 'admin') return '/admin'

  if (role === 'hospital') return '/hospital'

  return '/clinic'

}



function ProtectedRoutes() {

  const [user, setUserState] = useState(getUser())

  const navigate = useNavigate()



  useEffect(() => {

    const token = getToken()

    if (token && !user) {

      api.me().then((u) => {

        setUser(u)

        setUserState(u)

      }).catch(() => {

        clearToken()

        navigate('/login')

      })

    }

  }, [])



  if (!getToken() || !user) {

    return <Navigate to="/login" replace />

  }



  function handleLogout() {

    clearToken()

    setUserState(null)

    navigate('/login')

  }



  return (

    <Routes>

      <Route element={<Layout user={user} onLogout={handleLogout} />}>

        <Route path="/clinic" element={user.role === 'nurse' ? <ClinicDashboard user={user} /> : <Navigate to={homeForRole(user.role)} />} />

        <Route path="/hospital" element={user.role === 'hospital' ? <HospitalPanel user={user} /> : <Navigate to={homeForRole(user.role)} />} />

        <Route path="/admin" element={user.role === 'admin' ? <AdminPanel /> : <Navigate to={homeForRole(user.role)} />} />

        <Route path="/patients/:id" element={<PatientDetail />} />

        <Route path="/notifications" element={<Notifications />} />

        <Route path="*" element={<Navigate to={homeForRole(user.role)} />} />

      </Route>

    </Routes>

  )

}



function LoginRoute() {

  const navigate = useNavigate()

  if (getToken() && getUser()) {

    const u = getUser()

    return <Navigate to={homeForRole(u.role)} replace />

  }

  return <Login onLogin={(u) => navigate(homeForRole(u.role))} />

}



export default function App() {

  return (

    <BrowserRouter>

      <Routes>

        <Route path="/login" element={<LoginRoute />} />

        <Route path="/forgot-password" element={<ForgotPassword />} />

        <Route path="/*" element={<ProtectedRoutes />} />

      </Routes>

    </BrowserRouter>

  )

}

