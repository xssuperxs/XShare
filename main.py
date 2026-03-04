import sqlite3
import numpy as np


print(0==0)

# data_list = []
#
# data = ['sh.000042', np.float64(1749.72), np.float64(1817.22), '2026-03-03', 'd', np.int64(9)]
#
# data_list.append(data)
#
# conn = sqlite3.connect('/root/work/data/xshare.db')
#
# cursor = conn.cursor()
#
# for data in data_list:
#     cursor.execute('''
#         INSERT OR REPLACE INTO xshare.db
#         VALUES (?, ?, ?, ?, ?, ?)
#     ''', data)
#
# conn.commit()
# conn.close()
# print(f"成功插入 {len(data_list)} 条数据！")