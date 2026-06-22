//! Tonalis — a generic, format-agnostic music-harmony DSL: parse · lint · chord-grammar · AST · AST→JSON.
//!
//! This crate is the pure language core — it contains NO notation-format SCRUBBED, URL assembly, or
//! body renderer; format-specific codecs live in separate adapter crates. It is the Rust port of
//! the polyglot conformance spec, mirroring the Python and TypeScript members.
//!
//! Public surface mirrors the other ports: [`parse_dsl`], [`lint`], [`is_valid_chord`],
//! [`ast::ast_to_json`], [`ast::ast_from_json`], [`serialize_text`]. All sub-modules are public for
//! testing and downstream reuse.

pub mod ast;
pub mod chord_grammar;
pub mod lint;
pub mod parser;
pub mod serialize_text;

// Re-exports mirroring the TS/Python ports' pure public surface.
pub use ast::{ast_from_json, ast_to_json, SCHEMA_VERSION};
pub use chord_grammar::is_valid_chord;
pub use lint::lint;
pub use parser::parse_dsl;
pub use serialize_text::serialize_text;
