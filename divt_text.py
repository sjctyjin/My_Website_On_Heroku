import time
import socket
import struct
import pymssql
import traceback
import datetime
import json

PLC = []
order = 'SBC-220418001'#工單
M_status = [] #狀態
Inspect = ""#靜音檢測條碼
Generate_code = ""#生成第一站條碼
SQL_Data = ""
CurrentTime = ""
check_status = 0
check_status2 = 0
check_no1 = 0#是否為第一筆
# parameter = {
#     "T07":""
#     ,"T08":""
#     ,"T09":""
#     ,"T10":""
#     ,"T11":""
#     ,"T13":""
#     ,"T15":""
#     ,"T17":""
#     ,"T18":""
#     ,"T19":""
#     ,"T21":""
#     ,"T23":""
#     ,"T25":""
#     ,"T27":""
#     ,"T29":""
#     ,"T33":""}

parameter = []

"""開啟json檔 將資料輸入列表中"""
with open('output.json', 'r') as f:
    data = json.load(f)
print(data)
"""將IP資料從data中取出"""
plcc = 0
for ip in range(4):
    # print(ip)
    if data[f'PLC{ip}'][0]['IP_address'] != 'undefined':
        print(data[f'PLC{ip}'][0]['IP_address'])
        if (len(data[f'PLC{ip}'][0]['IP_address'].split(':')) > 1):
            cs = [(f"{data[f'PLC{ip}'][0]['IP_address'].split(':')[0]}"),
                  int(data[f'PLC{ip}'][0]['IP_address'].split(':')[1])]
            PLC.append(cs)
            parameter.append({})  # 在字串中建立空dict
            plcc += 1
            print('here')
        else:
            cs = [(f"{data[f'PLC{ip}'][0]['IP_address'].split(':')[0]}"), 1025]
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





print(parameter)
def ReadSQL():
    global  order
    global  M_status
    global  parameter
    global  Inspect
    global  SQL_Data
    global  Generate_code
    global  check_status
    global  check_no1
    SQL = f"SELECT * FROM MES023 ORDER BY T02 ASC"

    try:
        cn = ConnectSQL()
        cursor = cn.cursor(as_dict=True)
        cursor.execute(SQL)
        data = cursor.fetchall()
        cn.close()
        """把MES023每一台尚未完成組裝的產品列出，並給定狀態"""

        if data != []:
            check_no1 = 1  # 是否為第一筆
            if M_status[1]:
                check_status = 0
            if M_status[3]:
                if (check_status == 0):
                    check_status = 1
                    for datalist in data:
                        # print(datalist['T01'].split('-')[0])
                        # print(datalist['T01'].split('-')[0] + '-' + str(int(datalist['T01'].split('-')[1])+1201))
                                if datalist['T34'] != None:
                                    print('Ended')
                                elif datalist['T03'] == None:
                                    SQL_Data +=f"UPDATE MES023 SET T03 = '{datalist['T02']}-M100',T04 = '{datalist['T02']}-U100',T05='{datalist['T02']}-D100' WHERE T02 = '{datalist['T02']}';"
                                    Generate_code = datalist['T02'].split('-')[0] + '-' + str(int(datalist['T02'].split('-')[1])+1)
                                    SQL_Data += f"INSERT INTO MES023 (T01,T02) values ('{order}','{Generate_code}');"
                                    print("新標籤號 : ",Generate_code)
                                elif datalist['T06'] == None:
                                    SQL_Data +=f"UPDATE MES023 SET T06 = 'OK' WHERE T02 = '{datalist['T02']}';"
                                elif datalist['T07'] == None:
                                    SQL_Data += f"UPDATE MES023 SET T07 = '{parameter['T07']}',T08='{parameter['T08']}' WHERE T02 = '{datalist['T02']}';"
                                    Inspect = datalist['T02']
                                elif datalist['T09'] == None:
                                    SQL_Data += f"""UPDATE MES023 SET
                                    T09 = '{parameter['T09']}',
                                    T12 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T13 = '{parameter['T13']}',
                                    T14 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T15 = '{parameter['T15']}',
                                    T16 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T17 = '{parameter['T17']}',
                                    T19 = '{parameter['T19']}',
                                    T20 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T21 = '{parameter['T21']}',
                                    T22 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T23 = '{parameter['T23']}',
                                    T24 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T25 = '{parameter['T25']}',
                                    T26 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T27 = '{parameter['T27']}',
                                    T28 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T29 = '{parameter['T29']}',
                                    T30 = '{time.strftime('%Y-%m-%d %H:%M:%S')}',
                                    T31 = '{datalist['T02']}-H100'
                                    WHERE T02 = '{datalist['T02']}';
                                    UPDATE MES005 SET F11 = '{datalist['T02']}-H100';"""
                                elif datalist['T32'] == None:
                                    SQL_Data += f"""UPDATE MES023 SET
                                    T32 = 'OK',
                                    T33 = '{parameter['T33']}',
                                    T34 = '{time.strftime('%Y-%m-%d %H:%M:%S')}'
                                    WHERE T02= '{datalist['T02']}';"""
        else:
            cn = ConnectSQL()
            cursor = cn.cursor(as_dict=True)
            cursor.execute(f"INSERT MES023 (T01,T02) values ('{order}','AB-2204001')")
            cn.commit()
            cn.close()



    except:
        print(traceback.format_exc())
moveing = 0
def ReadPLC(i):
    global PLC
    global order
    global Inspect
    global M_status
    global parameter
    global SQL_Data
    global Generate_code
    global  moveing
    global  check_status2
    global  check_no1
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP
    # sock = socket.socket(socket.AF_INET, SOCK_STREAM)      #UDP
    sock.settimeout(2.5)
    TT = ""
    try:
        print(tuple(PLC[i][0:2]))
        sock.connect(tuple(PLC[i][0:2]))
        sock.sendall(bytes(PLC[i][2]))  # Send TO PLC
        data = sock.recv(1024)[11:]  # Receive FROM PLC
        sock.close()

        # print(struct.unpack('H', data[0:2])[0])
        # print(data[0:PLC[i][2][15]]*2)
        # print("陣列 : ",parameter[i])
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
            print(parameter[i])

        # for z in range(PLC[i][2][15]):
        #     print(struct.unpack('H', data[0+(i*2):2+(i*2)])[0])

        # for cak in parameter[i]:
        #     print(cak)
        #     print(parameter[i][cak])

        # TT = struct.unpack('H', data[0:2])[0]#D495
        # reciprocal = struct.unpack('H', data[4:6])[0]#倒數 D497
        # K4M0 = struct.unpack('H', data[6:8])[0]#D498
        # M_status = [K4M0 >> i & 0x1 for i in range(16)]  # D498.0~D498.16
        # tension = struct.unpack('I', data[10:14])[0]#D350
        # Torque = struct.unpack('I', data[14:18])[0]#D352
        # degree = struct.unpack('f', data[22:26])[0]#D356
        # db_voic = struct.unpack('I', data[26:30])[0]#D358
        # vibration = struct.unpack('f', data[30:34])[0]#D360
        # speed = struct.unpack('f', data[34:38])[0]#D362
        # press = struct.unpack('f', data[42:46])[0]#D366
        # elec = struct.unpack('f', data[46:50])[0]#D368
        # ground = struct.unpack('I', data[50:54])[0]#D370
        # insulation = struct.unpack('f', data[54:58])[0]#D372
        # intelligent = struct.unpack('I', data[58:62])[0]#D374
        # kilogram = struct.unpack('f', data[18:22])[0]#D354
        #
        # print(M_status)
        # print("倒數 : ",round(reciprocal, 2))
        # print("TT : ",TT)
        # print("張力 : ",round(tension,2))
        # print("扭力 : ",round(Torque,2))
        # print("角度 : ",round(degree,2))
        # print("分貝 : ",round(db_voic,2))
        # print("震動 : ",round(vibration,2))
        # print("速度 : ",round(speed,2))
        # print("耐壓 : ",round(press,2))
        # print("電流 : ",round(elec,2))
        # print("接地 : ",round(ground,2))
        # print("絕緣 : ",round(insulation,2))
        # print("智能 : ",round(intelligent,2))
        # print("重量 : ",round(kilogram,2))



        # if M_status[1]:
        #     check_status = 0
        #     check_status2 = 0
        #     parameter['T07'] = round(tension,2)
        #     parameter['T08'] = round(Torque,2)
        #     parameter['T09'] = round(degree,2)
        #     parameter['T13'] = round(db_voic,2)
        #     parameter['T15'] = round(vibration,2)
        #     if speed > 0.5 and speed < 1.5:
        #         parameter['T17'] = round(speed,2)
        #     parameter['T19'] = round(speed,2)
        #     parameter['T21'] = round(press,2)
        #     parameter['T23'] = round(elec,2)
        #     parameter['T25'] = round(ground,2)
        #     parameter['T27'] = round(insulation,2)
        #     parameter['T29'] = round(intelligent,2)
        #     parameter['T33'] = round(kilogram,2)
        #     SQL_Data += f"""
        #     UPDATE MES005 set F05 = 'G',F06 = {reciprocal},F09 = {speed};
        #     UPDATE MES005 set F04 = {degree} where F01 = 'T540C_Degree';
        #     UPDATE MES005 set F04 = {db_voic} where F01 = 'T540C_DB';
        #     UPDATE MES005 set F04 = {vibration} where F01 = 'T540C_Vibration';
        #     UPDATE MES005 set F04 = {speed} where F01 = 'T540C_Speed';
        #     UPDATE MES005 set F04 = {press} where F01 = 'T540C_Press';
        #     UPDATE MES005 set F04 = {elec} where F01 = 'T540C_Elec';
        #     UPDATE MES005 set F04 = {ground} where F01 = 'T540C_Ground';
        #     UPDATE MES005 set F04 = {insulation} where F01 = 'T540C_Insulation';
        #     UPDATE MES005 set F04 = {intelligent} where F01 = 'T540C_intelligent';
        #     """
        #     moveing = 0
        # if M_status[0]:
        #     SQL_Data += f"UPDATE MES005 set F05 = 'Y';"
        #     print('產線停止')
        #     moveing = 0
        # if M_status[2]:
        #     SQL_Data += f"UPDATE MES005 set F05 = 'R';"
        #     print('產線異常暫停')
        #     moveing = 0
        # if M_status[3]:
        #     print(check_status2)
        #     if(check_status2 == 0):
        #         check_status2 = 1
        #         SQL_Data += f"""UPDATE MES005 set F02 = '{Inspect}',F05 = 'M';"""
        #     moveing += 1
        #     print('產線移動中',moveing)

    except:
        print(traceback.format_exc())
    # finally:
        # SQL_Data += f"UPDATE MES005 set F07 = '{TT}';"
        # print('finally')
def WriteSQL():
    global SQL_Data

    # for s in SQL_Data.split(";"):
    #     print(s)

    try:
        cn = ConnectSQL()
        cn.cursor().execute(SQL_Data)
        cn.commit()
        cn.close()
    except:
        print(traceback.format_exc())
    finally:
        SQL_Data = ""
def ConnectSQL():
    try:
        return pymssql.connect(server='127.0.0.1',user='sa',password='pass',database='MinYaoMES',timeout=2,login_timeout=2)
    except:
        print(traceback.format_exc())
def Now():
    return time.strftime('%Y-%m-%d %H:%M:%S')
def Main():
    global CurrentTime

    while True:


        if CurrentTime != Now():
            CurrentTime = Now()
            ReadPLC(0)
            # ReadSQL()
            # WriteSQL()

            time.sleep(0.5)

#
if __name__ == "__main__":
    Main()