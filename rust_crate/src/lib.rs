use pyo3::prelude::*;

pub mod models;
use models::{RustedBibEntry, TransitivelyClosedBibEntry};

pub mod transitive_closure;
use transitive_closure::{compute_transitive_closures, find_all_repeated_bibentries};

/// Formats the sum of two numbers as string. Test function for this crate that should be callable from python.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_crate(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_class::<RustedBibEntry>()?;
    m.add_class::<TransitivelyClosedBibEntry>()?;
    m.add_function(wrap_pyfunction!(find_all_repeated_bibentries, m)?)?;
    m.add_function(wrap_pyfunction!(compute_transitive_closures, m)?)?;
    Ok(())
}
