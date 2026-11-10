import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { BackendProvider } from './context/BackendContext';
import { Sidebar } from './components/layout/Sidebar';
import { BackendStatusBanner } from './components/common/BackendStatusBanner';
import { ConnectionModal } from './components/common/ConnectionModal';
import { ApiContractModal } from './components/common/ApiContractModal';
import { Overview } from './pages/Overview';
import { RunDetails } from './pages/RunDetails';
import { TryFix } from './pages/TryFix';
import { BatchVerification } from './pages/BatchVerification';

export default function App() {
  return (
    <BackendProvider>
      <HashRouter>
        {/* Background decorative dots and rings from Rewind.html */}
        <div className="bg-decor" aria-hidden="true">
          <div className="dots" />
          <div className="rings" />
          <div className="rings b" />
        </div>

        {/* Application Shell */}
        <div className="relative z-1 max-w-[1360px] mx-auto px-4 md:px-6 py-6 pb-14 flex flex-col md:flex-row gap-8">
          <Sidebar />

          <main className="flex-1 min-w-0" aria-live="polite">
            <BackendStatusBanner />
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/run/:id" element={<RunDetails />} />
              <Route path="/replay/:id" element={<TryFix />} />
              <Route path="/batch" element={<BatchVerification />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>

        {/* Configuration and API Contract Drawers */}
        <ConnectionModal />
        <ApiContractModal />
      </HashRouter>
    </BackendProvider>
  );
}
