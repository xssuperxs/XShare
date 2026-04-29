import db
import baostock as bs

if __name__ == '__main__':
    fpa = db.get_ana_text("1")
    print(fpa)
    # ret_data, date, period = db._get_stock_data('2025-08-08')
    # print(ret_data)
    # print(date)
    # print(period)
    # my_list = [1, 2, 3, 4, 5]
    # result = ', '.join(str(item) for item in my_list)
    # print(result)  # 输出: 1, 2, 3, 4, 5
    # # print(db.check_user("LiuKeSheng1"))
