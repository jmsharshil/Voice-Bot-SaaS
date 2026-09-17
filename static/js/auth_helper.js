(function() {
    // Decode and check if JWT token is expired (or close to expiring with a 10-second buffer)
    function isTokenExpired(token) {
        if (!token) return true;
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            const payload = JSON.parse(jsonPayload);
            return Date.now() >= (payload.exp * 1000 - 10000);
        } catch (e) {
            return true;
        }
    }

    // Helper to determine if a URL is an internal/relative endpoint on our own server
    function isInternalUrl(url) {
        if (!url) return false;
        if (url.startsWith('/') && !url.startsWith('//')) return true;
        if (url.startsWith(window.location.origin)) return true;
        return false;
    }

    // Clear all auth storage items
    function clearAuthStorage() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('username');
        localStorage.removeItem('is_admin');
        localStorage.removeItem('permissions');
        localStorage.removeItem('role');
        localStorage.removeItem('assigned_agent_id');
    }

    let refreshPromise = null;

    // Refresh access token if it's expired or forced (e.g. on 401 status)
    async function refreshTokenIfNeeded(force = false) {
        const accessToken = localStorage.getItem('access_token');
        const refreshToken = localStorage.getItem('refresh_token');

        if (!accessToken) {
            return null;
        }

        if (force || isTokenExpired(accessToken)) {
            if (!refreshToken) {
                clearAuthStorage();
                window.location.replace('/accounts/login/');
                return null;
            }

            // Deduplicate multiple simultaneous refresh calls
            if (!refreshPromise) {
                refreshPromise = (async () => {
                    try {
                        const response = await originalFetch('/api/accounts/token/refresh/', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ refresh: refreshToken }),
                        });
                        if (response.ok) {
                            const data = await response.json();
                            if (data.access) {
                                localStorage.setItem('access_token', data.access);
                                return data.access;
                            }
                        }
                    } catch (e) {
                        console.error("Token refresh request failed:", e);
                    }
                    // Refresh failed (refresh token expired/invalid), clear session and logout
                    clearAuthStorage();
                    window.location.replace('/accounts/login/');
                    return null;
                })();
            }

            const newAccessToken = await refreshPromise;
            refreshPromise = null;
            return newAccessToken;
        }

        return accessToken;
    }

    // Intercept global fetch
    const originalFetch = window.fetch;
    window.fetch = async function(resource, options) {
        const urlStr = typeof resource === 'string' ? resource : (resource.url || '');
        
        // Skip intercepting the token refresh request itself to avoid infinite loops
        if (urlStr.includes('/api/accounts/token/refresh/')) {
            return originalFetch(resource, options);
        }

        const hasAccessToken = localStorage.getItem('access_token');

        if (hasAccessToken && isInternalUrl(urlStr)) {
            const token = await refreshTokenIfNeeded();
            if (token) {
                options = options || {};
                options.headers = options.headers || {};

                // Automatically inject/update the Authorization header for all internal calls
                if (options.headers instanceof Headers) {
                    options.headers.set('Authorization', 'Bearer ' + token);
                } else if (typeof options.headers === 'object') {
                    const authKey = Object.keys(options.headers).find(k => k.toLowerCase() === 'authorization') || 'Authorization';
                    options.headers[authKey] = 'Bearer ' + token;
                }
            }
        }

        const response = await originalFetch(resource, options);

        // Fallback: If any internal API request returns 401 Unauthorized, force token refresh and retry once
        if (response.status === 401 && !urlStr.includes('/api/accounts/token/refresh/') && hasAccessToken && isInternalUrl(urlStr)) {
            const token = await refreshTokenIfNeeded(true); // Force refresh on 401
            if (token) {
                options = options || {};
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('Authorization', 'Bearer ' + token);
                } else if (typeof options.headers === 'object') {
                    const authKey = Object.keys(options.headers).find(k => k.toLowerCase() === 'authorization') || 'Authorization';
                    options.headers[authKey] = 'Bearer ' + token;
                }
                return originalFetch(resource, options);
            }
        }

        return response;
    };

    // Auth guard check on page load for protected paths
    const publicPaths = [
        '/accounts/login/',
        '/accounts/signup/',
        '/accounts/forgot-password/',
        '/accounts/reset-password/',
        '/voicebot/'
    ];

    const isPublicPage = publicPaths.some(path => window.location.pathname.startsWith(path));

    async function checkAuthOnLoad() {
        if (isPublicPage) {
            return;
        }

        const accessToken = localStorage.getItem('access_token');
        const refreshToken = localStorage.getItem('refresh_token');

        if (!accessToken && !refreshToken) {
            clearAuthStorage();
            window.location.replace('/accounts/login/');
            return;
        }

        // If access token is expired, trigger refresh immediately on load
        if (!accessToken || isTokenExpired(accessToken)) {
            const token = await refreshTokenIfNeeded();
            if (!token) {
                clearAuthStorage();
                window.location.replace('/accounts/login/');
            }
        }
    }

    // Run auth check immediately when script is parsed
    checkAuthOnLoad();
})();
