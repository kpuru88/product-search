import { ChatViewPurpleElegant } from './components/ChatViewPurpleElegant';

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-slate-100">
      <div className="border-b bg-white/80 backdrop-blur-sm shadow-sm">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Insurance Claims Product Search</h1>
          <p className="text-gray-600 mt-1">Lost-Item Product Search & Discovery</p>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6">
        <ChatViewPurpleElegant />
      </div>
    </div>
  );
}
