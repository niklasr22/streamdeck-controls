import math


def binary(liste, l, r, s):
    comp = 0
    while r - l > 1:
        mid = math.ceil(l + (r - l) / 2)
        x = liste[mid]
        if s < x:
            r = mid
        else:
            l = mid
        comp += 1
    return l, comp


x = [1, 4, 7, 8, 10, 13, 15]
print(binary(x, 0, len(x), 1), math.ceil(math.log2(len(x) + 1)))
