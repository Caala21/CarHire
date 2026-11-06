import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./auth.jsx";
import "./styles.css";

class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("The application crashed.", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="grid min-h-screen place-items-center bg-canvas px-5 text-center text-ink">
          <div className="max-w-md">
            <h1 className="text-2xl font-black">Something went wrong</h1>
            <p className="mt-3 text-sm leading-6 text-muted">
              We couldn’t load this page. Please reload and try again.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="btn-primary mt-6"
            >
              Reload page
            </button>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <ErrorBoundary>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ErrorBoundary>
  </BrowserRouter>,
);
