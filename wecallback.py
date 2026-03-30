from flask import Flask, request, Response
import xml.etree.ElementTree as ET
import time
from WXBizMsgCrypt import WXBizMsgCrypt

import requests
import os
import tempfile

# 导入企业微信加解密库
app = Flask(__name__)

# ========== 配置信息（从企业微信后台获取） ==========
TOKEN = "pzlGMWJNQDjrxvvaY"  # 在回调配置页面随机生成
ENCODING_AES_KEY = "7vjAN2MqtjvpvTygunFePZF96Fv2zMLtOaRtGrQXshO"  # 43位密钥，在回调配置页面生成
CORP_ID = "wwbc97f0f0104738c3"  # 在"我的企业"页面查看

SECRET = "KD8cus4SWIlvBuPboLJd_tD-bBnaTuPKruebNTa5Ew0"  # 你的应用Secret
AGENT_ID = 1000003  # 你的应用ID

# 初始化加解密类
wxcpt = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)


def send_wechat_message(toUser, content, msgType='text'):
    """
    给企业微信成员发送消息（支持文本消息和文本文件）
    Args:
        toUser: 接收消息的成员账号（如 "LiuKeSheng"）
        content: 消息内容（文本消息时是字符串，文件消息时是文件路径或文本内容）
        msgType: 消息类型
            - 'text': 发送文本消息（默认）
            - 'file': 发送文件（需要提供文件路径）
            - 'text_as_file': 将文本内容作为文件发送
    Returns:
        dict: 发送结果
    """
    # 获取 access_token
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={SECRET}"
    token_res = requests.get(token_url).json()

    if token_res.get('errcode', 0) != 0:
        return {"error": f"获取token失败: {token_res}"}

    access_token = token_res.get('access_token')

    # 如果是文件消息或文本作为文件
    if msgType == 'file':
        try:
            # 直接发送已存在的文件
            if not os.path.exists(content):
                return {"error": f"文件不存在: {content}"}
            file_path = content
            # 上传文件
            upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=file"

            with open(file_path, 'rb') as f:
                files = {'media': f}
                upload_res = requests.post(upload_url, files=files)

            upload_result = upload_res.json()

            if upload_result.get('errcode', 0) != 0:
                return {"error": f"上传文件失败: {upload_result}"}

            media_id = upload_result.get('media_id')

            # 发送文件消息
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

            data = {
                "touser": toUser,
                "msgtype": "file",
                "agentid": AGENT_ID,
                "file": {
                    "media_id": media_id
                },
                "safe": 0
            }

            response = requests.post(send_url, json=data)
            return response.json()
        finally:
            pass
    # 发送文本消息
    if msgType == 'text':
        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

        data = {
            "touser": toUser,
            "msgtype": "text",
            "agentid": AGENT_ID,
            "text": {
                "content": content
            },
            "safe": 0
        }

        response = requests.post(send_url, json=data)
        return response.json()


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
                res = send_wechat_message(from_user, "1234", 'text')
                print(res)
        except Exception as e:
            print(f"处理消息出错: {e}")
            return "success"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8181, debug=True)
