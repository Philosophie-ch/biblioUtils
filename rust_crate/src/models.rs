use std::collections::HashMap;

use pyo3::prelude::*;

pub type Bibkey = String;

#[pyclass]
#[derive(Debug, Clone)]
pub struct RustedBibEntry {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub bibkey: Bibkey,
    #[pyo3(get)]
    pub title: String,
    #[pyo3(get)]
    pub notes: String,
    #[pyo3(get)]
    pub crossref: String,
    #[pyo3(get)]
    pub further_note: String,
    #[pyo3(get)]
    pub further_references: Vec<String>,
    #[pyo3(get)]
    pub depends_on: Vec<String>,
}

#[pymethods]
impl RustedBibEntry {
    #[new]
    fn new(
        id: String,
        bibkey: Bibkey,
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
        }
    }

    fn __str__(&self) -> String {
        format!(
            "RustedBibEntry(id={}, bibkey={}, further_references={:?}, depends_on={:?})",
            self.id, self.bibkey, self.further_references, self.depends_on
        )
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct TransitivelyClosedBibEntry {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub bibkey: Bibkey,
    #[pyo3(get)]
    pub title: String,
    #[pyo3(get)]
    pub notes: String,
    #[pyo3(get)]
    pub crossref: String,
    #[pyo3(get)]
    pub further_note: String,
    #[pyo3(get)]
    pub further_references: String,
    #[pyo3(get)]
    pub depends_on: String,
    #[pyo3(get)]
    pub further_references_closed: String,
    #[pyo3(get)]
    pub depends_on_closed: String,
    #[pyo3(get)]
    pub max_depth_reached: usize,
    #[pyo3(get)]
    pub status: String,
    #[pyo3(get)]
    pub error_message: String,
}

#[pymethods]
impl TransitivelyClosedBibEntry {
    #[new]
    fn new(
        id: String,
        bibkey: Bibkey,
        title: String,
        notes: String,
        crossref: String,
        further_note: String,
        further_references: String,
        depends_on: String,
        further_references_closed: String,
        depends_on_closed: String,
        max_depth_reached: usize,
        status: String,
        error_message: String,
    ) -> Self {
        TransitivelyClosedBibEntry {
            id,
            bibkey,
            title,
            notes,
            crossref,
            further_note,
            further_references,
            depends_on,
            further_references_closed,
            depends_on_closed,
            max_depth_reached,
            status,
            error_message,
        }
    }

    fn __str__(&self) -> String {
        format!(
            "TransitivelyClosedBibEntry(id={}, bibkey={}, further_references={:?}, depends_on={:?})",
            self.id, self.bibkey, self.further_references, self.depends_on
        )
    }

    fn to_dict(&self) -> PyResult<HashMap<String, String>> {
        let mut dict = HashMap::new();
        dict.insert("id".to_string(), self.id.clone());
        dict.insert("bibkey".to_string(), self.bibkey.clone());
        dict.insert("title".to_string(), self.title.clone());
        dict.insert("notes".to_string(), self.notes.clone());
        dict.insert("crossref".to_string(), self.crossref.clone());
        dict.insert("further_note".to_string(), self.further_note.clone());
        dict.insert(
            "further_references".to_string(),
            self.further_references.clone(),
        );
        dict.insert("depends_on".to_string(), self.depends_on.clone());
        dict.insert(
            "further_references_closed".to_string(),
            self.further_references_closed.clone(),
        );
        dict.insert(
            "depends_on_closed".to_string(),
            self.depends_on_closed.clone(),
        );
        dict.insert(
            "max_depth_reached".to_string(),
            self.max_depth_reached.to_string(),
        );
        dict.insert("status".to_string(), self.status.clone());
        dict.insert("error_message".to_string(), self.error_message.clone());
        Ok(dict)
    }
}
