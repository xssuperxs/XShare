import baostock as bs
import pandas as pd
import akshare as ak
from dateutil.relativedelta import relativedelta
from datetime import datetime

if __name__ == '__main__':
    "stock_board_industry_cons_em"  # 行业板块-板块成份
    "stock_board_industry_hist_em"  # 行业板块-历史行情
    "stock_board_industry_hist_min_em"  # 行业板块-分时历史行情
    "stock_board_industry_name_em"  # 行业板块-板块名称
    #
    # df = ak.stock_zh_index_daily('sh000001')
    # last_trade_date = df['date'].iloc[-1]
    # previous_year_date = last_trade_date - relativedelta(years=1)
    # start_date = previous_year_date.strftime("%Y%m%d")
    # end_date = last_trade_date.strftime("%Y%m%d")  # 输出 '20301230'
    #
    # # df = ak.stock_board_industry_hist_em(symbol='半导体', start_date=start_date, end_date=end_date)
    # # print(df)
    # df = ak.stock_board_industry_name_em()
    # # 方法1：使用列表推导式
    # tuple_list = [(row['板块名称'], row['板块代码']) for _, row in df.iterrows()]
    #
    # # 遍历每个元组
    # for name, code in tuple_list:
    #     # 示例计算：计算板块名称的长度（你可以替换成你的实际计算逻辑）
    #
    #     df = ak.stock_board_industry_hist_em(symbol=name, start_date=start_date, end_date=end_date)
    #
    #     df = df.tail(100)
    #
    #     # 添加到新列表
    #     new_tuple_list.append(new_tuple)
    #
    # print(df)
    df = ak.stock_board_industry_hist_em()
    print(df)
    print(df)
    # df_name = ak.stock_board_industry_name_ths()
    #
    # print(df_name)
    # stock_code = "sh000300"  # 沪市用 sh600000

    #
    # # 向前减一年
    #
    #
    # start_date = previous_year_date.strftime("%Y%m%d")
    # end_date = last_trade_date.strftime("%Y%m%d")  # 输出 '20301230'
    #
    # # df = ak.stock_board_industry_info_ths()
    # df = ak.stock_board_industry_index_ths(symbol='种植业与林业', start_date='20250430', end_date='20300531')

    print(df)

    lg = bs.login()  # 登录系统
    # 设置股票代码（注意格式：sh.600519）
    # rs = bs.query_stock_industry()
    # print('query_stock_industry respond error_code:' + rs.error_code)
    # print('query_stock_industry respond error_msg:' + rs.error_msg)
    #
    # # 转换为DataFrame
    # industry_list = []
    # while (rs.error_code == '0') & rs.next():
    #     industry_list.append(rs.get_row_data())
    #
    # industry_df = pd.DataFrame(industry_list, columns=rs.fields)
    # print(industry_df)
    # print(industry_df.head())

    # rs = bs.query_history_k_data_plus("sh.600519",
    #                                   "date,code,open,high,low,close,volume",
    #                                   start_date='1991-07-01', end_date='2030-12-31',
    #                                   frequency="d", adjustflag="3")
    # print('query_history_k_data_plus respond error_code:' + rs.error_code)
    # print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
    #
    # #### 打印结果集 ####
    # data_list = []
    # while (rs.error_code == '0') & rs.next():
    #     # 获取一条记录，将记录合并在一起
    #     data_list.append(rs.get_row_data())
    # result = pd.DataFrame(data_list, columns=rs.fields)
    # result = result.tail(1)
    # print(result)

    # 登出
    bs.logout()

    # 查看数据
    # print(f"获取到 {len(df)} 条记录")
    # print(df.head())
    # print(df.tail())
