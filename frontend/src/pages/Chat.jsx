import { useState, useEffect, useRef } from 'react';
import { chatService } from '../services/api';
import AgentMonitor from '../components/Monitoring/AgentMonitor';
import BookingFlow from '../components/Booking/BookingFlow';
import { Send, Mic, MicOff, Volume2, VolumeX, Bot, User, Sparkles, RefreshCw } from 'lucide-react';
import { getWebSocketUrl } from '../services/api';

export default function Chat() {
  const [sessionId] = useState(() => {
    const savedId = localStorage.getItem('traingpt_session_id');
    if (savedId) return savedId;
    const newId = `session_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('traingpt_session_id', newId);
    return newId;
  });

  const [messages, setMessages] = useState(() => {
    const savedMsgs = localStorage.getItem(`traingpt_messages_${sessionId}`);
    if (savedMsgs) {
      try {
        return JSON.parse(savedMsgs);
      } catch (e) {
        console.error('Failed to parse saved messages:', e);
      }
    }
    return [
      {
        role: 'assistant',
        content: 'Welcome! I am TrainGPT, your AI Railway Booking Assistant. How can I help you today? You can search trains, check seats, calculate fares, book tickets, or track PNRs.'
      }
    ];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Voice Settings
  const [isListening, setIsListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const recognitionRef = useRef(null);
  
  // Real-time Agent Tracking via WS duplication
  const [activeAgent, setActiveAgent] = useState('OrchestratorAgent');
  const [lastTool, setLastTool] = useState('');
  const [bookingSuccess, setBookingSuccess] = useState(false);
  
  const messagesEndRef = useRef(null);
  const handleSubmitRef = useRef(null);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Save messages to localStorage whenever they update
  useEffect(() => {
    localStorage.setItem(`traingpt_messages_${sessionId}`, JSON.stringify(messages));
  }, [messages, sessionId]);

  // Connect to WS in parallel to capture agent/tool changes for the Stepper
  useEffect(() => {
    const wsUrl = getWebSocketUrl('/ws/agents');
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'agent_status' && data.status === 'Running') {
          setActiveAgent(data.agent);
        } else if (data.type === 'tool_execution') {
          setLastTool(data.tool);
          if (data.tool === 'book_ticket' && data.status === 'success') {
            setBookingSuccess(true);
          }
        }
      } catch (err) {
        console.error(err);
      }
    };

    return () => ws.close();
  }, []);

  // Web Speech API - Recognition Setup
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'en-IN';

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
        // Automatically send after voice dictation
        if (handleSubmitRef.current) {
          handleSubmitRef.current(transcript);
        }
      };

      rec.onerror = (err) => {
        console.error('Speech recognition error:', err);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = rec;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Speech Recognition is not supported in this browser. Please use Chrome.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      setInput('');
      recognitionRef.current.start();
    }
  };

  // Web Speech API - Text to Speech Synthesis
  const speakText = (text) => {
    if (!voiceEnabled || !('speechSynthesis' in window)) return;
    
    // Clean up text (remove markdown codes, etc.)
    const cleanText = text.replace(/[*#`_-]/g, '').trim();

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    // Prefer female/assistant voices if available
    const voices = window.speechSynthesis.getVoices();
    const assistantVoice = voices.find(v => v.name.includes('Google') || v.name.includes('Natural'));
    if (assistantVoice) utterance.voice = assistantVoice;
    
    window.speechSynthesis.speak(utterance);
  };

  const handleSubmitMessage = async (textToSend) => {
    const prompt = (textToSend || input).trim();
    if (!prompt) return;

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: prompt }]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatService.sendMessage(prompt, sessionId);
      const reply = response.data.reply;
      
      // Add assistant response
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
      
      // Trigger voice read-back
      speakText(reply);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an issue connecting to the AI agent team. Please verify your GEMINI_API_KEY is configured.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Keep handleSubmitRef current
  useEffect(() => {
    handleSubmitRef.current = handleSubmitMessage;
  });

  const handleSuggestionClick = (prompt) => {
    handleSubmitMessage(prompt);
  };

  const suggestions = [
    'Find trains from Hyderabad (SC) to Bangalore (SBC) on 2026-06-21',
    'Check availability for train 12627 class 3A on 2026-06-21',
    'What is the fare for train 12727 class SL for 2 passengers?',
    'Book 2 tickets on Karnataka Express 12627 class SL on 2026-06-21 for Rajesh age 28 Male and Sneha age 26 Female',
    'Check booking status of PNR 1234567890',
  ];

  return (
    <div className="max-w-[1600px] mx-auto p-6 flex flex-col lg:flex-row gap-6 h-[calc(100vh-100px)] overflow-hidden mt-12">
      {/* Left Chat Window (2/3 width) */}
      <div className="flex-1 flex flex-col bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-md">
        {/* Chat Header */}
        <div className="bg-zinc-50 dark:bg-zinc-950 p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white">
              <Bot size={18} />
            </div>
            <div>
              <h2 className="font-bold text-sm text-zinc-900 dark:text-zinc-50">TrainGPT Booking Assistant</h2>
              <p className="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">Session: {sessionId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* TTS Toggle */}
            <button
              onClick={() => setVoiceEnabled(!voiceEnabled)}
              title={voiceEnabled ? 'Mute Speech' : 'Enable Speech'}
              className={`p-2 rounded-lg border transition-all ${
                voiceEnabled
                  ? 'border-blue-500/30 bg-blue-500/10 text-blue-500'
                  : 'border-zinc-200 dark:border-zinc-800 text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900'
              }`}
            >
              {voiceEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
          </div>
        </div>

        {/* Chat Feed */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-white shrink-0 shadow-sm ${
                  msg.role === 'user' ? 'bg-zinc-700' : 'bg-blue-600'
                }`}
              >
                {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div
                className={`p-3.5 rounded-xl border leading-relaxed text-sm select-text ${
                  msg.role === 'user'
                    ? 'bg-zinc-100 border-zinc-200 dark:bg-zinc-800 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 rounded-tr-none'
                    : 'bg-white border-zinc-200 dark:bg-zinc-900 dark:border-zinc-800/80 text-zinc-800 dark:text-zinc-200 rounded-tl-none shadow-sm'
                }`}
              >
                <div className="whitespace-pre-line font-sans">{msg.content}</div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 max-w-[85%]">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white shrink-0 animate-pulse">
                <Bot size={14} />
              </div>
              <div className="p-3.5 bg-zinc-50 border border-zinc-200 dark:bg-zinc-900 dark:border-zinc-850 rounded-xl rounded-tl-none flex items-center gap-2 text-zinc-500">
                <RefreshCw size={14} className="animate-spin text-blue-500" />
                <span className="text-xs font-mono font-medium">Agent team is thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick suggestions panel */}
        {messages.length === 1 && (
          <div className="p-4 border-t border-zinc-100 dark:border-zinc-900/60 bg-zinc-50/50 dark:bg-zinc-900/10">
            <h4 className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Sparkles size={12} />
              Quick Suggestions
            </h4>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(item)}
                  className="text-left text-xs bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-lg px-3 py-1.5 transition-colors max-w-sm truncate"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Controls */}
        <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/60 flex items-center gap-3">
          {/* Voice Input Button */}
          <button
            onClick={toggleListening}
            className={`p-3 rounded-lg border transition-all ${
              isListening
                ? 'bg-rose-600 border-rose-600 text-white animate-pulse'
                : 'bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800'
            }`}
            title={isListening ? 'Stop Listening' : 'Speak Prompt'}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmitMessage()}
            placeholder={isListening ? 'Listening...' : 'Ask TrainGPT to search trains, book tickets, check status...'}
            disabled={loading}
            className="flex-1 bg-white dark:bg-[#09090b] border border-zinc-200 dark:border-zinc-800 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />

          <button
            onClick={() => handleSubmitMessage()}
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg p-3 shadow-md transition-colors"
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* Right Panels (1/3 width) */}
      <div className="w-full lg:w-96 flex flex-col gap-6 overflow-y-auto h-full pr-1">
        <BookingFlow activeAgent={activeAgent} lastToolExecuted={lastTool} bookingSuccess={bookingSuccess} />
        <div className="flex-1 min-h-[300px]">
          <AgentMonitor />
        </div>
      </div>
    </div>
  );
}
