# import baostock as bs
# import datetime
# import pandas as pd
#
#
# def get_trade_dates(period: str = 'd') -> tuple[str, str]:
#     today = datetime.date.today()
#     start_date = (today - datetime.timedelta(weeks=103)).strftime('%Y-%m-%d')
#     rs = bs.query_history_k_data_plus(
#         code='sh.000001',
#         fields="date",  # 字段可调整
#         start_date=start_date,  # 尽可能早的日期
#         end_date='2050-12-30',  # 未来日期确保覆盖最新数据
#         frequency=period,  # d=日线，w=周线，m=月线
#         adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
#     )
#     data_list = []
#     while (rs.error_code == '0') & rs.next():
#         data_list.append(rs.get_row_data())
#     df = pd.DataFrame(data_list, columns=rs.fields)
#     start_date = df['date'].iloc[-101]
#     end_date = df['date'].iloc[-1]
#     return start_date, end_date
#
#
# bs.login()
# print(get_trade_dates())
# bs.logout()
