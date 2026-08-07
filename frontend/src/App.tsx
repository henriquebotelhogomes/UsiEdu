import { useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import type { LoginResponse } from "./types";
import { setToken } from "./api";
import LandingPage from "./components/LandingPage";
import LoginPage from "./components/LoginPage";
import ChatPage from "./components/ChatPage";

export default function App() {
  const [user, setUser] = useState<LoginResponse | null>(null);
  const navigate = useNavigate();

  const handleLogin = (loggedUser: LoginResponse) => {
    setUser(loggedUser);
    navigate("/chat");
  };

  const handleLogout = () => {
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
