import { useEffect, useState, useRef } from 'react';
import { getWebSocketUrl } from '../../services/api';
import { Terminal, Activity, Cpu, AlertTriangle, Hourglass } from 'lucide-react';

export default function AgentMonitor() {
  const [agents, setAgents] = useState({
    OrchestratorAgent: 'Idle',
    SearchAgent: 'Idle',
    AvailabilityAgent: 'Idle',
    FareAgent: 'Idle',
    BookingAgent: 'Idle',
    PnrAgent: 'Idle',
    CancellationAgent: 'Idle',
  });
  
  const [timeline, setTimeline] = useState([]);
  const [wsStatus, setWsStatus] = useState('connecting');
  const scrollRef = useRef(null);

  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;

    const connect = () => {
      setWsStatus('connecting');
      const wsUrl = getWebSocketUrl('/ws/agents');
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsStatus('connected');
        // Seed initial timeline
        setTimeline((prev) => [
          ...prev,
          {
            time: new Date().toLocaleTimeString(),
            message: 'Connected to TrainGPT AI Multi-Agent Coordinator.',
            type: 'system'
          }
        ]);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'agent_status') {
            setAgents((prev) => ({
              ...prev,
              [data.agent]: data.status,
            }));
            
            if (data.status === 'Running') {
              setTimeline((prev) => [
                ...prev,
                {
                  time: new Date().toLocaleTimeString(),
                  message: `${data.agent} is active: ${data.message || 'Processing task'}`,
                  type: 'agent_start'
                }
              ]);
            }
          } else if (data.type === 'tool_execution') {
            setTimeline((prev) => [
              ...prev,
              {
                time: new Date().toLocaleTimeString(),
                message: `Tool [${data.tool}] executed: ${data.message} (${data.execution_time})`,
                type: data.status === 'success' ? 'tool_success' : 'tool_error'
              }
            ]);
          } else if (data.type === 'timeline') {
            setTimeline((prev) => [
              ...prev,
              {
                time: data.time || new Date().toLocaleTimeString(),
                message: data.message,
                type: 'info'
              }
            ]);
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      ws.onclose = () => {
        setWsStatus('disconnected');
        // Set all agents to idle
        setAgents({
          OrchestratorAgent: 'Idle',
          SearchAgent: 'Idle',
          AvailabilityAgent: 'Idle',
          FareAgent: 'Idle',
          BookingAgent: 'Idle',
          PnrAgent: 'Idle',
          CancellationAgent: 'Idle',
        });
        // Auto-reconnect after 3 seconds
        reconnectTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket Error:', err);
        ws.close();
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  // Autoscroll timeline
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [timeline]);

  const getAgentColorClass = (status) => {
    switch (status) {
      case 'Running':
        return 'border-emerald-500 bg-emerald-500/10 text-emerald-400';
      case 'Error':
        return 'border-rose-500 bg-rose-500/10 text-rose-400';
      default:
        return 'border-zinc-800 bg-zinc-900/40 text-zinc-400';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Running':
        return <Activity size={14} className="animate-spin text-emerald-400" />;
      case 'Error':
        return <AlertTriangle size={14} className="text-rose-400" />;
      default:
        return <Hourglass size={14} className="text-zinc-500" />;
    }
  };

  const getTimelineItemColor = (type) => {
    switch (type) {
      case 'tool_success':
        return 'text-emerald-400';
      case 'tool_error':
        return 'text-rose-400 font-bold';
      case 'agent_start':
        return 'text-blue-400';
      case 'system':
        return 'text-zinc-500 italic';
      default:
        return 'text-zinc-300';
    }
  };

  return (
    <div className="glass-panel rounded-xl overflow-hidden shadow-lg border border-zinc-200 dark:border-zinc-800 flex flex-col h-full glow-blue">
      {/* Header */}
      <div className="bg-zinc-100 dark:bg-zinc-900/60 p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="text-blue-500 animate-pulse" size={18} />
          <h3 className="font-bold text-sm tracking-wide uppercase text-zinc-700 dark:text-zinc-300">Live Agent Monitoring</h3>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${wsStatus === 'connected' ? 'bg-emerald-500 status-indicator-active' : 'bg-rose-500'}`} />
          <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400 capitalize">{wsStatus}</span>
        </div>
      </div>

      <div className="flex-1 p-4 flex flex-col gap-4 overflow-hidden">
        {/* Active Agents Grid */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2">Active Agents</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {Object.entries(agents).map(([name, status]) => (
              <div
                key={name}
                className={`p-2.5 border rounded-lg flex flex-col gap-1 transition-all ${getAgentColorClass(status)}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold truncate">{name.replace('Agent', '')}</span>
                  {getStatusIcon(status)}
                </div>
                <span className="text-[10px] uppercase font-bold tracking-wider opacity-80">{status}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Timeline Log */}
        <div className="flex-1 flex flex-col min-h-[180px] overflow-hidden">
          <div className="flex items-center gap-1.5 mb-2">
            <Terminal size={14} className="text-zinc-500" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Execution Timeline</h4>
          </div>
          <div
            ref={scrollRef}
            className="flex-1 bg-zinc-950 dark:bg-black p-3 rounded-lg border border-zinc-200 dark:border-zinc-800 font-mono text-xs overflow-y-auto space-y-2 select-text"
          >
            {timeline.length === 0 ? (
              <div className="text-zinc-600 italic text-center py-4">Waiting for agent activity...</div>
            ) : (
              timeline.map((item, idx) => (
                <div key={idx} className="flex gap-2 items-start leading-relaxed border-b border-zinc-900 pb-1.5 last:border-b-0">
                  <span className="text-zinc-600 font-medium shrink-0">[{item.time}]</span>
                  <span className={`${getTimelineItemColor(item.type)} flex-1 break-words`}>
                    {item.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
