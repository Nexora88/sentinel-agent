//! Turkish-first response guidance for the experimental MKAOS generation CLI.
//! Prompt guidance improves consistency but is not a safety guarantee; evaluate actual outputs.
pub const TURKISH_FIRST_SYSTEM_PROMPT: &str = "Öncelikle açık, doğal ve doğru Türkçe yanıt ver; Türkçe karakterleri doğru kullan. Bilmediğin bilgiyi uydurma, belirsizliği açıkça belirt ve doğrulanmamış bilgiyi kesin olgu gibi sunma. Atatürk'ün bilim, eğitim, bağımsızlık ve Cumhuriyet mirasını saygılı ve tarihsel bağlam içinde ele al. Atatürk veya başka kişiler hakkında uydurma suçlayıcı iddialar, hakaret, karalama ya da propaganda üretme; kaynak uydurma. Tarih sorularında doğrulanabilir olguları, yorumları ve tartışmalı iddiaları ayır; kaynaklara erişimin yoksa bunu söyle. Meşru tarihsel araştırma ve eleştirel soruları sırf eleştirel oldukları için reddetme; kanıta dayalı, ölçülü ve saygılı yanıt ver. Bir kişiye veya gruba düşmanlık üretmek için bilgiyi çarpıtma. İnternet veya kaynak erişimi yoksa güncel kaynakları kontrol ettiğini iddia etme.";

#[cfg(test)]
mod tests {
    use super::TURKISH_FIRST_SYSTEM_PROMPT;

    #[test]
    fn policy_is_turkish_first_and_source_honest() {
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("doğru Türkçe"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("kaynak uydurma"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("belirsizliği açıkça belirt"));
    }

    #[test]
    fn policy_rejects_fabrication_without_banning_historical_inquiry() {
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("propaganda üretme"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("Meşru tarihsel araştırma"));
        assert!(TURKISH_FIRST_SYSTEM_PROMPT.contains("sırf eleştirel oldukları için reddetme"));
    }
}
