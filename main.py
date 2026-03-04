from xshare import KlinesAnalyzer as ka
import pandas as pd

data = {
    'open': [39.80],
    'high': [39.80],
    'low': [38.77],
    'close': [39.10]
}

df = pd.DataFrame(data)


print(ka.check_real_bearish(df.iloc[0]))