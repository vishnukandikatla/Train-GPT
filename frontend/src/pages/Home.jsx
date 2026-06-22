import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Train, Bot, ArrowRight, Shield, Activity } from 'lucide-react';
import { analyticsService } from '../services/api';

export default function Home() {
  const [stats, setStats] = useState({
    bookings_today: 1450,
    search_requests: 3500,
    active_users: 890,
    active_agents: 6,
  });

  useEffect(() => {
    // Load actual stats if backend is running
    analyticsService.getAnalytics()
      .then((res) => {
        if (res.data && res.data.stats) {
          setStats(res.data.stats);
        }
      })
      .catch(() => console.log('Backend not started yet, using seed stats'));
  }, []);

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-hidden">
      {/* Animated Train Track & Train */}
      <div className="absolute top-24 left-0 w-full h-8 bg-zinc-200/50 dark:bg-zinc-800/30 border-y border-zinc-300 dark:border-zinc-700/50 flex items-center overflow-hidden pointer-events-none">
        <div className="train-animate absolute flex items-center gap-1 text-blue-600 dark:text-blue-400">
          <Train size={24} className="fill-current" />
          <div className="w-16 h-4 bg-blue-500/80 rounded-sm" />
          <div className="w-16 h-4 bg-blue-500/80 rounded-sm" />
          <div className="w-16 h-4 bg-blue-500/80 rounded-sm" />
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-6 py-16 w-full flex-1 flex flex-col justify-center gap-12 z-10 mt-12">
        {/* Hero Section */}
        <div className="text-center space-y-6 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-zinc-200 dark:border-zinc-850 bg-white/50 dark:bg-zinc-900/50 text-xs font-mono text-zinc-600 dark:text-zinc-400">
            <Bot size={14} className="text-blue-500" />
            <span>Coordinated by Google ADK & Gemini</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-500 dark:from-blue-400 dark:to-indigo-300 bg-clip-text text-transparent">
            TrainGPT AI
          </h1>
          <p className="text-xl md:text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            Multi-Agent Railway Booking Assistant
          </p>
          <p className="text-zinc-500 dark:text-zinc-400 max-w-xl mx-auto text-sm leading-relaxed">
            Search routes, check seat counts, compare class fares, book tickets, and track PNR status with standard conversational flows and voice commands.
          </p>
          <div className="flex justify-center gap-4 pt-4">
            <Link
              to="/chat"
              className="bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-6 py-3 font-semibold shadow-md flex items-center gap-2 transition-all hover:translate-x-1"
            >
              Start Booking
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/dashboard"
              className="bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-lg px-6 py-3 font-semibold shadow-sm transition-all"
            >
              View Dashboard
            </Link>
          </div>
        </div>

        {/* Live Stats Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto w-full">
          {[
            { label: "Today's Bookings", val: stats.bookings_today, desc: "Successful checkouts" },
            { label: "Search Queries", val: stats.search_requests, desc: "Route requests" },
            { label: "Active Users", val: stats.active_users, desc: "Live sessions" },
            { label: "Active Agents", val: stats.active_agents, desc: "ADK Sub-agents", highlighted: true },
          ].map((item, idx) => (
            <div
              key={idx}
              className={`p-6 rounded-xl border glass-panel shadow-sm flex flex-col justify-between h-32 transition-all hover:scale-[1.02] ${
                item.highlighted ? 'border-blue-500/50 glow-blue' : ''
              }`}
            >
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">{item.label}</span>
              <span className="text-3xl font-extrabold tracking-tight text-zinc-950 dark:text-zinc-50">{item.val}</span>
              <span className="text-[10px] text-zinc-400 dark:text-zinc-500">{item.desc}</span>
            </div>
          ))}
        </div>

        {/* Feature Cards Grid */}
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto w-full">
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50">
            <Bot className="text-blue-500 mb-3" size={24} />
            <h3 className="font-bold text-base mb-2">Multi-Agent Design</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Consists of 6 specialized sub-agents working together to resolve search, availability, fare calculations, and bookings.
            </p>
          </div>
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50">
            <Activity className="text-emerald-500 mb-3" size={24} />
            <h3 className="font-bold text-base mb-2">Real-time Timeline</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Every backend logic step, agent transition, and tool call is broadcast in real time to the live dashboard monitoring widget.
            </p>
          </div>
          <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50">
            <Shield className="text-indigo-500 mb-3" size={24} />
            <h3 className="font-bold text-base mb-2">Voice & Text Booking</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Interact conversationally via keyboard input or voice dictation with automated text-to-speech feedback.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
