import unittest
from unittest.mock import patch

from scripts import cloud_acceptance as acceptance
from src import moodle_cloud as cli


class CloudAcceptanceGuardsTests(unittest.TestCase):
    def setUp(self):
        self.config = str(cli.ROOT / "config/sydney.yaml")

    def test_bad_confirmation_does_not_call_aws(self):
        with patch.object(cli, "aws") as api:
            self.assertEqual(acceptance.main(["--config", self.config, "--expected-account", "111111111111",
                                             "--confirm", "wrong", "--seed"]), 2)
        api.assert_not_called()

    def test_wrong_account_does_not_submit_a_command(self):
        with patch.object(cli, "aws", return_value={"Account": "222222222222"}) as api:
            self.assertEqual(acceptance.main(["--config", self.config, "--expected-account", "111111111111",
                                             "--confirm", "moodle-sydney-dev", "--seed"]), 2)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(api.call_args.args[1:], ("sts", "get-caller-identity"))

    def test_restored_fixture_cannot_be_read_from_an_unrelated_bucket(self):
        config = cli.load_config(self.config)
        with self.assertRaises(cli.ConfigError):
            acceptance.command_script(config, fixture_uri="s3://unrelated/moodle-sydney-dev/acceptance-fixture.json")


if __name__ == "__main__":
    unittest.main()
