import cron
import xshare
import sqlite3
import pandas as pd

last_date = cron.get_last_trade_date()

print(last_date)
# 连接数据库
# conn = sqlite3.connect('/root/work/data/xshare.db')
conn = sqlite3.connect('D:\\Users\\Administrator\\Desktop\\xshare.db')
cursor = conn.cursor()


def check_today_kline(stock_data: tuple = ()) -> bool:
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


check_today_kline()

# 查询as1表的所有数据
cursor.execute('SELECT * FROM as1')
rows = cursor.fetchall()
for row in rows:

    if check_today_kline(row):
        # 执行更新语句
        cursor.execute("UPDATE as1 SET rcnt = ? WHERE code = ?", (888, row[0]))
        # 提交事务
        conn.commit()
    # 更新RCNT 为 888
    # record = rows
    print(type(row[0]))
    print(row)  # 每条记录是字典格式
    # 可以通过字段名访问：record['字段名']
# 1 999的 直接提取走
# 冲高回落 平头阴 提取走
# 破前低的要提走
# 超过三个月的要提走

# 把符合条件的 全改成 rcnt 888
# 每天要复盘这些股票 其它的不用复盘

# 获取列名
cursor.execute("PRAGMA table_info(as1)")
columns = [column[1] for column in cursor.fetchall()]
print("列名:", columns)

# 显示所有数据
print(f"数据行数: {len(rows)}")
for row in rows:
    print(row)

# 关闭连接
conn.close()
