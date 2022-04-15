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
if __name__ == "__main__":
    # 運行 Flask server

    app.run()