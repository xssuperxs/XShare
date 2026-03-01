import datetime

import baostock as bs
import pandas as pd
import threading
import time
from typing import Optional, List


class XBaoStock:
    """
    BaoStock数据获取类 - 使用类方法管理连接
    """
    # 类变量：所有实例共享
    _connection = None
    _is_connected = False

    @classmethod
    def login(cls) -> bool:
        """
        类方法：建立连接
        所有实例共享同一个连接
        """
        try:
            lg = bs.login()
            if lg.error_code == '0':
                cls._connection = lg
                cls._is_connected = True
                return True
            else:
                print(f"连接失败：{lg.error_msg}")
                return False
        except Exception as e:
            print(f"连接异常：{e}")
            return False

    @classmethod
    def logout(cls) -> None:
        """
        类方法：断开连接
        """
        if cls._is_connected:
            try:
                bs.logout()
            except Exception as e:
                print(f"断开连接异常：{e}")
            finally:
                cls._connection = None
                cls._is_connected = False

    @classmethod
    def get_trade_dates(cls, period: str = 'd') -> tuple[str, str]:
        today = datetime.date.today()
        start_date = (today - datetime.timedelta(weeks=103)).strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(
            code='sh.000001',
            fields="date",  # 字段可调整
            start_date=start_date,  # 尽可能早的日期
            end_date='2050-12-30',  # 未来日期确保覆盖最新数据
            frequency=period,  # d=日线，w=周线，m=月线
            adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
        )
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        df = pd.DataFrame(data_list, columns=rs.fields)
        start_date = df['date'].iloc[-101]
        end_date = df['date'].iloc[-1]
        return start_date, end_date

    @classmethod
    def get_stock_codes(cls, code_type: tuple = ("1", "2")) -> List[str]:
        """
        :param code_type:  获取需要类型的股票 代码  1是股票 2是代码 5是ETF  4是转债
        :return: 返回提取的股票代码  带有sh.600519  sz.000353 这样格式的list
        """
        print("[INFO] Fetching stock codes...")
        stock_list = bs.query_stock_basic()
        stock_df = stock_list.get_data()
        filtered_stocks = stock_df[
            (stock_df['type'].isin(code_type)) &  # 1 是股票  5 是ETF  2是指数
            (stock_df['status'] == '1') &  # 在交易
            (~stock_df['code_name'].str.contains('ST|\\*ST|退|警示|终止上市', na=False))  # 排除ST股和问题股
            ]
        # 获取股票代码列表
        code_list = filtered_stocks['code'].tolist()
        # 过滤掉暂时不需要的代码
        patterns = [".7", ".9", ".688", ".4"]
        ret_cods = [item for item in code_list if not any(pattern in item for pattern in patterns)]
        return ret_cods

    @classmethod
    def get_stock_hist(cls, code: str, period: str = 'd',
                       start_date: str = None,
                       end_date: str = None) -> Optional[pd.DataFrame]:
        """
        类方法：获取股票历史数据
        """
        # 1. 获取数据
        try:
            fields = "date,open,close,high,low,volume,amount"

            rs = bs.query_history_k_data_plus(
                code=code,
                fields=fields,  # 字段可调整
                start_date=start_date,  # 尽可能早的日期
                end_date=end_date,  # 未来日期确保覆盖最新数据
                frequency=period,  # d=日线，w=周线，m=月线
                adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
            )
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            df = pd.DataFrame(data_list, columns=rs.fields)
            if df.empty:
                return df

            float_cols = ['open', 'close', 'high', 'low', 'volume', 'amount']
            # 转换并保留两位小数
            df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').round(2)
            return df

        except Exception as e:
            print(f"获取数据异常：{e}")
            return None
