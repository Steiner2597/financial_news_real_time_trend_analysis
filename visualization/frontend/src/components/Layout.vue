<!-- frontend/src/components/SentimentBar.vue -->
<template>
    <div class="sentiment-bar-container">
      <div class="sentiment-bars">
        <div class="bar-item positive">
          <div class="bar-label">
            <span class="label-text">👍 Positive</span>
            <span class="label-value">{{ sentiment.positive_count || 0 }}</span>
          </div>
          <div class="bar-background">
            <div 
              class="bar-fill positive-fill" 
              :style="{ width: getPercentage('positive') + '%' }"
              :title="`Positive: ${sentiment.positive_count || 0} (${getPercentage('positive')}%)`"
            ></div>
          </div>
        </div>
  
        <div class="bar-item neutral">
          <div class="bar-label">
            <span class="label-text">➡️ Neutral</span>
            <span class="label-value">{{ sentiment.neutral_count || 0 }}</span>
          </div>
          <div class="bar-background">
            <div 
              class="bar-fill neutral-fill" 
              :style="{ width: getPercentage('neutral') + '%' }"
              :title="`Neutral: ${sentiment.neutral_count || 0} (${getPercentage('neutral')}%)`"
            ></div>
          </div>
        </div>
  
        <div class="bar-item negative">
          <div class="bar-label">
            <span class="label-text">👎 Negative</span>
            <span class="label-value">{{ sentiment.negative_count || 0 }}</span>
          </div>
          <div class="bar-background">
            <div 
              class="bar-fill negative-fill" 
              :style="{ width: getPercentage('negative') + '%' }"
              :title="`Negative: ${sentiment.negative_count || 0} (${getPercentage('negative')}%)`"
            ></div>
          </div>
        </div>
      </div>
  
      <div class="sentiment-summary">
        <div class="summary-item">
          <span class="summary-label">Total Comments</span>
          <span class="summary-value">{{ sentiment.total_comments || 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Sentiment Trend</span>
          <span class="summary-value" :class="`sentiment-label-${getSentimentTrend()}`">
            {{ getSentimentTrendText() }}
          </span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Sentiment Score</span>
          <span class="summary-value sentiment-score">{{ calculateSentimentScore() }}</span>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { computed } from 'vue'
  
  const props = defineProps({
    sentiment: {
      type: Object,
      default: () => ({
        positive_count: 0,
        neutral_count: 0,
        negative_count: 0,
        total_comments: 0,
        label: 'neutral'
      })
    }
  })
  
  // 计算百分比
  function getPercentage(type) {
    const total = props.sentiment.total_comments || 
      (props.sentiment.positive_count || 0) + 
      (props.sentiment.neutral_count || 0) + 
      (props.sentiment.negative_count || 0)
    
    if (total === 0) return 0
    
    const count = props.sentiment[`${type}_count`] || 0
    return Math.round((count / total) * 100)
  }
  
  // 计算情感指数 (范围: -100 ~ 100)
  function calculateSentimentScore() {
    const positive = props.sentiment.positive_count || 0
    const neutral = props.sentiment.neutral_count || 0
    const negative = props.sentiment.negative_count || 0
    const total = positive + neutral + negative
  
    if (total === 0) return 0
  
    // 计算加权分数
    const score = Math.round(((positive - negative) / total) * 100)
    return score
  }
  
  // 获取情感趋势
  function getSentimentTrend() {
    const score = calculateSentimentScore()
    if (score > 20) return 'positive'
    if (score < -20) return 'negative'
    return 'neutral'
  }
  
  // 获取情感趋势文本
  function getSentimentTrendText() {
    const score = calculateSentimentScore()
    if (score > 20) return '👍 Positive'
    if (score < -20) return '👎 Negative'
    return '➡️ Neutral'
  }
  </script>
  
  <style scoped>
  .sentiment-bar-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 8px 0;
  }
  
  .sentiment-bars {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  
  .bar-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .bar-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .label-text {
    font-size: 12px;
    font-weight: 600;
    color: #333;
    min-width: 60px;
  }
  
  .label-value {
    font-size: 11px;
    font-weight: 600;
    color: #666;
    min-width: 30px;
    text-align: right;
  }
  
  .bar-background {
    width: 100%;
    height: 16px;
    background: #f0f0f0;
    border-radius: 8px;
    overflow: hidden;
    position: relative;
  }
  
  .bar-fill {
    height: 100%;
    border-radius: 8px;
    transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }
  
  .bar-fill::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255, 255, 255, 0.3),
      transparent
    );
    animation: shimmer 2s infinite;
  }
  
  @keyframes shimmer {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(100%);
    }
  }
  
  .positive-fill {
    background: linear-gradient(90deg, #27ae60, #2ecc71);
  }
  
  .neutral-fill {
    background: linear-gradient(90deg, #95a5a6, #bdc3c7);
  }
  
  .negative-fill {
    background: linear-gradient(90deg, #e74c3c, #ff6b6b);
  }
  
  .sentiment-summary {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    padding: 8px;
    background: #f9f9f9;
    border-radius: 6px;
    border: 1px solid #f0f0f0;
  }
  
  .summary-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    align-items: center;
    text-align: center;
  }
  
  .summary-label {
    font-size: 10px;
    color: #999;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .summary-value {
    font-size: 13px;
    font-weight: 700;
    color: #333;
  }
  
  .sentiment-label-positive {
    color: #27ae60;
  }
  
  .sentiment-label-negative {
    color: #e74c3c;
  }
  
  .sentiment-label-neutral {
    color: #95a5a6;
  }
  
  .sentiment-score {
    font-size: 14px;
    font-weight: 800;
    padding: 2px 6px;
    border-radius: 4px;
    background: #f0f0f0;
  }
  
  /* 响应式设计 */
  @media (max-width: 480px) {
    .sentiment-summary {
      grid-template-columns: 1fr;
      gap: 8px;
    }
  
    .label-text {
      font-size: 11px;
    }
  
    .bar-background {
      height: 14px;
    }
  }
  
  /* 深色模式支持 */
  @media (prefers-color-scheme: dark) {
    .bar-item {
      color: #e0e0e0;
    }
  
    .label-text {
      color: #e0e0e0;
    }
  
    .label-value {
      color: #b0b0b0;
    }
  
    .bar-background {
      background: #333;
    }
  
    .sentiment-summary {
      background: #2a2a2a;
      border-color: #444;
    }
  
    .summary-label {
      color: #888;
    }
  
    .summary-value {
      color: #e0e0e0;
    }
  
    .sentiment-score {
      background: #3a3a3a;
    }
  }
  </style>