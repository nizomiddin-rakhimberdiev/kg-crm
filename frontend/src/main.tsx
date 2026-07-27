import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { SoundProvider } from './app/providers/SoundProvider'
import { ToastProvider } from './app/providers/ToastProvider'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SoundProvider>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </SoundProvider>
  </React.StrictMode>,
)
