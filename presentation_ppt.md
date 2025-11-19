# Financial Real-Time Trend Analysis System - PPT Content

---

## Slide 1: Introduction

**Financial Real-Time Trend Analysis System**

- **Background**: Financial sentiment and trends change rapidly; manual monitoring is inefficient
- **Questions**: How to automatically collect and analyze multi-source data in real-time?
- **Solution**: Automated scraper → data cleaner → sentiment analysis → real-time visualization
- **Architecture**: Scraper → Redis → Cleaner → Processor → Visualization
- **Key Value**: 24-hour monitoring, multi-source integration, real-time decision support

---

## Slide 2: System and Technical Architecture

**System Architecture**

```
                                              ┌─────────────────────────────────┐
                                              │         Redis (Central)          │
                                              ├─────────────────────────────────┤
┌──────────────┐      ┌──────────────┐       │ DB0: Raw data queue             │
│   Scraper    │─────→│   Cleaner    │       │ DB1: Cleaned data queue         │
└──────────────┘      └──────────────┘       │ DB2: Analysis results & cache   │
      ▲                     ▲                 └─────────────────────────────────┘
      │                     │                            ▲
      │ Push raw data       │ Push cleaned data          │
      │ (DB0)              │ (DB1)                       │
      │                     │                  ┌─────────┴─────────┬─────────────┐
      │                     │                  │                   │             │
[News Sites]          ┌──────────────┐         │              Push analyzed      │
[Social Media]        │  Processor   │─────────┤              data (DB2)        │
[Comments]            └──────────────┘         │                   │             │
                            │                  │          ┌────────▼─────────┐  │
                            │                  │          │ Visualization    │  │
                            │ BERT Analysis    │          │ Backend (FastAPI)│  │
                            │                  │          └────────┬─────────┘  │
                            └──────────────────┤                   │            │
                               Query results   │          Subscribe WebSocket   │
                               (DB2)           │          updates (DB2)         │
                                              │                   │            │
                                              └───────────────────┼────────────┘
                                                                  ▼
                                              ┌─────────────────────────────────┐
                                              │  Visualization Frontend (Vue 3) │
                                              │  - Sentiment Bar                │
                                              │  - Trend Chart                  │
                                              │  - Word Cloud                   │
                                              │  - Keywords Panel               │
                                              │  - News Feed                    │
                                              │  - Sources Chart                │
                                              └─────────────────────────────────┘
```

Our system implements a modular pipeline architecture that processes data through four main stages. The pipeline begins when scrapers collect raw data from multiple sources including news sites, social media, and comment platforms, then push this data to Redis DB0 as a message queue. The cleaner module consumes from the queue, standardizes formats, removes duplicates, and enqueues the cleaned data to Redis DB1. The processor then consumes cleaned data from DB1, performs sentiment analysis using BERT, detects emerging trends by comparing keyword frequencies, and outputs results to Redis DB2 for real-time access. The visualization backend subscribes to Redis DB2 updates and serves data via REST API and WebSocket connections. Finally, the visualization frontend receives real-time updates and renders interactive charts and dashboards. This design ensures all modules maintain loose coupling through Redis, allowing independent scaling and fault isolation while enabling seamless real-time data flow across the entire system.

**Technical Architecture**

```
BACKEND LAYER                          FRONTEND LAYER
┌──────────────────────────────┐      ┌──────────────────────┐
│   Python Services            │      │  Vue 3 + ECharts     │
│  ├─ Data Scraper             │      │  ├─ Sentiment Bar    │
│  ├─ Data Cleaner             │      │  ├─ Trend Chart      │
│  ├─ BERT Processor           │      │  ├─ Word Cloud       │
│  └─ FastAPI Server           │      │  ├─ Keywords Panel   │
└───────────────┬──────────────┘      │  ├─ News Feed        │
                │                      │  └─ Sources Chart    │
         ┌──────▼──────┐              └────────┬─────────────┘
         │    Redis    │                        │
         │  (Cache &   │◄──────WebSocket────────┤
         │   Queue)    │                        │
         └─────────────┘         REST API       │
                                  (200-600ms)   │
                                   Fallback     │
                                    Polling     │
```

**Data Flow Details**

1. **Collection**: Scrapers collect raw data from multiple sources and push to Redis queue
2. **Cleaning**: Cleaner consumes from queue, standardizes formats, deduplicates, and queues cleaned data
3. **Analysis**: Processor analyzes sentiment using BERT, detects trends, outputs to both Redis and JSON
4. **Visualization**: Dashboard subscribes to Redis updates via WebSocket for real-time display

---

## Slide 3: Data Scraper

**Multi-Source Real-Time Collection**

- **Implementation**: Multi-platform collection (news sites, social media); JSON standardization; UTC timezone handling; 24-hour rolling window; Redis async queues
- **Team**: LIU Yuhao (architecture), LYU Buyi (anti-crawler optimization)


---

## Slide 5: Data Cleaner

**Data Standardization and Quality**

- **Implementation**: Field mapping, timestamp standardization (UTC ISO 8601), text cleaning, data filtering, deduplication via Redis sets, incremental processing
- **Team**: LIN Guancheng (full responsibility)

---

## Slide 6: Sentiment Analysis and Processor

**AI-Powered Sentiment Analysis and Trend Detection**

- **Core Algorithms**:
  - BERT semantic analysis: Identify Bullish/Bearish sentiment
  - Rule engine fallback: Keyword matching for fault tolerance
  - Trend detection: Compare current vs 24h average keyword frequency

- **Dual Output**: Redis (real-time dashboard), JSON files (offline analysis)

- **Team**: LIN Junyu (architecture & optimization), YANG Donghui (testing & verification)

---

## Slide 7: Data Visualization



**Real-Time Interactive Dashboard**

- **Six Visualization Components**:
  1. Sentiment distribution bar: Real-time positive/neutral/negative ratios
  2. 24-hour trend chart: Multi-keyword frequency comparison
  3. Word cloud: Keyword hotness visualization
  4. Trending keywords: Top 10 with growth rates
  5. News feed: Latest news with source and sentiment
  6. Sources distribution: Data source composition

- **Data Architecture**: Processor → Redis → REST API/WebSocket → Pinia → Vue Components

- **Real-time Mechanism**: REST API for initial load, WebSocket for real-time push, Auto-fallback to polling

- **Team**: LU Wei (design & development)

---

## Slide 8: Team Contributions

**Team Members and Responsibilities**

| Member | Role | Contribution |
|--------|------|--------------|
| **LU Wei** | Project Manager & visualization | • Overall planning & scheduling<br>• Work assignment & progress tracking<br>• Code integration & assembly<br>• Visualization module development<br>• Report framework design & content review and revision |
| **LIU Yuhao** | Scraper Lead | • Data Source finding & Analysis<br/>• Automated Data Crawling Module Development<br/>• Raw Data Storage in the Pipeline |
| **LYU Buyi** | Scraper Support | • Part of Data Crawler Implementation<br/>• Data Freshness Validation & Bug Fixes<br/>• Report writing |
| **LIN Guancheng** | Cleaner | • Cleaning pipeline<br>• Field mapping & standardization<br>• Deduplication mechanism<br>• Incremental processing |
| **LIN Junyu** | Processor Lead | • Data preprocessing<br/>• Bert model building, training and prediction  <br/>• Word frequency statistics <br/>• Predicting sentiment tags <br/>• Keyword sentiment analysis |
| **YANG Donghui** | Processor Support | • Model improving<br>• Report writing |

**Key Achievements**
- ✅ Modular architecture for maintainability
- ✅ Real-time WebSocket push with continuous data delivery
- ✅ Robust data collection from multiple sources
- ✅ High-quality cleaned and deduplicated data
- ✅ Interactive dashboard with smooth animations

