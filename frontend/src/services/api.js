import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const chatService = {
  sendMessage: (message, sessionId) => api.post('/api/chat', { message, session_id: sessionId }),
};

export const trainService = {
  getStations: () => api.get('/api/trains/stations'),
  searchTrains: (source, destination, date) => api.post('/api/trains/search', { source, destination, date }),
  checkAvailability: (trainNo, classType, date) => api.post('/api/trains/availability', { train_no: trainNo, class_type: classType, date }),
  calculateFare: (trainNo, classType, numPassengers) => api.post('/api/trains/fare', { train_no: trainNo, class_type: classType, num_passengers: numPassengers }),
};

export const bookingService = {
  createBooking: (bookingData) => api.post('/api/bookings', bookingData),
  getBookings: (userId = 'guest_user') => api.get(`/api/bookings?user_id=${userId}`),
  cancelBooking: (pnr) => api.delete(`/api/bookings/${pnr}`),
};

export const pnrService = {
  checkStatus: (pnr) => api.get(`/api/pnr/${pnr}`),
};

export const analyticsService = {
  getAnalytics: () => api.get('/api/analytics'),
};

export const getWebSocketUrl = (path) => {
  return `${WS_BASE_URL}${path}`;
};
