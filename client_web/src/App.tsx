
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Terminal, LayoutDashboard, PlusCircle } from "lucide-react";
import Dashboard from "./components/Dashboard";
import NewSession from "./components/NewSession";
import Interview from "./components/Interview";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-indigo-500/30">
        <nav className="border-b border-slate-800 bg-slate-950/50 backdrop-blur-xl sticky top-0 z-50">
          <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2 font-bold text-xl tracking-tight text-indigo-400 hover:text-indigo-300 transition-colors">
              <Terminal className="w-6 h-6" />
              <span>Antigravity Interview</span>
            </Link>
            <div className="flex gap-6 text-sm font-medium text-slate-400">
              <Link to="/" className="flex items-center gap-2 hover:text-slate-100 transition-colors">
                <LayoutDashboard className="w-4 h-4" />
                Dashboard
              </Link>
              <Link to="/new" className="flex items-center gap-2 hover:text-slate-100 transition-colors">
                <PlusCircle className="w-4 h-4" />
                New Session
              </Link>
            </div>
          </div>
        </nav>

        <main className="max-w-5xl mx-auto px-6 py-12">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new" element={<NewSession />} />
            <Route path="/session/:id" element={<Interview />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
