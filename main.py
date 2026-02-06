import akshare as ak
import pandas as pd
import baostock as bs
from datetime import datetime, timedelta

# bs.login()
# rs = bs.query_history_k_data_plus(
#     code='sh.000001',
#     fields="date",  # 字段可调整
#     start_date='1988-01-01',  # 尽可能早的日期
#     end_date='2050-12-31',  # 未来日期确保覆盖最新数据
#     frequency='w',  # d=日线，w=周线，m=月线
#     adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
# )
# data_list = []
# while (rs.error_code == '0') & rs.next():
#     data_list.append(rs.get_row_data())
#
# df = pd.DataFrame(data_list, columns=rs.fields)
# start_date = df['date'].iloc[-102]
# end_date = df['date'].iloc[-1]
#
# bs.logout()
