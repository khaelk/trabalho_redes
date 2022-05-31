import socket
import threading
from time import sleep, perf_counter
from threading import Thread 
import queue
import binascii

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

#TO-DO controle do token

#TO-DO Gerador de erros (crc ou msg)

#TO-DO msgs para TODOS ou unicast

#TO-DO threads -> usuario poder digitar (((((((FALTA TESTAR)))))))

#TO-DO no nak de retransmissao recolocar a msg original (anotado ali embaixo onde colocar isso) (((((((FALTA TESTAR)))))))


q = queue.Queue(10)

def getMessageConsole():
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
    #2222;maquinanaoexiste:Joao:Maria:19385749:Oi Pessoas!
    #1111
    if q.empty:
        print("Nenhuma mensagem na fila, vou enviar o Token adiante")
        Token = False
        send.sendto(bytes("1111", "utf8"), SENDTO)
    elif Token:
        print("Vou enviar uma mensagem")
        if Retransmits>0:
            print("Será uma retransmissao!!!")
        send.sendto(bytes(q.queue[0], "utf8"), SENDTO)
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
                        print("ACK: (" + str(packet, "utf-8") + ")")
                        q.get()
                    if ack == "maquinanaoexiste":
                        #mensagem para termos controle de quando temos um maquinanaoexiste e
                        #de qual pacote é
                        print("maquinanaoexiste: (" + str(packet, "utf-8") + ")")
                        q.get()
                    #passo o token pra prox maquina
                    Token = False
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
                    #### IMPORTANTE: colocar a mensagem original novamente antes de por na fila
                    #### (ter um jeito de guardar isso)

                    q.put(mnePacket)
                    #envio o token e nao o pacote!!!!!
                    Token = False
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
                if binascii.crc32(bytes(recvMsg, "utf-8")) != crc:
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
            sendMsg()


if Token:
    sendMsg()

threadAdd = threading.Thread(target=getMessageConsole).start()
threadRemove = threading.Thread(target=receiveMsg).start()

udp.close()
send.close()