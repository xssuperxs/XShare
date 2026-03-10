import cron
import xshare
import sqlite3

last_date = cron.get_last_trade_date()

# 连接数据库
conn = sqlite3.connect('/root/work/data/xshare.db')
cursor = conn.cursor()

# 查询as1表的所有数据
cursor.execute("SELECT * FROM as1")
rows = cursor.fetchall()

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