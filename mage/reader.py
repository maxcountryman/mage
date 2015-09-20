import collections
import fractions
import re
import sys

import mage.fn as fn
import mage.hashmap as hashmap
import mage.list as list
import mage.namespace as namespace
import mage.rt as rt
import mage.symbol as symbol
import mage.vector as vector

whitespace = {' ', ',', '\n', '\t', '\r', '\b', '\f'}

symbol_pattern = re.compile('[:]?([\\D^/].*/)?([\\D^/][^/]*)')

int_pattern = \
    re.compile('(?P<sign>[+-])?'
               '(:?'
               '(?P<radix>(?P<base>[1-9]\d?)[rR](?P<value>[0-9a-zA-Z]+))|'
               '(?P<dec_int>0|[1-9]\d*)                                 |'
               '0(?P<oct_int>[0-7]+)                                    |'
               '0[xX](?P<hex_int>[0-9a-fA-F]+))$', re.X)

float_pattern = re.compile('[+-]?\d+(\.\d*([eE][+-]?\d+)?|[eE][+-]?\d+)$')

ratio_pattern = re.compile('[-+]?(0|[1-9]\d*)/(0|[1-9]\d*)$')

char_literals = {'t': '\t',
                 'r': '\r',
                 'n': '\n',
                 'b': '\b',
                 'f': '\f',
                 '\\': '\\',
                 '"': '"'}

named_chars = {'newline': '\n',
               'space': ' ',
               'tab': '\t',
               'backspace': '\b',
               'formfeed': '\f',
               'return': '\r'}

octal_chars = set('01234567')
hex_chars = set('0123456789abcdefABCDEF')

# Interned symbols.
DEF = symbol.Symbol.intern('def')
DEFMACRO = symbol.Symbol.intern('defmacro')
LET = symbol.Symbol.intern('let')
DO = symbol.Symbol.intern('do')
IF = symbol.Symbol.intern('if')

FN = symbol.Symbol.intern('fn')
QUOTE = symbol.Symbol.intern('quote')
SYNTAX_QUOTE = symbol.Symbol.intern('`')
UNQUOTE = symbol.Symbol.intern('~')
UNQUOTE_SPLICE = symbol.Symbol.intern('~@')


class ReaderError(Exception):
    pass


class Reader(object):
    def __init__(self,
                 stream,
                 start_line=-1,
                 start_column=0,
                 line_delims=None):
        self._stream = stream
        self._queue = collections.deque()
        self._queue_len = 0

        self.line = start_line
        self.column = start_column

        if line_delims is None:
            self._line_delims = {'\n', '\r'}

    def __iter__(self):
        return self

    def next(self):
        if self._queue_len > 0:
            self._queue_len -= 1
            return self._queue.popleft()

        c = self._stream.next()

        self.column += 1
        if c in self._line_delims:
            self.column -= 1
            self.line += 1

        return c

    def push(self, val):
        self._queue.append(val)
        self._queue_len += 1

    def read_one(self):
        try:
            c = self.next()
        except StopIteration:
            return

        return c


def read(reader, eof_is_error=False, eof_value=None):
    try:
        while True:
            c = reader.read_one()

            while c in whitespace:
                c = reader.read_one()

            if c is None and eof_is_error:
                raise RuntimeError('EOF while reading')
            elif c is None:
                return eof_value

            if c.isdigit():
                return read_number(reader, c)

            macro_reader = reader_macros.get(c)
            if macro_reader is not None:
                ret = macro_reader(reader, c)

                # No-op macros return reader.
                if ret is reader:
                    continue

                return ret

            token = read_token(reader, c)
            return interpret_token(token)
    except Exception as e:
        raise ReaderError(reader.line, reader.column, e), \
            None, \
            sys.exc_info()[2]  # Include the full stacktrace.


def read_string(s):
    return read(Reader(c for c in s))


def read_token(reader, c):
    cs = [c]
    while True:
        c = reader.read_one()
        if c is None or c in whitespace or c in reader_macros:
            reader.push(c)
            return ''.join(cs)

        cs.append(c)


def read_number(reader, c):
    cs = [c]
    while True:
        c = reader.read_one()
        if c is None or c in whitespace or c in reader_macros:
            reader.push(c)
            break

        cs.append(c)

    s = ''.join(cs)
    n = match_number(s)
    if n is None:
        raise RuntimeError('Invalid number: ' + s)

    return n


def read_delimited_list(reader, delimiter):
    first_line = reader.line
    args = []

    while True:
        c = reader.read_one()
        while c in whitespace:
            c = reader.read_one()

        if c is None:
            if first_line < 0:
                raise RuntimeError('EOF while reading')

            msg = 'EOF while reading, starting at line ' + str(first_line)
            raise RuntimeError(msg)

        if c == delimiter:
            break

        macro = macros.get(c)
        if macro is not None:
            ret = macro(reader, c)
            if ret is not None and ret is not reader:
                args.append(ret)
        else:
            reader.push(c)
            ret = read(reader, eof_is_error=True)
            args.append(ret)

    return args


def match_number(s):
    match = int_pattern.match(s)
    if match is not None:
        md = match.groupdict()
        sign = md['sign'] or '+'

        # 12rAA
        if md['radix'] is not None:
            return int(sign + md['value'], int(md['base'], 10))

        # 42
        if md['dec_int'] is not None:
            return int(sign + md['dec_int'])

        # 0666
        if md['oct_int'] is not None:
            return int(sign + md['oct_int'], 8)

        # 0xdeadbeef
        if md['hex_int'] is not None:
            return int(sign + md['hex_int'], 16)

    match = float_pattern.match(s)
    if match is not None:
        return float(match.group())

    match = ratio_pattern.match(s)
    if match is not None:
        return fractions.Fraction(match.group())


def interpret_token(s):
    if s == 'nil':
        return None

    if s == 'true':
        return True

    if s == 'false':
        return False

    sym = match_symbol(s)
    if sym is not None:
        return sym

    raise RuntimeError('Invalid token: ' + s)


def match_symbol(s):
    match = symbol_pattern.match(s)
    if match is not None:
        ns = match.group(1)
        name = match.group(2)

        if ns is not None and ns.endswith(':/') \
                or name.endswith(':') \
                or s.find('::', 1) != -1:
            return

        return symbol.Symbol.intern(s)


def codepoint_to_unicode(token, offset, base):
    try:
        return unichr(int(token[offset:], base))
    except:
        try:
            token = '\\' + token
            return token.decode('unicode-escape')
        except Exception as e:
            raise e
            raise UnicodeError('Invalid unicode character: {}'.format(token))


def char_reader(reader, _):
    c = reader.read_one()
    if c is None:
        raise RuntimeError('EOF while reading character')

    token = read_token(reader, c)
    if len(token) == 1:
        return token
    elif token in named_chars:
        return named_chars[token]
    elif token.lower().startswith('u'):
        try:
            c = codepoint_to_unicode(token.upper(), 1, 16)
        except UnicodeError as e:
            raise RuntimeError(e), None, sys.exc_info()[2]
        return c
    elif token.lower().startswith('o'):
        if len(token) > 4:
            err_fmt = ('Invalid octal escape sequence length in literal '
                       'string: {}')
            raise RuntimeError(err_fmt.format(token))
        try:
            c = codepoint_to_unicode(token.upper(), 1, 8)
        except UnicodeError as e:
            raise RuntimeError(e), None, sys.exc_info()[2]
        if ord(c) > 255:
            err_fmt = ('Octal escape sequence in literal string must be '
                       'in range [0, 377], got: ({})')
            raise RuntimeError(err_fmt.format(ord(c)))
        return c
    raise RuntimeError('Unsupported character: \\{}'.format(token))


def string_reader(reader, _):
    cs = []
    c = reader.read_one()
    while c != '"':
        if c is None:
            raise RuntimeError('EOF while reading string')

        if c == '\\':
            c = reader.read_one()
            if c is None:
                raise RuntimeError('EOF while reading string')

            if c in char_literals:
                c = char_literals[c]
            elif c == 'u':
                c = reader.read_one()
                if c not in hex_chars:
                    err_fmt = ('Hexidecimal digit expected after \\u in '
                               'literal string, got: ({})')
                    raise RuntimeError(err_fmt.format(c))
                # c = read_unicode_char(reader, c, 16, 4, True)
            elif c in octal_chars:
                # c = read_unicode_char(reader, c, 8, 3, False)
                if ord(c) > 255:
                    err_fmt = ('Octal escape sequence in literal string must '
                               'be in range [0, 377], got: ({})')
                    raise RuntimeError(err_fmt.format(ord(c)))
            else:
                err_fmt = 'Unsupported escape character in literal string: {}'
                raise RuntimeError(err_fmt.format(c))
        cs.append(c)
        c = reader.read_one()

    return ''.join(cs)


def quote_reader(reader, _):
    c = reader.read_one()
    token = read_token(reader, c)
    return list.List([QUOTE, token])


def list_reader(reader, _):
    args = read_delimited_list(reader, ')')
    if len(args) == 0:
        return list.List()

    return list.List(args)


def vector_reader(reader, _):
    args = read_delimited_list(reader, ']')
    if len(args) == 0:
        return vector.Vector()

    return vector.Vector(args)


def set_reader(reader, _):
    args = read_delimited_list(reader, '}')
    if len(args) == 0:
        set()

    return set(args)


def map_reader(reader, _):
    args = read_delimited_list(reader, '}')
    if len(args) == 0:
        hashmap.HashMap()

    return hashmap.HashMap((k, v) for k, v in zip(args[::2], args[1::2]))


def unmatched_delimiter_reader(_, delimiter):
    msg = 'Unmatched delimiter: ' + delimiter
    raise RuntimeError(msg)


reader_macros = {'\\': char_reader,
                 '"': string_reader,
                 '\'': quote_reader,
                 '(': list_reader,
                 ')': unmatched_delimiter_reader,
                 '[': vector_reader,
                 ']': unmatched_delimiter_reader,
                 '{': map_reader,
                 '}': unmatched_delimiter_reader}

macros = {}


def namespace_for(sym, in_ns):
    sym_ns = symbol.Symbol(sym.ns)
    ns = in_ns.lookup_alias(sym_ns)
    if ns is None:
        return namespace.Namespace.find(sym_ns)
    return ns


def eval(form, ns):
    while True:
        if isinstance(form, symbol.Symbol):
            if form.ns is not None:
                sym_ns = namespace_for(form, ns)
                v = sym_ns.find_interned_var(symbol.Symbol(form.name))
            else:
                v = ns.find_interned_var(form)

            if v is None:
                err_fmt = 'Unable to resolve symbol: {} in this context'
                raise RuntimeError(err_fmt.format(form))

            return v.root
        elif not isinstance(form, list.List):
            return form
        elif len(form) == 0:
            return form
        elif form[0] == DEF:
            _, sym, val = form
            v = ns.intern(sym)
            v.root = eval(val, ns)
            return v
        elif form[0] == DO:
            if len(form) > 1:
                for f in form[1:-1]:
                    eval(f, ns)
                form = form[-1]
        elif form[0] == IF:
            if len(form) == 4:
                _, question, answer, exception = form
                if rt.bool_cast(eval(question, ns)):
                    form = answer
                else:
                    form = exception
            elif len(form) == 3:
                _, question, answer = form
                if rt.bool_cast(eval(question, ns)):
                    form = answer
                else:
                    form = None
            else:
                raise ReaderError('Wrong number of forms given to if')
        elif form[0] == QUOTE:
            _, sym = form
            return sym
        elif form[0] == FN:
            body = None
            if len(form) == 3:
                _, params, body = form
            else:
                _, params = form
            return fn.Fn(params, body, ns)
        else:
            current_ns = ns
            args = list.List(eval(f, ns) for f in form)
            func = args.pop(0)
            if isinstance(func, fn.Fn):
                form = func.body
                fn_scope_sym = symbol.Symbol('fn__' + str(id(func)))
                ns = fn.Closure(fn_scope_sym, outer=func.outer)
                for param, arg in zip(func.params, args):
                    v = ns.intern(param)
                    v.root = arg
            else:
                ns = current_ns
                return func(*args)


def expand(form, ns):
    if not isinstance(form, list.List):
        return form
    elif form[0] == QUOTE:
        return form
    elif form[0] == IF:
        return list.List(expand(f, ns) for f in form)
    elif form[0] == FN:
        params, body = form[1], form[2:]
        if not isinstance(params, vector.Vector):
            raise RuntimeError('Parameter declaration should be a vector')

        for x in params:
            if not isinstance(x, symbol.Symbol):
                raise RuntimeError('Unsupported binding form: {}'.format(x))

        if len(body) == 1:
            body = body[0]
        else:
            body = list.List([DO] + body)

        return list.List([FN, params, expand(body, ns)])
    elif form[0] == DEF:
        _, sym, val = form
        if not isinstance(sym, symbol.Symbol):
            raise RuntimeError('First argument to def must be a Symbol')
        return list.List([DEF, sym, expand(val, ns)])
    elif form[0] == DEFMACRO:
        body = None
        if len(form) == 3:
            _, sym, args = form
        elif len(form) == 4:
            _, sym, args, body = form
        else:
            # TODO: Better error.
            raise RuntimeError('Bad macro form')
        args = expand(args, ns)
        body = expand(body, ns)
        macros[sym] = eval(body, ns)
        return
    elif form[0] == LET:
        body = None
        if len(form) == 2:
            _, bindings = form
        elif len(form) == 3:
            _, bindings, body = form
        else:
            # TODO: Better error.
            raise RuntimeError('Bad let form')

        if len(bindings) % 2 != 0:
            err_fmt = ('let requires an even number of forms in binding '
                       'vector in {}')
            raise RuntimeError(err_fmt.format(ns))

        if not isinstance(bindings, vector.Vector):
            err_fmt = 'let requires a vector for its bindings in {}'
            raise RuntimeError(err_fmt.format(ns))

        for x in bindings[::2]:
            if not isinstance(x, symbol.Symbol):
                raise RuntimeError('Unsupported binding form: {}'.format(x))

        pairs = zip(bindings[::2], bindings[1::2])

        # Create a closure which contains the bindings defined by let.
        #
        # (let [x 42 y x] (print y)) -> ((fn [x] (fn [y] (print y)) x) 42)
        for i, (param, val) in enumerate(reversed(pairs)):
            param = vector.Vector([param])
            if i == 0:
                # Body may be empty.
                if body is not None:
                    body = list.List(expand(f, ns) for f in body)

                closure = list.List([FN, param, body])
                let = list.List([closure]) + list.List([expand(val, ns)])
                continue

            closure = list.List([FN, param, let])
            let = list.List([closure]) + list.List([expand(val, ns)])
        return expand(let, ns)
    elif form[0] == DO:
        if len(form) > 1:
            return list.List(expand(f, ns) for f in form)
        return
    elif form[0] == SYNTAX_QUOTE:
        return expand_syntax_quote(form)
    elif isinstance(form[0], symbol.Symbol) and form[0] in macros:
        macro = macros[form[0]]
        return expand(macro(*form[1:]), ns)

    return list.List(expand(f, ns) for f in form)


def expand_syntax_quote(form):
    pass
