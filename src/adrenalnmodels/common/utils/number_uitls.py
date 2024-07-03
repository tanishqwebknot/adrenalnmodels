from random import randint


def random_n_digit(n):
    try:
        random_number = ''.join(["%s" % randint(0, 9) for num in range(0, n)])
        return random_number
    except Exception as err:
        return None