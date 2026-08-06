import { useState } from "react";
import type { LoginResponse } from "./types";
import { setToken } from "./api";
import LoginPage from "./components/LoginPage";
import ChatPage from "./components/ChatPage";

export default function App() {
  const [user, setUser] = useState<LoginResponse | null>(null);

  const handleLogin = (user: LoginResponse) => {
    setUser(user);
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
  };

  if (!user) {
    return (
      <div className="app">
        <LoginPage onLogin={handleLogin} />
      </div>
    );
  }

  return (
    <div className="app">
      <ChatPage user={user} onLogout={handleLogout} />
    </div>
  );
}