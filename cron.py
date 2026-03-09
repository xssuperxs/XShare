import baostock as bs
import pandas as pd
from datetime import datetime
import subprocess
import sys


def get_last_trade_date():
    rs = bs.query_history_k_data_plus('sh.000001',
                                      fields="date,code,open,high,low,close,volume",  # 根据需要选择字段
                                      start_date='2026-03-01',  # 可以指定一个较近的开始日期，减少数据量
                                      end_date='',  # 留空以获取到最新交易日
                                      frequency="d",
                                      adjustflag="3")

    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)

    # 提取最后一个交易日的日期
    if not result.empty:
        last_date = result['date'].iloc[-1]  # 关键代码
        return last_date
    else:
        print("没有查询到数据")


# subprocess.run() 会等待子进程执行完成才继续执行后续代码：
if __name__ == '__main__':
    today = datetime.now().strftime("%Y-%m-%d")
    bs.login()
    last_trade_day = get_last_trade_date()
    bs.logout()
    if today != last_trade_day:
        exit(0)
    venv_python = "/root/work/code/.venv/bin/python"
    weekday_now = datetime.now().weekday()

    if weekday_now < 5:  # 礼拜四之前都这样操作
        subprocess.run([venv_python, '/root/work/code/as1.py', 'd'])
        if weekday_now == 4:
            subprocess.run([venv_python, '/root/work/code/as1.py', 'w'])


# 30 22 * * * /root/work/code/.venv/bin/python /root/work/code/cron.py >> /root/work/log/cron.log 2>&1