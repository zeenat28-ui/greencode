import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { TenantProvider } from './context/TenantContext';
import { ToastProvider } from './context/ToastContext';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <TenantProvider>
        <ToastProvider>
          <App />
        </ToastProvider></TenantProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);

