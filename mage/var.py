import mage.symbol as symbol


class Var(object):
    def __init__(self, sym=None, root=None, ns=None):
        if sym is not None:
            assert isinstance(sym, symbol.Symbol)

        self.sym = sym
        self.root = root
        self.ns = ns

    def __str__(self):
        if self.ns is not None:
            return '#\'' + str(self.ns) + '/' + str(self.sym)

        return '#\'' + str(self.sym)

    @staticmethod
    def intern(sym, root=None, ns=None):
        import mage.namespace as namespace

        assert isinstance(sym, symbol.Symbol)

        if isinstance(ns, symbol.Symbol):
            ns = namespace.Namespace.find_or_create(ns)

        if root is not None:
            v = ns.intern(sym)
            v.root = root
        return v

    @staticmethod
    def find(ns_qualified_sym):
        import mage.namespace as namespace

        assert isinstance(ns_qualified_sym, symbol.Symbol)
        if ns_qualified_sym.ns is None:
            raise ValueError('Symbol must be namespace-qualified')

        ns = namespace.Namespace.find(symbol.Symbol.intern(ns_qualified_sym.ns))
        if ns is None:
            raise ValueError('No such namespace: ' + ns_qualified_sym.ns)

        return ns.find_interned_var(symbol.Symbol.intern(ns_qualified_sym))
