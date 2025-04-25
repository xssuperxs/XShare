import asyncio
import pymongo
import json

mongoDBCli = pymongo.MongoClient("mongodb://dbroot:123456ttqqTTQQ@113.44.193.120:28018/")
db = mongoDBCli['ashare']

# 分析结果的集合
coll_analysis_Results = db['analysis_results']

# 用户的集合
coll_users = db['users']


async def read_full(reader):
    data = b''
    while True:
        packet = await reader.read(100)
        if not packet:
            break
        data += packet
    return data


def checkSN(sn: str):
    query = {'sn': sn}
    result = coll_users.find_one(query)
    if result:
        return True
    else:
        return False


def queryAnalysisResults():
    result = coll_analysis_Results.find_one(sort=[('analysis_date', -1)],
                                            projection={'type2': 1, 'type1': 1, '_id': 0, 'analysis_date': 1})
    if result:
        return json.dumps(result, default=str)
    return json.dumps({"error": "Data array is empty"})


# queryAnalysisResults()


async def handle_client(reader, writer):
    data = await reader.read(100)
    sn = data.decode()
    # addr = writer.get_extra_info('peername')
    if not checkSN(sn):
        write_results = "sn error !"
    else:
        write_results = queryAnalysisResults()

    writer.write(write_results.encode())

    await writer.drain()

    # print("Close the connection")
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 32135)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
