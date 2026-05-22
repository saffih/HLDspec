from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RunSkepticTerminologyTests(unittest.TestCase):
    def test_agents_uses_runskeptic_as_formal_trigger(self) -> None:
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('RunSkeptic', text)
        self.assertIn('formal invocation string', text)
        self.assertIn('runtime source of truth', text)

    def test_terminology_defines_runskeptic(self) -> None:
        text = (ROOT / 'TERMINOLOGY.md').read_text(encoding='utf-8')
        self.assertIn('**RunSkeptic**', text)
        self.assertIn('Formal invocation string', text)

    def test_no_hldspec_authored_beskeptic_wording_in_core_docs(self) -> None:
        checked = [
            ROOT / 'AGENTS.md',
            ROOT / 'TERMINOLOGY.md',
            ROOT / 'docs' / 'CANONICAL_FLOW.md',
            ROOT / 'docs' / 'CONTEXT_TAILORING_PROTOCOL.md',
            ROOT / 'docs' / 'SPECKIT_PROXY_PROTOCOL.md',
        ]
        for path in checked:
            if not path.exists():
                continue
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('Beskeptic', text, msg=str(path))
            self.assertNotIn('beskeptic', text, msg=str(path))
            self.assertNotIn('Beskeptic', text, msg=str(path))
            self.assertNotIn('beskeptic', text, msg=str(path))


if __name__ == '__main__':
    unittest.main()
