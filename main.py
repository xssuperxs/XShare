from xshare import KlinesAnalyzer as ka
import pandas as pd

data = {
    'open': [25.74],
    'high': [26.18],
    'low': [25.23],
    'close': [25.76]
}

df = pd.DataFrame(data)


print(ka.check_highToLow(df.iloc[0]))