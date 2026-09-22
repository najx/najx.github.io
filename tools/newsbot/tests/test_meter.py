from newsbot.meter import Meter


def test_a_meter_adds_prices_and_prints_one_line():
    m = Meter("Claude Haiku", usd_per_mtok_in=1.0, usd_per_mtok_out=5.0)
    m.add(1_000_000, 100_000)
    m.add(None, None)
    assert m.requests == 2 and m.input_tokens == 1_000_000 and m.output_tokens == 100_000
    assert m.cost_usd == 1.5
    assert m.summary() == "Claude Haiku: 2 requests, 1,000,000 tokens in, 100,000 out, $1.500"
    m.reset()
    assert m.requests == 0 and m.cost_usd == 0.0


def test_a_model_with_free_output_does_not_print_output_tokens():
    m = Meter("Jev", usd_per_mtok_in=0.042)
    m.add(2_000_000, 5)
    assert m.summary() == "Jev: 1 requests, 2,000,000 tokens in, $0.084"
