export function getAccessToken() {
  return localStorage.getItem('access_token') || '';
}

export function getAuthHeaders() {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function appendTokenToUrl(url) {
  const token = getAccessToken();
  if (!token) return url;
  const connector = url.includes('?') ? '&' : '?';
  return `${url}${connector}token=${encodeURIComponent(token)}`;
}
