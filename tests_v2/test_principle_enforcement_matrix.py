from __future__ import annotations

import unittest
from pathlib import Path


class PrincipleEnforcementMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]
        self.matrix = self.repo / "docs" / "HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md"

    def matrix_rows(self) -> list[list[str]]:
        text = self.matrix.read_text(encoding="utf-8")
        rows: list[list[str]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            if "---" in stripped:
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and cells[0] == "Principle":
                continue
            rows.append(cells)
        return rows

    def test_matrix_exists(self) -> None:
        self.assertTrue(self.matrix.exists())

    def test_every_matrix_row_has_required_columns(self) -> None:
        rows = self.matrix_rows()
        self.assertGreaterEqual(len(rows), 8)

        for row in rows:
            self.assertEqual(4, len(row), row)
            principle, current_enforcement, tests_proving_it, missing_enforcement = row
            self.assertTrue(principle, row)
            self.assertTrue(current_enforcement, row)
            self.assertTrue(tests_proving_it, row)
            self.assertTrue(missing_enforcement, row)

    def test_no_matrix_row_uses_placeholder_values(self) -> None:
        placeholders = {"", "-", "tbd", "todo", "none", "n/a", "na"}
        for row in self.matrix_rows():
            for cell in row:
                normalized = cell.strip().lower()
                self.assertNotIn(normalized, placeholders, row)
                self.assertNotIn("tbd", normalized, row)


if __name__ == "__main__":
    unittest.main()
