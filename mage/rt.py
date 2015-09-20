import mage.namespace as namespace
import mage.symbol as symbol

MAGE_NS = namespace.Namespace.find_or_create(symbol.Symbol('mage.core'))


def bool_cast(x):
    if isinstance(x, bool):
        return x

    return x is None
