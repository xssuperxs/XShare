from flask import Flask, request, Response
import xml.etree.ElementTree as ET
import time
from WXBizMsgCrypt import WXBizMsgCrypt

# 导入企业微信加解密库
app = Flask(__name__)

# ========== 配置信息（从企业微信后台获取） ==========
TOKEN = "pzlGMWJNQDjrxvvaY"  # 在回调配置页面随机生成
ENCODING_AES_KEY = "7vjAN2MqtjvpvTygunFePZF96Fv2zMLtOaRtGrQXshO"  # 43位密钥，在回调配置页面生成
CORP_ID = "wwbc97f0f0104738c3"  # 在"我的企业"页面查看

# 初始化加解密类
wxcpt = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)


@app.route('/wework/callback', methods=['GET', 'POST'])
def callback():
    # 获取URL参数
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    # ========== GET 请求：URL验证（配置回调时触发） ==========
    if request.method == 'GET':
        echostr = request.args.get('echostr')

        # 注意：echostr 中的空格需要替换为 +，否则解密失败
        if echostr:
            echostr = echostr.replace(' ', '+')

        # 调用 VerifyURL 验证并解密
        ret, sEchoStr = wxcpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
        if ret == 0:
            return sEchoStr
        else:
            # 验证失败，返回错误码
            return f"verify failed, error code: {ret}", 403

    # ========== POST 请求：接收并回复消息 ==========
    elif request.method == 'POST':
        # 获取加密的POST数据
        post_data = request.data

        # 调用 DecryptMsg 解密消息
        ret, sMsg = wxcpt.DecryptMsg(post_data, msg_signature, timestamp, nonce)

        if ret != 0:
            print(f"解密失败，错误码: {ret}")
            return "decrypt failed", 403

        try:
            # 解析解密后的XML
            root = ET.fromstring(sMsg)
            # 获取消息类型
            msg_type = root.find('MsgType')
            if msg_type is None:
                return "success"

            # ========== 新增：以普通文本形式输出接收到的消息 ==========
            # 处理文本消息
            if msg_type.text == 'text':
                # 获取发送者和内容
                from_user = root.find('FromUserName').text
                # 查找用户是否在数据库中 没有直接返回错误
                content = root.find('Content').text  # 这里收到的内容

                # 在这里处理你的业务逻辑
                # 例如：生成回复内容
                reply_content = f"hellow  小胜: {content}"

                # 如果需要回复消息
                reply_xml = build_reply_xml(from_user, reply_content)
                ret, sEncryptMsg = wxcpt.EncryptMsg(reply_xml, timestamp, nonce)

                if ret == 0:
                    return Response(sEncryptMsg, mimetype='application/xml')
                else:
                    return "encrypt failed", 500
            return "success"

        except Exception as e:
            print(f"处理消息出错: {e}")
            return "success"


def generate_reply(question):
    """根据用户问题生成回复内容"""
    question = question.strip()

    if "你好" in question or "hello" in question.lower():
        return "你好！我是企业微信助手，有什么可以帮你的？"
    elif "天气" in question:
        return "天气查询功能正在开发中，敬请期待~"
    elif "帮助" in question:
        return "发送消息即可与我对话。"
    elif "时间" in question:
        return f"当前时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        return f"收到：{question}"


def build_reply_xml(to_user, content):
    """构造文本回复的XML（明文）"""
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{CORP_ID}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8181, debug=True)
