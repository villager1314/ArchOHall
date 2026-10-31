// Isolate the production module's embedded release manifest from Portal's tree.
// All implementation logic and unit tests still come from the real source.
use std::{env, fs, path::PathBuf};
fn main() {
    let here = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap());
    let source = here.join("../provisioning.rs");
    let fixture = here.join("runtime-fixture.json");
    println!("cargo:rerun-if-changed={}", source.display());
    println!("cargo:rerun-if-changed={}", fixture.display());
    let text = fs::read_to_string(source).unwrap();
    let needle = "include_str!(\"../../assets/debian-runtime.json\")";
    assert_eq!(text.matches(needle).count(), 1, "Production manifest embedding changed; review the test harness");
    let text = text.replace(needle, &format!("include_str!({:?})", fixture));
    // include! expands inside a module; retain module documentation as comments.
    let text = text.lines().map(|line| line.strip_prefix("//!").map_or_else(|| line.to_owned(), |rest| format!("//{rest}"))).collect::<Vec<_>>().join("\n");
    fs::write(PathBuf::from(env::var_os("OUT_DIR").unwrap()).join("provisioning.rs"), text).unwrap();
}
