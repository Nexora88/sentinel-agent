import base64, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from core.safety.sovereignty import sovereignty_status
from core.media.generation_bridge import GenerationBridge
from core.media.engine import MediaEngine, MediaEngineError
from core.approval_protocol import SignedApprovalProtocol, ApprovalProtocolError
from core.personal_memory import PersonalMemory

class SovereigntyTests(unittest.TestCase):
    def test_never_claims_fully_sovereign_from_environment_only(self):
        with patch.dict("os.environ", {"VERCEL":"1"}, clear=True):
            state=sovereignty_status()
        self.assertFalse(state["fully_sovereign"])
        self.assertEqual(state["state"], "cloud_detected")
    def test_no_cloud_signal_is_still_unverified(self):
        with patch.dict("os.environ", {}, clear=True):
            state=sovereignty_status()
        self.assertFalse(state["air_gapped_verified"])

class MediaEngineTests(unittest.TestCase):
    def test_unknown_operation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            engine=MediaEngine(GenerationBridge(), state_path=str(Path(d)/"jobs.json"))
            with self.assertRaises(MediaEngineError): engine.submit("remote_api", {})
    def test_bridge_has_no_fallback(self):
        bridge=GenerationBridge()
        with self.assertRaisesRegex(RuntimeError, "dış servise gönderilmedi"):
            bridge.execute("generate", {"prompt":"test"})
    def test_queue_does_not_store_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            engine=MediaEngine(GenerationBridge(), state_path=str(Path(d)/"jobs.json"))
            with self.assertRaises(MediaEngineError): engine.submit("edit", {"image":b"secret"})


    def test_vision_adapter_is_disabled_without_explicit_model(self):
        from core.media.generation_bridge import LocalVisionAdapter
        adapter = LocalVisionAdapter(base_url="http://127.0.0.1:11434", model="")
        caps = adapter.capabilities()
        self.assertFalse(caps["enabled"])
        self.assertEqual(caps["operations"], [])

    def test_vision_adapter_rejects_public_endpoint(self):
        from core.media.generation_bridge import LocalVisionAdapter
        adapter = LocalVisionAdapter(base_url="https://example.com", model="llava")
        self.assertFalse(adapter.capabilities()["enabled"])

    def test_image_generator_capabilities_do_not_claim_unconfigured_backend(self):
        from core.media.generation_bridge import ImageGeneratorAdapter
        from tools.image_gen import ImageGenerator
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ", {"SD_API_URL": ""}):
            caps = ImageGeneratorAdapter(ImageGenerator(d)).capabilities()
        self.assertFalse(caps["enabled"])
        self.assertEqual(caps["operations"], [])

class ForgetMemoryTests(unittest.TestCase):
    def test_topic_must_be_specific_enough(self):
        instance=PersonalMemory.__new__(PersonalMemory)
        with self.assertRaisesRegex(ValueError, "en az 3 karakter"):
            instance.forget_matching("ab", 24)

class SignedApprovalTests(unittest.TestCase):
    def test_valid_signature_is_audited_and_replay_is_rejected(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        key=Ed25519PrivateKey.generate()
        public=key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        public_b64=base64.b64encode(public).decode()
        payload={"request_id":"request-once","action":"review"}
        signature=base64.b64encode(key.sign(SignedApprovalProtocol.canonical_payload(payload))).decode()
        with tempfile.TemporaryDirectory() as d:
            protocol=SignedApprovalProtocol(str(Path(d)/"audit.jsonl"), public_key_b64=public_b64)
            self.assertTrue(protocol.verify(payload, signature)["valid"])
            with self.assertRaisesRegex(ApprovalProtocolError, "replay engellendi"):
                protocol.verify(payload, signature)

    def test_missing_public_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            protocol=SignedApprovalProtocol(str(Path(d)/"audit.jsonl"), public_key_b64="")
            with self.assertRaises(ApprovalProtocolError):
                protocol.verify({"request_id":"r1","action":"git_push"}, "AA==")
    def test_payload_canonicalization_stable(self):
        one={"request_id":"r1","action":"review","n":1}
        two={"n":1,"action":"review","request_id":"r1"}
        self.assertEqual(SignedApprovalProtocol.canonical_payload(one), SignedApprovalProtocol.canonical_payload(two))

if __name__=="__main__": unittest.main()
