from dataclasses import dataclass
import logging
import re
import sys
import time
import types

import pygame
from pygame import display
from pygame import event
from pygame import transform
import requests


@dataclass(frozen=True)
class Symbol:
    name: str

    def __repr__(self):
        return "S-" + self.name


@dataclass
class Apply(object):
    function: None
    argument: None
    result: None = None

    def __repr__(self):
        if self.result:
            return f"Apply = {self.result}"
        else:
            return f"({self.function} {self.argument})"


def t(x0):
    def t1(x1):
        return x0
    return t1


def f(x0):
    def f1(x1):
        return x1
    return f1


def bool_to_int(x0):
    return x0(1)(0)


def eq(x0):
    def eq1(x1):
        return t if eval_ast(x0) == eval_ast(x1) else f
    return eq1


def lt(x0):
    def lt1(x1):
        return t if eval_ast(x0) < eval_ast(x1) else f
    return lt1


def s_combinator(x0):
    def s1(x1):
        def s2(x2):
            return Apply(Apply(x0, x2), Apply(x1, x2))
        return s2
    return s1


def c_combinator(x0):
    def c1(x1):
        def c2(x2):
            return Apply(Apply(x0, x2), x1)
        return c2
    return c1


def b_combinator(x0):
    def b1(x1):
        def b2(x2):
            return Apply(x0, Apply(x1, x2))
        return b2
    return b1


def i_combinator(x0):
    return x0


def cons(x0):
    def cons1(x1):
        def cons2(x2):
            return eval_ast(eval_ast(x2)(x0))(x1)
        return cons2
    return cons1


car = lambda x2: eval_ast(x2)(t)  # noqa
cdr = lambda x2: eval_ast(x2)(f)  # noqa


def nil(x2):
    return t


isnil = lambda x2: eval_ast(x2)(lambda x0: lambda x1: f)  # noqa


def iterate_cons(x0):
    head = car(x0)
    while not bool_to_int(isnil(head)):
        logging.debug(f"yielding {head}")
        yield head
        x0 = cdr(x0)
        head = car(x0)


def modulate(x0, for_human=False):
    x = eval_ast(x0)
    if isinstance(x, int):
        return modulate_number(x, for_human)
    elif isinstance(x, types.FunctionType):
        return modulate_list(x, for_human)
    else:
        raise ValueError(f"cannot modulate {x}")


def modulate_number(x, for_human):
    if for_human:
        return str(x)
    s = "01" if x >= 0 else "10"
    if x > 0:
        bits = bin(x)[2:]
    elif x < 0:
        bits = bin(x)[3:]
    else:
        bits = ""
    width = len(bits)
    div, mod = divmod(width, 4)
    width_bits = div + 1 if mod else div
    s += "1" * width_bits + "0"
    padding = "0" * (width_bits * 4 - width)
    s += padding + bits
    return s


def modulate_list(l, for_human):
    if bool_to_int(isnil(l)):
        s = "00" if not for_human else "nil"
    else:
        s = "11" if not for_human else "(cons "
        s += modulate(car(l), for_human)
        if for_human:
            s += " "
        s += modulate(cdr(l), for_human)
        if for_human:
            s += ")"

    return s


def demodulate(x0):
    x = eval_ast(x0)
    x, s = demodulate_rec(x)
    if s:
        logging.warning(f"extra bits after demodulation: {s}")
    return x


def demodulate_rec(x):
    type_ = x[:2]
    if type_ in ("01", "10"):
        return demodulate_number(x)
    elif type_ in ("00", "11"):
        return demodulate_list(x)
    else:
        raise ValueError(f"unsupported message type '{type_}'")


def demodulate_number(s):
    type_ = s[:2]
    s = s[2:]
    if type_ == "01":
        sign = 1
    elif type_ == "10":
        sign = -1
    else:
        raise ValueError("not a number")
    width_bits_end = s.find("0")
    width_bits = s[:width_bits_end]
    width = len(width_bits) * 4
    start = width_bits_end + 1
    end = start + width
    bits = s[start:end]
    s = s[end:]
    x = sign * int(bits, base=2) if bits else 0
    return x, s


def demodulate_list(s):
    type_ = s[:2]
    s = s[2:]
    if type_ == "00":
        x = nil
    elif type_ == "11":
        x0, s = demodulate_rec(s)
        x1, s = demodulate_rec(s)
        x = cons(x0)(x1)
    else:
        raise ValueError("not a list")

    return x, s


def eval_ast(node):
    logging.debug(f"evaluating {node}")
    if isinstance(node, Apply):
        if node.result is not None:
            return node.result
        function = eval_ast(node.function)
        node.result = eval_ast(function(node.argument))
        return node.result
    elif isinstance(node, Symbol):
        return eval_ast(global_environment[node])
    elif isinstance(node, (int, types.FunctionType, types.MethodType, str)):
        return node
    else:
        raise Exception("unsupported node: {}".format(repr(node)))


def load(module_path):
    environment = {}
    with open(module_path) as f:
        for line in f:
            symbol_name, expression_string = line.split("=")
            environment[Symbol(symbol_name.strip())] = parse(expression_string)
    return environment


def parse(expression_string):
    return read_from_tokens(expression_string.split())


def read_from_tokens(tokens):
    token = tokens.pop(0)
    if re.match("-?[0-9]+", token):
        return int(token)
    elif token == "ap":
        apply = Apply(read_from_tokens(tokens), read_from_tokens(tokens))
        return apply
    elif token in ("(", ",", ")"):
        raise Exception("not implemented")
    else:
        return Symbol(token)


global_environment = {
    Symbol("dec"): lambda x0: eval_ast(x0) - 1,
    Symbol("inc"): lambda x0: eval_ast(x0) + 1,
    Symbol("neg"): lambda x0: - eval_ast(x0),
    Symbol("add"): lambda x0: lambda x1: eval_ast(x0) + eval_ast(x1),
    Symbol("mul"): lambda x0: lambda x1: eval_ast(x0) * eval_ast(x1),
    Symbol("div"): lambda x0: lambda x1: eval_ast(x0) // eval_ast(x1),

    Symbol("eq"): eq,
    Symbol("lt"): lt,

    Symbol("t"): t,
    Symbol("f"): f,

    Symbol("s"): s_combinator,
    Symbol("c"): c_combinator,
    Symbol("b"): b_combinator,
    Symbol("i"): i_combinator,

    Symbol("cons"): cons,
    Symbol("car"): car,
    Symbol("cdr"): cdr,
    Symbol("nil"): nil,
    Symbol("isnil"): isnil,

    Symbol("mod"): modulate,
    Symbol("dem"): demodulate,
}


class Evaluator:
    def __init__(self, module_path, proxy_url, player_key):
        global_environment.update(load(module_path))
        self.proxy_url = proxy_url
        self.player_key = player_key
        global_environment[Symbol("send")] = self.send
        self.width, self.height = 320, 240
        display.init()
        self.screen = display.set_mode(
            (self.width * 4, self.height * 4)
        )
        print("display flags", bin(self.screen.get_flags()))
        global_environment[Symbol("draw")] = self.draw
        global_environment[Symbol("multipledraw")] = self.multipledraw

    def eval(self, expression_string):
        ast = parse(expression_string)
        start_time = time.time()
        print(eval_ast(ast))
        eval_time = time.time() - start_time
        logging.info(f"eval time {eval_time}")
        while True:
            for e in event.get():
                if e.type == pygame.QUIT:
                    return
            time.sleep(0.001)

    colors = [
        (255, 255, 255, 128),
        (255, 255, 0, 128),
        (255, 0, 255, 128),
        (255, 0, 0, 128),
        (0, 255, 255, 128),
        (0, 255, 0, 128),
        (0, 0, 255, 128)
    ]

    def draw(self, x0, color=colors[0]):
        surface = pygame.Surface((self.width, self.height),
                                 flags=pygame.SRCALPHA)
        print("surface flags", bin(surface.get_flags()))
        surface.fill((0, 0, 0, 0))
        for v in iterate_cons(x0):
            ax, ay = eval_ast(car(v)), eval_ast(cdr(v))
            x, y = ax + self.width // 2, ay + self.height // 2
            if x > (self.width - 1) or y > self.height - 1:
                logging.error(f"no space for pixel ({x}, {y})")
                sys.exit(1)
            logging.debug(f"drawing at {ax} {ay} -> {x}, {y}")
            surface.set_at((x, y), color)
        self.screen.blit(
            transform.scale(surface, (self.width * 4, self.height * 4)),
            (0, 0)
        )
        display.flip()
        return t

    def multipledraw(self, x0):
        black = 0, 0, 0
        self.screen.fill(black)
        for n, x in enumerate(iterate_cons(x0)):
            self.draw(x, color=self.colors[n])
        return t

    def f38(self, protocol, protocol_result):
        flag = eval_ast(car(protocol_result))
        new_state = car(cdr(protocol_result))
        data = car(cdr(cdr(protocol_result)))
        if flag == 0:
            return cons(new_state)(self.multipledraw(data))
        else:
            return self.interact(protocol, new_state, self.send(data))

    def interact(self, protocol, state, vector):
        logging.info("running")
        result = self.f38(protocol, eval_ast(eval_ast(protocol(state)))(vector))
        logging.info("finished")
        return result

    def interact_loop(self, protocol):
        protocol = eval_ast(Symbol(protocol))
        state = cons(1)(cons(cons(11)(nil))(cons(0)(cons(nil)(nil))))
        while True:
            click = None
            while not click:
                for e in event.get():
                    if e.type == pygame.QUIT:
                        return
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        x, y = e.pos[0], e.pos[1]
                        ax = x // 4 - self.width // 2
                        ay = y // 4 - self.height // 2
                        logging.info(f"click {x} {y} -> {ax} {ay}")
                        click = cons(ax)(ay)
                time.sleep(0.001)
            result = self.interact(protocol, state, click)
            state = car(result)
            logging.info("modulated state " + modulate(state, for_human=True))
            logging.info(state)

    def send(self, x):
        if not self.player_key:
            raise Exception(
                "player key is required to communicate with aliens"
            )

        data = modulate(x)
        logging.info(f"~~~~~ {data}")
        response = requests.post(
            self.proxy_url + "/aliens/send?apiKey=" + self.player_key,
            data=data
        )
        logging.info(f"{response.text} ~~~~~")
        if response.status_code != 200:
            print("Unexpected server response:")
            print("HTTP code:", response.status_code)
            exit(2)
        return demodulate(response.text)
