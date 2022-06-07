import socket
import threading
from time import sleep, perf_counter
from threading import Thread 
import queue
import binascii
import random
import time

from numpy import minimum

#variaveis globais, de token, retransmissao, e pacote atual
Token = False
Control = False
Retransmits = 0
tokenTime = time.time()
minimumTime = 5

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
    
#socket de envio de mensagens
send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SENDTO = (IP, int(PORTA))

#socket de recebimento de mensagens
MYIP = ''
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
RECEIVER = (MYIP, int(PORTA))
udp.bind(RECEIVER)

#TO-DO controle do token

#TO-DO Gerador de erros (crc ou msg) ((((((((((check só falta testar))))))))))

#TO-DO msgs para TODOS ou unicast ((((((((check só falta testar))))))

#TO-DO threads -> usuario poder digitar ((((melhorar exibicao do console))))

q = queue.Queue(10)

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
        

def sendMsg():
    global Token
    global Retransmits
    global tokenTime
    #2222;maquinanaoexiste:Joao:Maria:19385749:Oi Pessoas!
    #1111
    sleep(5)
    if q.qsize() == 0:
        print("Nenhuma mensagem na fila, vou enviar o Token adiante")
        Token = False
        send.sendto(bytes("1111", "utf8"), SENDTO)
        tokenTime = time.time()
    elif Token:
        print("Vou enviar uma mensagem")
        #mensagem de aviso se é retransmissao
        if Retransmits>0:
            print("Será uma retransmissao!!!")
        #calculo para ver se envia msg com erro
        error = random.randint(1, 100)
        #ajuste de chance de erro (0 = 100% de chance)
        if error<0:
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
        if diff > TIME_TOKEN:
            print("Timeout do token, reenviando novo token")
            Token = False
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
        if receivedPacket[0] == '2222':
            print("Recebi uma mensagem!")
            msgHeader = receivedPacket[1].split(':', 4)
            ack = msgHeader[0]
            origin = msgHeader[1]
            destination = msgHeader[2]
            crc = msgHeader[3]
            recvMsg = msgHeader[4]
            ######################################################################se eu for a origem
            if origin == MY_NAME:
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
                    send.sendto(bytes("1111", "utf8"), SENDTO)
                    
                    #caso um pacote com NAK tenha retornado com ACK ou maquinanaoexiste
                    #reestabeleco que posso ter retransmissao p o prox da fila
                    Retransmits = 0                    
                if ack == "NAK" and Retransmits<1:
                    #se for nak e nao tiver retransmitido
                    #reenvio a mensagem na rede
                    print("NAK: (" + str(packet, "utf-8") + ")")
                    #recoloco o pacote que deu NAK na fila novamente
                    #colocar na fila com maquinanaoexiste
                    mnePacket = str(packet, "utf-8")
                    mnePacket = mnePacket.replace("NAK", "maquinanaoexiste", 1)
                    #envio o token e nao o pacote!!!!!
                    Token = False
                    
                    tokenTime = time.time()
                    send.sendto(bytes("1111", "utf8"), SENDTO)
                    #inibo que haja mais de uma retransmissao
                    Retransmits = 1
                if ack == "NAK" and Retransmits>0:
                    #se for nak e já tiver retransmitido
                    print("NAK and already Retransmitted: ("+ str(packet, "utf-8") + ")")
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
                    send.sendto(bytes(ackPacket, "utf8"), SENDTO)                
            #########################################################################################
            #########################################################se eu for broadcast
            if destination == 'TODOS':
                print(recvMsg, end='')
                print(" Cliente:", end='')
                print(str(client))
                send.sendto(bytes(packet, "utf8"), SENDTO)  
            #########################################################se eu for apenas o intermediario
            if origin != MY_NAME and destination != MY_NAME:
                #se eu nao for nenhum dos dois, so envia pro proximo
                print("Pacote nao e para mim enviando para a proxima maquina")
                send.sendto(packet, SENDTO) 
            #########################################################################################               
        elif receivedPacket[0] == '1111':
            print("Recebi o Token!")
            Token = True
            print(time.time() - tokenTime, minimumTime)
            if(minimumTime > time.time() - tokenTime):
                Token = False
                print("Removendo o token por ter sido recebido antes do tempo mínimo..")
        else:
            print("Unknown type of packet")
        if Token:
            sendMsg()
        elif(random.randint(1,100) < 1):
            send.sendto(bytes("1111", "utf8"), SENDTO)

if (START_TOKEN == "true"):
    Token = True
    threading.Thread(target=timing).start()

if Token:
    sendMsg()

threading.Thread(target=getMessageConsole).start()
threading.Thread(target=receiveMsg).start()
