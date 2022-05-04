# 引入套件 flask
from flask import Flask, request, abort,jsonify,render_template
import random
import os
from flask_cors import CORS

from linebot import (
    LineBotApi, WebhookHandler
)
# 引入 linebot 異常處理
from linebot.exceptions import (
    InvalidSignatureError
)
# 引入 linebot 訊息元件
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
import time
import traceback
import json
import struct
import socket
import requests

"""plc UPDATE"""
PLC = []
M_status = []  # 狀態
SQL_Data = ""
CurrentTime = ""
check_status = 0
check_status2 = 0
check_no1 = 0  # 是否為第一筆
data = ""
parameter = []
def upd(data):
# with open('static/output.json', 'r') as f:
#     data = json.load(f)

    parameter = []

    PLC = []
    # M_status = [] #狀態
    # SQL_Data = ""
    # CurrentTime = ""
    # check_status = 0
    # check_status2 = 0
    # check_no1 = 0#是否為第一筆
    #
    # parameter = []
    """開啟json檔 將資料輸入列表中"""
    # with open('static/output.json', 'r') as f:
    #     data = json.load(f)
    # page = requests.get(url="https://lazyjimapp.herokuapp.com/FX5U_SQL")
    # data =  json.loads(page.text)
    """將IP資料從data中取出"""
    plcc = 0
    for ip in range(4):
    # print(ip)
    #        data['PLC{}'.format(ip)][0]['IP_address']
        if data['PLC{}'.format(ip)][0]['IP_address'] != "undefined":
            if(len(data['PLC{}'.format(ip)][0]['IP_address'].split(':')) > 1):
                cs = [(f"{data['PLC{}'.format(ip)][0]['IP_address'].split(':')[0]}"),int(data['PLC{}'.format(ip)][0]['IP_address'].split(':')[1])]
                PLC.append(cs)
                parameter.append({})#在字串中建立空dict
                plcc += 1
            else:
                cs = [(f"{data['PLC{}'.format(ip)][0]['IP_address'].split(':')[0]}"),1025]
                PLC.append(cs)
                parameter.append({})  # 在字串中建立空dict
                plcc += 1
            # print(data[f'PLC{(ip+1)}'][0]['IP_address'])
        # print(int(data[f'PLC{0}'][0]['single_num']))
        # print(struct.pack('h',99)[0])
        """依據PLC建立數量 更新SLMP通訊內容"""
        for i in range(len(PLC)):
            SLMP = [
                0x50, 0x00,  # Subheader (0,1)
                0x00,  # Request destination network No. (2)
                0xFF,  # Request destination station No. (3)
                0xFF, 0x03,  # Request destination module I/O No. (4,5)
                0x00,  # Request destination multidrop station No. (6)
                0x00, 0x00,  # Request data length (7,8)
                0x00, 0x00,  # Monitoring timer (9,10)
                0x03, 0x04,  # Command (11,12)
                0x00, 0x00,  # Subcommand (13,14)
                0x02,  # Word access points
                0x06,  # Double-word access points

                # Word
                # 0x00, 0x00, 0x00, 0x90,  # M0~M15
                # 0x30, 0x01, 0x00, 0xA8,  # D304(每分鐘數量)

                # Double Word
                # 0x24,0x03,0x00,0xA8,    #D804(紙片數量)
                # 0x54, 0x01, 0x00, 0xA8,  # D340(紙片數量)
                # 0x20, 0x00, 0x00, 0x9C,  # X40~X70
                # 0x7B, 0x00, 0x00, 0x90,  # M123~M154
                # 0x83, 0x03, 0x00, 0x90,  # M899~M930
                # 0xB4, 0x03, 0x00, 0x90,  # M948~M979
                # 0x28, 0x03, 0x00, 0xA8,  # D808(不合格數量)
            ]
            SLMP[15] = struct.pack('h',int(data[f'PLC{i}'][0]['single_num']))[0]
            SLMP[16] = struct.pack('h',int(data[f'PLC{i}'][0]['double_num']))[0]

            # Single 位址
            for m in range(SLMP[15]):
                if int(SLMP[15]) == 0: break
                word = data[f'PLC{i}'][0]['single_address'][m].split(':')[0]
                word_type =  data[f'PLC{i}'][0]['single_address'][m].split(':')[1]
                parameter[i].update({f"{word_type}{word}": ""})
                if word_type == 'D':
                    word_type = 168 #0xA8
                elif word_type == 'X':
                    word_type = 156  # 0x9C
                elif word_type == 'M':
                    word_type = 144  # 0x9C
                SLMP[17+(m*4):21+(m*4)] = struct.pack('h',int(word))+struct.pack('>h',int(word_type))


            # Double 位址
            for n in range(SLMP[16]):
                if int(SLMP[16]) == 0: break

                word = data[f'PLC{i}'][0]['double_address'][n].split(':')[0]#暫存器位置
                word_type = data[f'PLC{i}'][0]['double_address'][n].split(':')[1]#暫存器型別
                word_data_type = data[f'PLC{i}'][0]['double_address'][n].split(':')[2]#讀取型態(float或double)
                parameter[i].update({f"{word_type}{word}": [word_data_type,0]})
                # print(word)
                if word_type == 'D':
                    word_type = 168  # 0xA8
                elif word_type == 'X':
                    word_type = 156  # 0x9C
                elif word_type == 'M':
                    word_type = 144  # 0x9C
                SLMP[17+SLMP[15]*4 + (n * 4):21+17+SLMP[15]*4 + (n * 4)] = struct.pack('h', int(word)) + struct.pack('>h', int(word_type))

            SLMP[7:9] = struct.pack('H', len(SLMP[9:]))  # Request data length
            PLC[i].append(SLMP)
    return PLC,parameter



def ReadPLC(i,PLC,parameter):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP
    # sock = socket.socket(socket.AF_INET, SOCK_STREAM)      #UDP
    sock.settimeout(2.5)
    TT = ""
    try:
        sock.connect(tuple(PLC[i][0:2]))
        sock.sendall(bytes(PLC[i][2]))  # Send TO PLC
        data = sock.recv(1024)[11:]  # Receive FROM PLC
        sock.close()

        db_begin = PLC[i][2][15]*2
        f = 0
        dbcount = 0
        if data != "":
            for li in parameter[i]:
                # if f < PLC[i][2][15]:
                #     print(f)
                # elif f < PLC[i][2][16]+PLC[i][2][15]:
                #     print("DB: ",f)
                if f < PLC[i][2][15]:
                    parameter[i][li] = struct.unpack('H', data[0+(f*2):2+(f*2)])[0]
                    # print(f)
                elif f < PLC[i][2][16] + PLC[i][2][15]:
                    # print("起 : ",db_begin+(dbcount*4))
                    # print("訖 : ",(db_begin+4)+(dbcount*4))
                    if parameter[i][li][0] == 'f':
                        dbw = round(struct.unpack('f', data[db_begin+(dbcount*4):(db_begin+4)+(dbcount*4)])[0],2)
                    else:
                        dbw = struct.unpack('I', data[db_begin+(dbcount*4):(db_begin+4)+(dbcount*4)])[0]
                        # dbw = struct.unpack('I', data[10:14])[0]

                    parameter[i][li][1] = dbw
                    dbcount+=1
                f+=1

    except:
        print(traceback.format_exc())



""""""


tpe = {
    "id": 0,
    "city_name": "台北1",
    "country_name": "台灣",
    "is_capital": True,
    "location": {
        "longitude": 121.569649,
        "latitude": 25.036786
    }
}
nyc = {
    "id": 1,
    "city_name": "紐約",
    "country_name": "美國",
    "is_capital": False,
    "location": {
        "longitude": -74.004369,
        "latitude": 40.71040522
    }
}
ldn = {
    "id": 2,
    "city_name": "倫敦",
    "country_name": "英國",
    "is_capital": True,
    "location": {
        "longitude": -0.114089,
        "latitude": 51.507497
    }
}
cities = [tpe, nyc, ldn]

app = Flask(__name__)
# set LINE_CHANNEL_ACCESS_TOKEN=uTuivMhwJ+Ga5pe3yAIbdGqAXwnKAEaJwFdu4j1wLW1ukP/Y7KyoYRC/q5h20h4nsemUEptljxr0ePlFnw+jLwtRqrh+c8JJJ3Gnvu0/HNf9MACxfgcGWdZxSBF+vUqYZsmlaHcO0Phm1k1rpw/skAdB04t89/1O/w1cDnyilFU=
# set LINE_CHANNEL_SECRET=c85057d464f08fae854df3be3d39d6c4
# LINE_CHANNEL_SECRET 和 LINE_CHANNEL_ACCESS_TOKEN 類似聊天機器人的密碼，記得不要放到 repl.it 或是和他人分享。請替換成你的憑證內容
# LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('uTuivMhwJ+Ga5pe3yAIbdGqAXwnKAEaJwFdu4j1wLW1ukP/Y7KyoYRC/q5h20h4nsemUEptljxr0ePlFnw+jLwtRqrh+c8JJJ3Gnvu0/HNf9MACxfgcGWdZxSBF+vUqYZsmlaHcO0Phm1k1rpw/skAdB04t89/1O/w1cDnyilFU=')
# LINE_CHANNEL_SECRET = os.environ.get('c85057d464f08fae854df3be3d39d6c4')
CORS(app)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False


os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "uTuivMhwJ+Ga5pe3yAIbdGqAXwnKAEaJwFdu4j1wLW1ukP/Y7KyoYRC/q5h20h4nsemUEptljxr0ePlFnw+jLwtRqrh+c8JJJ3Gnvu0/HNf9MACxfgcGWdZxSBF+vUqYZsmlaHcO0Phm1k1rpw/skAdB04t89/1O/w1cDnyilFU="
os.environ["LINE_CHANNEL_SECRET"] = "c85057d464f08fae854df3be3d39d6c4"

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
# print(LINE_CHANNEL_ACCESS_TOKEN)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
# 本機端 ngrok 測試用

# line_bot_api = LineBotApi('uTuivMhwJ+Ga5pe3yAIbdGqAXwnKAEaJwFdu4j1wLW1ukP/Y7KyoYRC/q5h20h4nsemUEptljxr0ePlFnw+jLwtRqrh+c8JJJ3Gnvu0/HNf9MACxfgcGWdZxSBF+vUqYZsmlaHcO0Phm1k1rpw/skAdB04t89/1O/w1cDnyilFU=')
# handler = WebhookHandler('c85057d464f08fae854df3be3d39d6c4')

user_command_dict = {}
good_luck_list = ['2330 台積電', '2317 鴻海', '2308 台達電', '2454 聯發科']
stock_price_dict = {
    '2330': 210,
    '2317': 90,
    '2308': 150,
    '2454': 300
}
# 此為歡迎畫面處理函式，當網址後面是 / 時由它處理
@app.route("/", methods=['GET'])
def hello():
    return f'''
    <html>
    <head>
    <title>This is my website</title>
    </head>
    <body onload="window.location.href='Electrop_Monitor'">
    </body>
    </html>'''

@app.route("/list_all",)
def listall():
    return render_template('post.html')

@app.route("/demo_script",)
def demo_script():
    return render_template('ToolBox_Board.html')

@app.route("/3D_Works",)
def Works_3D():
    return render_template('3D_Works.html')

@app.route("/CPS_Demo",)
def CPS_Demo():
    return render_template('CPS_Demo.html')

@app.route("/Electrop_Monitor",)
def Electrop_Monitor():
    return render_template('Electrop_Monitor.html')

# 此為 Webhook callback endpoint
@app.route("/callback", methods=['POST'])
def callback():
    # 取得網路請求的標頭 X-Line-Signature 內容，確認請求是從 LINE Server 送來的
    signature = request.headers['X-Line-Signature']

    # 將請求內容取出
    body = request.get_data(as_text=True)

    # handle webhook body（轉送給負責處理的 handler，ex. handle_message）
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# decorator 負責判斷 event 為 MessageEvent 實例，event.message 為 TextMessage 實例。所以此為處理 TextMessage 的 handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 決定要回傳什麼 Component 到 Channel，這邊使用 TextSendMessage
    # event.message.text 為使用者的輸入，把它原封不動回傳回去
    # if event.message.text == "":
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     TextSendMessage(text=event.message.text))
    # if time.strftime("%Y-%m-%d %H:%M:%S") == "10:55:00":
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text='測試成功'))
    user_message = event.message.text
    reply_message = TextSendMessage(text='請輸入正確指令')
    user_id = event.source.user_id

    # 根據使用者 ID 暫存指令
    user_command = user_command_dict.get(user_id)

    # 判斷使用者輸入為 @查詢股價 且 之前輸入的指令非 @查詢股價
    if user_message == '@查詢股價' and user_command != '@查詢股價':
        reply_message = TextSendMessage(text='請問你要查詢的股票是？')
        # 儲存使用者輸入了 @查詢股價 指令
        user_command_dict[user_id] = '@查詢股價'
    elif user_message == '@報明牌':
        # 隨機從 good_luck_list 中取出一個股票代號
        random_stock = random.choice(good_luck_list)
        reply_message = TextSendMessage(text=f'報明牌：{random_stock}')
        # 將暫存指令清空
        user_command_dict[user_id] = None
    # 若上一個指令為 @查詢股價
    elif user_message == '@勞贖?':
        # 隨機從 good_luck_list 中取出一個股票代號
        random_stock = random.choice(good_luck_list)
        reply_message = TextSendMessage(text=f'讓我們敬也不是蠢~蛋的你')
        # 將暫存指令清空
        user_command_dict[user_id] = None
    # 若上一個指令為 @查詢股價
    elif user_message == '@報時':
        # 隨機從 good_luck_list 中取出一個股票代號
        random_stock = random.choice(good_luck_list)
        reply_message = TextSendMessage(text=f'現在時間：{time.strftime("%Y-%m-%d %H:%M:%S")}')
        # 將暫存指令清空
        user_command_dict[user_id] = None
    # 若上一個指令為 @查詢股價
    elif user_command == '@查詢股價':
        # 若使用者上一指令為 @查詢股價 則取出使用者輸入代號的股票價格資訊
        stock_price = stock_price_dict[user_message]
        if stock_price:
            reply_message = TextSendMessage(text=f'成交價：{stock_price}')
            # 清除指令暫存
            user_command_dict[user_id] = None

    # 回傳訊息給使用者
    line_bot_api.reply_message(
        event.reply_token,
        reply_message)
@app.route('/cities/all', methods=['GET'])
def cities_all():
    return jsonify(cities)
# port = int(os.environ.get('PORT', 8000))
# reply_message = TextSendMessage(text=f'現在時間：{time.strftime("%Y-%m-%d %H:%M:%S")}')
# __name__ 為內建變數，若程式不是被當作模組引入則為 __main__

@app.route('/PLC_setting', methods=['GET'])
def PlC_setting():
    # print(socket.gethostbyname(socket.gethostname()))
    # cn = pymssql.connect(server='127.0.0.1', user='sa', password='pass', database='Image_test', charset='big5')
    # cursor = cn.cursor(as_dict=True)
    # cursor.execute("SELECT * FROM MES005")
    # data_list = cursor.fetchall()
    # for data in data_list:
    #     cs = {"s":data["F14"]}
    # return f"<h1>{time.strftime('%Y/%m/%d %H:%M:%S')}</h1>"

    return render_template(f'POST_sc.html')


@app.route('/FX5U_SQL', methods=['GET'])
def FX5U_GET():
    try:
        with open('static/output.json','r') as f:
            PLC_data_list = []
            data = json.load(f)
            PLC_data_list.append(data)
        return jsonify(PLC_data_list)
        # return render_template(f'output.json')
    except:
        lsi = traceback.format_exc()
        return f"{lsi}"

@app.route('/FX5U_SQL', methods=['POST'])
def FX5U_POST():
    data_res = request.get_json()
    print(data_res)
    with open("static/output.json", "w") as f:
        json.dump(data_res, f, indent=4)  # indent : 指定縮排長度

    return  jsonify(data_res)


@app.route('/PLC_RealTime', methods=['GET'])
def psa():
    # cn = pymssql.connect(server='127.0.0.1', user='sa', password='pass', database='Image_test', charset='big5')
    # cursor = cn.cursor(as_dict=True)
    # cursor.execute("SELECT * FROM MES005")
    # data_list = cursor.fetchall()
    # for data in data_list:
    #     cs = {"s":data["F14"]}
    # return f"<h1>{time.strftime('%Y/%m/%d %H:%M:%S')}</h1>"
    # return render_template('Electrop_Monitor.html')
    # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # s.connect(('8.8.8.8', 80))
    # ip = s.getsockname()[0]
    return render_template('Show_RealTime.html', title="127.0.0.1")
    # return render_template('Show_RealTime.html')

@app.route('/RealTime', methods=['GET'])
def RealTime():
    try:
        # PLC = []
        # with open('static/output.json', 'r') as f:
        #     data = json.load(f)
        page = requests.get(url="https://lazyjimapp.herokuapp.com/FX5U_SQL")
        data = json.loads(page.text)[0]
        print(data['PLC{}'.format(1)][0]['IP_address'])
        # print(data['PLC{}'.format(ip)][0]['IP_address'])
        PLC,parameter = upd(data)
        print(tuple(PLC[0][0:2]))

        for k in range(len(PLC)):
            print(k)
            ReadPLC(k,PLC,parameter)
        return jsonify(parameter)
        # return jsonify(data)

    except:
        lsi = traceback.format_exc()
        return f"{lsi}<br/>"

if __name__ == "__main__":
    # 運行 Flask server

    app.run()