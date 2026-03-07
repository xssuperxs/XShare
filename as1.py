
import subprocess
import sys
import sqlite3
import xshare


def append_result(ret_list, code, end_date, period):
    ret_list.insert(0, code)
    ret_list.insert(3, end_date)
    ret_list.insert(4, period)
    return ret_list


def analyze_A_stocks(period):
    codes = xshare.bs_get_stock_codes()
    if not codes:
        return []
    nError = 0
    ret_results = []
    for code in codes:
        try:
            ret_list = xshare.analyze_an_stock(code, period)
            if ret_list:
                ret_results.append(period)
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
    p_period = 'd' if len(sys.argv) > 1 and sys.argv[1] == 'd' else 'w'
    analyze_A_stocks(p_period)

