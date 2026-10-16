//! Small, deterministic, fully local reasoning seed for MKAOS.
//! This is a symbolic rule engine, not a trained language model.
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReasoningResult { pub answer: String, pub trace: Vec<String> }

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReasoningError { EmptyInput }
impl fmt::Display for ReasoningError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self { Self::EmptyInput => write!(f, "girdi boş olamaz") }
    }
}
impl std::error::Error for ReasoningError {}

/// Processes a Turkish prompt locally using explicit rules and a tiny arithmetic evaluator.
pub fn reason(input: &str) -> Result<ReasoningResult, ReasoningError> {
    let prompt = input.trim();
    if prompt.is_empty() { return Err(ReasoningError::EmptyInput); }
    let lower = prompt.to_lowercase();

    if let Some(value) = arithmetic(&lower) {
        return Ok(ReasoningResult {
            answer: format!("Sonuç: {value}"),
            trace: vec!["İfade tek bir temel aritmetik işlemi içeriyor.".into(),
                        "İşlem yerel olarak hesaplandı; ağ veya harici model kullanılmadı.".into()],
        });
    }
    if ["merhaba", "selam", "iyi günler", "iyi akşamlar"].iter().any(|g| lower == *g || lower.starts_with(&format!("{g} "))) {
        return Ok(ReasoningResult {
            answer: "Merhaba! Ben MKAOS'un yerel akıl yürütme çekirdeğiyim. Şimdilik açık mantık kuralları ve temel aritmetik üzerinde çalışıyorum.".into(),
            trace: vec!["Selamlama kuralı eşleşti.".into()],
        });
    }
    if lower.contains("kimsin") || lower.contains("ne yapabilirsin") {
        return Ok(ReasoningResult {
            answer: "Ben MKAOS'un küçük, çevrimdışı başlangıç çekirdeğiyim. Önceden eğitilmiş ağırlık kullanmıyorum; açık kurallar üzerinden sınırlı çıkarım yapıyorum. Henüz genel amaçlı bir LLM değilim.".into(),
            trace: vec!["Sistem kimliği kuralı eşleşti.".into()],
        });
    }

    // Minimal forward chaining: "A ise B. A" => infer B.
    let statements: Vec<String> = prompt.split(|c| c == '.' || c == '\n' || c == ';')
        .map(normalize_statement).filter(|s| !s.is_empty()).collect();
    let mut rules: Vec<(String, String)> = Vec::new();
    let mut facts: Vec<String> = Vec::new();
    for statement in &statements {
        if let Some((left, right)) = split_rule(statement) {
            if !left.is_empty() && !right.is_empty() { rules.push((left, right)); }
        } else { facts.push(statement.clone()); }
    }
    for (antecedent, consequent) in &rules {
        if facts.iter().any(|fact| fact == antecedent) {
            return Ok(ReasoningResult {
                answer: format!("Çıkarım: {consequent}."),
                trace: vec![
                    format!("Kural bulundu: '{antecedent}' doğruysa '{consequent}' sonucu çıkar."),
                    format!("Verilen olgu eşleşti: '{antecedent}'."),
                    format!("Modus ponens uygulandı; sonuç: '{consequent}'."),
                ],
            });
        }
    }
    if lower.contains("neden") || lower.contains("nasıl") || lower.contains("düşün") || lower.contains("akıl yürüt") {
        return Ok(ReasoningResult {
            answer: "Bu sürüm bu soruyu güvenilir biçimde çıkarımlayacak kadar bilgi veya kural içermiyor. İlgili olguları ve 'A ise B. A' biçiminde açık bir kuralı verirsen sınırlı çıkarım yapabilirim.".into(),
            trace: vec!["Bilgi/kural eşleşmesi bulunamadı; sistem tahmin uydurmak yerine sınırını belirtti.".into()],
        });
    }
    Ok(ReasoningResult {
        answer: "Bu başlangıç sürümünde bu ifadeye uygun bir kural bulamadım. Şimdilik basit aritmetik ve açık 'A ise B. A' mantık çıkarımını destekliyorum.".into(),
        trace: vec!["Eşleşen kural veya desteklenen aritmetik ifade yok.".into()],
    })
}
fn normalize_statement(s: &str) -> String {
    s.trim().trim_end_matches(&['.', ',', '?', '!', ':'][..]).trim().to_lowercase()
}
fn split_rule(s: &str) -> Option<(String, String)> {
    let (left, right) = s.split_once(" ise ")?;
    Some((normalize_statement(left), normalize_statement(right)))
}
fn arithmetic(s: &str) -> Option<String> {
    let compact: String = s.chars().filter(|c| !c.is_whitespace()).collect();
    for (idx, ch) in compact.char_indices() {
        if idx == 0 && (ch == '-' || ch == '+') { continue; }
        if ['+', '-', '*', '/'].contains(&ch) {
            let left = compact[..idx].parse::<f64>().ok()?;
            let right = compact[idx + ch.len_utf8()..].parse::<f64>().ok()?;
            let value = match ch {
                '+' => left + right, '-' => left - right, '*' => left * right,
                '/' if right != 0.0 => left / right, _ => return None,
            };
            if !value.is_finite() { return None; }
            return Some(if value.fract() == 0.0 { format!("{value:.0}") } else { value.to_string() });
        }
    }
    None
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn derives_conclusion_with_trace() {
        let r = reason("Yağmur yağıyor ise yol ıslaktır. Yağmur yağıyor").unwrap();
        assert_eq!(r.answer, "Çıkarım: yol ıslaktır."); assert_eq!(r.trace.len(), 3);
    }
    #[test] fn computes_arithmetic() { assert_eq!(reason("12 * 3").unwrap().answer, "Sonuç: 36"); }
    #[test] fn rejects_empty_input() { assert_eq!(reason(" ").unwrap_err(), ReasoningError::EmptyInput); }
    #[test] fn admits_limits_instead_of_fabricating() {
        assert!(reason("Neden gökyüzü mavi?").unwrap().answer.contains("güvenilir biçimde"));
    }
}
