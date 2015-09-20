class Symbol(object):
    def __init__(self, name, ns=None):
        if ns is not None:
            assert isinstance(ns, str)

        self.name = name
        self.ns = ns

    def __str__(self):
        if self.ns is None:
            return str(self.name)

        return self.ns + '/' + self.name

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False

        return self.ns is other.ns and self.name == other.name

    def __hash__(self):
        return hash(self.ns) ^ hash(self.name)

    @staticmethod
    def intern(name, ns=None):
        if ns is not None:
            assert isinstance(ns, str)

        if ns is None:
            if isinstance(name, Symbol):
                return name

            index = name.find('/')
            if index == -1 or name == '/':
                return Symbol(name)

            ns, name = name.split('/', 1)

        return Symbol(name, ns)
