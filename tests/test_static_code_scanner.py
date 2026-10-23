import json

from tools.static_code_scanner import StaticCodeScanner


def test_parse_json_preserves_evidence_and_location():
    payload = json.dumps({
        "results": [{
            "check_id": "python.lang.security.audit.eval-detected",
            "path": "src/app.py",
            "start": {"line": 12},
            "end": {"line": 12},
            "extra": {"severity": "ERROR", "message": "Avoid eval", "lines": "eval(user_input)"},
        }],
        "errors": [],
    })
    result = StaticCodeScanner.parse_json(payload)
    assert result["status"] == "completed"
    assert result["findings"] == [{
        "rule_id": "python.lang.security.audit.eval-detected",
        "severity": "ERROR",
        "message": "Avoid eval",
        "path": "src/app.py",
        "start_line": 12,
        "end_line": 12,
        "evidence": "eval(user_input)",
        "source": "semgrep",
    }]


def test_parse_json_handles_invalid_payload():
    result = StaticCodeScanner.parse_json("{not-json")
    assert result["status"] == "error"
    assert result["findings"] == []


def test_report_marks_findings_as_unverified():
    report = StaticCodeScanner.format_report({
        "status": "completed",
        "findings": [{
            "rule_id": "example.rule",
            "severity": "WARNING",
            "path": "app.py",
            "start_line": 4,
            "message": "Potential issue",
            "evidence": "dangerous_call()",
        }],
    })
    assert "app.py:4" in report
    assert "dangerous_call()" in report
    assert "does not apply fixes" in report
