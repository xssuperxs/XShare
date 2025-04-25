import asyncio
import json
import os

# file_path = os.getcwd() + '\\stock.txt'
file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"


async def tcp_client(message):
    async def read_full(arg_reader):
        data = b''
        while True:
            packet = await arg_reader.read(100)
            if not packet:
                break
            data += packet
        return data

    reader, writer = await asyncio.open_connection('113.44.193.120', 32135)

    # print(f'Send: {message}')
    writer.write(message.encode())
    await writer.drain()

    full_data = await read_full(reader)
    receivedStr = full_data.decode()
    if 'sn' in receivedStr:
        print(receivedStr)
        return

    json_data = json.loads(full_data)
    # dt = datetime.strptime(json_data['analysis_date'], '%Y-%m-%d %H:%M:%S')
    print("分析时间:", json_data['analysis_date'])
    print("破低翻:", json_data['type1'])
    print("创新高:", json_data['type2'])

    # 打开文件以写入模式 可以不加type2 看个人需要
    # stockResults = json_data['type1']
    stockResults = json_data['type1'] + json_data['type2']
    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in stockResults:
            file.write(f'{item}\n')

    writer.close()
    await writer.wait_closed()


# SN
asyncio.run(tcp_client('fe52d22a86854eac9aabe1f27672eabd'))
