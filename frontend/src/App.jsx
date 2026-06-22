import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import Home from './pages/Home';
import Chat from './pages/Chat';
import Dashboard from './pages/Dashboard';
import PNRTracker from './pages/PNRTracker';
import History from './pages/History';
import { Sun, Moon, Train, MessageSquare, BarChart3, Search, Clock } from 'lucide-react';

function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Home', icon: Train },
    { path: '/chat', label: 'Chat Assistant', icon: MessageSquare },
    { path: '/dashboard', label: 'Analytics Dashboard', icon: BarChart3 },
    { path: '/pnr', label: 'PNR Tracker', icon: Search },
    { path: '/history', label: 'My Bookings', icon: Clock },
  ];

  return (
    <header className="fixed top-0 left-0 w-full bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800 z-50 transition-colors duration-300">
      <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
        {/* Title aligned left */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="p-1.5 rounded-lg bg-blue-600 text-white transition-transform group-hover:scale-105">
            <Train size={18} />
          </div>
          <span className="font-extrabold tracking-tight text-lg text-zinc-900 dark:text-zinc-50 flex items-center gap-1.5">
            TrainGPT <span className="text-blue-500 font-mono text-[10px] bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 rounded">AI</span>
          </span>
        </Link>

        {/* Navigation Tabs centered/right */}
        <nav className="hidden md:flex items-center gap-6 h-full">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`h-full flex items-center gap-1.5 px-1 border-b-2 text-xs font-semibold uppercase tracking-wider transition-all ${
                  isActive
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-zinc-500 hover:text-zinc-950 dark:hover:text-zinc-200 hover:border-zinc-300 dark:hover:border-zinc-700'
                }`}
              >
                <Icon size={14} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Theme Toggle aligned right */}
        <div className="flex items-center gap-3">
          {/* Mobile Menu Icon for tiny screens (fallback) */}
          <div className="md:hidden flex items-center gap-2">
            <Link to="/chat" className="p-2 border border-zinc-200 dark:border-zinc-800 rounded-lg text-zinc-500 hover:text-zinc-950">
              <MessageSquare size={16} />
            </Link>
            <Link to="/dashboard" className="p-2 border border-zinc-200 dark:border-zinc-800 rounded-lg text-zinc-500 hover:text-zinc-950">
              <BarChart3 size={16} />
            </Link>
          </div>
          
          <button
            onClick={toggleTheme}
            className="p-2.5 border border-zinc-200 dark:border-zinc-800 rounded-lg text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-all"
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>
    </header>
  );
}

function AppContent() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 transition-colors duration-300">
      <Navbar />
      <main className="pt-16 min-h-[calc(100vh-64px)] flex flex-col">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/pnr" element={<PNRTracker />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
      
      {/* Footer */}
      <footer className="py-6 border-t border-zinc-200 dark:border-zinc-900 text-center text-xs text-zinc-400 dark:text-zinc-600 bg-white dark:bg-[#0c0c0f]">
        <div className="max-w-[1600px] mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <span>&copy; 2026 TrainGPT AI. Built for portfolio & Capstone Agent projects.</span>
          <div className="flex gap-4">
            <a href="https://github.com/google/adk-python" target="_blank" rel="noreferrer" className="hover:underline">Google ADK</a>
            <span>&bull;</span>
            <a href="https://google.github.io/adk-docs" target="_blank" rel="noreferrer" className="hover:underline">Documentation</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </ThemeProvider>
  );
}
