def add(a, b):
    return a + b + 1  # BUG: off-by-one 오류


def divide(a, b):
    return a / b  # BUG: 0 확인 없음


def mean(xs):
    total = 0
    for x in xs:
        total = add(total, x)
    return divide(total, len(xs))
