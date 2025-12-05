import React, { useState } from 'react';
import GlassesViewer from './GlassesViewer';
import { matchImages } from './api';

export default function App() {
  const [modelUrl, setModelUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      Array.from(files).forEach(file => {
        formData.append('images', file);
      });

      const result = await matchImages(formData);
      
      if (result.matched && result.model_url) {
        setModelUrl(result.model_url);
      } else {
        setError('No matching glasses found');
      }
    } catch (err) {
      setError(err.message || 'Failed to match images');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>AI Glasses Try-On</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <input 
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          disabled={loading}
        />
      </div>

      {loading && <p>Processing images...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      
      {modelUrl && (
        <div>
          <h2>Your Matched Glasses</h2>
          <GlassesViewer glbUrl={modelUrl} />
        </div>
      )}
    </div>
  );
}
