use mkaos_inference::memory::{FactMemory, RememberOutcome};
use std::{io::{self, Read}, path::PathBuf};

fn usage() {
    eprintln!("Kullanım: mkaos-reason [--memory DOSYA] [--remember ÖZNE=DEĞER | --resolve ÖZNE=DEĞER | --forget ÖZNE | --list-facts | --conflicts] [soru]");
}
fn pair(value: &str) -> Result<(&str, &str), String> {
    value.split_once('=').ok_or_else(|| "ÖZNE=DEĞER biçimi gerekli".to_string())
}
fn main() {
    let mut args = std::env::args().skip(1).peekable();
    let mut memory_path: Option<PathBuf> = None;
    let mut action: Option<(String, String)> = None;
    let mut prompt_parts = Vec::new();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--memory" => match args.next() { Some(path) => memory_path = Some(path.into()), None => { usage(); std::process::exit(2); } },
            "--remember" | "--resolve" | "--forget" => {
                let value = match args.next() { Some(v) => v, None => { usage(); std::process::exit(2); } };
                action = Some((arg, value));
            }
            "--list-facts" | "--conflicts" => action = Some((arg, String::new())),
            "--help" | "-h" => { usage(); return; }
            _ => prompt_parts.push(arg),
        }
    }
    let path = memory_path.unwrap_or_else(|| PathBuf::from("mkaos-memory.tsv"));
    let mut memory = match FactMemory::load(&path) {
        Ok(m) => m,
        Err(e) => { eprintln!("Bellek yüklenemedi: {e}"); std::process::exit(2); }
    };
    if let Some((command, value)) = action {
        match command.as_str() {
            "--remember" => {
                let (subject, fact) = match pair(&value) { Ok(p) => p, Err(e) => { eprintln!("{e}"); std::process::exit(2); } };
                match memory.remember(subject, fact) {
                    Ok(RememberOutcome::Added) => println!("Olgu kaydedildi."),
                    Ok(RememberOutcome::Unchanged) => println!("Bu olgu zaten kayıtlı."),
                    Ok(RememberOutcome::Conflict { existing }) => println!("ÇELİŞKİ: önceki değer(ler): {}. Yeni değer de kaydedildi; --resolve ile açıkça seçebilirsin.", existing.join(", ")),
                    Err(e) => { eprintln!("{e}"); std::process::exit(2); }
                }
                if let Err(e) = memory.save(&path) { eprintln!("Bellek kaydedilemedi: {e}"); std::process::exit(2); }
                return;
            }
            "--resolve" => {
                let (subject, fact) = match pair(&value) { Ok(p) => p, Err(e) => { eprintln!("{e}"); std::process::exit(2); } };
                if let Err(e) = memory.resolve(subject, fact).and_then(|_| memory.save(&path)) { eprintln!("Çelişki çözülemedi: {e}"); std::process::exit(2); }
                println!("Seçilen değer korundu ve bellek güncellendi."); return;
            }
            "--forget" => {
                if !memory.forget(&value) { println!("Bu özne bellekte bulunamadı."); return; }
                if let Err(e) = memory.save(&path) { eprintln!("Bellek kaydedilemedi: {e}"); std::process::exit(2); }
                println!("Özneye ait olgular silindi."); return;
            }
            "--list-facts" => {
                for fact in memory.facts() { println!("{} = {}", fact.subject, fact.value); }
                return;
            }
            "--conflicts" => {
                let conflicts = memory.conflicts();
                if conflicts.is_empty() { println!("Çelişki bulunamadı."); }
                for (subject, values) in conflicts { println!("{subject}: {}", values.join(" <> ")); }
                return;
            }
            _ => unreachable!(),
        }
    }
    let mut prompt = prompt_parts.join(" ");
    if prompt.is_empty() {
        let mut buffer = String::new();
        if io::stdin().read_to_string(&mut buffer).is_err() {
            eprintln!("Girdi okunamadı."); std::process::exit(2);
        }
        prompt = buffer;
    }
    for fact in memory.as_statements() { prompt.push_str(". "); prompt.push_str(&fact); }
    match mkaos_inference::reasoning::reason(&prompt) {
        Ok(result) => {
            println!("{}", result.answer);
            if std::env::var("MKAOS_REASON_TRACE").map(|v| v == "1").unwrap_or(false) {
                for (i, step) in result.trace.iter().enumerate() { println!("{}. {}", i + 1, step); }
            }
        }
        Err(err) => { eprintln!("MKAOS yerel çekirdek: {err}"); std::process::exit(2); }
    }
}
