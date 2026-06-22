import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { analyticsService } from '../services/api';
import { Cpu, Ticket, Search, Users, Activity, RefreshCw, BarChart2 } from 'lucide-react';

export default function Dashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = () => {
    setLoading(true);
    analyticsService.getAnalytics()
      .then((res) => {
        setAnalytics(res.data);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setTimeout(fetchAnalytics, 0);
    // Poll every 10 seconds for live updates
    const interval = setInterval(fetchAnalytics, 10000);
    return () => clearInterval(interval);
  }, []);

  const stats = analytics?.stats || {
    bookings_today: 1450,
    search_requests: 3500,
    active_users: 890,
    active_agents: 6
  };

  const logs = analytics?.logs || [];
  const popularityData = analytics?.popularity_data || [
    { name: 'Karnataka Express', value: 124 },
    { name: 'Godavari Express', value: 85 },
    { name: 'Rajdhani Express', value: 62 },
    { name: 'Duronto Express', value: 37 }
  ];

  // ECharts Config
  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} bookings ({d}%)',
      backgroundColor: 'rgba(9, 9, 11, 0.95)',
      borderColor: '#27272a',
      textStyle: { color: '#fafafa', fontFamily: 'DM Sans, sans-serif' }
    },
    legend: {
      bottom: '0%',
      left: 'center',
      textStyle: { color: '#71717a', fontFamily: 'DM Sans, sans-serif' }
    },
    series: [
      {
        name: 'Route Popularity',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: 'transparent',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
            formatter: '{b}'
          }
        },
        labelLine: {
          show: false
        },
        data: popularityData,
        color: ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4"]
      }
    ]
  };

  const getStatusBadge = (status) => {
    return status === 'success' 
      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-500/20'
      : 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 border-rose-500/20';
  };

  return (
    <div className="max-w-[1600px] mx-auto p-6 space-y-8 mt-12">
      {/* Header Row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-900 dark:text-zinc-50">Railway Analytics</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Real-time stats, AI agent activities, and booking insights.</p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="flex items-center gap-1.5 px-4 py-2 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-semibold hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh Stats
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Bookings Today', val: stats.bookings_today, icon: Ticket, trend: '+14% this hour', color: 'text-blue-500' },
          { label: 'Search Queries', val: stats.search_requests, icon: Search, trend: '+28% today', color: 'text-amber-500' },
          { label: 'Active Users', val: stats.active_users, icon: Users, trend: '+8% live', color: 'text-emerald-500' },
          { label: 'AI Agents active', val: stats.active_agents, icon: Cpu, trend: 'Coordinating', color: 'text-indigo-500' },
        ].map((kpi, idx) => (
          <div key={idx} className="p-6 bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm flex items-center justify-between">
            <div className="space-y-2">
              <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{kpi.label}</span>
              <h2 className="text-3xl font-extrabold tracking-tight text-zinc-950 dark:text-zinc-50">{kpi.val}</h2>
              <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-semibold uppercase">{kpi.trend}</span>
            </div>
            <div className={`p-3 rounded-lg bg-zinc-100 dark:bg-zinc-900 ${kpi.color}`}>
              <kpi.icon size={22} />
            </div>
          </div>
        ))}
      </div>

      {/* Main split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Popular routes visualization (1/3) */}
        <div className="glass-panel p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col h-[400px]">
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={16} className="text-blue-500" />
            <h3 className="font-bold text-sm text-zinc-800 dark:text-zinc-200">Route Popularity Index</h3>
          </div>
          <div className="flex-1 min-h-[250px]">
            <ReactECharts option={chartOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        {/* Live logs auditing table (2/3) */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col h-[400px]">
          <div className="flex items-center gap-2 mb-4 justify-between">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-emerald-500" />
              <h3 className="font-bold text-sm text-zinc-800 dark:text-zinc-200">AI Agent Audit Logs</h3>
            </div>
            <span className="text-[10px] font-mono bg-zinc-100 dark:bg-zinc-900 px-2 py-0.5 rounded text-zinc-400">Auto-update active</span>
          </div>

          <div className="flex-1 overflow-auto border border-zinc-200/50 dark:border-zinc-800/80 rounded-lg">
            <table className="w-full text-left border-collapse">
              <thead className="bg-zinc-100 dark:bg-zinc-900/50 sticky top-0 text-xs font-semibold text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800">
                <tr>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Agent</th>
                  <th className="p-3">Tool</th>
                  <th className="p-3">Speed</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Activity Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200/40 dark:divide-zinc-800/40 text-xs text-zinc-700 dark:text-zinc-300">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-zinc-500 italic">No agent log traces available yet. Invoke the chat to start recording.</td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-zinc-100/50 dark:hover:bg-zinc-800/20 transition-colors">
                      <td className="p-3 font-mono text-[10px] whitespace-nowrap">{new Date(log.timestamp).toLocaleTimeString()}</td>
                      <td className="p-3 font-semibold text-blue-600 dark:text-blue-400">{log.agent_name.replace('Agent', '')}</td>
                      <td className="p-3"><code className="bg-zinc-100 dark:bg-zinc-900 px-1 py-0.5 rounded font-mono text-[10px]">{log.tool_name || 'N/A'}</code></td>
                      <td className="p-3 font-mono text-zinc-500">{log.execution_time}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-medium ${getStatusBadge(log.status)}`}>
                          {log.status}
                        </span>
                      </td>
                      <td className="p-3 max-w-xs truncate" title={log.message}>{log.message}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
