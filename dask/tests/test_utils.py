import functools
import operator
import pickle

import numpy as np
import pytest

from dask.sharedict import ShareDict
from dask.utils import (takes_multiple_arguments, Dispatch, random_state_data,
                        memory_repr, methodcaller, M, skip_doctest,
                        SerializableLock, funcname, ndeepmap, ensure_dict,
                        extra_titles, asciitable, itemgetter, partial_by_order,
                        Interval,
                        )
from dask.utils_test import inc


def test_takes_multiple_arguments():
    assert takes_multiple_arguments(map)
    assert not takes_multiple_arguments(sum)

    def multi(a, b, c):
        return a, b, c

    class Singular(object):
        def __init__(self, a):
            pass

    class Multi(object):
        def __init__(self, a, b):
            pass

    assert takes_multiple_arguments(multi)
    assert not takes_multiple_arguments(Singular)
    assert takes_multiple_arguments(Multi)

    def f():
        pass

    assert not takes_multiple_arguments(f)

    def vararg(*args):
        pass

    assert takes_multiple_arguments(vararg)
    assert not takes_multiple_arguments(vararg, varargs=False)


def test_dispatch():
    foo = Dispatch()
    foo.register(int, lambda a: a + 1)
    foo.register(float, lambda a: a - 1)
    foo.register(tuple, lambda a: tuple(foo(i) for i in a))
    foo.register(object, lambda a: a)

    class Bar(object):
        pass
    b = Bar()
    assert foo(1) == 2
    assert foo.dispatch(int)(1) == 2
    assert foo(1.0) == 0.0
    assert foo(b) == b
    assert foo((1, 2.0, b)) == (2, 1.0, b)


def test_dispatch_lazy():
    # this tests the recursive component of dispatch
    foo = Dispatch()
    foo.register(int, lambda a: a)

    import decimal

    # keep it outside lazy dec for test
    def foo_dec(a):
        return a + 1

    @foo.register_lazy("decimal")
    def register_decimal():
        import decimal
        foo.register(decimal.Decimal, foo_dec)

    # This test needs to be *before* any other calls
    assert foo.dispatch(decimal.Decimal) == foo_dec
    assert foo(decimal.Decimal(1)) == decimal.Decimal(2)
    assert foo(1) == 1


def test_random_state_data():
    seed = 37
    state = np.random.RandomState(seed)
    n = 10000

    # Use an integer
    states = random_state_data(n, seed)
    assert len(states) == n

    # Use RandomState object
    states2 = random_state_data(n, state)
    for s1, s2 in zip(states, states2):
        assert s1.shape == (624,)
        assert (s1 == s2).all()

    # Consistent ordering
    states = random_state_data(10, 1234)
    states2 = random_state_data(20, 1234)[:10]

    for s1, s2 in zip(states, states2):
        assert (s1 == s2).all()


def test_memory_repr():
    for power, mem_repr in enumerate(['1.0 bytes', '1.0 KB', '1.0 MB', '1.0 GB']):
        assert memory_repr(1024 ** power) == mem_repr


def test_method_caller():
    a = [1, 2, 3, 3, 3]
    f = methodcaller('count')
    assert f(a, 3) == a.count(3)
    assert methodcaller('count') is f
    assert M.count is f
    assert pickle.loads(pickle.dumps(f)) is f
    assert 'count' in dir(M)

    assert 'count' in str(methodcaller('count'))
    assert 'count' in repr(methodcaller('count'))


def test_skip_doctest():
    example = """>>> xxx
>>>
>>> # comment
>>> xxx"""

    res = skip_doctest(example)
    assert res == """>>> xxx  # doctest: +SKIP
>>>
>>> # comment
>>> xxx  # doctest: +SKIP"""

    assert skip_doctest(None) == ''


def test_extra_titles():
    example = """

    Notes
    -----
    hello

    Foo
    ---

    Notes
    -----
    bar
    """

    expected = """

    Notes
    -----
    hello

    Foo
    ---

    Extra Notes
    -----------
    bar
    """

    assert extra_titles(example) == expected


def test_asciitable():
    res = asciitable(['fruit', 'color'],
                     [('apple', 'red'),
                      ('banana', 'yellow'),
                      ('tomato', 'red'),
                      ('pear', 'green')])
    assert res == ('+--------+--------+\n'
                   '| fruit  | color  |\n'
                   '+--------+--------+\n'
                   '| apple  | red    |\n'
                   '| banana | yellow |\n'
                   '| tomato | red    |\n'
                   '| pear   | green  |\n'
                   '+--------+--------+')


def test_SerializableLock():
    a = SerializableLock()
    b = SerializableLock()
    with a:
        pass

    with a:
        with b:
            pass

    with a:
        assert not a.acquire(False)

    a2 = pickle.loads(pickle.dumps(a))
    a3 = pickle.loads(pickle.dumps(a))
    a4 = pickle.loads(pickle.dumps(a2))

    for x in [a, a2, a3, a4]:
        for y in [a, a2, a3, a4]:
            with x:
                assert not y.acquire(False)

    b2 = pickle.loads(pickle.dumps(b))
    b3 = pickle.loads(pickle.dumps(b2))

    for x in [a, a2, a3, a4]:
        for y in [b, b2, b3]:
            with x:
                with y:
                    pass
            with y:
                with x:
                    pass


def test_SerializableLock_name_collision():
    a = SerializableLock('a')
    b = SerializableLock('b')
    c = SerializableLock('a')
    d = SerializableLock()

    assert a.lock is not b.lock
    assert a.lock is c.lock
    assert d.lock not in (a.lock, b.lock, c.lock)


def test_funcname():
    def foo(a, b, c):
        pass

    assert funcname(foo) == 'foo'
    assert funcname(functools.partial(foo, a=1)) == 'foo'
    assert funcname(M.sum) == 'sum'
    assert funcname(lambda: 1) == 'lambda'

    class Foo(object):
        pass

    assert funcname(Foo) == 'Foo'
    assert 'Foo' in funcname(Foo())


def test_funcname_toolz():
    toolz = pytest.importorskip('toolz')

    @toolz.curry
    def foo(a, b, c):
        pass

    assert funcname(foo) == 'foo'
    assert funcname(foo(1)) == 'foo'


def test_funcname_multipledispatch():
    md = pytest.importorskip('multipledispatch')

    @md.dispatch(int, int, int)
    def foo(a, b, c):
        pass

    assert funcname(foo) == 'foo'
    assert funcname(functools.partial(foo, a=1)) == 'foo'


def test_ndeepmap():
    L = 1
    assert ndeepmap(0, inc, L) == 2

    L = [1]
    assert ndeepmap(0, inc, L) == 2

    L = [1, 2, 3]
    assert ndeepmap(1, inc, L) == [2, 3, 4]

    L = [[1, 2], [3, 4]]
    assert ndeepmap(2, inc, L) == [[2, 3], [4, 5]]

    L = [[[1, 2], [3, 4, 5]], [[6], []]]
    assert ndeepmap(3, inc, L) == [[[2, 3], [4, 5, 6]], [[7], []]]


def test_ensure_dict():
    d = {'x': 1}
    assert ensure_dict(d) is d
    sd = ShareDict()
    sd.update(d)
    assert type(ensure_dict(sd)) is dict
    assert ensure_dict(sd) == d

    class mydict(dict):
        pass

    md = mydict()
    md['x'] = 1
    assert type(ensure_dict(md)) is dict
    assert ensure_dict(md) == d


def test_itemgetter():
    data = [1, 2, 3]
    g = itemgetter(1)
    assert g(data) == 2
    g2 = pickle.loads(pickle.dumps(g))
    assert g2(data) == 2
    assert g2.index == 1


def test_partial_by_order():
    assert partial_by_order(5, function=operator.add, other=[(1, 20)]) == 25


def test_intervals():
    inc = Interval.inclusive(5, 10)
    ex = Interval.exclusive(5, 10)
    base_tests = [
        (4, False),
        (5, True),
        (7, True),
        (15, False),
    ]
    for test, expected in base_tests + [(10, True)]:
        assert (test in inc) is expected

    for test, expected in base_tests + [(10, False)]:
        assert (test in ex) is expected

    assert not inc.strict_lt(ex)

    assert not Interval.inclusive(5, 10).strict_lt(Interval.inclusive(10, 15))
    assert Interval.exclusive(5, 10).strict_lt(Interval.inclusive(10, 15))

    # Range containment tests
    assert Interval.inclusive(5, 10) in Interval.inclusive(0, 10)
    assert Interval.exclusive(5, 10) in Interval.inclusive(5, 10)
    assert Interval.exclusive(5, 10) in Interval.exclusive(0, 10)
    assert not Interval.inclusive(5, 10) in Interval.exclusive(5, 10)

    assert not Interval.inclusive(5, 10) in Interval.exclusive(0, 10)

    assert not Interval.inclusive(0, 10) in Interval.inclusive(3, 7)

    # Logic tests
    assert not (inc & ex).closed
    assert (Interval(5, 10, 1) & Interval(7, 11, 0)) == Interval.inclusive(7, 10)
    assert (Interval(5, 10, 0) & Interval(7, 11, 1)) == Interval.exclusive(7, 10)
    assert (Interval(5, 10, 1) & Interval(7, 9, 0)) == Interval.exclusive(7, 9)
    assert not (Interval.inclusive(5, 10) & Interval.inclusive(10, 11)).empty()
    assert (Interval.exclusive(5, 10) & Interval.inclusive(10, 11)).empty()
    assert 10 in (Interval.inclusive(5, 10) & Interval.inclusive(10, 11))
    assert (Interval.inclusive(5, 10) & Interval.inclusive(20, 30)).empty()

    assert Interval.inclusive(5, 10).overlaps(Interval.inclusive(7, 10))
    assert Interval.inclusive(5, 10).overlaps(Interval.inclusive(10, 10))
    assert not Interval.exclusive(5, 10).overlaps(Interval.inclusive(10, 10))
    assert not Interval.exclusive(5, 10).overlaps(Interval.inclusive(12, 12))

    # Comparison tests
    assert Interval.exclusive(0, 1) < Interval.inclusive(0, 1)
    assert Interval.inclusive(0, 1) < Interval.exclusive(0, 2)
    expected_order = [
        Interval.exclusive(5, 10),
        Interval.exclusive(7, 15),
        9,
        Interval.exclusive(10, 20),
        Interval.inclusive(10, 20),
        Interval.exclusive(12, 15),
    ]
    s = list(sorted(reversed(expected_order)))
    assert expected_order == s

    # Splitting
    assert (Interval.exclusive(0, 5).split(3)) == (Interval.exclusive(0, 3), Interval.exclusive(3, 5))
    assert (Interval.inclusive(0, 5).split(3)) == (Interval.exclusive(0, 3), Interval.inclusive(3, 5), )
    assert (Interval.exclusive(0, 5).split(0)) == (Interval.exclusive(0, 5), )
    assert (Interval.inclusive(0, 5).split(5)) == (Interval.inclusive(0, 5), )

    for interval, split in [(Interval.inclusive(0, 1), -1), (Interval.exclusive(0, 1), 1)]:
        with pytest.raises(ValueError):
            interval.split(split)
