export async function matchImages(formData) {
  const API = import.meta.env.VITE_API_URL;
  const resp = await fetch(`${API}/match`, { method: "POST", body: formData });
  return resp.json();
}
