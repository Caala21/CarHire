import { createContext, useCallback, useContext, useRef, useState } from "react";
import { ApiError, apiUrl, readResponse } from "./lib/api.js";

const AuthContext = createContext(null);
const AUTH_STORAGE_KEY = "carhire.auth";

function readStoredTokens() {
  const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!stored) return null;

  try {
    const value = JSON.parse(stored);
    if (
      typeof value?.access_token === "string" &&
      typeof value?.refresh_token === "string" &&
      value.user
    ) {
      return value;
    }
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
  return null;
}

export function AuthProvider({ children }) {
  const [tokens, setTokenState] = useState(readStoredTokens);
  const [sessionExpired, setSessionExpired] = useState(false);
  const tokensRef = useRef(tokens);
  const refreshPromise = useRef(null);

  const setTokens = useCallback((value) => {
    const next = value
      ? {
          access_token: value.access_token,
          refresh_token: value.refresh_token,
          user: value.user,
        }
      : null;
    tokensRef.current = next;
    setTokenState(next);
    if (next) window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(next));
    else window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }, []);

  const requestResponse = useCallback(
    async (path, options = {}) => {
      const makeRequest = (accessToken) => {
        const headers = new Headers(options.headers || {});
        if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
        if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
          headers.set("Content-Type", "application/json");
        }
        return fetch(apiUrl(path), { ...options, headers });
      };

      let response = await makeRequest(tokensRef.current?.access_token);
      if (response.status === 401 && tokensRef.current?.refresh_token && path !== "/api/auth/refresh") {
        if (!refreshPromise.current) {
          refreshPromise.current = fetch(apiUrl("/api/auth/refresh"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: tokensRef.current.refresh_token }),
          })
            .then(readResponse)
            .then((refreshed) => {
              setTokens(refreshed);
              return refreshed.access_token;
            })
            .finally(() => {
              refreshPromise.current = null;
            });
        }
        try {
          response = await makeRequest(await refreshPromise.current);
        } catch (error) {
          if (error.status !== 401) throw error;
          setTokens(null);
          setSessionExpired(true);
          throw new ApiError("Your session has expired. Please sign in again.", 401);
        }
      }

      if (response.status === 401 && tokensRef.current) {
        setTokens(null);
        setSessionExpired(true);
      }
      return response;
    },
    [setTokens],
  );
  const request = useCallback(
    async (path, options) => readResponse(await requestResponse(path, options)),
    [requestResponse],
  );
  const requestFile = useCallback(
    async (path, options) => {
      const response = await requestResponse(path, options);
      if (!response.ok) await readResponse(response);
      return response.blob();
    },
    [requestResponse],
  );

  const signIn = useCallback(
    (tokenResponse) => {
      setTokens(tokenResponse);
      setSessionExpired(false);
    },
    [setTokens],
  );
  const signOut = useCallback(() => {
    setTokens(null);
    setSessionExpired(false);
  }, [setTokens]);

  return (
    <AuthContext.Provider
      value={{
        tokens,
        user: tokens?.user ?? null,
        isSignedIn: Boolean(tokens?.access_token),
        sessionExpired,
        clearSessionExpired: () => setSessionExpired(false),
        request,
        requestFile,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
