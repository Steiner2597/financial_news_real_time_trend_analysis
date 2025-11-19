**1** **Introduction**

This financial news and comments real-time trend analysis system is a comprehensive platform for financial market monitoring, integrating multi-source data collection, automated processing, and interactive visualization. The system operates through a real-time pipeline architecture, enabling users to track market trends and public sentiment as events unfold.

It consists of four core modules: the Scraper collects data from multiple financial sources; the Cleaner performs standardization and deduplication; the Processor conducts sentiment analysis and trend detection; and the Visualization module provides an interactive dashboard for real-time display.

Key features include a 24-hour data retention policy to maintain focus on current conditions, and the use of Redis as a central message broker to enable seamless data flow. The modular design supports independent operation, ease of maintenance, and future expansion.

2.1 **Data Scraping**

The crawler module acquires data from multiple sources, including financial news and discussions on social media platforms, aiming to provide comprehensive information. Data from the past 24 hours is collected during crawling, with keyword filtering mechanisms applied to some data sources to avoid excessive irrelevant information. The crawler receives and stores data via a Redis server, allowing downstream modules to use the data asynchronously without blocking the collection process.

The crawled data is converted to a standardized JSON format and stored on the Redis server. Each data item contains necessary fields, including a source identifier, data type, timestamp, content text, and platform-specific data. The system implements UTC timezone processing during the collection process to prevent timezone-related errors from data becoming older than 24 hours. The quota management system monitors whether the length of the Redis queue reaches a configurable threshold and automatically exports data when a certain limit is reached to prevent memory overflow. When a certain limit is reached, data is automatically exported to prevent memory overflow, ensuring the crawler can run continuously without manual intervention and maintaining system stability.

2.2 **Data Cleaning**

The cleaning module uses local Redis as the only communication channel to convert the original multi-source crawler output into a consistent and trustworthy dataset. The upstream module pushes the original JSON string into the db_in. The cleaner detects the data and reads the database, and writes the cleaned result as a dedicated clean_data_queue to db_out while ensuring that the original data remains intact.

In terms of methodology, the execution mode of the cleaning module is standardized. Heterogeneous fields are mapped into a unified structure, including id, source, created_at, timestamp, title, text, author, score, comments, tags, url, and selected source specific attributes such as subreddit, symbol, symbols, and user_followers. Various formats of timestamps are standardized to UTC ISO 8601. The text content is decoded, stripped of HTML and control characters, and standardized into clean title and text.

Next, the cleaning module will discard records that do not have id and url, have publishing times that cannot be parsed, or have text shorter than a configurable threshold (default 10 characters). Only semantically reliable fields are retained. For example, StockTwits bullish/bearish sentiment is retained, while noisy sentiment fields from other sources are cleared.

Finally, the cleaning module tracks the total number of processed items and outputs new data to Redis in LPUSH mode. Every time it runs, it calculates how many new elements have appeared and precisely processes the prefix to avoid re reading old data. Data deduplication is achieved through a Redis collection consisting of source::id or url (if necessary) keywords to prevent cross-source ID collisions and duplicate entries across runs. Each execution also records concise runtime metadata in Redis and log files, creating transparent and repeatable cleaning tasks.

2.3 **Data Processing**

The data processing module serves as the core analytical engine of the financial sentiment analysis system, employing a layered processing architecture to transform raw text data into structured market intelligence. The entire processing workflow follows an event-driven model to ensure real-time responsiveness and efficient analysis.

The system workflow begins with the data acquisition phase, where standardized text data from the data cleaning module is continuously received through Redis message queues. This is followed by the text preprocessing stage, which includes word segmentation, stop word filtering, and short word removal, utilizing a custom financial domain dictionary to optimize analytical accuracy.

The sentiment analysis phase adopts a dual-track parallel mechanism: the primary path uses pre-trained BERT models for deep semantic understanding to automatically identify bullish/bearish sentiment tendencies in the text; the backup path activates a rule engine based on keyword matching when the model is unavailable, ensuring continuous system availability.

The trend detection module employs a time window comparison strategy, comparing keyword frequencies from the current period (e.g., last 60 minutes) with historical benchmarks (e.g., 24-hour average). By comprehensively calculating frequency weights and growth rate indicators, it generates trend scores that reflect changes in market attention.

During the data output phase, processing results are simultaneously written to two destinations: Redis database for real-time invocation by the visualization module, and local JSON files for historical data archiving and offline analysis. The entire process incorporates fault-tolerant design, maintaining core functionality during network interruptions or system failures.

2.4 **Data Visualization**

The visualization module provides a comprehensive real-time dashboard for financial sentiment analysis, implemented using Vue 3 frontend framework and FastAPI backend with WebSocket support. The system comprises six core visualization components.

The Sentiment Bar presents positive/negative sentiment distribution via 2 animated horizontal progress bars (dynamically updating with counts/percentages) and a bottom summary panel with total comments, sentiment trend, and a consolidated score for market polarity assessment; the Trend Chart uses multi-line charts with legends/gridlines to visualize 24-hour keyword frequency fluctuations, merging time series data and dynamically scaling the Y-axis for temporal pattern comparison; the Word Cloud Analysis represents high-frequency keywords with frequency-correlated font sizes and seeded pseudo-random rotations/skew transformations for visual diversity; the Trending Keywords Panel ranks keywords by growth rate in a scrollable list, displaying growth percentage, sentiment distribution, total comments, and frequency metrics with real-time ranking change animations; the News Feed shows recent news in a vertical scrollable list with source, publish time, sentiment labels, heat scores for relevance, and clickable keyword tags; the News Sources Distribution uses a pie chart to illustrate source composition, supporting cross-source information coverage analysis.

**3 Discussions**

The system successfully demonstrates the viability of an integrated, event-driven pipeline for real-time financial trend analysis. The modular architecture enabled parallel development and clear integration, while the Redis-based communication layer unified data persistence and messaging, simplifying the overall design.

Data quality was crucial, with the cleaning module ensuring downstream accuracy through deduplication and filtering. Current limitations include English-only focus and domain specificity, which restrict generalizability. Future work could incorporate multi-lingual analysis, semantic duplicate detection, and integration with real-time market data.

The system validates its core objective, providing a solid foundation for timely market intelligence and future enhancements.