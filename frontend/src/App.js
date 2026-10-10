import { useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { Toaster } from './components/ui/toaster';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import Footer from './components/Footer';
import Home from './pages/Home';
import About from './pages/About';
import Leadership from './pages/Leadership';
import Initiatives from './pages/Initiatives';
import Events from './pages/Events';
import Gallery from './pages/Gallery';
import Transparency from './pages/Transparency';
import Donate from './pages/Donate';
import Volunteer from './pages/Volunteer';
import Contact from './pages/Contact';
import Legal from './pages/Legal';
import Login from './pages/Login';
import Admin from './pages/Admin';
import AuthCallback from './pages/AuthCallback';
import PaymentSuccess from './pages/PaymentSuccess';
import ManageGift from './pages/ManageGift';
import RsvpAction from './pages/RsvpAction';
import { Loader2 } from 'lucide-react';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [pathname]);
  return null;
}

function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-[#B4247E]" size={36} />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Shell() {
  const location = useLocation();

  // Process the OAuth callback FIRST (session_id in URL fragment)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  const bare = location.pathname.startsWith('/admin') || location.pathname === '/login';

  return (
    <>
      <ScrollToTop />
      {!bare && <Header />}
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/leadership" element={<Leadership />} />
          <Route path="/initiatives" element={<Initiatives />} />
          <Route path="/events" element={<Events />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/transparency" element={<Transparency />} />
          <Route path="/donate" element={<Donate />} />
          <Route path="/payment/success" element={<PaymentSuccess />} />
          <Route path="/manage-gift" element={<ManageGift />} />
          <Route path="/rsvp" element={<RsvpAction />} />
          <Route path="/volunteer" element={<Volunteer />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/privacy-policy" element={<Legal type="privacy" />} />
          <Route path="/terms-of-service" element={<Legal type="terms" />} />
          <Route path="/accessibility" element={<Legal type="accessibility" />} />
          <Route path="/donor-privacy" element={<Legal type="donor" />} />
          <Route path="/login" element={<Login />} />
          <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
        </Routes>
      </main>
      {!bare && <Footer />}
    </>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Shell />
          <Toaster />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
