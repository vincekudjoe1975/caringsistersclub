import { useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Toaster } from './components/ui/toaster';
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

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  }, [pathname]);
  return null;
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <ScrollToTop />
        <Header />
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
            <Route path="/volunteer" element={<Volunteer />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/privacy-policy" element={<Legal type="privacy" />} />
            <Route path="/terms-of-service" element={<Legal type="terms" />} />
            <Route path="/accessibility" element={<Legal type="accessibility" />} />
            <Route path="/donor-privacy" element={<Legal type="donor" />} />
          </Routes>
        </main>
        <Footer />
        <Toaster />
      </BrowserRouter>
    </div>
  );
}

export default App;
