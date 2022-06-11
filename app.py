import socket
import threading
from time import sleep, perf_counter
from threading import Thread 
import queue
import binascii
import random
import time

#variaveis globais, de token, controle do token, retransmissao, timer, tempo de sleep
#e tempo minimo de circulacao do token
Token = False
Control = False
Retransmits = 0
tokenTime = time.time()
sleepTime = 0

#chance de gerar erro e chance de perder token/gerar um aleatoriamente
nakChance = 30
tokChance = 10

#funcao de leitura do arquivo de configuracao
def readFile( name ):
    lineCount = 1
    with open(name, 'r') as file:
        for lin in file:
            print(lineCount, end=': ')
            print(lin.rstrip('\n'))
            if lineCount == 1:
                IP_PORTA = lin.rstrip('\n')
                IP = lin.rstrip('\n').split(':')[0]
                PORTA = lin.rstrip('\n').split(':')[1]              
            if lineCount == 2:
                NAME = lin.rstrip('\n')
            if lineCount == 3:
                TIME_TOKEN = lin.rstrip('\n')
                TIME_TOKEN = int(TIME_TOKEN)
            if lineCount == 4:
                TOKEN = lin.rstrip('\n')
            lineCount = lineCount + 1
    return IP_PORTA, NAME, TIME_TOKEN, TOKEN, IP, PORTA

IP_PORTA, MY_NAME, TIME_TOKEN, START_TOKEN, IP, PORTA = readFile('arq.txt')

sleepTime = TIME_TOKEN
#quantidade de maquinas na rede a mais que a atual
qtdMachines = 1
minimumTime = sleepTime * qtdMachines
timeout = 20
    
#socket de envio de mensagens
send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SENDTO = (IP, int(PORTA))

#socket de recebimento de mensagens tamanho max -> 10
MYIP = ''
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
RECEIVER = (MYIP, int(PORTA))
udp.bind(RECEIVER)
q = queue.Queue(10)

print("Tempo minimo para receber o token:", minimumTime)

#funcao que registra as entradas do usuario
def getMessageConsole():
    global q
    while True:
        print('Digite o apelido da maquina destino:')
        dest = input()
        print('Digite a mensagem:')
        msg = input()
        crc = binascii.crc32(bytes(msg, "utf-8"))
        msg = "2222;maquinanaoexiste:"+MY_NAME+":"+dest+":"+str(crc)+":"+msg
        try:
            q.put_nowait(msg)
        except:
            print('Fila cheia D:')
        
#envio de msg
def sendMsg():
    global Token
    global Retransmits
    global tokenTime
    #2222;maquinanaoexiste:Joao:Maria:19385749:Oi Pessoas!
    #1111
    sleep(sleepTime)
    if q.qsize() == 0:
        print("Nenhuma mensagem na fila, vou enviar o Token adiante")
        Token = False
        if(random.randint(1,100) > tokChance):
            send.sendto(bytes("1111", "utf8"), SENDTO)   
        else:
            print("Nao enviei o token!!!")
        tokenTime = time.time()
    elif Token:
        print("Vou enviar uma mensagem")
        #mensagem de aviso se é retransmissao
        if Retransmits>0:
            print("Será uma retransmissao!!!")
        #calculo para ver se envia msg com erro
        error = random.randint(1, 100)
        #chance de erro
        if error<nakChance:
            nextMsg = q.queue[0]
            headers = nextMsg.split(';', 1)
            infoHeader = headers[1].split(':', 4)
            nextMsgHeaderCrc = infoHeader[3]
            insertedError = int(nextMsgHeaderCrc) + 1
            nextMsg = q.queue[0].replace(nextMsgHeaderCrc, str(insertedError), 1)
            send.sendto(bytes(nextMsg, "utf8"), SENDTO)
        else:
            send.sendto(bytes(q.queue[0], "utf8"), SENDTO)

def timing():
    global Token
    global tokenTime
    while True:
        diff =  time.time() - tokenTime
        if (diff > timeout and Token == False):
            print("Timeout do token, reenviando novo token")
            tokenTime = time.time()
            send.sendto(bytes("1111", "utf8"), SENDTO)


def receiveMsg():
    global Token
    global Retransmits
    global q, tokenTime, minimumTime
    while True:
        print("Vou receber um pacote")
        packet, client = udp.recvfrom(1024)
        receivedPacket = str(packet, "utf-8").split(';', 1)
        content = receivedPacket[0].rstrip('\x00')
        if content == '2222':
            print("Recebi uma mensagem!")
            msgHeader = receivedPacket[1].split(':', 4).rstrip('\x00')
            ack = msgHeader[0]
            origin = msgHeader[1]
            destination = msgHeader[2]
            crc = msgHeader[3]
            recvMsg = msgHeader[4]
            ######################################################################se eu for a origem
            if origin == MY_NAME and destination != "TODOS":
                if ack == "maquinanaoexiste" or ack == "ACK":
                    #"retiro da fila" a mensagem, ou seja nao repasso nao faço nada com ela
                    if ack == "ACK":
                        #mensagem para termos controle de quando temos um ACK e de qual pacote é
                        print("ACK: (" + str(packet, "utf-8") + ")")
                        q.get()
                    if ack == "maquinanaoexiste":
                        #mensagem para termos controle de quando temos um maquinanaoexiste e
                        #de qual pacote é
                        print("maquinanaoexiste: (" + str(packet, "utf-8") + ")")
                        q.get()
                    #passo o token pra prox maquina
                    Token = False
                    tokenTime = time.time()
                    if(random.randint(1,100) > tokChance):
                        send.sendto(bytes("1111", "utf8"), SENDTO)   
                    else:
                        print("Nao enviei o token!!!")                 
                    #caso um pacote com NAK tenha retornado com ACK ou maquinanaoexiste
                    #reestabeleco que posso ter retransmissao p o prox da fila
                    Retransmits = 0                    
                if ack == "NAK" and Retransmits<1:
                    #se for nak e nao tiver retransmitido
                    print("NAK: (" + str(packet, "utf-8") + ")")
                    #passo o token adiante
                    Token = False                    
                    tokenTime = time.time()
                    if(random.randint(1,100) > tokChance):
                        send.sendto(bytes("1111", "utf8"), SENDTO)
                    else:
                        print("Nao enviei o token!!!")
                    #inibo que haja mais de uma retransmissao
                    Retransmits = 1
                elif ack == "NAK" and Retransmits>0:
                    #se for nak e já tiver retransmitido
                    print("NAK and already Retransmitted: ("+ str(packet, "utf-8") + ")")
                    #reestabeleco que pode haver retransmissao para proximo pacotes
                    Retransmits = 0
                    q.get()
            #########################################################################################
            ######################################################################se eu for o destino
            if destination == MY_NAME:
                #se eu for o destino
                #verificar o crc para o recalculo / NAK se não passar
                if binascii.crc32(bytes(recvMsg, "utf-8")) != int(crc):
                    #caso a igualdade de crc de diferente poem NAK
                    ack = "NAK"
                    print("Encontrei um erro na mensagem! Coloquei NAK")
                    nakPacket = str(packet, "utf-8")
                    nakPacket = nakPacket.replace("maquinanaoexiste", "NAK", 1)
                    #reconstroi o packet e envia pro proximo com NAK
                    sleep(sleepTime)
                    send.sendto(bytes(nakPacket, "utf8"), SENDTO)  
                #caso contrario ->     
                else:
                    #se passar no calculo de crc coloca o ACK
                    ack = "ACK"
                    print(recvMsg, end='')
                    print(" Cliente:", end='')
                    print(str(client))
                    ackPacket = str(packet, "utf-8")
                    ackPacket = ackPacket.replace("maquinanaoexiste", "ACK", 1)
                    ackPacket = ackPacket.replace("NAK", "ACK", 1)
                    #reconstroi o packet e envia pro proximo com ACK
                    sleep(sleepTime)
                    send.sendto(bytes(ackPacket, "utf8"), SENDTO)                
            #########################################################################################
            #########################################################se eu for broadcast
            if destination == 'TODOS':
                if origin == MY_NAME:
                    print('Removi uma mensagem que foi enviada para TODOS da fila.')
                    q.get()
                else:
                    sleep(sleepTime)
                    print(recvMsg, end='')
                    print(" Cliente:", end='')
                    print(str(client))
                    send.sendto(packet, SENDTO)  
            #########################################################se eu for apenas o intermediario
            elif origin != MY_NAME and destination != MY_NAME:
                #se eu nao for nenhum dos dois, so envia pro proximo
                sleep(sleepTime)
                print("Pacote nao e para mim enviando para a proxima maquina")
                send.sendto(packet, SENDTO) 
            #########################################################################################               
        elif content == '1111':
            print("Recebi o Token!")
            if Token:
                print("Recebi um token duplicado (ja tenho um token)!")
                continue
            Token = True
            #para maquina com true no arquivo de config controla se recebeu antes do tempo
            if((minimumTime > time.time() - tokenTime) and Control):
                Token = False
                print("Removendo o token por ter sido recebido antes do tempo mínimo.")
        else:
            #caso nao seja msg nem token
            print("Unknown type of packet")
        if Token:
            sendMsg()
        if(random.randint(1,100) < tokChance):
            sleep(2)
            print('Novo token gerado aleatoriamente!!!')
            send.sendto(bytes("1111", "utf8"), SENDTO)

if (START_TOKEN == "true"):
    Control = True
    Token = True
    threading.Thread(target=timing).start()

if Token:
    sendMsg()

threading.Thread(target=getMessageConsole).start()
threading.Thread(target=receiveMsg).start()
