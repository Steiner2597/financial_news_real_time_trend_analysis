# 配置文件
CONFIG = {
    # 原有配置...
    "input_file": "input_data.csv",
    "output_file": "output_data.json",
    "trending_keywords_count": 10,
    "word_cloud_count": 20,
    "history_hours": 24,
    "history_interval_minutes": 30,
    
    # 持续处理配置
    "process_interval_seconds": 60,  # 处理间隔（秒），默认1分钟

    # Redis配置
    "redis": {
        "host": "localhost",
        "port": 6379,
        
        # 💡 数据流配置
        "input_db": 1,              # 从 DB1 读取（Cleaner 的输出）
        "output_db": 2,             # 输出到 DB2（Visualization 的输入）
        
        # 💡 队列名配置
        "input_queue": "clean_data_queue",    # 从 Cleaner 的输出队列读取
        "output_prefix": "processed_data",    # 输出键的前缀
        
        # 💡 通知监听配置（从 Cleaner 接收）
        "notification": {
            "enabled": True,              # 是否启用事件驱动
            "channel": "cleaner_complete",  # 监听频道
            "mode": "event_driven"        # 运行模式
        },
        
        # 可选：发布订阅（用于实时通知）
        "publish_channel": "processed_data_updates",
        
        # 过期时间
        "key_ttl_seconds": 86400,  # 24小时
        
        "password": None,
        
        # 保留：旧配置（兼容性）
        "raw_data_channel": "raw_financial_data",
        "processed_data_channel": "processed_financial_data"
    },

    "stop_words": [
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
        "this", "that", "these", "those", "it", "its", "it's", "i", "you", "he",
        "she", "we", "they", "my", "your", "his", "her", "our", "their", "me",
        "him", "us", "them", "what", "which", "who", "whom", "whose", "where",
        "when", "why", "how", "all", "any", "both", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "s", "t", "can", "will", "just",
        "don", "should", "now", "d", "ll", "m", "o", "re", "ve", "y", "ain",
        "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn",
        "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren",
        "won", "wouldn", "$", "http", "https", "com", "www"
    ]
}