import cron
import xshare
import sqlite3
import pandas as pd
import os
import json
import wecallback as we

last_date = cron.get_last_trade_date()

# 连接数据库
# conn = sqlite3.connect('/root/work/data/xshare.db')
conn = sqlite3.connect('D:\\Users\\Administrator\\Desktop\\xshare.db')
cursor = conn.cursor()


def check_today_kline(stock_data: tuple = ()) -> bool:
    if not stock_data:
        return False
    if stock_data[5] == 999:
        return True
    df = xshare.bs_get_stock_hist(stock_data[0], 'd', last_date, last_date)
    if len(df) == 0:
        return False
    # 判断仙人指路 或 平头阴线
    if xshare.check_highToLow(df) or xshare.check_real_bearish(df):
        return True
    if df['low'].iloc[0] < stock_data[1]:
        return True

    # 判断两个日期 大否大于三月
    today_date = pd.to_datetime(df['date'].iloc[0])
    ana_date = pd.to_datetime(stock_data[3])
    # 计算月份差
    months_diff = (ana_date.year - today_date.year) * 12 + (ana_date.month - today_date.month)
    return months_diff > 3


result_list = []

# 查询as1表的所有数据 888 表示已经二次筛选 符合条件的
cursor.execute('SELECT * FROM as1 WHERE rcnt != 888')
rows = cursor.fetchall()
i = 0
for row in rows:
    if check_today_kline(row):
        code_str = row[0]
        # 执行更新语句
        cursor.execute("UPDATE as1 SET rcnt = ? WHERE code = ?", (888, code_str))
        # 提交事务
        conn.commit()
        last_six = code_str[-6:] if len(code_str) >= 6 else code_str
        result_list.append(last_six)
        break

result_str = json.dumps(result_list)  # 转换为 '[1, 2, 3, 4, 5]'
cursor.execute("INSERT INTO as2 (ana_date, result) VALUES (?, ?)", (last_date, result_str))
conn.commit()
# 关闭连接
conn.close()

# 目标目录
data_dir = "D:\\Users\\Administrator\\Desktop\\"
# data_dir = "/root/work/data/"
filename = f"{last_date}.txt"
filepath = os.path.join(data_dir, filename)

# 确保目录存在
os.makedirs(data_dir, exist_ok=True)

# 写入新文件
with open(filepath, 'w', encoding='utf-8') as f:
    for item in result_list:
        f.write(f"{item}\n")

# 开始上传 上传成功后 删除文件
res = we.send_wechat_message('LiuKeSheng', filepath, 'file')
if res.get('errcode') == 0:
    if os.path.exists(filepath):
        os.remove(filepath)
else:
    print('send_wechat_message error!')
