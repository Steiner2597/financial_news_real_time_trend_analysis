# 配置文件
CONFIG = {
    # 原有配置...
    "input_file": "input_data.csv",
    "output_file": "output_data.json",
    "trending_keywords_count": 10,
    "word_cloud_count": 20,
    
    # ⏰ 时间窗口配置
    "current_window_minutes": 60,  # 当前窗口时长（分钟）- 用于计算当前词频
    "history_hours": 24,  # 历史窗口时长（小时）- 用于计算历史平均频率
    "history_interval_minutes": 60,
    
    # 持续处理配置
    "process_interval_seconds": 60,  # 处理间隔（秒），默认1分钟
    
    # 🤖 BERT 情感预测配置
    "bert": {
        "enabled": True,                    # 是否启用 BERT 预测
        "model_path": None,                 # 模型路径（None 表示自动查找）
        "max_len": 256,                     # 最大序列长度
        "batch_size": 128,                   # 批处理大小
        "fallback_to_simple": True,         # 模型加载失败时使用简单规则
        "defer_redis_update": True          # ✅ 延迟 Redis 更新（速度快 5 倍）
    },

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
        # 25.11.19-9:30 LUWEI新增
        "does", "did", "day", "lot","bro","lol","thing","things","yeah","long","post",
        "action","work","doing","kind","let","point","home","life","message","told",
        "automatically","subreddit","contact","que","questions","question","person",
        "man","comment","compose","performed","days","started","having",
        # 25.11.19-9:30 LUWEI新增 - 结束
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
        "won", "wouldn", "$", "http", "https", "com", "www", "has", "have","people",
        "would","know","about","think","even","one","also","into","could","out",
        "there","had","from","beacuse","time","a", "about", "above", "across", "after", "afterwards", "again", "against", "all", "almost",
        "alone", "along", "already", "also", "although", "always", "am", "among", "amongst", "amoungst",
        "amount", "an", "and", "another", "any", "anyhow", "anyone", "anything", "anyway", "anywhere",
        "are", "around", "as", "at", "back", "be", "became", "because", "become", "becomes",
        "becoming", "been", "before", "beforehand", "behind", "being", "below", "beside", "besides", "between",
        "beyond", "bill", "both", "bottom", "but", "by", "call", "can", "cannot", "cant",
        "co", "computer", "con", "could", "couldnt", "cry", "de", "describe", "detail", "do",
        "done", "down", "due", "during", "each", "eg", "eight", "either", "eleven", "else",
        "elsewhere", "empty", "enough", "etc", "even", "ever", "every", "everyone", "everything", "everywhere",
        "except", "few", "fifteen", "fifty", "fill", "find", "fire", "first", "five", "for",
        "former", "formerly", "forty", "found", "four", "from", "front", "full", "further", "get",
        "give", "go", "had", "has", "hasnt", "have", "he", "hence", "her", "here",
        "hereafter", "hereby", "herein", "hereupon", "hers", "herself", "him", "himself", "his", "how",
        "however", "hundred", "i", "ie", "if", "in", "inc", "indeed", "interest", "into",
        "is", "it", "its", "itself", "keep", "last", "latter", "latterly", "least", "less",
        "ltd", "made", "many", "may", "me", "meanwhile", "might", "mill", "mine", "more",
        "moreover", "most", "mostly", "move", "much", "must", "my", "myself", "name", "namely",
        "neither", "never", "nevertheless", "next", "nine", "no", "nobody", "none", "noone", "nor",
        "not", "nothing", "now", "nowhere", "of", "off", "often", "on", "once", "one",
        "only", "onto", "or", "other", "others", "otherwise", "our", "ours", "ourselves", "out",
        "over", "own", "part", "per", "perhaps", "please", "put", "rather", "re", "same",
        "see", "seem", "seemed", "seeming", "seems", "serious", "several", "she", "should", "show",
        "side", "since", "sincere", "six", "sixty", "so", "some", "somehow", "someone", "something",
        "sometime", "sometimes", "somewhere", "still", "such", "system", "take", "ten", "than", "that",
        "the", "their", "them", "themselves", "then", "thence", "there", "thereafter", "thereby", "therefore",
        "therein", "thereupon", "these", "they", "thick", "thin", "third", "this", "those", "though",
        "three", "through", "throughout", "thru", "thus", "to", "together", "too", "top", "toward",
        "towards", "twelve", "twenty", "two", "un", "under", "until", "up", "upon", "us",
        "very", "via", "was", "we", "well", "were", "what", "whatever", "when", "whence",
        "whenever", "where", "whereafter", "whereas", "whereby", "wherein", "whereupon", "wherever", "whether", "which",
        "while", "whither", "who", "whoever", "whole", "whom", "whose", "why", "will", "with",
        "within", "without", "would", "yet", "you", "your", "yours", "yourself", "yourselves","make","way","going",
        "new","buy","need","really","year","years","nbsp","want","like","use",
        "said", "says", "according", "accordingly", "added", "additionally", "almost", "already",
        "although", "altogether", "anyhow", "anyone", "anything", "anyway", "anyways", "anywhere",
        "appear", "appreciate", "appropriate", "around", "aside", "ask", "asking", "associated",
        "available", "away", "basically", "became", "become", "becomes", "becoming", "beforehand",
        "begins", "behind", "believe", "beside", "besides", "better", "beyond", "brief", "briefly",
        "came", "cannot", "cant", "certain", "certainly", "clearly", "come", "comes", "completely",
        "concerning", "consequently", "consider", "considering", "contain", "containing", "contains",
        "corresponding", "course", "currently", "definitely", "described", "despite", "done",
        "downwards", "during", "easily", "either", "entirely", "especially", "essentially", "everybody",
        "everyone", "everything", "everywhere", "exactly", "example", "except", "exactly", "fact",
        "far", "fifth", "finally", "five", "followed", "following", "follows", "former", "formerly",
        "forth", "four", "furthermore", "generally", "gets", "getting", "given", "gives", "goes",
        "going", "gone", "got", "gotten", "greetings", "hardly", "hello", "help", "hence", "hereafter",
        "hereby", "herein", "hereupon", "hi", "hither", "hopefully", "howbeit", "however", "immediate",
        "immediately", "important", "indeed", "indicate", "indicated", "indicates", "inner", "insofar",
        "instead", "inward", "it'd", "it'll", "itself", "keep", "keeps", "kept", "knows", "largely",
        "lastly", "lately", "later", "latter", "lest", "let's", "liked", "likely", "look", "looking",
        "looks", "mainly", "many", "maybe", "mean", "means", "meantime", "meanwhile", "merely", "might",
        "moreover", "mostly", "much", "must", "myself", "name", "namely", "near", "nearly", "necessary",
        "need", "needs", "neither", "never", "nevertheless", "next", "nine", "nobody", "non", "none",
        "nonetheless", "noone", "normally", "nothing", "novel", "nowadays", "obviously", "often", "oh",
        "ok", "okay", "old", "once", "ones", "onto", "otherwise", "outside", "overall", "particular",
        "particularly", "past", "per", "perhaps", "placed", "please", "plus", "possible", "presumably",
        "probably", "provides", "quite", "rather", "really", "reasonably", "recently", "regarding",
        "regardless", "regards", "relatively", "respectively", "right", "said", "saw", "say", "saying",
        "says", "second", "secondly", "seeing", "seem", "seemed", "seeming", "seems", "seen", "self",
        "selves", "sensible", "sent", "serious", "seriously", "seven", "several", "shall", "shed",
        "shes", "should", "show", "showed", "shown", "shows", "significant", "significantly", "similar",
        "similarly", "since", "slightly", "somebody", "somehow", "someone", "something", "sometime",
        "sometimes", "somewhat", "somewhere", "soon", "sorry", "specified", "specify", "specifying",
        "still", "sub", "substantially", "successfully", "such", "sufficiently", "sure", "take", "taken",
        "taking", "tell", "tends", "thank", "thanks", "thanx", "thats", "theirs", "themselves", "thence",
        "thereafter", "thereby", "therefore", "therein", "theres", "thereupon", "think", "thorough",
        "thoroughly", "though", "throughout", "thru", "thus", "together", "took", "toward", "towards",
        "tried", "tries", "truly", "try", "trying", "twice", "two", "unfortunately", "unless", "unlikely",
        "until", "unto", "upon", "useful", "usefully", "usefulness", "uses", "using", "usually", "value",
        "various", "very", "via", "viz", "want", "wants", "wasn't", "way", "we'd", "we'll", "we're",
        "we've", "welcome", "well", "went", "weren't", "whatever", "what's", "whence", "whenever",
        "whereafter", "whereas", "whereby", "wherein", "whereupon", "wherever", "whether", "whither",
        "who's", "whoever", "whom", "whose", "widely", "willing", "wish", "within", "without", "won't",
        "wonder", "wouldn't", "yes", "yet", "you'd", "you'll", "you're", "you've", "yourself", "yourselves",
        #经济金融通用术语（无实际分析价值）
        "market", "markets", "price", "prices", "stock", "stocks", "share", "shares", "trade", "trading",
        "invest", "investment", "investor", "investors", "company", "companies", "business", "financial",
        "finance", "economy", "economic", "money", "cash", "currency", "dollar", "dollars", "euro",
        "pound", "yen", "capital", "asset", "assets", "fund", "funds", "bank", "banks", "banking",
        "interest", "rate", "rates", "growth", "profit", "profits", "loss", "losses", "revenue",
        "income", "expense", "cost", "costs", "value", "valuation", "worth", "return", "returns",
        "risk", "risks", "volatility", "volatile", "liquidity", "credit", "debt", "loan", "loans",
        "bond", "bonds", "security", "securities", "index", "indices", "exchange", "sector", "industry",
        "global", "world", "international", "domestic", "foreign", "local", "national", "federal",
        "government", "central", "policy", "policies", "regulation", "regulatory", "law", "laws",
        "tax", "taxes", "inflation", "deflation", "recession", "depression", "crisis", "bubble",
        "cycle", "trend", "trends", "analysis", "analyst", "analysts", "report", "reports", "data",
        "information", "news", "update", "updates", "today", "yesterday", "tomorrow", "week", "weeks",
        "month", "months", "year", "years", "time", "times", "period", "periods", "date", "dates",
        "current", "currently", "recent", "recently", "past", "future", "potential", "potentially",
        "possible", "possibly", "likely", "unlikely", "certain", "certainly", "definite", "definitely",
        "actual", "actually", "real", "really", "true", "truly", "false", "fact", "facts", "figure",
        "figures", "number", "numbers", "amount", "amounts", "total", "totals", "sum", "average",
        "median", "mean", "high", "higher", "highest", "low", "lower", "lowest", "big", "bigger",
        "biggest", "small", "smaller", "smallest", "large", "larger", "largest", "major", "minor",
        "significant", "insignificant", "important", "unimportant", "good", "better", "best", "bad",
        "worse", "worst", "positive", "negative", "neutral", "bullish", "bearish", "optimistic",
        "pessimistic", "strong", "stronger", "strongest", "weak", "weaker", "weakest", "up", "down",
        "rise", "rising", "fall", "falling", "increase", "increasing", "decrease", "decreasing",
        "gain", "gaining", "lose", "losing", "win", "winning", "success", "successful", "fail",
        "failure", "failed", "problem", "problems", "issue", "issues", "challenge", "challenges",
        "opportunity", "opportunities", "threat", "threats", "advantage", "disadvantage", "benefit",
        "benefits", "drawback", "drawbacks", "pro", "cons", "reason", "reasons", "cause", "causes",
        "effect", "effects", "result", "results", "impact", "impacts", "influence", "influences",
    ]
}