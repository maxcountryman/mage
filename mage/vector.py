class Vector(list):
    def __str__(self):
        return '[' + ' '.join(map(str, self)) + ']'
