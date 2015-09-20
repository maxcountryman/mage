import atexit
import readline
import os
import traceback

import mage.reader as reader
import mage.symbol as symbol
import mage.namespace as namespace


def unbalanced(line):
    parens = {'(', '{', '['}
    matches = {')': '(', '}': '{', ']': '['}
    stack = []

    for c in line:
        if c in parens:
            stack.append(c)

        if c in matches:
            if not stack:
                raise RuntimeError('Unmatched delimiter: ' + c)

            if not stack[-1] == matches.get(c):
                raise RuntimeError('Unmatched delimiter: ' + c)

            stack.pop()

    return bool(stack)


class Completer(object):
    def __init__(self, ns):
        self.prefix = None
        self.match_symbols = []
        self.ns = ns

    def complete(self, prefix, index):
        if prefix != self.prefix:
            symbols = self.ns._mappings.items()
            self.matching_symbols = \
                [s.name for s, v in symbols if s.name.startswith(prefix)]
            self.prefix = prefix

        try:
            return self.matching_symbols[index]
        except IndexError:
            return


if __name__ == '__main__':
    history = os.path.join(os.path.expanduser('~'), '.mage_history')
    if not os.path.isfile(history):
        with open(history, 'a'):
            os.utime(history, None)

        os.chmod(history, int('640', 8))

    try:
        readline.read_history_file(history)
    except IOError:
        pass

    atexit.register(readline.write_history_file, history)

    repl_ns = namespace.Namespace(symbol.Symbol('user'))

    completer = Completer(repl_ns)
    readline.parse_and_bind('tab: complete')
    readline.set_completer(completer.complete)

    # Version message.
    print 'Mage 0.0.1\n'

    while True:
        try:
            line = raw_input(str(repl_ns) + '=> ')

            if line in ('exit', 'quit'):
                print 'Bye for now!'
                break

            while unbalanced(line):
                line += '\n' + raw_input(' ' * len(str(repl_ns)) + '.. ')

            # Evaluation involves three steps:
            #
            #   1. Tokenize a string.
            #   2. Expand tokens. (Macro expansion, error checking.)
            #   3. Eval expanded tokens.
            parsed = reader.read_string(line)
            expanded = reader.expand(parsed, repl_ns)
            evaled = reader.eval(expanded, repl_ns)
            if evaled is None:
                print 'nil'
            else:
                print evaled
        except KeyboardInterrupt:
            print '\n'
        except Exception:
            traceback.print_exc()
