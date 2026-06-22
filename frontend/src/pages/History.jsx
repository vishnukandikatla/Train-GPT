import { useEffect, useState } from 'react';
import { bookingService } from '../services/api';
import { Ticket, Calendar, Train, Users, XCircle, AlertCircle, RefreshCw } from 'lucide-react';

export default function History() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Cancellation Modal State
  const [selectedPnr, setSelectedPnr] = useState(null);
  const [cancellationResult, setCancellationResult] = useState(null);
  const [cancelling, setCancelling] = useState(false);

  const fetchBookings = () => {
    setLoading(true);
    setError('');
    bookingService.getBookings('guest_user')
      .then((res) => {
        setBookings(res.data.bookings || []);
      })
      .catch((err) => {
        console.error(err);
        setError('Failed to retrieve booking records.');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setTimeout(fetchBookings, 0);
  }, []);

  const handleCancelClick = (pnr) => {
    setSelectedPnr(pnr);
    setCancellationResult(null);
  };

  const handleConfirmCancellation = async () => {
    if (!selectedPnr) return;
    setCancelling(true);
    try {
      const res = await bookingService.cancelBooking(selectedPnr);
      setCancellationResult(res.data);
      // Refresh list
      bookingService.getBookings('guest_user').then((r) => setBookings(r.data.bookings || []));
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to cancel the booking. Please try again.');
    } finally {
      setCancelling(false);
    }
  };

  const getStatusBadgeClass = (status) => {
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-900 dark:text-zinc-50">Booking History</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">View and manage your active train tickets, seating details, and cancellations.</p>
        </div>
        <button
          onClick={fetchBookings}
          className="flex items-center gap-1.5 px-4 py-2 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-semibold hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh List
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/30 text-rose-800 dark:text-rose-400 rounded-lg p-4 flex gap-3 text-sm">
          <AlertCircle className="shrink-0" size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading && bookings.length === 0 ? (
        <div className="text-center py-12 text-zinc-400 italic">Loading tickets...</div>
      ) : bookings.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-[#0c0c0f]">
          <Ticket className="mx-auto text-zinc-300 dark:text-zinc-800 mb-4" size={48} />
          <h3 className="font-bold text-sm text-zinc-700 dark:text-zinc-300 mb-1">No Bookings Found</h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-500 mb-4">You have not booked any train tickets yet.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {bookings.map((booking) => (
            <div key={booking.pnr} className="bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm flex flex-col md:flex-row">
              {/* Left Column: PNR & Route details */}
              <div className="p-6 md:w-2/3 space-y-4 border-b md:border-b-0 md:border-r border-zinc-200 dark:border-zinc-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Train size={18} className="text-blue-500" />
                    <span className="font-bold text-sm">{booking.train_no} - {booking.train_name}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${getStatusBadgeClass(booking.status)}`}>
                    {booking.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-zinc-400 block mb-0.5">Route</span>
                    <span className="font-bold text-zinc-800 dark:text-zinc-200">{booking.source} ➔ {booking.destination}</span>
                  </div>
                  <div>
                    <span className="text-zinc-400 block mb-0.5">Journey Date</span>
                    <span className="font-bold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                      <Calendar size={12} />
                      {booking.journey_date}
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-400 block mb-0.5">Travel Class</span>
                    <span className="font-bold text-zinc-800 dark:text-zinc-200">{booking.class_type}</span>
                  </div>
                  <div>
                    <span className="text-zinc-400 block mb-0.5">Booking PNR</span>
                    <span className="font-mono font-bold text-blue-500">{booking.pnr}</span>
                  </div>
                </div>

                {/* Passengers List */}
                <div className="space-y-1.5 pt-2">
                  <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1">
                    <Users size={12} />
                    Passengers & Seats
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {booking.passengers.map((p, idx) => (
                      <span key={idx} className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2.5 py-1 text-xs font-mono">
                        {p.name} ({p.age}/{p.gender[0]}) - <strong className="text-blue-500">{p.seat_no}</strong>
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Column: Actions */}
              <div className="p-6 md:w-1/3 flex flex-col justify-center items-center gap-4 bg-zinc-50/50 dark:bg-zinc-900/10">
                {booking.status !== 'Cancelled' ? (
                  <button
                    onClick={() => handleCancelClick(booking.pnr)}
                    className="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold shadow-sm transition-colors flex items-center justify-center gap-1.5"
                  >
                    <XCircle size={14} />
                    Cancel Reservation
                  </button>
                ) : (
                  <div className="text-center space-y-1 text-zinc-400 dark:text-zinc-600">
                    <XCircle size={28} className="mx-auto" />
                    <span className="text-xs font-semibold block">Ticket Cancelled</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Cancellation Modal */}
      {selectedPnr && (
        <div className="fixed inset-0 bg-zinc-950/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-50">Confirm Ticket Cancellation</h3>
            
            {!cancellationResult ? (
              <>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  Are you sure you want to cancel booking for PNR <strong className="font-mono text-blue-500">{selectedPnr}</strong>? 
                  A flat cancellation fee will be deducted depending on the reservation class:
                </p>
                <div className="bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 rounded-lg p-3 text-xs space-y-2">
                  <div className="flex justify-between">
                    <span>1A / 2A Classes Charge</span>
                    <span className="font-bold text-zinc-800 dark:text-zinc-200">Rs. 240</span>
                  </div>
                  <div className="flex justify-between">
                    <span>3A / Sleeper Classes Charge</span>
                    <span className="font-bold text-zinc-800 dark:text-zinc-200">Rs. 120</span>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    onClick={() => setSelectedPnr(null)}
                    className="px-4 py-2 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-semibold hover:bg-zinc-50 dark:hover:bg-zinc-900"
                  >
                    Close
                  </button>
                  <button
                    onClick={handleConfirmCancellation}
                    disabled={cancelling}
                    className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold"
                  >
                    {cancelling ? 'Cancelling...' : 'Confirm Cancel'}
                  </button>
                </div>
              </>
            ) : (
              <div className="space-y-4">
                <div className="bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/30 text-emerald-800 dark:text-emerald-400 rounded-lg p-4 flex gap-3 text-xs">
                  <XCircle className="shrink-0" size={18} />
                  <span>Ticket cancelled successfully. Seat allocations have been released back.</span>
                </div>
                <div className="bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4 text-xs space-y-2 font-mono">
                  <div className="flex justify-between">
                    <span>PNR</span>
                    <span className="font-bold text-blue-500">{cancellationResult.pnr}</span>
                  </div>
                  <div className="flex justify-between border-b border-zinc-200/50 dark:border-zinc-800/50 pb-2">
                    <span>Cancellation Fee</span>
                    <span className="font-bold text-rose-500">Rs. {cancellationResult.cancellation_charge}</span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span>Refunded Amount</span>
                    <span className="font-bold text-emerald-500 text-sm">Rs. {cancellationResult.refund_amount}</span>
                  </div>
                </div>
                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => setSelectedPnr(null)}
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
