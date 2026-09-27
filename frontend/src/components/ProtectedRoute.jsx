import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ user, children, allow = [] }) {
  if (!user) return <Navigate to="/login" replace />;
  if (allow.length > 0 && !allow.includes(user.position)) {
    return <Navigate to="/" replace />;
  }
  return children;
}