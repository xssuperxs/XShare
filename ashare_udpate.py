from datetime import date, datetime
import pymongo
import akshare as ak

# 定义聚合管道
pipeline = [
    # 按 code 和 trade_date 排序
    {"$sort": {"code": 1, "trade_date": -1}},  # 先按 code 升序，再按 trade_date 降序
    # 按 code 分组，保留每组的第一条数据
    {
        "$group": {
            "_id": "$code",  # 按 code 分组
            "firstDoc": {"$first": "$$ROOT"}  # 保留每组的第一条文档
        }
    },
    # 将结果中的 firstDoc 替换为原始文档
    {"$replaceRoot": {"newRoot": "$firstDoc"}}
]

#  数据库连接
mongoDBCli = pymongo.MongoClient("mongodb://dbroot:123456ttqqTTQQ@113.44.193.120:28018/")
db = mongoDBCli['ashare']
# 集合
coll_klines_day = db['klines_day']

# ========================================== 获取数据库中的数据 ====================================================
# 执行聚合操作 查询数据库的前一个交易日的数据
database_result = list(coll_klines_day.aggregate(pipeline))
# 获取库中的代码列表
database_stocks_list = [doc["code"] for doc in database_result]

# ========================================== 获取当天交易的数据 ====================================================
df_em = ak.stock_zh_a_spot_em()
spot_stocks_list = df_em['代码']


# 生成一条待插入的数据
def construct_doc(code, trade_date):
    record = {}
    try:
        target_stock = df_em[df_em['代码'] == code]
        cur_open = target_stock['今开'].values[0]
        cur_close = target_stock['最新价'].values[0]
        cur_high = target_stock['最高'].values[0]
        cur_low = target_stock['最低'].values[0]
        cur_vol = target_stock['成交量'].values[0]
        cur_price_chg = target_stock['涨跌额'].values[0]

        # 获取前一天记录
        if code in database_stocks_list:
            doc_values = next(
                ((item['open'], item['close'], item['high'], item['low'], item['vol']) for item
                 in
                 database_result if
                 item['code'] == code),
                (None, None, None, None, None, None)  # 如果找不到，返回 (None, None)
            )
        else:  # 新股
            doc_values = (None, None, None, None, None, None)
        # 获取当天的记录
        record = {
            "code": code,
            "open": cur_open,
            "close": cur_close,
            "high": cur_high,
            "low": cur_low,
            "vol": cur_vol,
            "trade_date": trade_date,
            "price_chg": cur_price_chg,
            "pre_open": doc_values[0],
            "pre_close": doc_values[1],
            "pre_high": doc_values[2],
            "pre_low": doc_values[3],
            "pre_vol": doc_values[4]
        }
    except Exception as e:
        print(code)
        print(f"发生未知错误: {e}")
    return record


def update_klines_day():
    stock_trade_info = []
    try:
        # 判断当日是否为交易日
        if datetime.now().date() not in ak.tool_trade_date_hist_sina()['trade_date'].values:
            print(" @@@@@@ " + 'Rest Day : ' + datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒") + " @@@@@@ ")
            return

        # 获取ST股票的代码
        st_stocks_df = ak.stock_zh_a_st_em()
        st_stocks_list = st_stocks_df['代码'].to_list()

        # 更新当天交易日期
        date_obj = datetime.strptime(date.today().strftime('%Y%m%d'), "%Y%m%d")
        # 更新99999的交易日期
        coll_klines_day.update_one(
            {"code": '999999'},  # 查询条件
            {"$set": {"trade_date": date_obj}},  # 更新操作
            upsert=True  # upsert 选项
        )
        for stock_code in spot_stocks_list:
            # ST 股票
            if stock_code in st_stocks_list:
                continue
            # 构造每一条股票的数据
            doc = construct_doc(stock_code, date_obj)
            # 获取数据库中前一条数据

            # coll_klines_day.insert_one(doc)
            stock_trade_info.append(doc)
            print(type(doc))
            print(doc)
        if len(stock_trade_info) > 0:
            coll_klines_day.insert_many(stock_trade_info)

    except Exception as error:
        print(error)


if __name__ == '__main__':
    # 查询的结束日期 当天
    print('==== begin : ' + datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒"), end="")
    update_klines_day()
    mongoDBCli.close()
    print(' end :  ' + datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒") + ' =====')
