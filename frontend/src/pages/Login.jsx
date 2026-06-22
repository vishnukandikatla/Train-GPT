import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import {
  Train, Eye, EyeOff, Bot, Lock, Mail,
  MapPin, Ticket, Search, Cpu, MessageSquare,
  ChevronRight, Zap, Shield
} from 'lucide-react';

// Floating Particle Component
function Particle({ x, y, size, delay, color }) {
  return (
    <motion.div
      className="absolute rounded-full pointer-events-none"
      style={{ left: `${x}%`, top: `${y}%`, width: size, height: size, background: color, filter: 'blur(1px)' }}
      animate={{
        y: [0, -120, 0],
        x: [0, Math.random() * 30 - 15, 0],
        opacity: [0.1, 0.5, 0.1]
      }}
      transition={{ duration: 8 + Math.random() * 8, delay, repeat: Infinity, ease: 'easeInOut' }}
    />
  );
}

// Background Energy Waves
function EnergyWaves() {
  return (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none opacity-20">
      {Array.from({ length: 4 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-0.5 bg-gradient-to-b from-transparent via-blue-500 to-transparent"
          style={{
            height: '35vh',
            left: `${15 + i * 25}%`,
            top: '-35vh',
          }}
          animate={{
            y: ['0vh', '150vh'],
            opacity: [0, 0.8, 0],
          }}
          transition={{
            duration: 9 + i * 2.5,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: i * 1.8,
          }}
        />
      ))}
      {Array.from({ length: 3 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-0.5 bg-gradient-to-b from-transparent via-orange-500 to-transparent"
          style={{
            height: '45vh',
            left: `${30 + i * 20}%`,
            top: '-45vh',
          }}
          animate={{
            y: ['0vh', '150vh'],
            opacity: [0, 0.7, 0],
          }}
          transition={{
            duration: 8 + i * 3,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: i * 2.5,
          }}
        />
      ))}
    </div>
  );
}

// Holographic Station Network
function HolographicNetwork() {
  return (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none opacity-25">
      <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <motion.path
          d="M 100 200 L 250 150 L 400 300 L 600 200 L 800 350 L 1100 200 L 1300 400"
          stroke="#3b82f6"
          strokeWidth="1"
          strokeDasharray="5 5"
          fill="none"
          animate={{ strokeDashoffset: [0, -40] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
        />
        <motion.path
          d="M 150 500 L 300 420 L 500 550 L 700 450 L 950 600 L 1200 480"
          stroke="#f97316"
          strokeWidth="1"
          strokeDasharray="8 6"
          fill="none"
          animate={{ strokeDashoffset: [0, 40] }}
          transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
        />
        <motion.path
          d="M 300 100 L 550 150 L 800 80 L 1050 120 L 1250 80"
          stroke="#8b5cf6"
          strokeWidth="0.75"
          strokeDasharray="4 8"
          fill="none"
          animate={{ strokeDashoffset: [0, -30] }}
          transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
        />
        <line x1="250" y1="150" x2="300" y2="420" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
        <line x1="400" y1="300" x2="500" y2="550" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
        <line x1="600" y1="200" x2="700" y2="450" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
        <line x1="800" y1="350" x2="950" y2="600" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
        <line x1="1100" y1="200" x2="1200" y2="480" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />

        {[
          { x: 100, y: 200, color: '#3b82f6' },
          { x: 250, y: 150, color: '#3b82f6' },
          { x: 400, y: 300, color: '#8b5cf6' },
          { x: 600, y: 200, color: '#3b82f6' },
          { x: 800, y: 350, color: '#f97316' },
          { x: 1100, y: 200, color: '#3b82f6' },
          { x: 1300, y: 400, color: '#8b5cf6' },
          
          { x: 150, y: 500, color: '#f97316' },
          { x: 300, y: 420, color: '#f97316' },
          { x: 500, y: 550, color: '#8b5cf6' },
          { x: 700, y: 450, color: '#f97316' },
          { x: 950, y: 600, color: '#f97316' },
          { x: 1200, y: 480, color: '#8b5cf6' },
          
          { x: 300, y: 100, color: '#8b5cf6' },
          { x: 550, y: 150, color: '#8b5cf6' },
          { x: 800, y: 80, color: '#f97316' },
          { x: 1050, y: 120, color: '#3b82f6' },
          { x: 1250, y: 80, color: '#8b5cf6' },
        ].map((node, index) => (
          <g key={index}>
            <circle cx={node.x} cy={node.y} r="2.5" fill={node.color} />
            <circle cx={node.x} cy={node.y} r="7" stroke={node.color} strokeWidth="1" fill="none" opacity="0.35" className="animate-ping" style={{ animationDuration: `${2.5 + (index % 3)}s` }} />
          </g>
        ))}
      </svg>
    </div>
  );
}

// Background Anti-gravity Maglev Train
function MaglevTrain() {
  return (
    <motion.div
      className="absolute w-[1100px] h-[240px] left-[calc(50%-550px)] top-[calc(50%-120px)] pointer-events-none z-0 opacity-45 select-none hidden lg:block"
      animate={{
        y: [-12, 12, -12],
        rotate: [-0.5, 0.5, -0.5]
      }}
      transition={{
        duration: 9,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    >
      {/* Glow behind the train */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-orange-500/5 to-purple-500/10 blur-[90px] rounded-full" />
      
      {/* SVG Train */}
      <svg width="100%" height="100%" viewBox="0 0 1100 240" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Maglev rail */}
        <path d="M 0 150 L 1100 150" stroke="url(#rail-gradient)" strokeWidth="4" strokeDasharray="12 18" />
        <path d="M 0 150 L 1100 150" stroke="url(#rail-glow-gradient)" strokeWidth="12" strokeLinecap="round" opacity="0.3" className="blur-[4px]" />
        
        {/* Supporting structures */}
        {Array.from({ length: 16 }).map((_, i) => (
          <motion.path
            key={i}
            d={`M ${i * 75} 155 Q ${i * 75 + 37.5} ${165 + (i % 2) * 5} ${i * 75 + 75} 155`}
            stroke="#3b82f6"
            strokeWidth="1.5"
            fill="none"
            opacity="0.25"
            animate={{ opacity: [0.15, 0.4, 0.15], y: [-2, 2, -2] }}
            transition={{ duration: 2 + (i % 3), repeat: Infinity, delay: i * 0.1 }}
          />
        ))}
        
        {/* Train Fuselage */}
        <g transform="translate(150, 50)">
          {/* Underglow */}
          <rect x="50" y="70" width="700" height="15" fill="url(#underglow-grad)" filter="blur(8px)" opacity="0.8" />
          
          {/* Fuselage shape */}
          <path d="M 800 70 L 150 70 L 50 70 C 20 70 0 50 0 35 C 0 15 30 10 90 10 L 780 10 L 800 30 Z" fill="url(#fuselage-grad)" stroke="url(#fuselage-stroke)" strokeWidth="1.5" />
          
          {/* Cabin windows */}
          {Array.from({ length: 11 }).map((_, i) => (
            <rect
              key={i}
              x={120 + i * 52}
              y={25}
              width="32"
              height="12"
              rx="3"
              fill="#3b82f6"
              className="animate-pulse"
              style={{
                fill: 'url(#window-glow)',
                animationDuration: `${2.2 + (i % 3) * 0.4}s`,
                filter: 'drop-shadow(0 0 4px rgba(59, 130, 246, 0.8))'
              }}
            />
          ))}
          
          {/* Cockpit */}
          <path d="M 95 20 L 70 20 L 45 40 L 75 40 Z" fill="url(#cockpit-glow)" filter="drop-shadow(0 0 6px rgba(249, 115, 22, 0.8))" />
          
          {/* Tech lines */}
          <path d="M 10 40 L 790 40" stroke="#f97316" strokeWidth="1.5" opacity="0.75" />
          <path d="M 80 50 L 770 50" stroke="#3b82f6" strokeWidth="1" opacity="0.5" strokeDasharray="30 10" />
          
          {/* Telemetry labels */}
          <text x="390" y="60" fill="rgba(255,255,255,0.6)" fontSize="9" fontWeight="900" letterSpacing="3" fontFamily="monospace">MAGLEV-TRAINGPT // PROTO-09</text>
          
          {/* Rivet details */}
          <circle cx="110" cy="18" r="1.5" fill="#f97316" />
          <circle cx="790" cy="18" r="1.5" fill="#f97316" />
          
          {/* Thrusters */}
          <path d="M 800 20 L 820 15 L 820 65 L 800 60 Z" fill="#1e293b" stroke="#3b82f6" strokeWidth="1" />
          <polygon points="820,20 870,25 870,55 820,60" fill="url(#thruster-glow)" opacity="0.85" className="animate-pulse" />
        </g>
        
        {/* Gradients */}
        <defs>
          <linearGradient id="rail-gradient" x1="0" y1="0" x2="1100" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="0.3" stopColor="#3b82f6" stopOpacity="0.8" />
            <stop offset="0.5" stopColor="#f97316" stopOpacity="0.9" />
            <stop offset="0.7" stopColor="#8b5cf6" stopOpacity="0.8" />
            <stop offset="1" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="rail-glow-gradient" x1="0" y1="0" x2="1100" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="0.4" stopColor="#3b82f6" stopOpacity="0.6" />
            <stop offset="0.6" stopColor="#f97316" stopOpacity="0.6" />
            <stop offset="1" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="underglow-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="rgba(59, 130, 246, 0)" />
            <stop offset="0.3" stopColor="rgba(59, 130, 246, 0.45)" />
            <stop offset="0.5" stopColor="rgba(249, 115, 22, 0.45)" />
            <stop offset="0.7" stopColor="rgba(139, 92, 246, 0.45)" />
            <stop offset="1" stopColor="rgba(59, 130, 246, 0)" />
          </linearGradient>
          <linearGradient id="fuselage-grad" x1="0" y1="0" x2="800" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#050a18" />
            <stop offset="0.5" stopColor="#0d1b3e" />
            <stop offset="0.9" stopColor="#111c30" />
            <stop offset="1" stopColor="#1e293b" />
          </linearGradient>
          <linearGradient id="fuselage-stroke" x1="0" y1="0" x2="800" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#1e3a8a" />
            <stop offset="0.4" stopColor="#3b82f6" />
            <stop offset="0.6" stopColor="#f97316" />
            <stop offset="1" stopColor="#475569" />
          </linearGradient>
          <linearGradient id="window-glow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#60a5fa" />
            <stop offset="1" stopColor="#1d4ed8" />
          </linearGradient>
          <linearGradient id="cockpit-glow" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#ffedd5" />
            <stop offset="0.4" stopColor="#f97316" />
            <stop offset="1" stopColor="#b45309" />
          </linearGradient>
          <linearGradient id="thruster-glow" x1="820" y1="0" x2="870" y2="0" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#f97316" />
            <stop offset="0.5" stopColor="#ef4444" stopOpacity="0.4" />
            <stop offset="1" stopColor="#7c2d12" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </motion.div>
  );
}

// Decorative Orbiting Floating Cards
function FloatingCard({ icon: Icon, title, desc, glow, iconColor, delay, position, yRange, duration }) {
  return (
    <motion.div
      className={`hidden lg:flex absolute items-center gap-3.5 p-3.5 w-[205px] rounded-2xl border backdrop-blur-md bg-slate-950/60 shadow-[0_15px_35px_rgba(0,0,0,0.6)] ${glow} ${position} select-none pointer-events-auto cursor-pointer z-10 transition-all duration-300 hover:scale-105 hover:bg-slate-900/80 hover:border-white/20`}
      animate={{ y: yRange }}
      transition={{
        duration,
        delay,
        repeat: Infinity,
        repeatType: "reverse",
        ease: "easeInOut"
      }}
    >
      <div className={`p-2 rounded-xl bg-slate-900/80 border border-white/5 ${iconColor}`}>
        <Icon size={18} />
      </div>
      <div className="flex flex-col">
        <span className="text-xs font-bold text-zinc-100">{title}</span>
        <span className="text-[10px] text-zinc-400 mt-0.5">{desc}</span>
      </div>
    </motion.div>
  );
}

// Bottom Telemetry Timeline
function RouteTimeline() {
  const stations = [
    { name: 'NDLS', full: 'New Delhi' },
    { name: 'CNB', full: 'Kanpur' },
    { name: 'ALD', full: 'Prayagraj' },
    { name: 'MGS', full: 'Mughal Sarai' },
    { name: 'HWH', full: 'Howrah' },
  ];

  return (
    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 w-full max-w-4xl px-8 pointer-events-none z-20 hidden md:block">
      <div className="relative backdrop-blur-md bg-slate-950/40 border border-white/5 rounded-2xl px-6 py-4 shadow-[0_12px_40px_rgba(0,0,0,0.6),inset_0_1px_1px_rgba(255,255,255,0.05)] flex flex-col gap-3">
        {/* Route Details / Stats */}
        <div className="flex items-center justify-between text-[9px] text-zinc-500 uppercase tracking-widest font-mono">
          <span>Telemetry Status: ACTIVE</span>
          <span>System Lock: IRNSS SATELLITE</span>
          <span>Avg Speed: 350 KM/H</span>
        </div>

        {/* Track Line */}
        <div className="relative h-1 bg-zinc-800 rounded-full w-full my-3">
          {/* Glowing track */}
          <motion.div
            className="absolute top-0 bottom-0 left-[8%] right-[8%] h-1 bg-gradient-to-r from-blue-500 via-orange-500 to-purple-600 rounded-full"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 2, ease: "easeOut" }}
            style={{ transformOrigin: "left" }}
          />
          {/* Live train marker */}
          <motion.div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-orange-500 border-2 border-white shadow-[0_0_15px_#f97316] z-10 flex items-center justify-center"
            animate={{ left: ["8%", "90%", "8%"] }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          >
            <div className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
          </motion.div>
        </div>

        {/* Stations labels */}
        <div className="flex justify-between items-center px-2">
          {stations.map((s, idx) => (
            <div key={idx} className="flex flex-col items-center">
              <div className="w-3.5 h-3.5 rounded-full bg-slate-950 border border-zinc-700 flex items-center justify-center">
                <motion.div
                  className="w-1.5 h-1.5 rounded-full bg-orange-500"
                  animate={{ scale: [1, 1.4, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 2, delay: idx * 0.4, repeat: Infinity }}
                />
              </div>
              <span className="text-xs font-bold text-orange-400 mt-1.5 font-mono">{s.name}</span>
              <span className="text-[9px] text-zinc-500 mt-0.5">{s.full}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const [form, setForm] = useState({ email: '', password: '', remember: false });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [focusField, setFocusField] = useState(null);

  const containerRef = useRef(null);

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email.trim() || !form.password.trim()) {
      setError('Please fill in all fields.');
      return;
    }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1000));
    const username = form.email.includes('@') ? form.email.split('@')[0] : form.email;
    login({ username, email: form.email });
    setLoading(false);
    navigate('/');
  };

  const handleSocialLogin = (provider) => {
    login({ username: `${provider} User`, provider });
    navigate('/');
  };

  const particles = Array.from({ length: 22 }, (_, i) => ({
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: 2 + Math.random() * 4,
    delay: Math.random() * 4,
    color: i % 3 === 0 ? '#FF7A00' : i % 3 === 1 ? '#3B82F6' : '#8B5CF6',
  }));

  const floatingCards = [
    {
      icon: Ticket,
      title: "Ticket Booking",
      desc: "Instant Confirm",
      glow: "border-orange-500/20 hover:border-orange-500/40 shadow-orange-500/5",
      iconColor: "text-orange-400",
      delay: 0,
      position: "lg:top-[12%] lg:left-[12%] xl:left-[18%]",
      yRange: [-10, 10],
      duration: 5
    },
    {
      icon: Search,
      title: "Train Search",
      desc: "142 Trains Active",
      glow: "border-blue-500/20 hover:border-blue-500/40 shadow-blue-500/5",
      iconColor: "text-blue-400",
      delay: 1,
      position: "lg:top-[12%] lg:right-[12%] xl:right-[18%]",
      yRange: [-12, 12],
      duration: 6
    },
    {
      icon: Zap,
      title: "Seat Availability",
      desc: "2A: Available (12)",
      glow: "border-emerald-500/20 hover:border-emerald-500/40 shadow-emerald-500/5",
      iconColor: "text-emerald-400",
      delay: 2,
      position: "lg:top-[45%] lg:right-[6%] xl:right-[12%]",
      yRange: [-8, 8],
      duration: 7
    },
    {
      icon: MapPin,
      title: "PNR Tracking",
      desc: "Chart Prepared",
      glow: "border-purple-500/20 hover:border-purple-500/40 shadow-purple-500/5",
      iconColor: "text-purple-400",
      delay: 3,
      position: "lg:bottom-[28%] lg:right-[12%] xl:right-[18%]",
      yRange: [-14, 14],
      duration: 8
    },
    {
      icon: MessageSquare,
      title: "Voice Assistant",
      desc: "Listening...",
      glow: "border-pink-500/20 hover:border-pink-500/40 shadow-pink-500/5",
      iconColor: "text-pink-400",
      delay: 4,
      position: "lg:bottom-[28%] lg:left-[12%] xl:left-[18%]",
      yRange: [-10, 10],
      duration: 5.5
    },
    {
      icon: Cpu,
      title: "AI Agent",
      desc: "Route Optimized",
      glow: "border-cyan-500/20 hover:border-cyan-500/40 shadow-cyan-500/5",
      iconColor: "text-cyan-400",
      delay: 5,
      position: "lg:top-[45%] lg:left-[6%] xl:left-[12%]",
      yRange: [-12, 12],
      duration: 6.5
    }
  ];

  return (
    <div
      ref={containerRef}
      className="min-h-screen w-full relative flex items-center justify-center bg-[#020408] overflow-hidden"
      onMouseMove={handleMouseMove}
    >
      {/* Background gradients */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#02050e] via-[#050b18] to-[#0f071e]" />
      
      {/* 3D Perspective Grid */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        <div
          className="absolute bottom-0 w-full h-[65%] opacity-[0.08] border-t border-blue-500/30"
          style={{
            backgroundImage: 'linear-gradient(rgba(59, 130, 246, 0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.15) 1px, transparent 1px)',
            backgroundSize: '50px 50px',
            transform: 'perspective(600px) rotateX(60deg) scale(1.6)',
            transformOrigin: 'bottom center',
          }}
        />
      </div>

      {/* Mouse Following Light Effect */}
      <div
        className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-300 opacity-80"
        style={{
          background: `radial-gradient(700px circle at ${mousePos.x}px ${mousePos.y}px, rgba(59, 130, 246, 0.08) 0%, rgba(249, 115, 22, 0.04) 40%, rgba(139, 92, 246, 0.02) 70%, transparent 100%)`
        }}
      />

      {/* Floating particles & waves */}
      {particles.map((p, i) => <Particle key={i} {...p} />)}
      <EnergyWaves />

      {/* Holographic Station Network */}
      <HolographicNetwork />

      {/* Maglev Train (Background) */}
      <MaglevTrain />

      {/* Floating status cards around the login card */}
      {floatingCards.map((c, idx) => <FloatingCard key={idx} {...c} />)}

      {/* CENTER LOGIN CARD */}
      <motion.div
        className="relative z-10 w-full max-w-[430px] px-4"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      >
        <motion.div
          className="relative rounded-3xl overflow-hidden p-8"
          style={{
            background: 'rgba(5, 8, 16, 0.75)',
            backdropFilter: 'blur(28px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 25px 60px rgba(0, 0, 0, 0.7), 0 0 40px rgba(59, 130, 246, 0.15), 0 0 60px rgba(249, 115, 22, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
          }}
          animate={{ y: [-6, 6] }}
          transition={{
            duration: 6,
            repeat: Infinity,
            repeatType: 'reverse',
            ease: 'easeInOut'
          }}
          whileHover={{
            boxShadow: '0 30px 70px rgba(0, 0, 0, 0.8), 0 0 50px rgba(59, 130, 246, 0.25), 0 0 80px rgba(249, 115, 22, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
          }}
        >
          {/* Top orange & blue dual gradient accent */}
          <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-[#FF7A00] via-[#3B82F6] to-[#8B5CF6]" />

          {/* Logo / Branding */}
          <div className="flex items-center justify-center gap-2.5 mb-6">
            <div className="p-2 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 shadow-md shadow-orange-500/20">
              <Train size={18} className="text-white" />
            </div>
            <div>
              <span className="text-xl font-black text-white tracking-tight">TrainGPT</span>
              <span className="ml-1.5 text-[9px] font-bold text-orange-400 bg-orange-500/15 border border-orange-500/25 px-1.5 py-0.5 rounded-md font-mono">AI</span>
            </div>
          </div>

          {/* AI Robot Avatar with energy rings */}
          <div className="flex justify-center mb-5">
            <div className="relative w-18 h-18 flex items-center justify-center">
              <motion.div
                className="absolute inset-0 rounded-full border border-dashed border-blue-500/35"
                animate={{ rotate: 360 }}
                transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
              />
              <motion.div
                className="absolute -inset-1.5 rounded-full border border-dotted border-orange-500/30"
                animate={{ rotate: -360 }}
                transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
              />
              <motion.div
                className="absolute -inset-3.5 rounded-full border border-blue-400/10"
                animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.6, 0.3] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              />
              <div className="w-13 h-13 rounded-2xl bg-gradient-to-br from-blue-950/80 to-slate-950 border border-blue-500/30 flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.3)]">
                <Bot size={26} className="text-blue-400" />
              </div>
            </div>
          </div>

          {/* Title & Subtitle */}
          <div className="text-center mb-6">
            <h2 className="text-2xl font-black text-white tracking-tight">Welcome to TrainGPT</h2>
            <p className="text-xs text-zinc-400 mt-1.5 font-medium">Your AI Railway Assistant</p>
          </div>

          {/* Social Sign Ins */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <motion.button
              id="login-google"
              onClick={() => handleSocialLogin('Google')}
              className="flex items-center justify-center gap-2 py-2.5 rounded-xl border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-800/60 hover:border-zinc-700 transition-all text-xs font-semibold text-zinc-300"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google
            </motion.button>

            <motion.button
              id="login-github"
              onClick={() => handleSocialLogin('GitHub')}
              className="flex items-center justify-center gap-2 py-2.5 rounded-xl border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-800/60 hover:border-zinc-700 transition-all text-xs font-semibold text-zinc-300"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-zinc-300">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              GitHub
            </motion.button>
          </div>

          {/* Divider */}
          <div className="relative flex items-center gap-3 mb-5">
            <div className="flex-1 h-px bg-zinc-800/80" />
            <span className="text-[10px] text-zinc-500 font-semibold px-1 uppercase tracking-wider">or enter credentials</span>
            <div className="flex-1 h-px bg-zinc-800/80" />
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-1.5">
              <label htmlFor="login-email" className="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                Email Address
              </label>
              <div className="relative">
                <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={handleChange}
                  onFocus={() => setFocusField('email')}
                  onBlur={() => setFocusField(null)}
                  placeholder="you@example.com"
                  disabled={loading}
                  className="w-full bg-slate-900/60 text-zinc-100 placeholder-zinc-700 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none transition-all disabled:opacity-50 border border-zinc-800"
                  style={{
                    borderColor: focusField === 'email' ? 'rgba(59, 130, 246, 0.7)' : 'rgba(63, 63, 70, 0.4)',
                    boxShadow: focusField === 'email' ? '0 0 15px rgba(59, 130, 246, 0.2)' : 'none',
                  }}
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="login-password" className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                  Password
                </label>
                <button type="button" className="text-[10px] text-blue-400 hover:text-blue-300 font-semibold transition-colors">
                  Forgot Password?
                </button>
              </div>
              <div className="relative">
                <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={form.password}
                  onChange={handleChange}
                  onFocus={() => setFocusField('password')}
                  onBlur={() => setFocusField(null)}
                  placeholder="••••••••••"
                  disabled={loading}
                  className="w-full bg-slate-900/60 text-zinc-100 placeholder-zinc-700 rounded-xl pl-10 pr-11 py-3 text-sm focus:outline-none transition-all disabled:opacity-50 border border-zinc-800"
                  style={{
                    borderColor: focusField === 'password' ? 'rgba(249, 115, 22, 0.7)' : 'rgba(63, 63, 70, 0.4)',
                    boxShadow: focusField === 'password' ? '0 0 15px rgba(249, 115, 22, 0.15)' : 'none',
                  }}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer group select-none">
                <input
                  type="checkbox"
                  name="remember"
                  checked={form.remember}
                  onChange={handleChange}
                  className="sr-only"
                />
                <motion.div
                  className="w-4 h-4 rounded border flex items-center justify-center transition-all bg-slate-950/80 border-zinc-700"
                  style={{
                    background: form.remember ? '#FF7A00' : 'transparent',
                    borderColor: form.remember ? '#FF7A00' : 'rgba(63, 63, 70, 0.8)',
                  }}
                  whileTap={{ scale: 0.9 }}
                >
                  <AnimatePresence>
                    {form.remember && (
                      <motion.svg key="check" width="9" height="9" viewBox="0 0 10 10"
                        initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                        <polyline points="1.5,5 4,7.5 8.5,2.5" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </motion.svg>
                    )}
                  </AnimatePresence>
                </motion.div>
                <span className="text-xs text-zinc-400 group-hover:text-zinc-300 transition-colors">Remember Me</span>
              </label>
            </div>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  className="flex items-center gap-2 bg-rose-500/10 border border-rose-500/25 rounded-xl px-4 py-2.5 text-rose-400 text-xs font-semibold"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Shield size={12} className="shrink-0" />
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Sign In Button */}
            <motion.button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full relative overflow-hidden rounded-xl py-3.5 font-bold text-sm text-white flex items-center justify-center gap-2 transition-all disabled:cursor-not-allowed shadow-[0_8px_25px_rgba(249,115,22,0.25)]"
              style={{
                background: 'linear-gradient(135deg, #FF7A00, #E85C00, #3B82F6)',
                backgroundSize: '200% auto',
              }}
              whileHover={{
                scale: 1.02,
                boxShadow: '0 12px 35px rgba(249,115,22,0.4)',
                backgroundPosition: 'right center'
              }}
              whileTap={{ scale: 0.98 }}
            >
              {/* Shimmer */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent -skew-x-12"
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 2.2, repeat: Infinity, repeatDelay: 1 }}
              />
              {loading ? (
                <>
                  <motion.svg className="w-4 h-4" viewBox="0 0 24 24" fill="none"
                    animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}>
                    <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="3" strokeOpacity="0.3" />
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="white" strokeWidth="3" strokeLinecap="round" />
                  </motion.svg>
                  Initializing...
                </>
              ) : (
                <>
                  <Train size={15} />
                  <span>Sign In to TrainGPT</span>
                  <ChevronRight size={14} className="ml-0.5" />
                </>
              )}
            </motion.button>
          </form>

          {/* Continue as Guest */}
          <motion.button
            type="button"
            onClick={() => { login({ username: 'Guest' }); navigate('/'); }}
            className="w-full mt-3 py-2.5 rounded-xl border border-zinc-800 bg-zinc-900/10 hover:bg-zinc-800/30 hover:border-zinc-700 text-zinc-400 hover:text-zinc-200 text-xs font-semibold transition-all"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
          >
            Continue as Guest · No account needed
          </motion.button>

          {/* Sign Up Link */}
          <p className="mt-5 text-center text-xs text-zinc-500 font-medium">
            New to TrainGPT?{' '}
            <button
              onClick={() => { login({ username: 'New User' }); navigate('/'); }}
              className="text-orange-400 hover:text-orange-300 font-bold transition-colors"
            >
              Create Account
            </button>
          </p>
        </motion.div>
      </motion.div>

      {/* Bottom telemetry HUD timeline */}
      <RouteTimeline />
    </div>
  );
}
