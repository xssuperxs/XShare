import platform
import sqlite3

is_windows = platform.system() == "Windows"
db_path = r'D:\Users\Administrator\Desktop\xshare.db' if is_windows else '/root/work/data/xshare.db'
ana_res_dir = r'D:\Users\Administrator\Desktop' if is_windows else '/root/work/data'


def save_ana_data(date, result, period):
    conn = None
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 把所有数据插入到 as2 库中
        cursor.execute("""INSERT OR REPLACE INTO as2 (ana_date, result, period) VALUES (?, ?, ?)""",
                       (date, result, period))
        conn.commit()
        conn.close()
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
