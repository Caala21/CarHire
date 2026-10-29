import { createContext, useCallback, useContext, useRef, useState } from "react";
import { ApiError, apiUrl, readResponse } from "./lib/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [tokens, setTokenState] = useState(null);
  const tokensRef = useRef(null);
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
      if (response.status === 401 && tokensRef.current?.refresh_token && path !== "/auth/refresh") {
        if (!refreshPromise.current) {
          refreshPromise.current = fetch(apiUrl("/auth/refresh"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: tokensRef.current.refresh_token }),
          })
            .then(readResponse)
            .then((refreshed) => {
              setTokens(refreshed);
              return refreshed.access_token;
            })
            .catch((error) => {
              setTokens(null);
              throw error;
            })
            .finally(() => {
              refreshPromise.current = null;
            });
        }
        try {
          response = await makeRequest(await refreshPromise.current);
        } catch {
          throw new ApiError("Your session has expired. Please sign in again.", 401);
        }
      }

      if (response.status === 401 && tokensRef.current) setTokens(null);
      return response;
    },
    [setTokens],
  );
  const request = useCallback(
    async (path, options) => readResponse(await requestResponse(path, options)),
    [requestResponse],
  );
  const requestFile = useCallback(
    async (path, options) => (await requestResponse(path, options)).blob(),
    [requestResponse],
  );

  const signIn = useCallback(
    (tokenResponse) => setTokens(tokenResponse),
    [setTokens],
  );
  const signOut = useCallback(() => setTokens(null), [setTokens]);

  return (
    <AuthContext.Provider
      value={{
        tokens,
        user: tokens?.user ?? null,
        isSignedIn: Boolean(tokens?.access_token),
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
