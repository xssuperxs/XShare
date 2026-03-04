from xshare import KlinesAnalyzer as ka
import pandas as pd

data = {
    'open': [1.84],
    'high': [1.9],
    'low': [1.74],
    'close': [1.79]
}

df = pd.DataFrame(data)


print(ka.check_real_bearish(df.iloc[0]))