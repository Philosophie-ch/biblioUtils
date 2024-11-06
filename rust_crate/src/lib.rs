use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

/// Formats the sum of two numbers as string. Test function for this crate.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct RustedBibEntry {
    #[pyo3(get)]
    id: String,
    #[pyo3(get)]
    bibkey: String,
    #[pyo3(get)]
    title: String,
    #[pyo3(get)]
    notes: String,
    #[pyo3(get)]
    crossref: String,
    #[pyo3(get)]
    further_note: String,
    #[pyo3(get)]
    further_references: Vec<String>,
    #[pyo3(get)]
    depends_on: Vec<String>,
    #[pyo3(get)]
    further_references_closed: HashSet<String>,
    #[pyo3(get)]
    depends_on_closed: HashSet<String>,
}

#[pymethods]
impl RustedBibEntry {
    #[new]
    fn new(
        id: String,
        bibkey: String,
        title: String,
        notes: String,
        crossref: String,
        further_note: String,
        further_references: Vec<String>,
        depends_on: Vec<String>,
    ) -> Self {
        RustedBibEntry {
            id,
            bibkey,
            title,
            notes,
            crossref,
            further_note,
            further_references,
            depends_on,
            further_references_closed: HashSet::new(),
            depends_on_closed: HashSet::new(),
        }
    }

    fn __str__(&self) -> String {
        format!(
            "RustedBibEntry(id={}, bibkey = {}, further_references = {:?}, depends_on = {:?})",
            self.id, self.bibkey, self.further_references, self.depends_on
        )
    }
}

type RustedBibEntryMap = HashMap<String, RustedBibEntry>;

fn compute_transitive_closure(
    bibkey: &str,
    entries: &RustedBibEntryMap,
    field: &str,
    memo: &mut HashMap<String, HashSet<String>>,
    depth: usize,
    max_depth: usize,
) -> HashSet<String> {
    // If closure is already computed, then return
    if let Some(cached_closure) = memo.get(bibkey) {
        return cached_closure.clone();
    }

    // Check if recursion depth is within limits
    if depth > max_depth {
        // Return empty set, indicating a potential infinite loop
        return HashSet::new();
    }

    // Initialize closure set; also, BFS to collect all reachable bibkeys
    let mut closure = HashSet::new();
    let mut stack = VecDeque::new();
    stack.push_back((bibkey.to_string(), depth));

    while let Some((current, current_depth)) = stack.pop_front() {
        // If entry exists in the map...
        if let Some(entry) = entries.get(&current) {
            // Explore its relevant field and choose the appropriate set
            let references = match field {
                "further_references" => &entry.further_references,
                "depends_on" => &entry.depends_on,
                _ => panic!("Invalid field"),
            };

            for ref_key in references {
                // Only add new references
                if !closure.contains(ref_key) {
                    closure.insert(ref_key.clone());
                    stack.push_back((ref_key.clone(), current_depth + 1));
                }
            }
        }
    }

    // Cache the result
    memo.insert(bibkey.to_string(), closure.clone());

    closure
}

#[pyfunction]
fn compute_transitive_closures(
    entries: RustedBibEntryMap,
    max_depth: usize,
) -> PyResult<(
    HashMap<String, HashSet<String>>,
    HashMap<String, HashSet<String>>,
)> {
    let mut further_references_memo = HashMap::new();
    let mut depends_on_memo = HashMap::new();

    let keys: Vec<String> = entries.keys().cloned().collect();
    for bibkey in keys {
        let further_references_closed = compute_transitive_closure(
            &bibkey,
            &entries,
            "further_references",
            &mut further_references_memo,
            0,
            max_depth,
        );

        let depends_on_closed = compute_transitive_closure(
            &bibkey,
            &entries,
            "depends_on",
            &mut depends_on_memo,
            0,
            max_depth,
        );

        further_references_memo.insert(bibkey.clone(), further_references_closed);
        depends_on_memo.insert(bibkey.clone(), depends_on_closed);
    }

    Ok((further_references_memo, depends_on_memo))
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_crate(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_class::<RustedBibEntry>()?;
    m.add_function(wrap_pyfunction!(compute_transitive_closures, m)?)?;
    Ok(())
}
