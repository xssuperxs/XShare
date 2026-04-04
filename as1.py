import subprocess
import sys
import sqlite3
import xshare
import cron
import os
import platform
import wecallback as we

last_date = cron.get_last_trade_date()
is_windows = platform.system() == "Windows"
db_path = r'D:\Users\Administrator\Desktop\xshare.db' if is_windows else '/root/work/data/xshare.db'
ana_res_dir = r'D:\Users\Administrator\Desktop' if is_windows else '/root/work/data'


def analyze_A_stocks(period):
    codes = xshare.bs_get_stock_codes()
    if not codes:
        return []
    nError = 0
    ret_results = []
    ret_codes = []
    for code in codes:
        try:
            ret_list = xshare.analyze_an_stock(code, period)
            if ret_list:
                ret_results.append(ret_list)
                last_six_code = code[-6:] if len(code) >= 6 else code
                ret_codes.append(last_six_code)
        except Exception as e:
            nError += 1
            if nError == 1:
                print(f"A Error: {e}")
            continue
    if nError > 1:
        print("analyze_A error count:" + str(nError))

    # 连接数据库
    conn = sqlite3.connect('/root/work/data/xshare.db')
    cursor = conn.cursor()
    # 把所有数据插入到 as2 库中
    cursor.execute("""INSERT OR REPLACE INTO as2 (ana_date, result) VALUES (?, ?)""", (last_date, ret_codes))
    conn.commit()
    # 把详细数据写到数据库中 as1
    for data in ret_results:
        cursor.execute('''
            INSERT OR REPLACE INTO as1
            VALUES (?, ?, ?, ?, ?, ?)
        ''', data)

    conn.commit()
    conn.close()
    # 把每天分析好的数据 发送到VX
    # 文件名
    filename = f"{last_date}.txt"
    filepath = os.path.join(ana_res_dir, filename)
    # 确保目录存在
    os.makedirs(ana_res_dir, exist_ok=True)

    # 写入新文件
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in ret_codes:
            f.write(f"{item}\n")

    # 开始上传 上传成功后 删除文件
    res = we.send_wechat_message('LiuKeSheng', filepath, 'file')
    if res.get('errcode') == 0:
        if os.path.exists(filepath):
            os.remove(filepath)
    else:
        print('send_wechat_message error!')


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
