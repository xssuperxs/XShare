from xshare import KlinesAnalyzer as ka
import pandas as pd

data = {
    'open': [57.50],
    'high': [57.65],
    'low': [56],
    'close': [56.32]
}

df = pd.DataFrame(data)


print(ka.check_real_bearish(df.iloc[0]))