import json
import tempfile
import unittest
from pathlib import Path

from src.validation.artifacts import ArtifactValidationError, validate_artifacts


class ArtifactValidationTests(unittest.TestCase):
    def test_repository_artifacts_pass_contract(self):
        validated = validate_artifacts()
        self.assertIn("comparacao_modelos", validated)

    def test_missing_artifacts_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ArtifactValidationError, "obrigatório ausente"):
                validate_artifacts(Path(directory))

    def test_invalid_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "risco_ola.json"
            target.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(ArtifactValidationError, "JSON inválido"):
                validate_artifacts(Path(directory))


if __name__ == "__main__":
    unittest.main()
