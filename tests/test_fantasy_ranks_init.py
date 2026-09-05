from fantasy_ranks import main


def test_fantasy_ranks_main(capsys):
    main()
    captured = capsys.readouterr()
    assert 'Hello from fantasy-ranks!' in captured.out
