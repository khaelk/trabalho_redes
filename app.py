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
    global Token
    #2222;maquinanaoexiste:Joao:Maria:19385749:Oi Pessoas!
    #1111
    if len(QueueMsgs) == 0:
        print("Nenhuma mensagem na fila, vou enviar o Token adiante")
        Token = False
        send.sendto(bytes("1111", "utf8"), SENDTO)
    if Token and len(QueueMsgs)>0:
        print("Vou enviar uma mensagem")
        send.sendto(bytes(QueueMsgs.pop(0), "utf8"), SENDTO)
    # no envio verificar se é unicast ou broadcast

def receiveMsg():
    global Token
    global Retransmits
    while True:
        sleep(5)
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
                        print("ACK: " + str(packet, "utf-8"))
                    if ack == "maquinanaoexiste":
                        #mensagem para termos controle de quando temos um maquinanaoexiste e
                        #de qual pacote é
                        print("maquinanaoexiste: " + str(packet, "utf-8"))
                    #passo o token pra prox maquina
                    Token = False
                    send.sendto(bytes("1111", "utf8"), SENDTO)
                    #caso um pacote com NAK tenha retornado com ACK ou maquinanaoexiste
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
                    print("NAK and already Retransmitted: "+ str(packet, "utf-8"))
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
            print("Recebi o Token!")
            Token = True
        else:
            print("Unknown type of packet")
        if Token:
            sendMsg(Token)

if Token:
    sendMsg()

receiveMsg()

udp.close()
send.close()