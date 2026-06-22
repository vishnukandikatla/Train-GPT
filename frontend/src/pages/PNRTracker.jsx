import { useState } from 'react';
import { pnrService } from '../services/api';
import { Search, Train, Calendar, Users, Ticket, ShieldAlert } from 'lucide-react';

export default function PNRTracker() {
  const [pnr, setPnr] = useState('');
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!/^\d{10}$/.test(pnr)) {
      setError('Please enter a valid 10-digit numeric PNR.');
      setTicket(null);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const res = await pnrService.checkStatus(pnr);
      setTicket(res.data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'PNR not found in system databases. Make sure to input a valid PNR generated during booking.');
      setTicket(null);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'Confirmed':
        return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-500/20';
      case 'Waitlisted':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400 border-amber-500/20';
      case 'Cancelled':
        return 'bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-400 border-rose-500/20';
      default:
        return 'bg-zinc-100 text-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 border-zinc-500/20';
    }
  };

  return (
    <div className="max-w-[1600px] mx-auto p-6 space-y-8 mt-12 max-w-4xl">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-zinc-900 dark:text-zinc-50">PNR Status Tracker</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Enter your 10-digit Passenger Name Record (PNR) to track your live itinerary status.</p>
      </div>

      {/* Input Box */}
      <form onSubmit={handleSearch} className="flex gap-3 bg-white dark:bg-[#0c0c0f] p-4 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm">
        <div className="relative flex-1">
          <Ticket className="absolute left-3.5 top-3.5 text-zinc-400" size={18} />
          <input
            type="text"
            value={pnr}
            onChange={(e) => setPnr(e.target.value.replace(/\D/g, '').slice(0, 10))}
            placeholder="Enter 10-digit PNR Number (e.g. 1234567890)"
            className="w-full bg-zinc-50 dark:bg-[#09090b] border border-zinc-200 dark:border-zinc-800 rounded-lg pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          disabled={loading || pnr.length !== 10}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg px-6 py-3 font-semibold shadow-md flex items-center gap-2 transition-all"
        >
          {loading ? 'Searching...' : 'Check Status'}
          <Search size={16} />
        </button>
      </form>

      {/* Error state */}
      {error && (
        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/30 text-rose-800 dark:text-rose-400 rounded-lg p-4 flex gap-3 text-sm">
          <ShieldAlert className="shrink-0" size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Booking Details Display */}
      {ticket && ticket.status === 'success' && (
        <div className="bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-md">
          {/* Card Header */}
          <div className="bg-zinc-50 dark:bg-zinc-900/60 p-6 border-b border-zinc-200 dark:border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">PNR NUMBER</span>
              <h2 className="text-2xl font-mono font-extrabold text-zinc-950 dark:text-zinc-50 tracking-wide">{ticket.pnr}</h2>
            </div>
            <div className="flex gap-2">
              <span className={`px-3 py-1.5 rounded-full border text-xs font-semibold tracking-wide uppercase ${getStatusBadgeColor(ticket.booking_status)}`}>
                {ticket.booking_status}
              </span>
            </div>
          </div>

          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Journey Details */}
            <div className="space-y-6">
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                <Train size={14} />
                Journey Details
              </h3>
              <div className="bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4 space-y-4">
                <div className="flex justify-between items-center pb-2 border-b border-zinc-200/50 dark:border-zinc-800/50">
                  <span className="text-xs text-zinc-500">Train</span>
                  <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{ticket.train_no} - {ticket.train_name}</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-zinc-200/50 dark:border-zinc-800/50">
                  <span className="text-xs text-zinc-500">Route</span>
                  <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1">
                    {ticket.source}
                    <span className="text-zinc-400">➔</span>
                    {ticket.destination}
                  </span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-zinc-200/50 dark:border-zinc-800/50">
                  <span className="text-xs text-zinc-500">Date of Journey</span>
                  <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                    <Calendar size={14} className="text-zinc-400" />
                    {ticket.journey_date}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-500">Class</span>
                  <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{ticket.class_type}</span>
                </div>
              </div>
            </div>

            {/* Passenger & Berth Details */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                <Users size={14} />
                Passenger Details
              </h3>
              <div className="overflow-hidden border border-zinc-200/50 dark:border-zinc-800/50 rounded-lg">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-zinc-50 dark:bg-zinc-900/30 text-[10px] font-bold text-zinc-500 uppercase tracking-wider border-b border-zinc-200 dark:border-zinc-800">
                    <tr>
                      <th className="p-3">#</th>
                      <th className="p-3">Name</th>
                      <th className="p-3">Age/Gender</th>
                      <th className="p-3 text-right">Berth Allocation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-200/50 dark:divide-zinc-800/50 text-xs text-zinc-700 dark:text-zinc-300">
                    {ticket.passengers.map((p, idx) => (
                      <tr key={idx}>
                        <td className="p-3 font-mono text-zinc-500">{idx + 1}</td>
                        <td className="p-3 font-semibold">{p.name}</td>
                        <td className="p-3">{p.age} / {p.gender}</td>
                        <td className="p-3 text-right font-mono font-bold text-blue-600 dark:text-blue-400">{p.seat_no}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
