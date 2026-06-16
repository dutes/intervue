import { useState } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Terminal, LayoutDashboard, PlusCircle, HelpCircle } from "lucide-react";
import Dashboard from "./components/Dashboard";
import NewSession from "./components/NewSession";
import Interview from "./components/Interview";
import InterviewReport from "./components/Report";
import HowItWorks from "./components/HowItWorks";

const HOW_IT_WORKS_SEEN_KEY = "intervue_seen_how_it_works";

function App() {
  // Auto-open the explainer on first run, then remember it's been seen.
  const [showHowItWorks, setShowHowItWorks] = useState(() => {
    try {
      return !localStorage.getItem(HOW_IT_WORKS_SEEN_KEY);
    } catch {
      return false; // e.g. storage blocked in private mode — don't nag
    }
  });

  const closeHowItWorks = () => {
    setShowHowItWorks(false);
    try {
      localStorage.setItem(HOW_IT_WORKS_SEEN_KEY, "1");
    } catch {
      // ignore storage errors
    }
  };

  return (
    <BrowserRouter>
      <div className="app-bg min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-indigo-500/30">
        <nav className="print:hidden relative z-10 border-b border-slate-800 bg-slate-950/50 backdrop-blur-xl sticky top-0">
          <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link to="/" className="font-display flex items-center gap-2 font-bold text-xl tracking-tight text-indigo-400 hover:text-indigo-300 transition-colors">
              <Terminal className="w-6 h-6" />
              <span>Intervue</span>
            </Link>
            <div className="flex gap-6 text-sm font-medium text-slate-400">
              <button onClick={() => setShowHowItWorks(true)} className="flex items-center gap-2 hover:text-slate-100 transition-colors">
                <HelpCircle className="w-4 h-4" />
                How it works
              </button>
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

        <main className="relative z-10 max-w-5xl mx-auto px-6 py-12">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new" element={<NewSession />} />
            <Route path="/session/:id" element={<Interview />} />
            <Route path="/report/:id" element={<InterviewReport />} />
          </Routes>
        </main>

        <HowItWorks open={showHowItWorks} onClose={closeHowItWorks} />
      </div>
    </BrowserRouter>
  );
}

export default App;
