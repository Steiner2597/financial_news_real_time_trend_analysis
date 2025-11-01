Format conversion文件夹完成的内容是：
根据从redis上订阅的input_data.json(可能不叫这个名)，来完成Json格式到CSV格式的转化，并输出到Bert_Model的output_data.csv里，进行模型的训练和预测

然后Bert_Model文件夹完成的内容：
将数据分为带sentiment标签的数据和不带sentiment标签的数据
用带sentiment标签的数据进行bert模型的训练 来预测不带sentiment标签的数据 模型的训练已经保存为best_model.pth predict_bert.py直接调取训练的最佳模型来预测就好
最后整合成Analysis目录下的input_data.csv来做词频统计 历史数据和实时数据的分析（历史24h的数据和近30mins的数据）

首先Analysis文件夹的redis链接的部分：
config.py redis_config.py这些文件是redis的配置文件 请根据本地的不同进行调整
config.py - 存储项目配置参数和情感映射关系
data_loader.py - 加载和预处理原始CSV数据，清洗文本并转换时间格式
text_analyzer.py - 提取关键词、计算词频、增长率和趋势分数
sentiment_analyzer.py - 分析文本情感分布（Bullish/Bearish）
history_analyzer.py - 生成关键词的历史趋势数据（24小时时间序列）
news_processor.py - 生成新闻流数据并按时间排序
main.py - 主流程控制器，协调各模块生成最终输出数据
redis_manager.py - Redis数据库连接管理器，负责数据的获取和发布
data_processor.py - 自动化流程控制器，整合数据处理和Redis发布
redis_config.py - Redis连接配置参数存储

data_processor.py 中的 process_automatically() 方法会：
从Redis获取数据 → 保存到 D:\PythonProject\DataEngeneering\DataAnalysis\Format conversion\ 目录（按照实际的来）
处理数据 → 调用 main.py 中的所有功能
生成output.json → 在同级目录生成结果文件
发布到Redis → 将处理结果发布到Redis频道
这个python文件自动化完成了所有的流程

如果不行 可以将代码分开
只完成从Redis获取数据 写一个代码→ 保存到 D:\PythonProject\DataEngeneering\DataAnalysis\Format conversion\ 目录（按照实际的来）
手动在本地执行相关的代码，按顺序先Format conversion里的JsontoCSV再Bert_Model的predict_bert.pyz最后运行Analysis里的main.py生成output.json
生成output.json发布到Redis 写一个代码 → 将处理结果发布到Redis频道