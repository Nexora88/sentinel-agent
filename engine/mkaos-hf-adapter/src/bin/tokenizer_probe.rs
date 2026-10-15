use mkaos_hf_adapter::{render_smollm2_chat, ChatMessage, HuggingFaceTokenizer};
use std::env;
use std::process;

fn main() {
    let mut args = env::args().skip(1);
    let Some(tokenizer_path) = args.next() else {
        eprintln!("usage: tokenizer_probe <tokenizer.json> <text>... | --chat-template");
        process::exit(2);
    };
    let rest: Vec<String> = args.collect();
    if rest.first().map(String::as_str) == Some("--chat-template") {
        let messages = [
            ChatMessage::new("system", "Answer briefly and accurately."),
            ChatMessage::new("user", "Merhaba, how are you?"),
        ];
        match render_smollm2_chat(&messages, true) {
            Ok(rendered) => println!("{rendered}"),
            Err(error) => { eprintln!("{error}"); process::exit(1); }
        }
        return;
    }
    if rest.is_empty() {
        eprintln!("provide at least one text to tokenize");
        process::exit(2);
    }
    let tokenizer = match HuggingFaceTokenizer::from_file(tokenizer_path) {
        Ok(tokenizer) => tokenizer,
        Err(error) => { eprintln!("{error}"); process::exit(1); }
    };
    for text in rest {
        match tokenizer.encode(&text) {
            Ok(ids) => println!("{}", ids.iter().map(u32::to_string).collect::<Vec<_>>().join(",")),
            Err(error) => { eprintln!("{error}"); process::exit(1); }
        }
    }
}
