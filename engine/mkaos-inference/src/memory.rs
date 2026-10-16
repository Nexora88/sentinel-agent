//! Small local fact store. It uses a transparent, dependency-free hex TSV format.
//! No networking, telemetry, or external model calls occur here.
use std::{collections::BTreeMap, fs, io, path::Path};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fact { pub subject: String, pub value: String }

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RememberOutcome { Added, Unchanged, Conflict { existing: Vec<String> } }

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MemoryError { EmptyField, InvalidFormat(usize), Io(String) }
impl std::fmt::Display for MemoryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyField => write!(f, "özne ve değer boş olamaz"),
            Self::InvalidFormat(line) => write!(f, "bellek dosyası biçim hatası (satır {line})"),
            Self::Io(message) => write!(f, "bellek dosyası hatası: {message}"),
        }
    }
}
impl std::error::Error for MemoryError {}
impl From<io::Error> for MemoryError { fn from(e: io::Error) -> Self { Self::Io(e.to_string()) } }

/// Facts are keyed by normalized subject. Conflicting values are retained until explicit resolution.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FactMemory { facts: BTreeMap<String, BTreeMap<String, String>> }

impl FactMemory {
    pub fn new() -> Self { Self::default() }

    pub fn load(path: impl AsRef<Path>) -> Result<Self, MemoryError> {
        let path = path.as_ref();
        if !path.exists() { return Ok(Self::new()); }
        let data = fs::read_to_string(path)?;
        let mut memory = Self::new();
        for (index, line) in data.lines().enumerate() {
            if line.trim().is_empty() { continue; }
            let mut fields = line.split('\t');
            let subject = fields.next().and_then(decode_hex).ok_or(MemoryError::InvalidFormat(index + 1))?;
            let value = fields.next().and_then(decode_hex).ok_or(MemoryError::InvalidFormat(index + 1))?;
            if fields.next().is_some() || subject.trim().is_empty() || value.trim().is_empty() {
                return Err(MemoryError::InvalidFormat(index + 1));
            }
            memory.facts.entry(normalize(&subject)).or_default().insert(normalize(&value), value);
        }
        Ok(memory)
    }

    pub fn save(&self, path: impl AsRef<Path>) -> Result<(), MemoryError> {
        let path = path.as_ref();
        if let Some(parent) = path.parent() { if !parent.as_os_str().is_empty() { fs::create_dir_all(parent)?; } }
        let mut out = String::new();
        for (subject_key, values) in &self.facts {
            for value in values.values() {
                // Preserve display spelling for subjects using a matching normalized representation.
                let subject = self.display_subject(subject_key);
                out.push_str(&encode_hex(&subject)); out.push('\t'); out.push_str(&encode_hex(value)); out.push('\n');
            }
        }
        let tmp = path.with_extension("tmp");
        fs::write(&tmp, out)?;
        fs::rename(tmp, path)?;
        Ok(())
    }

    fn display_subject(&self, normalized: &str) -> String { normalized.to_string() }

    pub fn remember(&mut self, subject: &str, value: &str) -> Result<RememberOutcome, MemoryError> {
        if subject.trim().is_empty() || value.trim().is_empty() { return Err(MemoryError::EmptyField); }
        let subject_key = normalize(subject);
        let value_key = normalize(value);
        let values = self.facts.entry(subject_key).or_default();
        if values.contains_key(&value_key) { return Ok(RememberOutcome::Unchanged); }
        if !values.is_empty() {
            let existing = values.values().cloned().collect();
            values.insert(value_key, value.trim().to_string());
            return Ok(RememberOutcome::Conflict { existing });
        }
        values.insert(value_key, value.trim().to_string());
        Ok(RememberOutcome::Added)
    }

    /// Explicitly resolves a conflict by keeping only the chosen value.
    pub fn resolve(&mut self, subject: &str, chosen_value: &str) -> Result<(), MemoryError> {
        if subject.trim().is_empty() || chosen_value.trim().is_empty() { return Err(MemoryError::EmptyField); }
        let key = normalize(subject);
        let value_key = normalize(chosen_value);
        let values = self.facts.get_mut(&key).ok_or(MemoryError::EmptyField)?;
        let chosen = values.get(&value_key).cloned().unwrap_or_else(|| chosen_value.trim().to_string());
        values.clear();
        values.insert(value_key, chosen);
        Ok(())
    }

    pub fn forget(&mut self, subject: &str) -> bool { self.facts.remove(&normalize(subject)).is_some() }

    pub fn facts(&self) -> Vec<Fact> {
        self.facts.iter().flat_map(|(subject, values)| values.values().map(move |value| Fact {
            subject: subject.clone(), value: value.clone()
        })).collect()
    }

    pub fn conflicts(&self) -> Vec<(String, Vec<String>)> {
        self.facts.iter().filter(|(_, values)| values.len() > 1)
            .map(|(subject, values)| (subject.clone(), values.values().cloned().collect())).collect()
    }

    pub fn as_statements(&self) -> Vec<String> {
        self.facts().into_iter().map(|f| format!("{} {}", f.subject, f.value)).collect()
    }
}

fn normalize(value: &str) -> String {
    value.trim().replace('İ', "i").replace('I', "ı").to_lowercase()
}
fn encode_hex(value: &str) -> String { value.as_bytes().iter().map(|b| format!("{b:02x}")).collect() }
fn decode_hex(value: &str) -> Option<String> {
    if value.len() % 2 != 0 { return None; }
    let bytes: Option<Vec<u8>> = value.as_bytes().chunks_exact(2).map(|pair| {
        let hi = (pair[0] as char).to_digit(16)?;
        let lo = (pair[1] as char).to_digit(16)?;
        Some(((hi << 4) | lo) as u8)
    }).collect();
    String::from_utf8(bytes?).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn detects_conflict_and_resolves_explicitly() {
        let mut memory = FactMemory::new();
        assert_eq!(memory.remember("Başkent", "Ankara").unwrap(), RememberOutcome::Added);
        assert!(matches!(memory.remember("BAŞKENT", "İstanbul").unwrap(), RememberOutcome::Conflict { .. }));
        assert_eq!(memory.conflicts().len(), 1);
        memory.resolve("başkent", "Ankara").unwrap();
        assert!(memory.conflicts().is_empty());
        assert_eq!(memory.facts()[0].value, "Ankara");
    }
    #[test] fn persists_utf8_facts() {
        let path = std::env::temp_dir().join(format!("mkaos-memory-{}.tsv", std::process::id()));
        let mut memory = FactMemory::new();
        memory.remember("hava", "yağmurlu").unwrap();
        memory.save(&path).unwrap();
        let loaded = FactMemory::load(&path).unwrap();
        let _ = fs::remove_file(path);
        assert_eq!(loaded.facts()[0].value, "yağmurlu");
    }
    #[test] fn refuses_empty_fields() { assert_eq!(FactMemory::new().remember("", "x"), Err(MemoryError::EmptyField)); }
}
