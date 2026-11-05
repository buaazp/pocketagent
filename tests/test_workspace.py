from pocketagent.core.workspace import WorkspaceManager, sanitize_folder_name


def test_sanitize_folder_name_basic():
    assert sanitize_folder_name("general") == "general"


def test_sanitize_folder_name_strips_unsafe_chars():
    assert sanitize_folder_name("support / bot!! #1") == "support-bot-1"


def test_sanitize_folder_name_empty_falls_back():
    assert sanitize_folder_name("   ") == "channel"


def test_sanitize_folder_name_keeps_unicode_letters():
    assert sanitize_folder_name("我的服务器-general") == "我的服务器-general"


def test_sanitize_folder_name_distinguishes_chinese_names():
    assert sanitize_folder_name("开发") != sanitize_folder_name("测试")


def test_sanitize_folder_name_neutralizes_path_traversal():
    assert sanitize_folder_name("../../etc/passwd") == "etc-passwd"


def test_sanitize_folder_name_is_idempotent():
    once = sanitize_folder_name("~/我的 server!")
    assert sanitize_folder_name(once) == once


def test_sanitize_folder_name_caps_length_in_bytes_on_a_character_boundary():
    safe = sanitize_folder_name("服" * 200)
    assert safe == "服" * 66
    assert len(safe.encode("utf-8")) <= 200


def test_resolve_dir_creates_longest_cjk_name_with_collision_suffix(tmp_path):
    manager = WorkspaceManager(tmp_path / "base")
    name = "服" * 100 + "-" + "道" * 100
    assert manager.resolve_dir("111", name).is_dir()
    assert manager.resolve_dir("222", name).name.endswith("-2")


def test_resolve_dir_creates_directory(tmp_path):
    manager = WorkspaceManager(tmp_path / "base")
    path = manager.resolve_dir("123", "general")
    assert path.is_dir()
    assert path == tmp_path / "base" / "general"


def test_resolve_dir_persists_binding_across_instances(tmp_path):
    base = tmp_path / "base"
    first = WorkspaceManager(base)
    path1 = first.resolve_dir("123", "general")

    second = WorkspaceManager(base)
    path2 = second.resolve_dir("123", "renamed-channel")

    assert path1 == path2


def test_resolve_dir_disambiguates_name_collision(tmp_path):
    manager = WorkspaceManager(tmp_path / "base")
    path1 = manager.resolve_dir("111", "general")
    path2 = manager.resolve_dir("222", "general")
    assert path1 != path2
    assert path2.name == "general-2"


def test_resolve_dir_falls_back_to_channel_key(tmp_path):
    manager = WorkspaceManager(tmp_path / "base")
    path = manager.resolve_dir("999", None)
    assert path.name == "999"


def test_resolve_dir_absolute_path_override_bypasses_base_dir(tmp_path):
    target = tmp_path / "elsewhere" / "project"
    manager = WorkspaceManager(tmp_path / "base")
    path = manager.resolve_dir("123", str(target))
    assert path == target
    assert path.is_dir()


def test_resolve_dir_expands_user_in_absolute_override(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    manager = WorkspaceManager(tmp_path / "base")
    path = manager.resolve_dir("123", "~/workspace/pocketagent")
    assert path == tmp_path / "workspace" / "pocketagent"
    assert path.is_dir()


def test_resolve_dir_absolute_override_persists_across_instances(tmp_path):
    target = tmp_path / "elsewhere" / "project"
    base = tmp_path / "base"
    first = WorkspaceManager(base)
    path1 = first.resolve_dir("123", str(target))

    second = WorkspaceManager(base)
    path2 = second.resolve_dir("123", "some-other-name")

    assert path1 == path2 == target
