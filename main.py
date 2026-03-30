import wecallback as we

res = we.send_wechat_message('LiuKeSheng', "superxiaoohei")

if res.get('errcode') == 0:
    print('1111')

print(res)
