use mkaos_inference::reasoning::{reason, ReasoningError};
#[test]
fn rule_inference_is_deterministic() {
    let prompt = "A ise B. A";
    assert_eq!(reason(prompt).unwrap(), reason(prompt).unwrap());
    assert_eq!(reason(prompt).unwrap().answer, "Çıkarım: b.");
}
#[test]
fn empty_prompt_is_an_error() { assert_eq!(reason("").unwrap_err(), ReasoningError::EmptyInput); }
