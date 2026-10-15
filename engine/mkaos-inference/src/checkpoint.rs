//! Bounded, integrity-checked loader for the documented MKAOSW1 tensor container.
use crate::{sha256, KernelError, Tensor2};
use std::{collections::BTreeMap, fmt, fs::File, io::Read, path::Path};

const MAGIC: &[u8; 8] = b"MKAOSW1\0";
const MAX_TENSORS: usize = 4096;
const MAX_NAME_BYTES: usize = 256;

#[derive(Debug)]
pub enum CheckpointError {
    Io(std::io::Error),
    FileTooLarge,
    InvalidExpectedHash,
    HashMismatch { expected: String, actual: String },
    Malformed(&'static str),
    DuplicateTensor(String),
    Tensor(KernelError),
}
impl fmt::Display for CheckpointError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(e) => write!(f, "checkpoint I/O error: {e}"),
            Self::FileTooLarge => write!(f, "checkpoint exceeds configured byte limit"),
            Self::InvalidExpectedHash => write!(f, "expected SHA-256 must be 64 hexadecimal characters"),
            Self::HashMismatch { expected, actual } => write!(f, "checkpoint SHA-256 mismatch: expected {expected}, got {actual}"),
            Self::Malformed(s) => write!(f, "malformed checkpoint: {s}"),
            Self::DuplicateTensor(n) => write!(f, "duplicate tensor name: {n}"),
            Self::Tensor(e) => write!(f, "invalid tensor: {e}"),
        }
    }
}
impl std::error::Error for CheckpointError {}
impl From<std::io::Error> for CheckpointError { fn from(e: std::io::Error) -> Self { Self::Io(e) } }
impl From<KernelError> for CheckpointError { fn from(e: KernelError) -> Self { Self::Tensor(e) } }

#[derive(Debug)]
pub struct Checkpoint { pub tensors: BTreeMap<String, Tensor2>, pub sha256: String }

/// Read at most max_bytes+1 bytes, verify the whole-file SHA-256 before parsing,
/// then validate all lengths/shapes before allocating tensor payloads.
///
/// Binary layout (little endian):
/// 8-byte magic "MKAOSW1\\0", u32 tensor_count, then repeated:
/// u16 name_len, UTF-8 name, u32 rows, u32 cols, rows*cols IEEE754 f32 values.
pub fn load_checkpoint(path: impl AsRef<Path>, expected_sha256: &str, max_bytes: usize,
                       max_elements_per_tensor: usize) -> Result<Checkpoint, CheckpointError> {
    if expected_sha256.len() != 64 || !expected_sha256.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(CheckpointError::InvalidExpectedHash);
    }
    let file = File::open(path)?;
    let mut bytes = Vec::new();
    file.take((max_bytes as u64).saturating_add(1)).read_to_end(&mut bytes)?;
    if bytes.len() > max_bytes { return Err(CheckpointError::FileTooLarge); }
    let actual = sha256::to_hex(&sha256::sha256(&bytes));
    if !actual.eq_ignore_ascii_case(expected_sha256) {
        return Err(CheckpointError::HashMismatch { expected: expected_sha256.to_ascii_lowercase(), actual });
    }
    let mut cursor = Cursor { bytes: &bytes, pos: 0 };
    if cursor.take(8)? != MAGIC { return Err(CheckpointError::Malformed("bad magic/version")); }
    let count = cursor.u32()? as usize;
    if count == 0 || count > MAX_TENSORS { return Err(CheckpointError::Malformed("invalid tensor count")); }
    let mut tensors = BTreeMap::new();
    for _ in 0..count {
        let name_len = cursor.u16()? as usize;
        if name_len == 0 || name_len > MAX_NAME_BYTES { return Err(CheckpointError::Malformed("invalid tensor name length")); }
        let name = std::str::from_utf8(cursor.take(name_len)?)
            .map_err(|_| CheckpointError::Malformed("tensor name is not UTF-8"))?.to_owned();
        if name.chars().any(char::is_control) { return Err(CheckpointError::Malformed("control character in tensor name")); }
        let rows = cursor.u32()? as usize;
        let cols = cursor.u32()? as usize;
        if rows == 0 || cols == 0 { return Err(CheckpointError::Malformed("zero tensor dimension")); }
        let elements = rows.checked_mul(cols).ok_or(CheckpointError::Malformed("tensor shape overflow"))?;
        if elements > max_elements_per_tensor { return Err(CheckpointError::Malformed("tensor exceeds element limit")); }
        let byte_len = elements.checked_mul(4).ok_or(CheckpointError::Malformed("tensor byte size overflow"))?;
        let raw = cursor.take(byte_len)?;
        let mut values = Vec::with_capacity(elements);
        for b in raw.chunks_exact(4) {
            let value = f32::from_le_bytes([b[0],b[1],b[2],b[3]]);
            if !value.is_finite() { return Err(CheckpointError::Malformed("non-finite weight")); }
            values.push(value);
        }
        let tensor = Tensor2::new(rows, cols, values)?;
        if tensors.insert(name.clone(), tensor).is_some() { return Err(CheckpointError::DuplicateTensor(name)); }
    }
    if cursor.pos != bytes.len() { return Err(CheckpointError::Malformed("trailing bytes")); }
    Ok(Checkpoint { tensors, sha256: actual })
}

struct Cursor<'a> { bytes: &'a [u8], pos: usize }
impl<'a> Cursor<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8], CheckpointError> {
        let end = self.pos.checked_add(n).ok_or(CheckpointError::Malformed("offset overflow"))?;
        if end > self.bytes.len() { return Err(CheckpointError::Malformed("truncated file")); }
        let slice = &self.bytes[self.pos..end]; self.pos = end; Ok(slice)
    }
    fn u16(&mut self) -> Result<u16, CheckpointError> { let b=self.take(2)?; Ok(u16::from_le_bytes([b[0],b[1]])) }
    fn u32(&mut self) -> Result<u32, CheckpointError> { let b=self.take(4)?; Ok(u32::from_le_bytes([b[0],b[1],b[2],b[3]])) }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn rejects_bad_hash_before_parsing() {
        let path = std::env::temp_dir().join(format!("mkaos-bad-checkpoint-{}.bin", std::process::id()));
        std::fs::write(&path, b"not a checkpoint").unwrap();
        let err = load_checkpoint(&path, &"0".repeat(64), 1024, 1024).unwrap_err();
        assert!(matches!(err, CheckpointError::HashMismatch { .. }));
        let _ = std::fs::remove_file(path);
    }
    #[test] fn rejects_invalid_hash_format() {
        let err = load_checkpoint("does-not-need-to-exist", "bad", 1024, 1024).unwrap_err();
        assert!(matches!(err, CheckpointError::InvalidExpectedHash));
    }
}