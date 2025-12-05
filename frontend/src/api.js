const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export async function matchImages(formData) {
  const response = await fetch(`${API_URL}/match`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new Error(error.message || error.error || 'Failed to match images');
  }

  return response.json();
}

export async function healthCheck() {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
}
