class HashMap(dict):
    def __str__(self):
        kv_str = ', '.join(str(k) + ' ' + str(v) for k, v in self.items())
        return '{' + kv_str + '}'
