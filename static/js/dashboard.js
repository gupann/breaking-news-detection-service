// main dashboard logic

import {
  fetchBreakingNews,
  fetchStats,
  fetchTopics,
  checkHealth,
} from './api.js';
import { formatTimeAgo, formatScore, formatDate, debounce } from './utils.js';

class Dashboard {
  constructor() {
    this.currentTopic = null;
    this.refreshInterval = 30000; // 30 seconds
    this.refreshTimer = null;
    this.init();
  }

  // initialize dashboard
  init() {
    this.setupEventListeners();
    this.loadData();
    this.startAutoRefresh();
  }

  // setup event listeners
  setupEventListeners() {
    const topicFilter = document.getElementById('topic-filter');
    if (topicFilter) {
      topicFilter.addEventListener('change', (e) => {
        this.currentTopic = e.target.value || null;
        this.loadBreakingNews();
      });
    }

    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.loadData();
      });
    }
  }

  // load all data
  async loadData() {
    await Promise.all([
      this.loadBreakingNews(),
      this.loadStats(),
      this.loadTopics(),
      this.loadHealthInfo(),
    ]);
  }

  // load breaking news
  async loadBreakingNews() {
    try {
      const data = await fetchBreakingNews(this.currentTopic);
      this.renderBreakingNews(data);
    } catch (error) {
      console.error('Error loading breaking news:', error);
      this.showError('Failed to load breaking news');
    }
  }

  // load statistics
  async loadStats() {
    try {
      const data = await fetchStats();
      this.renderStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  }

  // load topics
  async loadTopics() {
    try {
      const data = await fetchTopics();
      this.renderTopics(data);
    } catch (error) {
      console.error('Error loading topics:', error);
    }
  }

  // load health info for second about box
  async loadHealthInfo() {
    try {
      const data = await checkHealth();
      this.renderHealthInfo(data);
    } catch (error) {
      console.error('Error loading health info:', error);
      this.renderHealthInfoError();
    }
  }

  // render breaking news
  renderBreakingNews(data) {
    const container = document.getElementById('breaking-news-list');
    if (!container) return;

    if (data.count === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon"></div>
          <p>No breaking news at the moment</p>
        </div>
      `;
      return;
    }

    container.innerHTML = data.breaking_news
      .map(
        (item) => `
      <div class="news-item">
        <div class="news-item-header">
          <div>
            <h3 class="news-title">${this.escapeHtml(item.title)}</h3>
            <div class="news-meta">
              ${
                item.topic
                  ? `<span>Topic: ${this.escapeHtml(item.topic)}</span>`
                  : ''
              }
              ${
                item.category
                  ? `<span>Category: ${this.escapeHtml(item.category)}</span>`
                  : ''
              }
            </div>
          </div>
          <div class="news-score">${formatScore(item.score)}</div>
        </div>
        ${
          item.description
            ? `<p class="text-muted">${this.escapeHtml(item.description)}</p>`
            : ''
        }
        ${
          item.detected_keywords.length > 0
            ? `
          <div class="news-keywords">
            ${item.detected_keywords
              .map(
                (kw) =>
                  `<span class="keyword-tag">${this.escapeHtml(kw)}</span>`
              )
              .join('')}
          </div>
        `
            : ''
        }
        ${
          item.link
            ? `<a href="${item.link}" target="_blank" class="text-accent mt-sm" style="display: inline-block; margin-top: 0.5rem;">Read more →</a>`
            : ''
        }
      </div>
    `
      )
      .join('');
  }

  // render statistics
  renderStats(data) {
    const container = document.getElementById('stats-container');
    if (!container) return;

    container.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">${data.total_processed.toLocaleString()}</div>
          <div class="stat-label">Articles Processed</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${data.breaking_news_count}</div>
          <div class="stat-label">Breaking News</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${data.active_topics}</div>
          <div class="stat-label">Active Topics</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${data.processing_rate.toFixed(1)}</div>
          <div class="stat-label">
            Articles/sec
            ${
              data.processing_status === 'complete'
                ? '<span style="font-size: 0.7em; opacity: 0.7; display: block; margin-top: 0.25rem;">(Final Rate)</span>'
                : '<span style="font-size: 0.7em; opacity: 0.7; display: block; margin-top: 0.25rem;">(Processing...)</span>'
            }
          </div>
        </div>
      </div>
    `;
  }

  // render topics
  renderTopics(data) {
    const select = document.getElementById('topic-filter');
    if (!select) return;

    // save current selection
    const currentValue = select.value;

    // clear and rebuild options
    select.innerHTML = '<option value="">All Topics</option>';
    data.topics.forEach((topic) => {
      const option = document.createElement('option');
      option.value = topic.topic;
      option.textContent = `${topic.topic} (${topic.article_count})`;
      select.appendChild(option);
    });

    // restore selection
    if (currentValue) {
      select.value = currentValue;
    }
  }

  // start auto-refresh
  startAutoRefresh() {
    this.refreshTimer = setInterval(() => {
      this.loadData();
    }, this.refreshInterval);
  }

  // stop auto-refresh
  stopAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  // show error message
  showError(message) {
    const container = document.getElementById('breaking-news-list');
    if (container) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon"></div>
          <p>${this.escapeHtml(message)}</p>
        </div>
      `;
    }
  }

  // render health info in second about box
  renderHealthInfo(data) {
    const container = document.getElementById('health-info');
    if (!container) return;

    const status = data.status || 'unknown';
    const processorRunning = data.processor_running ? 'Running' : 'Stopped';
    const timestamp = data.timestamp
      ? new Date(data.timestamp).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : 'N/A';

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 0.25rem; margin: 0; padding: 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; line-height: 1.2; margin: 0; padding: 0;">
          <span class="text-muted" style="font-size: 0.8rem; margin: 0; padding: 0;">Status:</span>
          <span style="color: ${
            status === 'healthy' ? 'var(--accent-primary)' : '#ff4444'
          }; font-weight: 600; font-size: 0.8rem; margin: 0; padding: 0;">
            ${status.toUpperCase()}
          </span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; line-height: 1.2; margin: 0; padding: 0;">
          <span class="text-muted" style="font-size: 0.8rem; margin: 0; padding: 0;">Processor:</span>
          <span style="color: ${
            data.processor_running ? 'var(--accent-primary)' : '#ff4444'
          }; font-size: 0.8rem; margin: 0; padding: 0;">
            ${processorRunning}
          </span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; line-height: 1.2; margin: 0; padding: 0;">
          <span class="text-muted" style="font-size: 0.8rem; margin: 0; padding: 0;">Last Check:</span>
          <span class="text-muted" style="font-size: 0.7rem; margin: 0; padding: 0;">${timestamp}</span>
        </div>
        ${
          !data.processor_running
            ? '<div style="font-size: 0.65rem; color: var(--text-secondary); margin-top: 0.05rem; line-height: 1.2; padding: 0;">(Finished processing all articles)</div>'
            : ''
        }
      </div>
    `;
  }

  // render health info error
  renderHealthInfoError() {
    const container = document.getElementById('health-info');
    if (!container) return;

    container.innerHTML = `
      <div style="color: #ff4444;">
        <span>Unable to load system status</span>
      </div>
    `;
  }

  // escape HTML
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// initialize dashboard when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
  });
} else {
  new Dashboard();
}
