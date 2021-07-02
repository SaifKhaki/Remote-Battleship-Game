import random
import threading 
import time
import socket
from _thread import *


# pre-inititalizing the size of the battlefield
battleground_width = 10
battleground_height = 10
alphabet_map_int = {'A':0,'B':1,'C':2,'D':3,'E':4, 'F':5, 'G':6, 'H':7, 'I':8, 'J':9}
ships = {'D':['Destroyer',1], 'S':['Submarine',2], 'C':['Cruiser',3], 'B':['Battleship',4], 'Y':['Yacht',5]}
ships_count = len(ships)
directions = {'v':0, 'h':1}
battlegrounds = {'human':[], 'pc':[], 'player2':[]}
mode = ''
MULTIPLAYER_PORT = 2068
MAX_HIT = 15

#reader-writer lock
class rwlock:
    def __init__(self):
        self.rwlock = 0
        self.writers_waiting = 0
        self.monitor = threading.Lock()
        self.readers_ok = threading.Condition(self.monitor)
        self.writers_ok = threading.Condition(self.monitor)
    
    def rlock(self):
        self.monitor.acquire()
        while self.rwlock < 0 or self.writers_waiting:
            self.readers_ok.wait()
        self.rwlock += 1
        self.monitor.release()

    def wlock(self):
        self.monitor.acquire()
        while self.rwlock != 0:
            self.writers_waiting += 1
            self.writers_ok.wait()
            self.writers_waiting -= 1
        self.rwlock = -1
        self.monitor.release()

    def release(self):
        self.monitor.acquire()
        if self.rwlock < 0:
            self.rwlock = 0
        else:
            self.rwlock -= 1
        wake_writers = self.writers_waiting and self.rwlock == 0
        wake_readers = self.writers_waiting == 0
        self.monitor.release()
        if wake_writers:
            self.writers_ok.acquire()
            self.writers_ok.notify()
            self.writers_ok.release()
        elif wake_readers:
            self.readers_ok.acquire()
            self.readers_ok.notifyAll()
            self.readers_ok.release()

#initializing lock 
rwl = rwlock()

#checking if ships overlap 
def check_overlap(row, col, direction, ship, player):
    if(direction):
        for i in range(col, col+ships[ship][1]):
            rwl.rlock()
            status = battlegrounds[player][alphabet_map_int[row]][i]
            rwl.release()
            if(status != 'O'):
                return 1
    else:
        for i in range(ord(row)+1,ord(row)+ships[ship][1]):
            rwl.rlock()
            status = battlegrounds[player][alphabet_map_int[chr(i)]][col]
            rwl.release()
            if(status != 'O'):
                return 1
    return 0

#printing all the values of the battlefield
def print_battleground(player):
    print_str = ''
    for row in battlegrounds[player]:
        print_str += " ".join(row)
        print_str += "\n"
    return print_str
    
#changning symbols in a battleground
def update_battleground(ship_number, row_indices, col_indices, symbol, player):
    to_change = 0
    for i in row_indices:
        for j in col_indices:
            rwl.rlock()
            status = battlegrounds[player][alphabet_map_int[i]][int(j)]
            rwl.release()
            if(status == "O"):
                to_change += 1
            else:
                create_random_location(ship_number, symbol, player)
    if(to_change == len(row_indices) + len(col_indices) -1):
        rwl.wlock()
        for i in row_indices:
            for j in col_indices:        
                battlegrounds[player][alphabet_map_int[i]][int(j)] = symbol
        rwl.release()

#avoiding overlap with a technique called Start from start
def avoid_overlap(row, col, direction, ship, player):
    row = 'A'
    col=0
    while(True):
        if(check_overlap(row, col, direction, ship, player)):
            col += 1
            if(col == 9):
                col = 0
                row = chr(ord(row)+1)
            continue   
        else:
            return (row, col)

#making location variable
def prepare_update(i, d, start_row, start_col, j, player):
    row_indices = []
    col_indices = []
    row_indices.append(start_row)
    if(d):
        for l in range(start_col, start_col+ships[j][1]):
            col_indices.append(l)
    else:
        for l in range(ord(start_row)+1,ord(start_row)+ships[j][1]):
            row_indices.append(chr(l))
        col_indices.append(start_col)
    
    if(len(row_indices) + len(col_indices) ==  ships[j][1] + 1):
        update_battleground(i, row_indices, col_indices, j, player)
        row_indices = []
        col_indices = []
        return 1
    else:
        return 0

#pc_random creation
def create_random_location(i, j, player):
    overlap_count = 0
    d = directions[list(directions.keys())[i%2]]
    if(d):
        start_row = random.choice(list(alphabet_map_int.keys())[:10])
        start_col = random.randrange(10 - ships[j][1])
    else:
        start_row = random.choice(list(alphabet_map_int.keys())[:10 - ships[j][1]])
        start_col = random.randrange(10)
    #checking if overlapped and then removing overlap
    while(True):
        if(check_overlap(start_row, start_col, d, j, player)):
            overlap_count += 1
            if(overlap_count >= 3):
                start_row, start_col = avoid_overlap(start_row, start_col, d, j ,player)
            if(not check_overlap(start_row, start_col, d, j, player)):
                break
        else:
            break
    #updating the battlefield
    prepare_update(i, d, start_row, start_col, j, player)
    return 1
    
#placing ships by 2 players
def placement(player, connection = None):
    i = 4
    threads = []*5
    while(True):
        if(i<0):
            break        
        j = list(ships.keys())[i]
        if(player == 'human'):
            while(True):
                print("Place your", ships[j][0], "with size of", ships[j][1], ": (Use syntax as <row><col><direction>)")
                location = input()
                try:
                    if( len(location) == 3 and ((location[0] in alphabet_map_int.keys()) and (isinstance(int(location[1]), int)) and (location[2] in directions.keys()))):
                        start_row = location[0]
                        start_col = int(location[1])
                        d = int(directions[location[2]])
                        break
                    else:
                        print("Wrong format.")
                except:
                    print("Wrong format.")
            if(check_overlap(start_row, start_col, d, j, player)):
                print('Your ship is overlapping with other ships. Try another combination.')
                continue
            if(prepare_update(i, d, start_row, start_col, j, player)):
                i -= 1
            else: 
                print("Invalid input for ",  ships[j][0], ". Try the syntax of <row><col><direction>"),
        elif(player == 'player2'):
            return_str = ''
            while(True):
                connection.send(str.encode(return_str + "Place your " + str(ships[j][0]) + " with size of " + str(ships[j][1]) + " : (Use syntax as <row><col><direction>)"))
                location = connection.recv(2048).decode('utf-8')
                try:
                    if( len(location) == 3 and ((location[0] in alphabet_map_int.keys()) and (isinstance(int(location[1]), int)) and (location[2] in directions.keys()))):
                        start_row = location[0]
                        start_col = int(location[1])
                        d = int(directions[location[2]])
                        break
                    else:
                        return_str += "Wrong format.\n"
                except:
                    return_str += "Wrong format.\n"
            if(check_overlap(start_row, start_col, d, j, player)):
                return_str += 'Your ship is overlapping with other ships. Try another combination.\n'
                continue
            if(prepare_update(i, d, start_row, start_col, j, player)):
                i -= 1
            else: 
                return_str += "Invalid input for " +  ships[j][0] + ". Try the syntax of <row><col><direction>\n"
        elif(player == 'pc'):
            threads.append(threading.Thread(target=create_random_location, args=(i, j, player,)))
            threads[len(threads)-1].start()
            i -= 1

    if(player == 'pc'):
        for thread in threads:
            thread.join()

#checking if the attack was a hit
def check_hit(row, col, player):
    status = battlegrounds[player][alphabet_map_int[row]][col]
    if(status != 'O' and status != 'X'):
        battlegrounds[player][alphabet_map_int[row]][col] = 'X'
        return ships[status][0]
    elif(status == 'X'):
        return 1
    else:
        battlegrounds[player][alphabet_map_int[row]][col] = 'X'
        return 0
    
#initializing board
for x in range(battleground_width):
    for y in battlegrounds:
        battlegrounds[y].append(["O"] * battleground_height)
        
# play game
def play_game(player1, player2, connection = None):
    if(player2 == 'pc'):
        #placement by both players
        t1 = threading.Thread(target=placement, args=('human',)) 
        t2 = threading.Thread(target=placement, args=('pc',))

        t1.start() 
        t2.start() 

        t1.join() 
        t2.join() 
    elif(player2 == 'player2'):
        t1 = threading.Thread(target=placement, args=('human',)) 
        t2 = threading.Thread(target=placement, args=('player2', connection))

        t1.start() 
        t2.start() 

        t1.join() 
        t2.join() 
        
    print('\nYour batleground is shown as:')
    print(print_battleground(player1))
    #start battle
    print("\nYou are good to go now! The battle begins.")
    hits = {player1:0, player2:0}
    if(player2 == 'player2'):
        return_str = '\nYour batleground is shown as:\n'
        return_str += print_battleground(player2)
        return_str += "\nYou are good to go now! The battle begins.\n"
    while(True):
        if(hits[player1] == MAX_HIT):
            print("You win!")
            if(player2 == 'player2'):
                return_str += "\nYou lost!"
                connection.send(str.encode(return_str))
            break
        elif(hits[player2] == MAX_HIT):
            if(player2 == 'player2'):
                return_str += "\nYou win!"
                connection.send(str.encode(return_str))
            print("You lost!")
            break
        while(True):
            print('\nYour turn: ', end='')
            hit_peg = input()
            try:
                if( len(hit_peg) == 2 and ((hit_peg[0] in alphabet_map_int.keys()) and (isinstance(int(hit_peg[1]), int)))):
                    start_row = hit_peg[0]
                    start_col = int(hit_peg[1])
                    break
                else:
                    print("Wrong format.")
            except:
                print("Wrong format.")
        #check at row and col of pc battleground
        status = check_hit(start_row, start_col, player2)
        if(player2 == 'player2'):
                return_str += "\n\nYour friend played: " + str(start_row) + str(start_col) + "\n"
        if(status not in [0,1]):
            print(status, " was hit.")
            if(player2 == 'player2'):
                return_str += status + " was hit."
            hits[player1] += 1
        elif(status == 1):
            print("This point was already hit. You wasted your turn.")
            if(player2 == 'player2'):
                return_str += "This point was already hit. Your friend wasted his turn."
        else:
            print("Miss")
            if(player2 == 'player2'):
                return_str += "Miss"

        print(player2, 'turn: ', end='')
        if(player2 == 'pc'):
            start_row = random.choice(list(alphabet_map_int.keys()))
            start_col = random.randrange(10)
            print(start_row+str(start_col))
            status = check_hit(start_row, start_col, player1)
            if(status not in [0,1]):
                print(status, " was hit.")
                hits[player2] += 1
            elif(status == 1):
                print("This point was already hit. You wasted your turn.")
            else:
                print("Miss")  
        elif(player2 == 'player2'):
            
            while(True):
                connection.send(str.encode(return_str + '\nYour turn: '))
                return_str = ''
                hit_peg = connection.recv(2048).decode('utf-8')
                try:
                    if( len(hit_peg) == 2 and ((hit_peg[0] in alphabet_map_int.keys()) and (isinstance(int(hit_peg[1]), int)))):
                        start_row = hit_peg[0]
                        start_col = int(hit_peg[1])
                        break
                    else:
                        return_str += "Wrong format."
                except:
                    return_str += "Wrong format."
            status = check_hit(start_row, start_col, player1)
            print(start_row+str(start_col))
            if(status not in [0,1]):
                print(status, " was hit.")
                return_str += status + " was hit.\n"
                hits[player2] += 1
            elif(status == 1):
                print("This point was already hit. Your friend wasted his turn.")
                return_str += "This point was already hit. You wasted your turn.\n"
            else:
                print("Miss")
                return_str += "Mis\ns"
            return_str += 'score board: Your score = ' + str(hits[player1]) + ", " + player2 + " = " + str(hits[player2])
         #check at row and col of pc battleground
        print('score board: Your score = ', hits[player1], ", ", player2, " = ", hits[player2])
    
print("Let's play Battleship!\nFirstly, place your ships on the battlefield:")
while(True):
    mode = input("Play single player (S) or multiplayer (M):")
    if(mode in ['S', 'M']):
        if(mode == 'S'):
            #printing your battleground
            play_game('human', 'pc')
            break
        elif(mode == 'M'):
            while(True):
                server = input("Do you want to create a new server (C) or join a server (J):")
                if(server in ['C', 'J']):
                    if(server == 'C'):
                        ServerSideSocket = socket.socket()
                        host = socket.gethostname()
                        print("The server's IP addres is (send this to your friend): ", socket.gethostbyname(host))
                        port = MULTIPLAYER_PORT
                        ThreadCount = 0
                        try:
                            ServerSideSocket.bind((host, port))
                        except socket.error as e:
                            print(str(e))
                        print('Waiting for your friend...')
                        ServerSideSocket.listen(1)
                        
                        Client, address = ServerSideSocket.accept()
                        print('Connected to: ' + address[0] + ':' + str(address[1]))
                        play_game('human', 'player2', Client)
                        break
                    elif(server == 'J'):
                        ClientMultiSocket = socket.socket()
                        host = input("Specify your friends IP address: ")
                        port = MULTIPLAYER_PORT
                        print('Waiting for connection response')
                        try:
                            ClientMultiSocket.connect((host, port))
                        except socket.error as e:
                            print(str(e))

                        res = ClientMultiSocket.recv(1024)
                        print(res.decode('utf-8'))
                        while True:
                            Input = input('press q to end game>>>> ')
                            if(Input == 'q'):
                                break
                            ClientMultiSocket.send(str.encode(Input))
                            res = ClientMultiSocket.recv(1024)
                            print(res.decode('utf-8'))

                        ClientMultiSocket.close()
                        break
                else:
                    print('Invalid Input')
            break
    else:
        print('Invalid Input')