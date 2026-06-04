import platform
import sqlite3
import os
import time

is_windows = platform.system() == "Windows"
db_path = r'D:\Users\Administrator\Desktop\xshare.db' if is_windows else '/root/work/data/xshare.db'
ana_res_dir = r'D:\Users\Administrator\Desktop' if is_windows else '/root/work/data'
TABLE_NAME = 'as2'


def save_ana_data(date, result_list, period):
    if not result_list:
        result_list = ['999999']

    result = ', '.join(str(item) for item in result_list)

    MAX_RETRY = 3
    RETRY_DELAY = 1  # 秒
    for attempt in range(1, MAX_RETRY + 1):
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                "INSERT OR REPLACE INTO as2 (ana_date, result, period) "
                "VALUES (?, ?, ?)",
                (date, result, period)
            )
            conn.commit()

            if check_save_success(date):
                break

        except sqlite3.OperationalError as e:
            # 锁表、磁盘满、数据库忙等
            print(f"[尝试 {attempt}] 数据库操作失败: {e}")
            time.sleep(RETRY_DELAY)

        except sqlite3.Error as e:
            # 其他 SQLite 错误（建表失败、SQL 错误）
            print(f"SQLite 错误: {e}")
            break  # 这类错误重试也没用

        except Exception as e:
            print(f"未知错误: {e}")
            break

        finally:
            if conn:
                conn.close()

    else:
        raise RuntimeError(f"写入数据库失败，ana_date={date}")


def check_save_success(target_date):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1
            FROM as2
            WHERE ana_date = ?
            LIMIT 1
        """, (target_date,))
        exists = cursor.fetchone() is not None
    except sqlite3.Error as e:
        print(f"err :check_save_success: {e}")
        return False
    finally:
        if conn:
            conn.close()
    return exists


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
