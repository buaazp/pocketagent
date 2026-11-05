from pocketagent.core.bilingual import clean_reply, strip_ansi


def test_plain_english_is_untouched():
    text = "Hello.\n\n```py\nx = 1\n```"
    assert clean_reply(text) == text


def test_strips_ansi_codes():
    assert strip_ansi("\x1b[90mgray\x1b[39m \x1b]8;;http://x\x07link\x1b]8;;\x07") == "gray link"


def test_colored_translation_becomes_quote():
    text = "Cats sleep a lot.\n\x1b[90m猫睡得很多。\x1b[39m"
    assert clean_reply(text) == "Cats sleep a lot.\n> 猫睡得很多。"


def test_uncolored_cjk_line_after_english_becomes_quote():
    assert clean_reply("Run it first.\n首先运行它。") == "Run it first.\n> 首先运行它。"


def test_translated_list_item_quote_drops_indent():
    assert clean_reply("- Run `pip`\n  运行 `pip`") == "- Run `pip`\n> 运行 `pip`"


def test_heading_translation_is_split_out():
    assert clean_reply("## Setup / 设置") == "## Setup\n> 设置"


def test_all_chinese_reply_is_not_quoted():
    text = "你好！\n今天做什么？"
    assert clean_reply(text) == text


def test_code_fences_and_tables_are_left_alone():
    text = "Example:\n```\nprint('x')\n打印\n```\n| a |\n|---|\n| 中 |"
    assert clean_reply(text) == text


def test_translation_next_to_real_quote_stays_separate():
    text = "Done.\n完成。\n> [!NOTE]\n> hi"
    assert clean_reply(text) == "Done.\n> 完成。\n\n> [!NOTE]\n> hi"
