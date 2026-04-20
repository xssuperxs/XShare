import baostock as bs
import pandas as pd
from datetime import datetime
import subprocess


def get_last_trade_date():
    rs = bs.query_history_k_data_plus('sh.000001',
                                      fields="date,code,open,high,low,close,volume",  # 根据需要选择字段
                                      start_date='2026-03-09',  # 可以指定一个较近的开始日期，减少数据量
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
    bs.login()
    last_trade_day = get_last_trade_date()
    bs.logout()
    today = datetime.now().strftime('%Y-%m-%d')
    # 预防节假日
    if today != last_trade_day:
        exit(0)
    venv_python = "/root/work/code/.venv/bin/python"
    weekday_now = datetime.now().weekday()
    period = 'd'
    if weekday_now < 5:  # 0代表礼拜一
        if weekday_now == 4:
            period = 'w'
        subprocess.run([venv_python, '/root/work/code/as1.py', period])
