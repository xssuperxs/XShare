from xshare import KlinesAnalyzer as ka
from xbaostock import XBaoStock as xbs
import subprocess
import sys
import sqlite3



def append_result(ret_list, code, end_date, period):
    ret_list.insert(0, code)
    ret_list.insert(3, end_date)
    ret_list.insert(4, period)
    return ret_list


def analyze_A_stocks(period):
    codes = xbs.get_stock_codes()
    if not codes:
        return []
    nError = 0
    ret_results = []
    start_date, end_date = xbs.get_trade_dates(period)
    start_date_w, end_date_w = xbs.get_trade_dates('w')
    for code in codes:
        try:
            df = xbs.get_stock_hist(code, period, start_date, end_date)
            ret_list = ka.check_pass_peak(df, period)
            if not ret_list:  # 列表为空
                continue

            if period == 'w':
                ret_results.append(append_result(ret_list, code, end_date, period))
                continue
            # 检查周线的快线在水上
            df_weekly = xbs.get_stock_hist(code, 'w', start_date_w, end_date_w)
            is_valid = ka.check2_week_macd(df_weekly)
            if is_valid:
                ret_results.append(append_result(ret_list, code, end_date, period))

        except Exception as e:
            nError += 1
            if nError == 1:
                print(f"A Error: {e}")
            continue
    if nError > 1:
        print("analyze_A error count:" + str(nError))

    # 把数据写到数据库中
    conn = sqlite3.connect('/root/work/data/xshare.db')
    cursor = conn.cursor()

    for data in ret_results:
        cursor.execute('''
            INSERT OR REPLACE INTO xshare.db 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', data)

    conn.commit()
    conn.close()


def update_packets():
    """
    更新需要的库（pip、akshare、baostock），并显示进度条
    :return: None
    """
    # 需要更新的包列表
    packages = [
        {"name": "pip", "command": [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]},
        {"name": "baostock", "command": [sys.executable, "-m", "pip", "install", "--upgrade", "baostock"]}
    ]
    # 使用 tqdm 显示进度
    for pkg in packages:
        try:
            # 执行命令
            subprocess.run(
                pkg['command'],
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception as e:
            print(f"update_packets 执行出错: {e}")


if __name__ == '__main__':
    # 先更新需要的包
    update_packets()
    xbs.login()
    p_period = 'd' if len(sys.argv) > 1 and sys.argv[1] == 'd' else 'w'
    analyze_A_stocks(p_period)
    xbs.logout()
