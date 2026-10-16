use std::io::{self, Read};
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let prompt = if args.is_empty() {
        let mut buffer = String::new();
        if io::stdin().read_to_string(&mut buffer).is_err() {
            eprintln!("Girdi okunamadı."); std::process::exit(2);
        }
        buffer
    } else { args.join(" ") };
    match mkaos_inference::reasoning::reason(&prompt) {
        Ok(result) => {
            println!("{}", result.answer);
            if std::env::var("MKAOS_REASON_TRACE").as_deref() == Ok("1") {
                for (i, step) in result.trace.iter().enumerate() { println!("{}. {}", i + 1, step); }
            }
        }
        Err(err) => { eprintln!("MKAOS yerel çekirdek: {err}"); std::process::exit(2); }
    }
}
