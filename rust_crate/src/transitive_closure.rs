use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

use crate::models::{Bibkey, RustedBibEntry, TransitivelyClosedBibEntry};

#[pyfunction]
pub fn find_all_repeated_bibentries(entries: Vec<RustedBibEntry>) -> Vec<RustedBibEntry> {
    let mut bibkeys = HashSet::new();
    let mut repeated_entries = Vec::new();
    for entry in entries {
        if bibkeys.contains(&entry.bibkey) {
            repeated_entries.push(entry.clone());
        }
        bibkeys.insert(entry.bibkey.clone());
    }
    repeated_entries
}

fn hset_s(hmap: &HashSet<String>, bibkey: &str) -> String {
    return hmap
        .iter()
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .filter(|s| s != &bibkey)
        .map(|s| s.to_string())
        .collect::<Vec<_>>()
        .join(",");
}

pub fn t_close(
    bibkey: &str,
    entries_map: &HashMap<Bibkey, &RustedBibEntry>,
    memo: &mut HashMap<Bibkey, TransitivelyClosedBibEntry>,
) -> TransitivelyClosedBibEntry {
    // Get the initial bibentry; if not found, return an error entry
    let bibentry = match entries_map.get(bibkey) {
        Some(entry) => *entry,
        None => {
            return TransitivelyClosedBibEntry {
                bibkey: bibkey.to_string(),
                title: "missing".to_string(),
                notes: "missing".to_string(),
                crossref: "missing".to_string(),
                further_note: "missing".to_string(),
                further_references: "".to_string(),
                depends_on: "".to_string(),
                further_references_closed: "".to_string(),
                depends_on_closed: "".to_string(),
                max_depth_reached: 0,
                status: "error".to_string(),
                error_message: "Bibkey not found in the provided array of bibentries".to_string(),
            }
        }
    };

    // If closure is already computed, then return
    if let Some(cached_closure) = memo.get(bibkey) {
        return cached_closure.clone();
    }

    // Initialize closure sets and variables for tracking depth
    let mut fr_closure = HashSet::new();
    let mut do_closure = HashSet::new();
    let mut fr_stack = VecDeque::new();
    let mut do_stack = VecDeque::new();

    fr_stack.push_back((bibkey.to_string(), 0));
    do_stack.push_back((bibkey.to_string(), 0));

    let mut max_depth_reached = 0;

    while let Some((current, current_depth)) = fr_stack.pop_front() {
        // Check if the current bibkey is already visited
        let mut visited = HashSet::new();
        if visited.contains(&current) {
            continue;
        }
        visited.insert(current.clone());

        // Compute the closure
        if let Some(entry) = entries_map.get(&current) {
            for ref_key in &entry.further_references {
                if fr_closure.insert(ref_key.clone()) {
                    fr_stack.push_back((ref_key.clone(), current_depth + 1));
                }
            }
        }
        max_depth_reached = max_depth_reached.max(current_depth);
    }

    while let Some((current, current_depth)) = do_stack.pop_front() {
        // Check if the current bibkey is already visited
        let mut visited = HashSet::new();
        if visited.contains(&current) {
            continue;
        }
        visited.insert(current.clone());

        // Compute the closure
        if let Some(entry) = entries_map.get(&current) {
            for dep_key in &entry.depends_on {
                if do_closure.insert(dep_key.clone()) {
                    do_stack.push_back((dep_key.clone(), current_depth + 1));
                }
            }
        }
        max_depth_reached = max_depth_reached.max(current_depth);
    }

    // Convert closures to strings
    let further_references_closed = hset_s(&fr_closure, &bibkey);
    let depends_on_closed = hset_s(&do_closure, &bibkey);

    // Create the closure entry
    let closed_entry = TransitivelyClosedBibEntry {
        bibkey: bibentry.bibkey.clone(),
        title: bibentry.title.clone(),
        notes: bibentry.notes.clone(),
        crossref: bibentry.crossref.clone(),
        further_note: bibentry.further_note.clone(),
        further_references: bibentry.further_references.clone().join(","),
        depends_on: bibentry.depends_on.clone().join(","),
        further_references_closed: further_references_closed.clone(),
        depends_on_closed: depends_on_closed.clone(),
        max_depth_reached,
        status: "success".to_string(),
        error_message: "".to_string(),
    };

    // Cache the result
    memo.insert(bibkey.to_string(), closed_entry.clone());

    closed_entry
}

#[pyfunction]
pub fn compute_transitive_closures(
    entries: Vec<RustedBibEntry>,
    py: Python<'_>,
) -> PyResult<Vec<TransitivelyClosedBibEntry>> {
    py.check_signals()?;

    // Build a HashMap for quick lookup of entries by bibkey
    let entries_map: HashMap<Bibkey, &RustedBibEntry> =
        entries.iter().map(|e| (e.bibkey.clone(), e)).collect();

    let mut memo = HashMap::new();
    let mut closed_entries = Vec::new();

    for entry in &entries {
        let closed_entry = t_close(&entry.bibkey, &entries_map, &mut memo);
        closed_entries.push(closed_entry);
    }

    Ok(closed_entries)
}

/// Testing
#[cfg(test)]
fn create_rusted_bibentry(
    bibkey: &str,
    further_references: Vec<&str>,
    depends_on: Vec<&str>,
) -> RustedBibEntry {
    RustedBibEntry {
        bibkey: bibkey.to_string(),
        title: bibkey.to_string(),
        notes: bibkey.to_string(),
        crossref: bibkey.to_string(),
        further_note: bibkey.to_string(),
        further_references: further_references.iter().map(|s| s.to_string()).collect(),
        depends_on: depends_on.iter().map(|s| s.to_string()).collect(),
    }
}

#[test]
fn test_direct_cycle() {
    // A -> A (self-referencing)
    let mut entries = HashMap::new();
    let binding = create_rusted_bibentry("A", vec!["A"], vec!["A"]);
    entries.insert("A".to_string(), &binding);

    let mut memo = HashMap::new();
    let result = t_close("A", &entries, &mut memo);

    assert_eq!(
        result.max_depth_reached, 1,
        "Direct cycle should only reach depth of 1"
    );
    assert!(
        !result.further_references_closed.contains("A"),
        "Bibkey 'A' should not reference itself in closure"
    );
}

#[test]
fn test_indirect_cycle() {
    // A -> B -> C -> A (indirect cycle)
    let mut entries = HashMap::new();
    let binding_a = create_rusted_bibentry("A", vec!["B"], vec!["B"]);
    let binding_b = create_rusted_bibentry("B", vec!["C"], vec!["C"]);
    let binding_c = create_rusted_bibentry("C", vec!["A"], vec!["A"]);
    entries.insert("A".to_string(), &binding_a);
    entries.insert("B".to_string(), &binding_b);
    entries.insert("C".to_string(), &binding_c);

    let mut memo = HashMap::new();
    let result = t_close("A", &entries, &mut memo);

    assert!(
        result.max_depth_reached > 0,
        "Indirect cycle should not lead to infinite depth"
    );
    assert!(
        result.further_references_closed.contains("B"),
        "Closure should contain B"
    );
    assert!(
        result.further_references_closed.contains("C"),
        "Closure should contain C"
    );
    assert!(
        !result.further_references_closed.contains("A"),
        "Closure should not contain A"
    );
    assert!(
        result.depends_on_closed.contains("B"),
        "Closure should contain B"
    );
    assert!(
        result.depends_on_closed.contains("C"),
        "Closure should contain C"
    );
    assert!(
        !result.depends_on_closed.contains("A"),
        "Closure should not contain A"
    );
}

#[test]
fn test_mixed_cycle_and_non_cycle() {
    // A -> B -> C, C -> D (Cyclic path) and D -> E (Acyclic path)
    let mut entries = HashMap::new();
    let entry_a = create_rusted_bibentry("A", vec!["B"], vec![]);
    let entry_b = create_rusted_bibentry("B", vec!["C"], vec![]);
    let entry_c = create_rusted_bibentry("C", vec!["A", "D"], vec![]);
    let entry_d = create_rusted_bibentry("D", vec!["E"], vec![]);
    let entry_e = create_rusted_bibentry("E", vec![], vec![]);

    entries.insert("A".to_string(), &entry_a);
    entries.insert("B".to_string(), &entry_b);
    entries.insert("C".to_string(), &entry_c);
    entries.insert("D".to_string(), &entry_d);
    entries.insert("E".to_string(), &entry_e);

    let mut memo = HashMap::new();
    let result = t_close("A", &entries, &mut memo);

    // Verify closure contains all non-cyclic entries
    assert!(
        result.further_references_closed.contains("D"),
        "Closure should contain D from acyclic path"
    );
    assert!(
        result.further_references_closed.contains("E"),
        "Closure should contain E from acyclic path"
    );

    // Verify max depth does not grow indefinitely
    assert!(
        result.max_depth_reached > 0 && result.max_depth_reached <= 4,
        "Max depth should not exceed acyclic path length"
    );
}

#[test]
fn test_no_cycle() {
    // Simple acyclic references A -> B -> C
    let mut entries = HashMap::new();
    let entry_a = create_rusted_bibentry("A", vec!["B"], vec![]);
    let entry_b = create_rusted_bibentry("B", vec!["C"], vec![]);
    let entry_c = create_rusted_bibentry("C", vec![], vec![]);
    entries.insert("A".to_string(), &entry_a);
    entries.insert("B".to_string(), &entry_b);
    entries.insert("C".to_string(), &entry_c);

    let mut memo = HashMap::new();
    let result = t_close("A", &entries, &mut memo);

    assert_eq!(
        result.max_depth_reached, 2,
        "Acyclic path A->B->C should reach max depth of 2"
    );
    assert!(
        result.further_references_closed.contains("B"),
        "Closure should contain B"
    );
    assert!(
        result.further_references_closed.contains("C"),
        "Closure should contain C"
    );
}
