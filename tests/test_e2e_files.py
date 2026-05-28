from any2md.pipeline import convert


def test_convert_csv_writes_markdown(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("name,role\nAda,pioneer\n")
    out = tmp_path / "vault"

    path = convert(str(csv), out, provider="none")

    assert path.exists()
    assert path.name == "data.md"
    text = path.read_text()
    assert text.startswith("---\n")
    assert "source_type: csv" in text
    assert "| name | role |" in text  # body extracted, non-empty
