import xshare
import subprocess
import sys
from tqdm import tqdm
import datetime


def back_test(code, end_date, period='d'):
    # 解析结束日期
    end = datetime.datetime.strptime(end_date, '%Y-%m-%d')

    # 计算100周前（1周 = 7天）
    start = end - datetime.timedelta(weeks=100)
    # 格式化
    end_date = end.strftime('%Y-%m-%d')
    start_date = start.strftime('%Y-%m-%d')

    xshare._end_date_d = xshare._end_date_w = end_date
    xshare._start_date_d = xshare._start_date_w = start_date
    return xshare.analyze_an_stock(code, period)


def analyze_A(period):
    codes = xshare.bs_get_stock_codes()
    if not codes:
        print("baostock 可能没有更新完成 稍后再试！")
        return []
    # 使用 tqdm 包装循环，并设置中文描述
    print("[INFO] Analyzing  A stocks and ETF...")
    nError = 0
    ret_results = []
    for code in tqdm(codes, desc="Progress"):
        try:
            if xshare.analyze_an_stock(code, period):
                ret_results.append(code[-6:])
        except Exception as e:
            nError += 1
            if nError == 1:
                print(f"A Error: {e}")
            continue
    if nError > 1:
        print("analyze_A error count:" + str(nError))

    return ret_results


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
    print("[INFO] Updating required packages...")
    # 使用 tqdm 显示进度
    with tqdm(packages, desc="Updating", unit="package") as pbar:
        for package in pbar:
            pbar.set_postfix_str(f"Current: {package['name']}")
            try:
                # 静默安装，避免输出干扰进度条
                subprocess.check_call(
                    package["command"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError as e:
                tqdm.write(f"[ERROR] Failed to update {package['name']}: {e}")
            except Exception as e:
                tqdm.write(f"[ERROR] Unexpected error with {package['name']}: {e}")


def handle_results(results):
    # 输出的文件路径
    file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"

    print("Analysis completed.： total: ", len(results))

    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in results:
            file.write(f'{item}\n')


if __name__ == '__main__':
    test = True
    if test:
        print(back_test('sh.605155', '2024-09-30', period='w'))
        sys.exit(0)
    p_period = 'd' if len(sys.argv) > 1 and sys.argv[1] == 'd' else 'w'
    print(p_period)
    # 更新包
    update_packets()
    # 开始分析
    handle_results(analyze_A(p_period))
