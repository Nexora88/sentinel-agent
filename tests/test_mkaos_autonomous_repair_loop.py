import unittest

from tools.mkaos_autonomous_repair_loop import parse_agent_command, safe_agent_env


class AutonomousRepairLoopContractTests(unittest.TestCase):
    def test_requires_explicit_workspace_and_prompt_placeholders(self):
        with self.assertRaises(ValueError):
            parse_agent_command('["local-agent", "--workspace", "here"]')

    def test_rejects_shell_metacharacters(self):
        with self.assertRaises(ValueError):
            parse_agent_command('["local-agent", "--workspace={workspace}", "--prompt={prompt_file}; echo bad"]')

    def test_accepts_literal_argv_only(self):
        command = parse_agent_command('["local-agent", "--workspace", "{workspace}", "--prompt-file", "{prompt_file}"]')
        self.assertEqual(command[0], "local-agent")

    def test_agent_environment_excludes_credentials(self):
        env = safe_agent_env()
        self.assertFalse(any("TOKEN" in key.upper() or "SECRET" in key.upper() or "PASSWORD" in key.upper()
                             for key in env))
        self.assertEqual(env["MKAOS_NETWORK_ACCESS"], "disabled-by-policy")


if __name__ == "__main__":
    unittest.main()
