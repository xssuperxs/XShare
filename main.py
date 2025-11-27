import thsdata
import pandas as pd


def get_all_stock_codes():
    """
    获取所有A股股票代码
    """
    # 登录
    td = thsdata.Data()
    if not td.login(user="18522276766", password="123456tt", exe_path="D:\\同花顺软件\\同花顺\\hexinlauncher.exe"):
        print("登录失败！")
        return None

    try:
        # 定义不同市场的代码
        # 上海交易所
        sh_stocks = td.get_stock_list(market="SH")  # 或类似方法
        # 深圳交易所
        sz_stocks = td.get_stock_list(market="SZ")  # 或类似方法

        # 合并两个市场的股票
        all_stocks = sh_stocks + sz_stocks

        print(f"共获取到 {len(all_stocks)} 只股票")
        return all_stocks

    except Exception as e:
        print(f"获取股票列表时出错: {e}")
        return None
    finally:
        td.logout()


# 使用示例
codes = get_all_stock_codes()
if codes:
    # 打印前20只股票
    for i, code in enumerate(codes[:20]):
        print(f"{i + 1}: {code}")