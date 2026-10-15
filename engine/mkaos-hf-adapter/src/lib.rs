//! Hugging Face tokenizer.json adapter and explicit SmolLM2 chat serialization.
//! The core tensor crate stays dependency-free; this adapter uses the upstream tokenizers
//! implementation so BPE/ByteLevel behavior comes from the pinned tokenizer artifact.
use std::path::Path;
use tokenizers::{Encoding, Tokenizer};
type TokenizerError = Box<dyn std::error::Error + Send + Sync>;

#[derive(Debug)]
pub enum AdapterError {
    Tokenizer(TokenizerError),
    InvalidRole(String),
    EmptyMessages,
}
impl std::fmt::Display for AdapterError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Tokenizer(e) => write!(f, "tokenizer error: {e}"),
            Self::InvalidRole(r) => write!(f, "unsupported chat role: {r}"),
            Self::EmptyMessages => write!(f, "chat must contain at least one message"),
        }
    }
}
impl std::error::Error for AdapterError {}
impl From<TokenizerError> for AdapterError {
    fn from(value: TokenizerError) -> Self { Self::Tokenizer(value) }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}
impl ChatMessage {
    pub fn new(role: impl Into<String>, content: impl Into<String>) -> Self {
        Self { role: role.into(), content: content.into() }
    }
}

pub struct HuggingFaceTokenizer {
    inner: Tokenizer,
}
impl HuggingFaceTokenizer {
    /// Load the exact tokenizer.json fetched from the immutable model revision.
    pub fn from_file(path: impl AsRef<Path>) -> Result<Self, AdapterError> {
        Ok(Self { inner: Tokenizer::from_file(path)? })
    }

    /// Use the upstream tokenizer implementation, including its model, normalizer,
    /// pre-tokenizer, BPE merges, added tokens and post-processor.
    pub fn encode(&self, text: &str) -> Result<Vec<u32>, AdapterError> {
        Ok(self.inner.encode(text, false)?.get_ids().to_vec())
    }

    pub fn encode_chat(&self, messages: &[ChatMessage], add_generation_prompt: bool)
        -> Result<Vec<u32>, AdapterError> {
        let rendered = render_smollm2_chat(messages, add_generation_prompt)?;
        self.encode(&rendered)
    }

    pub fn decode(&self, ids: &[u32], skip_special_tokens: bool) -> Result<String, AdapterError> {
        Ok(self.inner.decode(ids, skip_special_tokens)?)
    }

    pub fn encode_with_offsets(&self, text: &str) -> Result<Encoding, AdapterError> {
        Ok(self.inner.encode(text, false)?)
    }
}

/// SmolLM2's documented message framing: <|im_start|>{role}\n{content}<|im_end|>\n.
/// This deliberately supports only plain-text messages; tool calls and multimodal payloads
/// are rejected/not represented instead of being silently serialized incorrectly.
pub fn render_smollm2_chat(messages: &[ChatMessage], add_generation_prompt: bool)
    -> Result<String, AdapterError> {
    if messages.is_empty() { return Err(AdapterError::EmptyMessages); }
    let mut rendered = String::new();
    for message in messages {
        match message.role.as_str() {
            "system" | "user" | "assistant" => {}
            other => return Err(AdapterError::InvalidRole(other.to_owned())),
        }
        rendered.push_str("<|im_start|>");
        rendered.push_str(&message.role);
        rendered.push('\n');
        rendered.push_str(&message.content);
        rendered.push_str("<|im_end|>\n");
    }
    if add_generation_prompt { rendered.push_str("<|im_start|>assistant\n"); }
    Ok(rendered)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn serializes_system_user_and_assistant_prefix() {
        let messages = [
            ChatMessage::new("system", "Kısa ve doğru yanıt ver."),
            ChatMessage::new("user", "Merhaba"),
        ];
        assert_eq!(render_smollm2_chat(&messages, true).unwrap(),
            "<|im_start|>system\nKısa ve doğru yanıt ver.<|im_end|>\n<|im_start|>user\nMerhaba<|im_end|>\n<|im_start|>assistant\n");
    }
    #[test]
    fn rejects_unsupported_roles_and_empty_chat() {
        assert!(matches!(render_smollm2_chat(&[], false), Err(AdapterError::EmptyMessages)));
        assert!(matches!(render_smollm2_chat(&[ChatMessage::new("tool", "x")], false),
            Err(AdapterError::InvalidRole(_))));
    }
}
