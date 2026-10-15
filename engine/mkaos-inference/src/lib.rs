//! MKAOS experimental inference-kernel foundation.
//!
//! This crate deliberately starts with small, auditable CPU tensor primitives.
//! It is NOT yet a complete transformer runtime and does not load existing LLM
//! weights. The next stages must add a versioned model format, tokenizer,
//! transformer blocks, quantized kernels, and differential tests before it can
//! replace any production backend.

#![forbid(unsafe_code)]

use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum KernelError {
    EmptyTensor,
    ShapeMismatch { expected: usize, actual: usize },
    InvalidDimension,
    NonFiniteInput,
}

impl fmt::Display for KernelError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyTensor => write!(f, "tensor must not be empty"),
            Self::ShapeMismatch { expected, actual } =>
                write!(f, "shape mismatch: expected {expected}, got {actual}"),
            Self::InvalidDimension => write!(f, "dimensions must be non-zero"),
            Self::NonFiniteInput => write!(f, "input contains NaN or infinity"),
        }
    }
}

impl std::error::Error for KernelError {}

#[derive(Debug, Clone, PartialEq)]
pub struct Tensor2 {
    rows: usize,
    cols: usize,
    data: Vec<f32>,
}

impl Tensor2 {
    pub fn new(rows: usize, cols: usize, data: Vec<f32>) -> Result<Self, KernelError> {
        if rows == 0 || cols == 0 {
            return Err(KernelError::InvalidDimension);
        }
        let expected = rows.checked_mul(cols).ok_or(KernelError::InvalidDimension)?;
        if data.is_empty() {
            return Err(KernelError::EmptyTensor);
        }
        if data.len() != expected {
            return Err(KernelError::ShapeMismatch { expected, actual: data.len() });
        }
        if data.iter().any(|v| !v.is_finite()) {
            return Err(KernelError::NonFiniteInput);
        }
        Ok(Self { rows, cols, data })
    }

    pub fn rows(&self) -> usize { self.rows }
    pub fn cols(&self) -> usize { self.cols }
    pub fn as_slice(&self) -> &[f32] { &self.data }

    pub fn matmul(&self, rhs: &Self) -> Result<Self, KernelError> {
        if self.cols != rhs.rows {
            return Err(KernelError::ShapeMismatch {
                expected: self.cols,
                actual: rhs.rows,
            });
        }
        let mut out = vec![0.0_f32; self.rows * rhs.cols];
        for i in 0..self.rows {
            for k in 0..self.cols {
                let left = self.data[i * self.cols + k];
                for j in 0..rhs.cols {
                    out[i * rhs.cols + j] += left * rhs.data[k * rhs.cols + j];
                }
            }
        }
        Self::new(self.rows, rhs.cols, out)
    }

    /// Numerically stable row-wise softmax.
    pub fn softmax_rows(&self) -> Result<Self, KernelError> {
        let mut out = self.data.clone();
        for row in out.chunks_exact_mut(self.cols) {
            let max = row.iter().copied().fold(f32::NEG_INFINITY, f32::max);
            let mut sum = 0.0_f32;
            for value in row.iter_mut() {
                *value = (*value - max).exp();
                sum += *value;
            }
            if !sum.is_finite() || sum <= 0.0 {
                return Err(KernelError::NonFiniteInput);
            }
            for value in row.iter_mut() {
                *value /= sum;
            }
        }
        Self::new(self.rows, self.cols, out)
    }

    /// Root-mean-square normalization over each row, with a positive epsilon.
    pub fn rms_norm_rows(&self, epsilon: f32) -> Result<Self, KernelError> {
        if !epsilon.is_finite() || epsilon <= 0.0 {
            return Err(KernelError::NonFiniteInput);
        }
        let mut out = self.data.clone();
        for row in out.chunks_exact_mut(self.cols) {
            let mean_square = row.iter().map(|v| v * v).sum::<f32>() / self.cols as f32;
            let scale = (mean_square + epsilon).sqrt().recip();
            for value in row.iter_mut() {
                *value *= scale;
            }
        }
        Self::new(self.rows, self.cols, out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matrix_multiplication_has_expected_shape_and_values() {
        let a = Tensor2::new(2, 2, vec![1.0, 2.0, 3.0, 4.0]).unwrap();
        let b = Tensor2::new(2, 1, vec![2.0, 1.0]).unwrap();
        let c = a.matmul(&b).unwrap();
        assert_eq!((c.rows(), c.cols()), (2, 1));
        assert_eq!(c.as_slice(), &[4.0, 10.0]);
    }

    #[test]
    fn softmax_rows_sum_to_one() {
        let x = Tensor2::new(2, 3, vec![1000.0, 1001.0, 999.0, 1.0, 1.0, 1.0]).unwrap();
        let y = x.softmax_rows().unwrap();
        for row in y.as_slice().chunks_exact(3) {
            assert!((row.iter().sum::<f32>() - 1.0).abs() < 1e-5);
        }
    }

    #[test]
    fn rms_norm_is_finite_and_shape_preserving() {
        let x = Tensor2::new(1, 3, vec![3.0, 4.0, 0.0]).unwrap();
        let y = x.rms_norm_rows(1e-5).unwrap();
        assert_eq!((y.rows(), y.cols()), (1, 3));
        assert!(y.as_slice().iter().all(|v| v.is_finite()));
    }

    #[test]
    fn rejects_invalid_shape_and_non_finite_values() {
        assert!(matches!(Tensor2::new(2, 2, vec![1.0]), Err(KernelError::ShapeMismatch { .. })));
        assert_eq!(Tensor2::new(1, 1, vec![f32::NAN]).unwrap_err(), KernelError::NonFiniteInput);
    }

    #[test]
    fn rejects_mismatched_matmul_dimensions() {
        let a = Tensor2::new(1, 2, vec![1.0, 2.0]).unwrap();
        let b = Tensor2::new(3, 1, vec![1.0, 2.0, 3.0]).unwrap();
        assert!(a.matmul(&b).is_err());
    }
}
