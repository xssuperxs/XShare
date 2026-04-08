import wecallback as we
import os

filepath = 'D:\\Users\\Administrator\\Desktop\\2026-04-07.txt'

res = we.send_wechat_message('LiuKeSheng', filepath, 'file')
if res.get('errcode') == 0:
    if os.path.exists(filepath):
        os.remove(filepath)
else:
    print('send_wechat_message error!')
print(res)
