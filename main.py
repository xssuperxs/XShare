import numpy as np

import xshare
from scipy.signal import argrelextrema

from scipy.signal import find_peaks

ret_df = xshare._bs_get_stock_hist('sh.605136', 'd', '2010-07-12', '2024-07-12')
high_values = ret_df['high'].tail(100)
low_values = ret_df['low'].tail(100)
print(low_values.values)
print(len(ret_df))
high_idx = argrelextrema(high_values.values, np.greater, order=1)[0]
low_idx = argrelextrema(low_values.values, np.less, order=1)[0]
valley_idx, properties = find_peaks(-low_values, distance=1)
print(f"find_peaks 找到的谷值: {valley_idx}")
print(low_idx)

# order = 5
# data = [10, 0, 3., 1]
# aaa = np.array(data)
# # 寻找局部最大值和最小值
# high_idx = argrelextrema(aaa.values, np.greater, order=order)[0]
# low_idx = argrelextrema(aaa.values, np.less, order=order)[0]

# data = {
#     'open': [57.50],
#     'high': [57.65],
#     'low': [56],
#     'close': [56.32]
# }
#
# df = pd.DataFrame(data)
#
#
# print(ka.check_real_bearish(df.iloc[0]))

# 高斯平滑
# sigma = 2  # 平滑程度，越大越平滑
# smoothed_high = gaussian_filter1d(high_values, sigma=sigma)
#
# # 在平滑数据上寻找极值点
# local_max_idx = argrelextrema(smoothed_high, np.greater)[0]
# local_min_idx = argrelextrema(smoothed_high, np.less)[0]
#
# print(f"平滑后找到的极大值点数量: {len(local_max_idx)}")
# print(f"平滑后找到的极小值点数量: {len(local_min_idx)}")

# import matplotlib.pyplot as plt
#
# plt.figure(figsize=(15, 8))
#
# # 绘制价格曲线
# plt.plot(high_values, label='High Price', alpha=0.7)
#
# # 绘制原始极值点
# plt.scatter(local_max_idx_raw, high_values[local_max_idx_raw],
#            color='red', s=50, label='Original Max', marker='v')
# plt.scatter(local_min_idx_raw, high_values[local_min_idx_raw],
#            color='green', s=50, label='Original Min', marker='^')
#
# # 绘制过滤后的极值点
# plt.scatter(filtered_max, high_values[filtered_max],
#            color='darkred', s=100, label='Filtered Max', marker='v', edgecolors='black')
# plt.scatter(filtered_min, high_values[filtered_min],
#            color='darkgreen', s=100, label='Filtered Min', marker='^', edgecolors='black')
#
# plt.legend()
# plt.title('Extrema Points Filtering Comparison')
# plt.xlabel('Time')
# plt.ylabel('Price')
# plt.grid(True, alpha=0.3)
# plt.show()
