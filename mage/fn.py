import mage.symbol as symbol
import mage.var as var


class Closure(object):
    def __init__(self, name, outer):
        self.name = name
        self.outer = outer
        self._mappings = {}

    def intern(self, sym):
        assert isinstance(sym, symbol.Symbol)

        v = self._mappings.get(sym)
        if isinstance(v, var.Var):
            return v

        if v is None:
            v = var.Var(sym, self)
            self._mappings[sym] = v

        return v

    def find_interned_var(self, sym):
        assert isinstance(sym, symbol.Symbol)

        v = self._mappings.get(sym)
        if v is None and self.outer is not None:
            return self.outer.find_interned_var(sym)

        return v


class Fn(object):
    def __init__(self, params, body, outer):
        self.params = params
        self.body = body
        self.outer = outer

    def __call__(self, *args):
        import mage.reader as reader  # Avoid circular imports.

        expected_params = len(self.params)
        received_args = len(args)
        if expected_params != received_args:
            err_fmt = 'fn takes exactly {} arguments ({} given)'
            raise TypeError(err_fmt.format(expected_params, received_args))

        fn_scope_sym = symbol.Symbol('fn__' + str(id(self)))
        closure = Closure(fn_scope_sym, outer=self.outer)
        for param, arg in zip(self.params, args):
            v = closure.intern(param)
            v.root = arg

        return reader.eval(self.body, closure)
