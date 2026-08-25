import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Sources from './pages/Sources';
import CrawlRuns from './pages/CrawlRuns';
import Regulations from './pages/Regulations';
import RegulationDetail from './pages/RegulationDetail';
import Changes from './pages/Changes';
import ChangeDetail from './pages/ChangeDetail';
import Reviews from './pages/Reviews';
import ImpactAssessments from './pages/ImpactAssessments';
import ImpactDetail from './pages/ImpactDetail';
import Subscriptions from './pages/Subscriptions';
import Notifications from './pages/Notifications';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="sources" element={<Sources />} />
        <Route path="crawl-runs" element={<CrawlRuns />} />
        <Route path="regulations" element={<Regulations />} />
        <Route path="regulations/:id" element={<RegulationDetail />} />
        <Route path="changes" element={<Changes />} />
        <Route path="changes/:id" element={<ChangeDetail />} />
        <Route path="reviews" element={<Reviews />} />
        <Route path="impact" element={<ImpactAssessments />} />
        <Route path="impact/:id" element={<ImpactDetail />} />
        <Route path="subscriptions" element={<Subscriptions />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
    </Routes>
  );
}
