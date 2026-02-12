import os


def test_readme_mentions_type_hints():
    """README should document type hint support."""
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(readme_path, encoding='utf-8') as f:
        content = f.read()

    assert "type" in content.lower() or "typing" in content.lower()


def test_readme_mentions_status_enums():
    """README should document Status enums."""
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(readme_path, encoding='utf-8') as f:
        content = f.read()

    assert "MessageStatus" in content or "Status" in content


def test_readme_mentions_py_typed():
    """README should mention py.typed marker."""
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(readme_path, encoding='utf-8') as f:
        content = f.read()

    assert "py.typed" in content
