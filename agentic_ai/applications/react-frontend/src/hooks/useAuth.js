import { useState, useEffect, useRef } from 'react';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import { fetchAuthConfig } from '../services/api.js';

/**
 * Custom hook for managing MSAL authentication
 * @returns {object} Authentication state and methods
 */
export const useAuth = () => {
  const [authConfig, setAuthConfig] = useState({ authEnabled: false });
  const [authConfigLoaded, setAuthConfigLoaded] = useState(false);
  const [msalApp, setMsalApp] = useState(null);
  const [account, setAccount] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [error, setError] = useState(null);
  const authPromptedRef = useRef(false);

  const isAuthEnabled = authConfig.authEnabled;
  const isSignedIn = !!accessToken;

  /**
   * Acquire an access token silently or with popup
   */
  const acquireAccessToken = async (instance, activeAccount, scope) => {
    if (!instance || !activeAccount || !scope) {
      return null;
    }
    try {
      const result = await instance.acquireTokenSilent({
        scopes: [scope],
        account: activeAccount,
      });
      return result.accessToken;
    } catch (error) {
      if (error instanceof InteractionRequiredAuthError) {
        const interactiveResult = await instance.acquireTokenPopup({
          scopes: [scope],
          account: activeAccount,
        });
        return interactiveResult.accessToken;
      }
      throw error;
    }
  };

  /**
   * Initialize authentication configuration
   */
  useEffect(() => {
    const loadAuthConfig = async () => {
      try {
        const data = await fetchAuthConfig();
        setAuthConfig(data);

        if (data.authEnabled && data.clientId && data.authority) {
          const instance = new PublicClientApplication({
            auth: {
              clientId: data.clientId,
              authority: data.authority,
              redirectUri: window.location.origin,
            },
            cache: {
              cacheLocation: 'sessionStorage',
              storeAuthStateInCookie: false,
            },
          });
          await instance.initialize();
          setMsalApp(instance);

          const existingAccount = instance.getActiveAccount() || instance.getAllAccounts()[0];
          if (existingAccount) {
            instance.setActiveAccount(existingAccount);
            setAccount(existingAccount);
            const token = await acquireAccessToken(instance, existingAccount, data.scope);
            if (token) {
              setAccessToken(token);
            }
          }
        }
      } catch (error) {
        console.error('Error loading auth config:', error);
        
        // Set default non-auth config so app can still load
        setAuthConfig({ authEnabled: false });
        setError(error.message || 'Failed to load authentication configuration');
      } finally {
        setAuthConfigLoaded(true);
      }
    };

    loadAuthConfig();
  }, []);

  /**
   * Attempt interactive login if needed
   */
  useEffect(() => {
    const attemptInteractiveLogin = async () => {
      if (!msalApp || !authConfig.scope) {
        return;
      }

      const existingAccount = msalApp.getActiveAccount() || msalApp.getAllAccounts()[0];
      if (existingAccount) {
        msalApp.setActiveAccount(existingAccount);
        setAccount(existingAccount);
        const token = await acquireAccessToken(msalApp, existingAccount, authConfig.scope);
        if (token) {
          setAccessToken(token);
        }
        return;
      }

      if (authPromptedRef.current) {
        return;
      }
      authPromptedRef.current = true;

      try {
        const response = await msalApp.loginPopup({
          scopes: [authConfig.scope],
          prompt: 'select_account',
        });
        msalApp.setActiveAccount(response.account);
        setAccount(response.account);
        const token = response.accessToken || (await acquireAccessToken(msalApp, response.account, authConfig.scope));
        if (token) {
          setAccessToken(token);
        }
      } catch (error) {
        console.error('Automatic sign-in failed:', error);
        authPromptedRef.current = false;
        throw error;
      }
    };

    if (authConfigLoaded && authConfig.authEnabled && !accessToken) {
      attemptInteractiveLogin();
    }
  }, [authConfigLoaded, authConfig, msalApp, accessToken]);

  /**
   * Manually sign in
   */
  const signIn = async () => {
    if (!msalApp || !authConfig.scope) {
      throw new Error('Auth is not ready yet');
    }
    try {
      const response = await msalApp.loginPopup({ scopes: [authConfig.scope] });
      msalApp.setActiveAccount(response.account);
      setAccount(response.account);
      const token = response.accessToken || (await acquireAccessToken(msalApp, response.account, authConfig.scope));
      if (token) {
        setAccessToken(token);
      }
    } catch (error) {
      console.error('Sign-in failed:', error);
      throw error;
    }
  };

  /**
   * Sign out
   */
  const signOut = async () => {
    if (!msalApp) {
      return;
    }
    try {
      await msalApp.logoutPopup({ account: msalApp.getActiveAccount() ?? undefined });
    } catch (error) {
      console.error('Sign-out failed:', error);
    } finally {
      setAccount(null);
      setAccessToken(null);
    }
  };

  return {
    authConfig,
    authConfigLoaded,
    isAuthEnabled,
    isSignedIn,
    account,
    accessToken,
    error,
    signIn,
    signOut,
  };
};
