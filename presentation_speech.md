# **Financial News and Comments Real-Time Trend Analysis System** - Presentation Speech

Good afternoon everyone. I'm LU Wei. Today we're presenting the **Financial News and Comments Real-Time Trend Analysis System** that our team developed. **(翻页)**

We will introduce out project through 6 parts...**(翻页)**

## Introduction

**(翻页)** In financial markets, sentiment and opinion trends change rapidly. Investors need real-time market understanding. Traditional manual monitoring of multiple sources is inefficient. 

**(翻页)**  Our system automatically collects, cleans, analyzes and stores multi-source financial data into Redis, then it performs real-time sentiment analysis and displaying results through an interactive dashboard to support quick decision-making.

## Part 1: Individual Responsibilities & Contributions

**(翻页)** The division of labour of our team is as follows. I, **LU Wei**, handled overall project management including planning, scheduling, work assignment, and progress tracking. I also integrated all the code and modules together, developed the entire visualization module, and designed the framework for the project report with content review and revision. **LIU Yuhao** found and analyzed data sources, developed the scraper module with implemented raw data storage implemented in the pipeline. **LYU Buyi** handled data freshness validation with bug fixes to ensure stability, he also contributed to the report writing. **LIN Guancheng** is responsible for the cleaner module, including field mapping, data standardization, and deduplication mechanisms. **LIN Junyu** developed the processor module, handling data preprocessing, building and training the BERT model for prediction, performing word frequency statistics, and implementing keyword sentiment analysis. **YANG Donghui** supported the analysis module by improving the model and contributing to the report writing.

---

We will first introduce the data crawling module.**(翻页)** 

---

## Part 1: Data Scraper Module

**(翻页) ** Our scraper system collects financial data from six major sources: Reddit for real-time discussions, NewsAPI for news articles, RSS feeds for diverse sources, StockTwits for trader sentiment, Twitter for market commentary, and AlphaVantage for stock market data. We built a centralized control center that manages all crawlers with independent scheduling, normalizes JSON data, and handles timezone conversions to ensure consistency.

The key challenge is managing multiple data sources with different APIs and rate limits. We implemented stream crawlers for Reddit to consume real-time data feeds instead of periodic polling, and handle API throttling carefully.

---

## Part 2: Data Cleaner Module

**(翻页)** The cleaner module has three main responsibilities. First, we standardize data structure from different sources—mapping all fields into a unified format. Second, we clean raw data by removing HTML tags and malformed characters, and filter out incomplete records. Third, we handle deduplication—since the same story appears across multiple sources, we track processed items and remove duplicates to avoid redundant analysis.

---

## Part 3: Data Processing Module

**(翻页) ** We use a pre-trained BERT model that has deep semantic understanding capability. The model analyzes cleaned text and identifies whether the sentiment is Bullish or Bearish—positive or negative outlook about the market. This allows us to quantify market sentiment from news and comments.

We also have a rule-based engine as a fallback. If the BERT model is temporarily unavailable, the system can still analyze sentiment using keyword matching rules. This ensures our system remains robust and fault-tolerant even when something goes wrong.

Beyond classification, we detect trends by comparing current keyword frequency with the 24-hour historical average. This shows us whether topics are getting more or less attention, revealing what's capturing market focus right now.

**(翻页)**

---

## Part 4: Data Visualization Module

**(翻页) ** We built a real-time interactive dashboard using Vue 3 and ECharts. The dashboard has six main components that together give a comprehensive view of market sentiment.

First, There's a **trending keywords** panel showing the top 10 most active keywords ranked by growth rate. And we have a sentiment distribution bar that shows positive and negative comment proportions. This gives decision-makers an immediate sense of overall market mood. 

We also have a **24-hour trend chart** showing how keyword frequencies change over time, so people can see which topics are gaining or losing attention.

We include a **word cloud** to visualize keyword hotness through font sizing and colors. 

A **news feed** displays the latest articles with their sources and sentiment labels. 

Finally, a pie chart shows the composition of **data sources**, revealing where our information comes from.

**(翻页) ** This is the whole picture of the visualization of the system. The architecture flows from our Processor through Redis to the dashboard via WebSocket for real-time updates. This ensures both initial responsiveness and continuous real-time data flow.

---

Thank you for your attention!

