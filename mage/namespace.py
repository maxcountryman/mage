from __future__ import print_function

import operator

import mage.list as list
import mage.symbol as symbol
import mage.var as var


def successive_comp(xs, comparator):
    bs = []
    for i, x in enumerate(xs):
        if len(xs) > i + 1:
            y = xs[i + 1]
            bs.append(comparator(x, y))
        else:
            bs.append(comparator(xs[i - 1], x))
    return all(b for b in bs)


# Builtins.
ADD = var.Var(symbol.Symbol('+'))
ADD.root = lambda *xs: reduce(operator.add, xs)

SUB = var.Var(symbol.Symbol('-'))
SUB.root = lambda *xs: reduce(operator.sub, xs)

MUL = var.Var(symbol.Symbol('*'))
MUL.root = lambda *xs: reduce(operator.mul, xs)

DIV = var.Var(symbol.Symbol('/'))
DIV.root = lambda *xs: reduce(operator.div, xs)

EQ = var.Var(symbol.Symbol('='))
EQ.root = lambda *xs: xs.count(xs[0]) == len(xs)

NEQ = var.Var(symbol.Symbol('not='))
NEQ.root = lambda *xs: xs.count(xs[0]) != len(xs)

LT = var.Var(symbol.Symbol('<'))
LT.root = lambda *xs: successive_comp(xs, operator.lt)

GT = var.Var(symbol.Symbol('>'))
GT.root = lambda *xs: successive_comp(xs, operator.gt)

LE = var.Var(symbol.Symbol('<='))
LE.root = lambda *xs: successive_comp(xs, operator.le)

GE = var.Var(symbol.Symbol('>='))
GE.root = lambda *xs: successive_comp(xs, operator.ge)

MOD = var.Var(symbol.Symbol('mod'))
MOD.root = lambda a, b: a % b

ZEROQ = var.Var(symbol.Symbol('zero?'))
ZEROQ.root = lambda x: x == 0

LIST = var.Var(symbol.Symbol('list'))
LIST.root = lambda *xs: list.List(xs)

LISTQ = var.Var(symbol.Symbol('list?'))
LISTQ.root = lambda x: isinstance(x, list.List)

MAP = var.Var(symbol.Symbol('map'))
MAP.root = map

FILTER = var.Var(symbol.Symbol('filter'))
FILTER.root = filter

REDUCE = var.Var(symbol.Symbol('reduce'))
REDUCE.root = reduce

RANGE = var.Var(symbol.Symbol('range'))
RANGE.root = range


def print_xs(*xs):
    for x in xs:
        print(x)


PRINT = var.Var(symbol.Symbol('print'))
PRINT.root = print_xs

BUILTINS = {ADD.sym: ADD,
            SUB.sym: SUB,
            MUL.sym: MUL,
            DIV.sym: DIV,
            EQ.sym: EQ,
            NEQ.sym: NEQ,
            LT.sym: LT,
            GT.sym: GT,
            LE.sym: LE,
            GE.sym: GE,
            MOD.sym: MOD,
            ZEROQ.sym: ZEROQ,
            LIST.sym: LIST,
            LISTQ.sym: LISTQ,
            MAP.sym: MAP,
            FILTER.sym: FILTER,
            REDUCE.sym: REDUCE,
            RANGE.sym: RANGE,
            PRINT.sym: PRINT}

namespaces = {}


class Namespace(object):
    def __init__(self, name):
        assert isinstance(name, symbol.Symbol)
        self.name = name
        self._mappings = BUILTINS.copy()
        self._aliases = {}

        if name not in namespaces:
            namespaces[name] = self

    def __str__(self):
        return str(self.name)

    def intern(self, sym):
        assert isinstance(sym, symbol.Symbol)
        import mage.var as var

        if sym.ns is not None:
            raise ValueError('Can\'t intern namespace-qualified symbol')

        v = self._mappings.get(sym)
        if isinstance(v, var.Var) and v.ns == self:
            return v

        if v is None:
            v = var.Var(sym, self)
            self._mappings[sym] = v
            v.ns = self

        return v

    def find_interned_var(self, sym):
        assert isinstance(sym, symbol.Symbol)
        return self._mappings.get(sym)

    def reference(self, sym, val):
        assert isinstance(sym, symbol.Symbol)

        if sym.ns is not None:
            raise ValueError('Can\'t intern namespace-qualified symbol')

        v = self._mappings.get(sym)
        if v == val:
            return v

        self._mappings[sym] = val

        return val

    def refer(self, sym, var):
        assert isinstance(sym, symbol.Symbol)
        assert isinstance(var, var.Var)
        return var.Var(self.reference(sym, var))

    def lookup_alias(self, alias):
        assert isinstance(alias, symbol.Symbol)
        return self._aliases.get(alias)

    def add_alias(self, alias, ns):
        assert isinstance(alias, symbol.Symbol)
        assert isinstance(ns, Namespace)

        if alias not in self._aliases:
            self._aliases[alias] = ns

    @staticmethod
    def find(name):
        assert isinstance(name, symbol.Symbol)
        return namespaces.get(name)

    @staticmethod
    def find_or_create(name):
        assert isinstance(name, symbol.Symbol)
        ns = namespaces.get(name)
        if ns is not None:
            return ns

        ns = Namespace(name)
        namespaces[name] = ns
        return ns
