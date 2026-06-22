import { Search, ShieldCheck, CreditCard, Ticket, CheckSquare, Loader2 } from 'lucide-react';

export default function BookingFlow({ activeAgent, lastToolExecuted, bookingSuccess }) {
  let currentStep = 0;

  if (bookingSuccess) {
    currentStep = 5; // Confirmed
  } else if (activeAgent === 'SearchAgent') {
    currentStep = 1; // Searching
  } else if (activeAgent === 'AvailabilityAgent' || lastToolExecuted === 'check_availability') {
    currentStep = 2; // Availability
  } else if (activeAgent === 'FareAgent' || lastToolExecuted === 'get_fare') {
    currentStep = 3; // Fare calculation
  } else if (activeAgent === 'BookingAgent' || lastToolExecuted === 'book_ticket') {
    currentStep = 4; // Booking
  } else if (activeAgent === 'OrchestratorAgent') {
    currentStep = 1; // Default to Search step when Orchestrator is active
  }

  const steps = [
    { label: 'Start Request', icon: Search, desc: 'Listening to details...' },
    { label: 'Search Train', icon: Search, desc: 'Finding routes...' },
    { label: 'Check Availability', icon: ShieldCheck, desc: 'Verifying seats...' },
    { label: 'Calculate Fare', icon: CreditCard, desc: 'Computing pricing...' },
    { label: 'Book Ticket', icon: Ticket, desc: 'Reserving & Allocating...' },
    { label: 'PNR Generated', icon: CheckSquare, desc: 'Booking confirmed!' },
  ];

  return (
    <div className="glass-panel p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-md">
      <h3 className="text-sm font-bold tracking-wide uppercase text-zinc-500 dark:text-zinc-400 mb-4">
        Booking Workflow Status
      </h3>
      <div className="space-y-4">
        {steps.slice(1).map((step, index) => {
          const stepIndex = index + 1;
          const isCompleted = currentStep > stepIndex;
          const isActive = currentStep === stepIndex;
          const StepIcon = step.icon;

          return (
            <div key={index} className="flex items-center gap-4">
              {/* Stepper Node Icon */}
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center border transition-all duration-300 ${
                  isCompleted
                    ? 'bg-emerald-500 border-emerald-500 text-white'
                    : isActive
                    ? 'bg-blue-600 border-blue-600 text-white animate-pulse'
                    : 'bg-zinc-100 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-400 dark:text-zinc-500'
                }`}
              >
                {isActive && !isCompleted ? (
                  <Loader2 className="animate-spin" size={16} />
                ) : (
                  <StepIcon size={16} />
                )}
              </div>

              {/* Step Label & Status */}
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-sm font-medium ${
                      isActive
                        ? 'text-blue-600 dark:text-blue-400 font-semibold'
                        : isCompleted
                        ? 'text-zinc-800 dark:text-zinc-300'
                        : 'text-zinc-400 dark:text-zinc-600'
                    }`}
                  >
                    {step.label}
                  </span>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                    {isCompleted ? 'Done' : isActive ? 'In Progress' : 'Pending'}
                  </span>
                </div>
                {/* Loader or Progress bar for active step */}
                {isActive && (
                  <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-1 rounded-full mt-1.5 overflow-hidden">
                    <div className="bg-blue-500 h-full rounded-full animate-pulse style-width-progress" style={{ width: '60%' }}></div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
