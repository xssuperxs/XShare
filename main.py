import wecallback as we
import os
import cron
import baostock as  bs
cron.get_last_trade_date()
# filepath = 'D:\\Users\\Administrator\\Desktop\\2026-04-07.txt'
#
# res = we.send_wechat_message('LiuKeSheng', filepath, 'file')
# if res.get('errcode') == 0:
#     if os.path.exists(filepath):
#         os.remove(filepath)
# else:
#     print('send_wechat_message error!')
# print(res)
bs.login()
print(cron.get_last_trade_date())
bs.logout()