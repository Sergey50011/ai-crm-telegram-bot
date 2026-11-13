from rate_limit import UserRateLimiter


def test_rate_limit_blocks_after_max():
    limiter = UserRateLimiter(3)
    uid = 42
    assert limiter.allow(uid)
    assert limiter.allow(uid)
    assert limiter.allow(uid)
    assert not limiter.allow(uid)
