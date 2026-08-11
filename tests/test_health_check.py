from bot.utils import health_check


def test_check_bot_process_accepts_running_bot_main(tmp_path):
    cmdline = tmp_path / "1" / "cmdline"
    cmdline.parent.mkdir()
    cmdline.write_bytes(b"python\x00bot/main.py\x00")

    assert health_check.check_bot_process(proc_root=str(tmp_path)) == (
        True,
        "Процесс бота запущен",
    )


def test_check_bot_process_rejects_non_bot_pid_one(tmp_path):
    cmdline = tmp_path / "1" / "cmdline"
    cmdline.parent.mkdir()
    cmdline.write_bytes(b"sleep\x00infinity\x00")

    assert health_check.check_bot_process(proc_root=str(tmp_path)) == (
        False,
        "PID 1 не является процессом бота",
    )
