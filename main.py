from xshare import KlinesAnalyzer as ka
import pandas as pd

data = {
    'open': [12.02],
    'high': [12.05],
    'low': [11.83],
    'close': [11.86]
}

df = pd.DataFrame(data)


print(ka.check_real_bearish(df.iloc[0]))