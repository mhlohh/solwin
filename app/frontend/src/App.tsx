import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { MainLayout } from './components/layout/MainLayout';

// Pages
import { Dashboard } from './pages/Dashboard';
import { Inbox } from './pages/Inbox';
import { Conversations } from './pages/Conversations';
import { ConversationDetails } from './pages/ConversationDetails';
import { Threats } from './pages/Threats';
import { ThreatDetails } from './pages/ThreatDetails';
import { CustomerInsights } from './pages/CustomerInsights';
import { SecurityAnalytics } from './pages/SecurityAnalytics';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/conversations" element={<Conversations />} />
            <Route path="/conversations/:id" element={<ConversationDetails />} />
            <Route path="/threats" element={<Threats />} />
            <Route path="/threats/:id" element={<ThreatDetails />} />
            <Route path="/insights/customer" element={<CustomerInsights />} />
            <Route path="/analytics/security" element={<SecurityAnalytics />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default App;
