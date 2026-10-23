import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import Explorer from './pages/Explorer';
import Builder from './pages/Builder';
import TriggerDetail from './pages/TriggerDetail';
import TestPanel from './pages/TestPanel';
import MessageQueue from './pages/MessageQueue';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Explorer />} />
          <Route path="/builder" element={<Builder />} />
          <Route path="/queue" element={<MessageQueue />} />
          <Route path="/triggers/:id" element={<TriggerDetail />} />
          <Route path="/triggers/:id/test" element={<TestPanel />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
