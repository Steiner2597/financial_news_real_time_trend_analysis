import nltk
try:
    # 常用分词模型
    nltk.download('punkt', quiet=True)
    # 某些新版本需要这个（没有也不报错）
    try:
        nltk.download('punkt_tab', quiet=True)
    except Exception:
        pass
    print("NLTK 资源就绪")
except Exception as e:
    print("NLTK 下载遇到问题：", e)
