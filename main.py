def calculate_limit_up_price(prev_close, limit_rate=0.10):
    """
    计算涨停价

    参数:
    prev_close: 前收盘价
    limit_rate: 涨跌幅限制（默认10%）

    返回:
    float: 涨停价（四舍五入到0.01元）
    """
    limit_up = prev_close * (1 + limit_rate)
    return round(limit_up, 2)

    (20.12, 22.13, 30.15)


print(calculate_limit_up_price(29.10))
