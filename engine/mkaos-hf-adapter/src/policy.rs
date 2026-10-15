//! Short Turkish-first response guidance for the experimental MKAOS generation CLI.
//! Prompt guidance improves consistency but is not a safety guarantee; evaluate actual outputs.
pub const TURKISH_FIRST_SYSTEM_PROMPT: &str = "Önce kullanıcının diliyle, açık ve doğal yanıt ver; Türkçe sorularda doğru Türkçe ve karakterler kullan. Bilmediğin bilgiyi uydurma; belirsizliği ve kaynak erişimi olmadığını açıkça söyle. Kaynak, test, işlem veya güncel kontrol yaptığını iddia etme, gerçekten yapılmadıysa. Tarihsel konuları kanıta dayalı, bağlamlı ve saygılı ele al; meşru eleştirel araştırmayı sırf eleştirel diye reddetme.";

#[cfg(test)]
mod tests {
    use super::TURKISH_FIRST_SYSTEM_PROMPT;

    #[test]
    fn policy_is_turkish_first_and_source_honest() {
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("doğru Türkçe"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("uydurma"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("belirsizliği"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("gerçekten yapılmadıysa"));
    }

    #[test]
    fn policy_preserves_contextual_historical_inquiry() {
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("kanıta dayalı"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("meşru eleştirel araştırmayı"));
    }

    #[test]
    fn policy_is_short_enough_to_reduce_prompt_prefill() {
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.split_whitespace().count() < 60);
    }
}
