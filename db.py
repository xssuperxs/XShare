import platform
import sqlite3
import os

is_windows = platform.system() == "Windows"
db_path = r'D:\Users\Administrator\Desktop\xshare.db' if is_windows else '/root/work/data/xshare.db'
ana_res_dir = r'D:\Users\Administrator\Desktop' if is_windows else '/root/work/data'


def save_ana_data(date, result_list, period):
    result = ', '.join(str(item) for item in result_list)
    conn = None
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 把所有数据插入到 as2 库中
        cursor.execute("""INSERT OR REPLACE INTO as2 (ana_date, result, period) VALUES (?, ?, ?)""",
                       (date, result, period))
        conn.commit()
    except Exception as e:
        # 其他未知错误
        print(f"发生未知错误: {e}")
    finally:
        if conn:
            conn.close()


def check_user(user_name):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 使用 EXISTS 查询，效率高
        cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM user WHERE uname = ?
                )
            """, (user_name,))

        # 获取结果 (0 或 1)
        exists = cursor.fetchone()[0]
        return bool(exists)

    except sqlite3.Error as e:
        print(f"数据库查询错误: {e}")
        return False
    finally:
        if conn:
            conn.close()


def _get_stock_data(date):
    none_tuple = (None, None, None)
    if len(date) > 8:
        query = f"SELECT result, ana_date, period FROM as2 WHERE ana_date = '{date}'"
    else:
        query = "SELECT result, ana_date, period FROM as2 ORDER BY ana_date DESC LIMIT 1"

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                return result[0], result[1], result[2]  # 返回result字段的值
            else:
                return none_tuple

    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        return none_tuple
    except Exception as e:
        print(f"错误: {e}")
        return none_tuple


def get_ana_text(date):
    ret_data, date, period = _get_stock_data(date)
    if ret_data is None:
        return None
    data_list = [int(x) for x in ret_data.split(',')]
    filename = f"{date}_{period}.txt"
    filepath = os.path.join(ana_res_dir, filename)
    os.makedirs(ana_res_dir, exist_ok=True)
    # 写入新文件
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data_list:
            f.write(f"{item}\n")
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        if file_size > 0:
            return filepath
    return None
#
#    if period == 'w':
#        filename = f"{last_date}_w.txt"
#    filepath = os.path.join(ana_res_dir, filename)
#    # 确保目录存在
#    os.makedirs(ana_res_dir, exist_ok=True)
#
#    # 写入新文件
#    with open(filepath, 'w', encoding='utf-8') as f:
#        for item in ret_codes:
#            f.write(f"{item}\n")
#
#    # 开始上传 上传成功后 删除文件
#    res = we.send_wechat_message('LiuKeSheng', filepath, 'file')
#    if res.get('errcode') == 0:
#        if os.path.exists(filepath):
#            os.remove(filepath)
#    else:
#        print('send_wechat_message error!')
