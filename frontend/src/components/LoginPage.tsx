import { useState } from "react";
import type { LoginResponse } from "../types";
import { login, setToken } from "../api";

const DEMO_USERS = [
  {
    name: "Ana Souza",
    email: "ana@demo.usiedu",
    password: "estudante123",
    profile: "student" as const,
    description: "Estudante de ADS",
  },
  {
    name: "Carlos Oliveira",
    email: "carlos@demo.usiedu",
    password: "staff123",
    profile: "staff" as const,
    description: "Coordenador",
  },
];

interface LoginPageProps {
  onLogin: (user: LoginResponse) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await login({ email, password });
      setToken(result.access_token);
      onLogin(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao fazer login");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoClick = (user: (typeof DEMO_USERS)[0]) => {
    setEmail(user.email);
    setPassword(user.password);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h2>UsiEdu</h2>
        <p className="login-subtitle">Assistente Universitário Inteligente</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Sua senha"
              required
            />
          </div>
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <div className="demo-users">
          <h3>Usuários de demonstração</h3>
          {DEMO_USERS.map((user) => (
            <div
              key={user.email}
              className="demo-user-card"
              onClick={() => handleDemoClick(user)}
            >
              <div className="name">{user.name}</div>
              <div className="email">{user.email}</div>
              <span className={`profile-badge ${user.profile}`}>
                {user.profile === "student" ? "Estudante" : "Staff"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}