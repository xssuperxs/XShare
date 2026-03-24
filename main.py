
import requests
import os
import tempfile

CORP_ID = "wwbc97f0f0104738c3"  # 你的企业ID
SECRET = "KD8cus4SWIlvBuPboLJd_tD-bBnaTuPKruebNTa5Ew0"  # 你的应用Secret
AGENT_ID = 1000003  # 你的应用ID


def send_wechat_message(toUser, content, msgType='text', filename=None):
    """
    给企业微信成员发送消息（支持文本消息和文本文件）
    Args:
        toUser: 接收消息的成员账号（如 "LiuKeSheng"）
        content: 消息内容（文本消息时是字符串，文件消息时是文件路径或文本内容）
        msgType: 消息类型
            - 'text': 发送文本消息（默认）
            - 'file': 发送文件（需要提供文件路径）
            - 'text_as_file': 将文本内容作为文件发送
        filename: 当 msgType='text_as_file' 时，指定文件名（可选）

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
    if msgType == 'file' or msgType == 'text_as_file':
        file_path = None
        temp_file = None
        try:
            # 处理文件路径
            if msgType == 'file':
                # 直接发送已存在的文件
                if not os.path.exists(content):
                    return {"error": f"文件不存在: {content}"}
                file_path = content

            elif msgType == 'text_as_file':
                # 将文本内容写入临时文件
                temp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False)
                temp_file.write(content)
                temp_file.close()
                file_path = temp_file.name

                # 如果指定了文件名，重命名临时文件
                if filename:
                    new_path = os.path.join(os.path.dirname(file_path), filename)
                    os.rename(file_path, new_path)
                    file_path = new_path

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
            # 清理临时文件
            if temp_file and os.path.exists(file_path):
                os.unlink(file_path)

    # 发送文本消息
    else:
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


# ============= 使用示例 =============

if __name__ == "__main__":
    # 配置信息
    # 1. 发送普通文本消息
    result1 = send_wechat_message("LiuKeSheng", "您好，小胜 加油 你能行的")
    print("文本消息结果:", result1)

    # 2. 发送已存在的文件
    result2 = send_wechat_message("LiuKeSheng", "D:\\Users\\Administrator\\Desktop\\无标题.txt", msgType='file'
                                  )
    print("文件消息结果:", result2)

    # 3. 将文本内容作为文件发送（最常用）
    # report_content = ""
    # 报告标题：数据统计报告
    # "
