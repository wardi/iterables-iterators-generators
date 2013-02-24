def countdown_generator(fn):
    yield 5
    fn(5)
    yield 1
    fn(4)
    yield 1
    fn(3)
    yield 1
    fn(2)
    yield 1
    fn(1)
    yield 1
def running_avg():
    "coroutine that accepts numbers and yields their running average"
    total = float((yield))
    count = 1
    while True:
        i = yield total / count
        count += 1
        total += i
def advance_generator_once(original_fn):
    "decorator to advance a generator once immediately after it is created"
    def actual_call(*args, **kwargs):
        gen = original_fn(*args, **kwargs)
        assert gen.next() is None
        return gen
    return actual_call
running_avg = advance_generator_once(running_avg)
@advance_generator_once
def rock_paper_scissors():
    """
    coroutine for playing rock-paper-scissors

    yields: 'invalid key': invalid input was sent
            ('win', player, choice0, choice1): when a player wins
            ('tie', None, choice0, choice1): when there is a tie
            None: when waiting for more input

    accepts to .send(): (player, key):
        player is 0 or 1, key is a character in 'rps'
    """
    valid = 'rps'
    wins = 'rs', 'sp', 'pr'
    result = None

    while True:
        chosen = [None, None]
        while None in chosen:
            player, play = yield result
            result = None
            if play in valid:
                chosen[player] = play
            else:
                result = 'invalid key'
        
        if chosen[0] + chosen[1] in wins:
            result = ('win', 0) + tuple(chosen)
        elif chosen[1] + chosen[0] in wins:
            result = ('win', 1) + tuple(chosen)
        else:
            result = ('tie', None) + tuple(chosen)
import os
import termios
import tty

@advance_generator_once
def cbreak_keys(fd):
    "enter cbreak mode and yield keys as they arrive"
    termios_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    try:
        yield # initialize step
        while True:
            yield os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, termios_settings)
import socket

@advance_generator_once
def socket_read_and_close(sock):
    "yields strings from sock and ensures sock.shutdown() is called"
    try:
        b = None
        while b != '':
            yield b
            b = sock.recv(1)
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        sock.close()
@advance_generator_once
def telnet_filter():
    """
    coroutine accepting characters and yielding True when the character
    passed is actual input or False when it is part of a telnet command.
    """
    actual_input = None
    while True:
        key = yield actual_input # normal
        if key != chr(255):
            actual_input = True
            continue
            
        key = yield False # command
        if key == chr(255):
            actual_input = True
            continue
            
        actual_input = False
        if key == chr(250):
            while key != chr(240):
                key = yield False # subnegotiation
        else:
            yield False # parameter
@advance_generator_once
def telnet_keys(sock):
    "yields next key or None if key was a filtered out telnet command"
    # negotiate character-by-character, disable echo
    sock.send('\xff\xfd\x22\xff\xfb\x01')
    keep = telnet_filter()
    s = socket_read_and_close(sock)
    yield
    while True:
        # allow StopIteration to carry through:
        c = s.next()
        if keep.send(c):
            yield c
        else:
            yield None
class Timeout(Exception):
    pass

class Disconnect(Exception):
    pass

def game_machine(game_factory, output, best_of=9):
    """
    coroutine that manages and provides comminication for two-player games,
    best of N

    :param game_factory: a function that returns a game generator object
    :param output: a function that sends output to one or both players
    :param best_of: max games to play per guest (an odd number)

    yields: 'waiting' : waiting for a guest (disconnect any existing guest)
            'play': playing a game, accepting input
            'disable timeout': disable the guest timout, accepting input
            'reset timeout': reset and start guest timeout, accepting input

    accepts to .send():
        ('join', guest_name): Guest guest_name joined
        ('key', (player_num, key)): Input from player player_num (0 or 1)

    accepts to .throw(): Disconnect: the guest disconnected
                         Timeout: the guest timout fired
    """
    ravg = running_avg()
    while True:
        event, value = yield 'waiting'
        if event != 'join':
            continue
        game = game_factory()
        wins = [0, 0]
        output("Player connected: {0}".format(value), player=0)
        output("Welcome to the game", player=1)

        try:
            response = 'reset timeout'
            while True:
                event, value = yield response
                response = 'play'
                if event != 'key':
                    continue
                    
                player, key = value
                result = game.send((player, key))
                if result == 'invalid key':
                    output("Invalid key", player=player)
                    continue
                elif player == 1:
                    response = 'disable timeout'
                if not result:
                    continue
                    
                outcome, player, play0, play1 = result
                output("Player 0: {0}, Player 1: {1}".format(play0, play1))
                if outcome == 'win':
                    wins[player] += 1
                    output("Player {0} wins!".format(player))
                    output("Wins: {0} - {1}".format(*wins))
                    output("Overall: {0:5.2f}%".format(
                        (1 - ravg.send(player)) * 100), player=0)
                    
                if any(count > best_of / 2 for count in wins):
                    output("Thank you for playing!")
                    break
                response = 'reset timeout'
                
        except Disconnect:
            output("Opponent disconnected.", player=0)

        except Timeout:
            output("Timed out. Good-bye")
import socket
import sys
import time

def console_telnet_game_loop(game_factory, countdown_factory, best_of=9,
                             stdin=None, port=12333, now=None):
    """
    Coroutine that manages IO from console and incoming telnet connections
    (one client at a time), and tracks a timeout for the telnet clients.
    Console and telnet client act as player 0 and 1 of a game_machine.

    :param game_factory: passed to game_machine()
    :param coutdown_factory: function returning a countdown generator
    :param best_of: passed to game_machine()
    :param stdin: file object to use for player 0, default: sys.stdin
    :param port: telnet port to listen on for player 1
    :param now: function to use to get the current time in seconds,
                default: time.time

    yields args for select.select(*args)

    accepts to .send() the fd lists returned from select.select()
    """
    if stdin is None:
        stdin = sys.stdin
    if now is None:
        now = time.time
        
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('', port))
    server.listen(0)
    print "Listening for telnet connections on port", port
    
    client = None
    client_reader = None
    timeout = None
    countdown = None
    local_fd = stdin.fileno()
    local_user = cbreak_keys(local_fd)
    
    def output(txt, player='all'):
        if player != 1:
            print txt
        if player != 0 and client:
            client.send(txt + '\r\n')

    g = game_machine(game_factory, output, best_of)
    state = g.next()
    
    while True:
        if state == 'waiting' and client:
            client = client_reader = timeout = None
        if state == 'reset timeout':
            countdown = countdown_factory(lambda n: output(str(n), player=1))
            timeout = time.time() + countdown.next()
            state = 'play'
        if state == 'disable timeout':
            countdown = timeout = None
        
        telnet_fd = client.fileno() if client else server.fileno()
        timeout_seconds = max(0, timeout - now()) if timeout else None
        
        readable, _, _ = yield [local_fd, telnet_fd], [], [], timeout_seconds
        
        if not readable: # no files to read == timeout, advance countdown
            try:
                timeout = now() + countdown.next()
            except StopIteration:
                state = g.throw(Timeout())
                timeout = None
            continue
        if local_fd in readable: # local user input
            state = g.send(('key', (0, local_user.next())))
            readable.remove(local_fd)
            continue
        if client: # client input
            try:
                key = client_reader.next()
            except StopIteration:
                state = g.throw(Disconnect())
            else:
                if key: # might be None if telnet commands were filtered
                    state = g.send(('key', (1, key)))
            continue
        # accept a new client connection
        client, addr = server.accept()
        client_reader = telnet_keys(client)
        client_reader.next()
        state = g.send(('join', str(addr)))
import select

def main():
    loop = console_telnet_game_loop(rock_paper_scissors, countdown_generator)
    fd_lists = None
    while True:
        select_args = loop.send(fd_lists)
        fd_lists = select.select(*select_args)

if __name__ == "__main__":
    main()
