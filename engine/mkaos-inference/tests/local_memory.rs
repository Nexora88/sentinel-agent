use mkaos_inference::memory::{FactMemory, RememberOutcome};
use std::fs;

#[test]
fn memory_reports_conflicts_and_keeps_them_until_resolution() {
    let mut memory = FactMemory::new();
    assert_eq!(memory.remember("şehir", "Edirne").unwrap(), RememberOutcome::Added);
    assert!(matches!(memory.remember("ŞEHİR", "İstanbul").unwrap(), RememberOutcome::Conflict { .. }));
    assert_eq!(memory.conflicts().len(), 1);
    memory.resolve("şehir", "Edirne").unwrap();
    assert!(memory.conflicts().is_empty());
}

#[test]
fn memory_round_trip_is_local_and_utf8_safe() {
    let path = std::env::temp_dir().join(format!("mkaos-facts-{}.tsv", std::process::id()));
    let mut memory = FactMemory::new();
    memory.remember("hava", "yağmurlu").unwrap();
    memory.save(&path).unwrap();
    let loaded = FactMemory::load(&path).unwrap();
    let _ = fs::remove_file(path);
    assert_eq!(loaded.as_statements(), vec!["hava yağmurlu"]);
}

#[test]
fn can_forget_a_subject() {
    let mut memory = FactMemory::new();
    memory.remember("hava", "yağmurlu").unwrap();
    assert!(memory.forget("hava"));
    assert!(memory.facts().is_empty());
}
