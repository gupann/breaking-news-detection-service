// API client for dashboard

const API_BASE = '/api';

// fetch breaking news
export async function fetchBreakingNews(topic = null) {
  const url = topic 
    ? `${API_BASE}/breaking?topic=${encodeURIComponent(topic)}`
    : `${API_BASE}/breaking`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch breaking news: ${response.statusText}`);
  }
  return response.json();
}

// fetch statistics
export async function fetchStats() {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`);
  }
  return response.json();
}

// fetch topics
export async function fetchTopics() {
  const response = await fetch(`${API_BASE}/topics`);
  if (!response.ok) {
    throw new Error(`Failed to fetch topics: ${response.statusText}`);
  }
  return response.json();
}

// check health
export async function checkHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

