import unittest
from pathlib import Path
import yaml


class KubernetesManifestTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("deploy/kubernetes")

    def test_all_manifests_parse_as_yaml(self):
        for path in self.root.glob("*.yaml"):
            with self.subTest(path=str(path)):
                documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
                self.assertTrue(documents)
                self.assertTrue(all(isinstance(doc, dict) for doc in documents))

    def test_deployment_uses_restricted_security_context_and_internal_service(self):
        docs = list(yaml.safe_load_all((self.root / "deployment.yaml").read_text(encoding="utf-8")))
        deployment = next(doc for doc in docs if doc.get("kind") == "Deployment")
        pod = deployment["spec"]["template"]["spec"]
        container = pod["containers"][0]
        self.assertTrue(pod["automountServiceAccountToken"] is False)
        self.assertTrue(pod["securityContext"]["runAsNonRoot"])
        self.assertEqual(container["securityContext"]["capabilities"]["drop"], ["ALL"])
        self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
        self.assertEqual(container["imagePullPolicy"], "IfNotPresent")

        service = yaml.safe_load((self.root / "service.yaml").read_text(encoding="utf-8"))
        self.assertEqual(service["spec"]["type"], "ClusterIP")

    def test_network_policy_denies_unlisted_egress_by_default(self):
        policy = yaml.safe_load((self.root / "network-policy.yaml").read_text(encoding="utf-8"))
        self.assertEqual(set(policy["spec"]["policyTypes"]), {"Ingress", "Egress"})
        self.assertTrue(policy["spec"]["egress"])
        self.assertTrue(policy["spec"]["ingress"])


if __name__ == "__main__":
    unittest.main()
