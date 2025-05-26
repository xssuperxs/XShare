import akshare as ak

__WINDOW_SIZE = 6
nSubWindow = [i for i in range(2, __WINDOW_SIZE)]

print(nSubWindow)


def update_stock_cache(stock_market):
    pass


if __name__ == '__main__':
    # sector_df = ak.stock_board_industry_name_em()
    # print(sector_df)
    # df = ak.stock_board_industry_hist_em()
    # 获取"半导体"板块的K线数据
    df = ak.stock_board_industry_hist_em()
    ak.stock_zh_index_daily()
    print(df)
