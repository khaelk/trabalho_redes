import socket
from time import sleep, perf_counter
from threading import Thread

#variaveis globais, de token, retransmissao, e pacote atual
Token = False
Retransmits = 0

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
            if lineCount == 4:
                TOKEN = lin.rstrip('\n')
            lineCount = lineCount + 1
    return IP_PORTA, NAME, TIME_TOKEN, TOKEN, IP, PORTA

IP_PORTA, MY_NAME, TIME_TOKEN, START_TOKEN, IP, PORTA = readFile('arq2.txt')

if (START_TOKEN == "true"):
    Token = True
    
#socket de envio de mensagens
send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SENDTO = (IP, int(PORTA))

#socket de recebimento de mensagens
MYIP = ''
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
RECEIVER = (MYIP, int(PORTA))
udp.bind(RECEIVER)

QueueMsgs = [
"2222;maquinanaoexiste:Bob:Rob:19385749:Oi Pessoas1!", 
"2222;maquinanaoexiste:Bob:Rob:19385749:Oi Pessoas2!", 
"2222;maquinanaoexiste:Bob:Rob:19385749:Oi Pessoas3!"
]

def sendMsg():
    #2222;maquinanaoexiste:Joao:Maria:19385749:Oi Pessoas!
    #1111
    if len(QueueMsgs) == 0:
        send.sendto(bytes("1111", "utf8"), SENDTO)
    if Token:
        send.sendto(bytes(QueueMsgs.pop(0), "utf8"), SENDTO)
    # no envio verificar se é unicast ou broadcast

def receiveMsg(Token):
    while True:
        sleep(5)
        packet, client = udp.recvfrom(1024)
        receivedPacket = str(packet, "utf-8").split(';', 1)
        if receivedPacket[0] == '2222':
            msgHeader = receivedPacket[1].split(':', 4)
            ack = msgHeader[0]
            origin = msgHeader[1]
            destination = msgHeader[2]
            crc = msgHeader[3]
            recvMsg = msgHeader[4]
            ######################################################################se eu for a origem
            if origin == MY_NAME:
                if ack == "maquinanaoexiste" or ack == "ACK":
                    #retiro da fila
                    print("Nao retransmito a mensagem e apenas passo o token caso ME ou ACK")
                    #passo o token pra prox maquina
                    send.sendto(bytes("1111", "utf8"), SENDTO)
                    #caso o pacote com NAK tenha retornado com ACK
                    #reestabeleco que posso ter retransmissao p o prox da fila
                    Retransmits = 0
                if ack == "NAK" and Retransmits<1:
                    #se for nak e nao tiver retransmitido
                    #reenvio a mensagem na rede
                    print("NAK")
                    send.sendto(packet, SENDTO)
                    Retransmits = 1
                if ack == "NAK" and Retransmits>0:
                    #se for nak e já tiver retransmitido
                    print("Tiro da fila nao retransmito")
                    Retransmits = 0
            #########################################################################################
            ######################################################################se eu for o destino
            if destination == MY_NAME:
                #se eu for o destino
                #verificar o crc para o recalculo / NAK se não passar

                #se passar no calculo de crc coloca o ACK
                ack = "ACK"
                print(recvMsg, end='')
                print(" Cliente:", end='')
                print(str(client))
                ackPacket = str(packet, "utf-8")
                ackPacket.replace("maquinanaoexiste", ack, 1)
                ackPacket.replace("NAK", ack, 1)
                #reconstroi o packet e envia pro proximo
                send.sendto(bytes(ackPacket, "utf8"), SENDTO)                
            #########################################################################################
            #########################################################se eu for apenas o intermediario
            if origin != MY_NAME and destination != MY_NAME:
                #se eu nao for nenhum dos dois, so envia pro proximo
                print("Pacote nao e para mim enviando para a proxima maquina")
                send.sendto(packet, SENDTO) 
            #########################################################################################               
        elif receivedPacket[0] == '1111':
            Token = True
            print("Recebi o Token!")
        else:
            print("Unknown type of packet")
        if Token:
            sendMsg()

if Token:
    sendMsg()
receiveMsg(Token)

udp.close()
send.close()