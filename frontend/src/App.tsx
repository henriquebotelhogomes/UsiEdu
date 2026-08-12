import { useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import type { LoginResponse, StoredUser } from "./types";
import { clearStoredSession, loadStoredSession, setToken, storeSession } from "./api";
import LandingPage from "./components/LandingPage";
import LoginPage from "./components/LoginPage";
import ChatPage from "./components/ChatPage";
import InsightsPage from "./components/InsightsPage";

function postLoginRoute(state: unknown): "/chat" | "/insights" {
  return typeof state === "object" &&
    state !== null &&
    "from" in state &&
    state.from === "/insights"
    ? "/insights"
    : "/chat";
}

export default function App() {
  // Restaura a sessão persistida no localStorage (T7.4 / RF2-04)
  const [user, setUser] = useState<StoredUser | null>(() => {
    const stored = loadStoredSession();
    if (stored) setToken(stored.access_token);
    return stored;
  });
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogin = (loggedUser: LoginResponse, email: string) => {
    const storedUser: StoredUser = { ...loggedUser, email };
    storeSession(storedUser);
    setToken(storedUser.access_token);
    setUser(storedUser);
    navigate(postLoginRoute(location.state), { replace: true });
  };

  const handleLogout = () => {
    clearStoredSession();
    setToken(null);
    setUser(null);
    navigate("/");
  };

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <div className="app">
            <LoginPage onLogin={handleLogin} />
          </div>
        }
      />
      <Route
        path="/chat"
        element={
          user ? (
            <div className="app">
              <ChatPage user={user} onLogout={handleLogout} />
            </div>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/insights"
        element={
          user ? (
            <div className="app">
              <InsightsPage user={user} onLogout={handleLogout} />
            </div>
          ) : (
            <Navigate to="/login" replace state={{ from: "/insights" }} />
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
