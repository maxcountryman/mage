class List(list):
    def __str__(self):
        return '(' + ' '.join(map(str, self)) + ')'

    def __add__(self, other):
        # TODO: Fix O(N).
        for x in other:
            self.append(x)

        return self
